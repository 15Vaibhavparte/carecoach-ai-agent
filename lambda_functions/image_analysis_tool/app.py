"""
Main Lambda handler for the Image Analysis Tool.
This module provides the core Lambda function that orchestrates the complete workflow:
image → vision analysis → drug information → response synthesis.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Tuple

# Import our modules
from models import (
    ImageAnalysisRequest, 
    MedicationIdentification, 
    VisionModelResponse,
    ImageAnalysisError,
    ImageValidationError,
    VisionModelError,
    DrugInfoError
)
from config import config
from image_preprocessing import convert_base64_to_optimized_image, assess_image_quality_from_base64
from vision_client import VisionModelClient, MedicationExtractor
from drug_info_integration import get_drug_information
from response_synthesis import combine_results, format_bedrock_response, create_error_response
from error_handling import handle_lambda_error, ErrorContext
from monitoring import (
    structured_logger, 
    create_performance_monitor, 
    log_request_start, 
    log_request_end,
    TimingContext
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = structured_logger

def lambda_handler(event, context):
    """
    Main Lambda handler for medication image analysis.
    
    This function orchestrates the complete workflow:
    1. Parse and validate input
    2. Process image and assess quality
    3. Analyze image with vision model
    4. Extract medication information
    5. Retrieve drug information
    6. Synthesize and format response
    
    Args:
        event: Lambda event containing image data and parameters
        context: Lambda context object
        
    Returns:
        Bedrock Agent compatible response
    """
    # Initialize monitoring and logging
    request_id = log_request_start(event, context, logger)
    monitor = create_performance_monitor(request_id)
    
    start_time = time.time()
    success = False
    final_response = None
    
    try:
        # Step 1: Parse request and extract parameters
        with TimingContext(monitor, "request_parsing") as stage:
            logger.info("Starting medication image analysis", request_id=request_id)
            image_data, prompt = parse_request(event)
            
            stage.metadata.update({
                'has_image_data': bool(image_data),
                'prompt_length': len(prompt) if prompt else 0
            })
            
            if not image_data:
                logger.warning("No image data found in request", request_id=request_id)
                final_response = create_error_response(
                    "No image data provided. Please upload an image of the medication.",
                    event,
                    "validation_error"
                )
                return final_response
        
        # Step 2: Validate and preprocess image
        with TimingContext(monitor, "image_preprocessing") as stage:
            logger.info("Validating and preprocessing image", request_id=request_id)
            processed_image_data = validate_and_preprocess_image(image_data)
            
            # Record image size metrics
            original_size = len(image_data) * 3 // 4  # Approximate original size
            processed_size = len(processed_image_data) * 3 // 4
            
            monitor.record_gauge("image_original_size", original_size, "bytes")
            monitor.record_gauge("image_processed_size", processed_size, "bytes")
            monitor.record_gauge("image_compression_ratio", 
                               processed_size / max(original_size, 1), "ratio")
            
            stage.metadata.update({
                'original_size_bytes': original_size,
                'processed_size_bytes': processed_size,
                'compression_ratio': processed_size / max(original_size, 1)
            })
        
        # Step 3: Analyze image with vision model
        with TimingContext(monitor, "vision_analysis") as stage:
            logger.info("Analyzing image with vision model", request_id=request_id)
            vision_results = analyze_image_with_vision_model(processed_image_data, prompt)
            
            # Record vision analysis metrics
            confidence = vision_results.get('confidence', 0)
            monitor.record_gauge("vision_confidence", confidence, "score")
            monitor.record_counter("vision_analysis_requests", 1, 
                                 {'success': str(bool(vision_results.get('medication_name')))})
            
            stage.metadata.update({
                'medication_identified': bool(vision_results.get('medication_name')),
                'confidence_score': confidence,
                'image_quality': vision_results.get('image_quality', 'unknown')
            })
        
        # Step 4: Get drug information if medication was identified
        drug_info_results = {}
        medication_name = vision_results.get('medication_name')
        confidence = vision_results.get('confidence', 0)
        
        if medication_name and confidence > config.LOW_CONFIDENCE_THRESHOLD:
            with TimingContext(monitor, "drug_info_lookup") as stage:
                logger.info(f"Getting drug information for: {medication_name}", request_id=request_id)
                drug_info_results = get_drug_information(medication_name, event)
                
                # Record drug info metrics
                monitor.record_counter("drug_info_requests", 1, 
                                     {'success': str(drug_info_results.get('success', False))})
                
                stage.metadata.update({
                    'medication_name': medication_name,
                    'drug_info_found': drug_info_results.get('success', False)
                })
        else:
            logger.info("Skipping drug info lookup due to low confidence or no medication identified", 
                       request_id=request_id)
            drug_info_results = {
                'success': False,
                'error': 'Medication identification confidence too low for drug lookup',
                'drug_info': None
            }
            
            monitor.record_counter("drug_info_skipped", 1, 
                                 {'reason': 'low_confidence' if medication_name else 'no_medication'})
        
        # Step 5: Combine results and create response
        with TimingContext(monitor, "response_synthesis") as stage:
            logger.info("Synthesizing final response", request_id=request_id)
            combined_results = combine_results(vision_results, drug_info_results, event)
            
            stage.metadata.update({
                'response_success': combined_results.get('success', False),
                'has_drug_info': bool(combined_results.get('drug_information', {}).get('available'))
            })
        
        # Step 6: Format as Bedrock Agent response
        with TimingContext(monitor, "response_formatting") as stage:
            final_response = format_bedrock_response(combined_results, event)
            
            # Add processing time and monitoring metadata
            processing_time = time.time() - start_time
            
            if 'response' in final_response and 'responseBody' in final_response['response']:
                response_body = json.loads(final_response['response']['responseBody']['application/json']['body'])
                response_body['processing_time'] = processing_time
                response_body['request_id'] = request_id
                
                # Add performance metrics to response
                response_body['performance_metrics'] = {
                    'total_processing_time': processing_time,
                    'stage_count': len(monitor.stages),
                    'successful_stages': sum(1 for s in monitor.stages if s.success)
                }
                
                final_response['response']['responseBody']['application/json']['body'] = json.dumps(response_body)
            
            stage.metadata.update({
                'total_processing_time': processing_time,
                'response_size_bytes': len(json.dumps(final_response))
            })
        
        # Record overall success metrics
        monitor.record_counter("requests_total", 1, {'success': 'true'})
        monitor.record_timer("request_duration", processing_time)
        
        success = True
        logger.info(f"Image analysis completed successfully in {processing_time:.2f} seconds", 
                   request_id=request_id)
        
        return final_response
        
    except Exception as e:
        # Record failure metrics
        monitor.record_counter("requests_total", 1, {'success': 'false'})
        monitor.record_counter("request_errors", 1, {'error_type': type(e).__name__})
        
        logger.error(f"Error in lambda_handler: {str(e)}", 
                    request_id=request_id, include_traceback=True)
        
        # Use our error handling framework
        context_info = {
            'request_id': request_id,
            'operation': 'lambda_handler',
            'stage': 'main_workflow'
        }
        
        final_response = handle_lambda_error(e, event, context_info)
        return final_response
        
    finally:
        # Log final summary and metrics
        processing_time = time.time() - start_time
        monitor.log_final_summary()
        
        # Log request completion
        log_request_end(request_id, final_response or {}, processing_time, success, logger)

def parse_request(event: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """
    Parse the Lambda event to extract image data and prompt.
    Supports multiple input formats following the DrugInfoTool pattern.
    
    Args:
        event: Lambda event dictionary
        
    Returns:
        Tuple of (image_data, prompt)
    """
    image_data = None
    prompt = config.DEFAULT_ANALYSIS_PROMPT
    
    logger.debug("Parsing request for image data and prompt", stage="request_parsing")
    
    # Format 1: New Bedrock Agent format
    properties = event.get('input', {}).get('RequestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
    logger.debug(f"Format 1 - properties: {len(properties)} items found", stage="request_parsing")
    
    for prop in properties:
        if prop.get('name') == 'image_data':
            image_data = prop.get('value')
            logger.debug("Found image_data in Format 1", stage="request_parsing")
        elif prop.get('name') == 'prompt':
            prompt = prop.get('value', prompt)
            logger.debug("Found custom prompt in Format 1", stage="request_parsing")
    
    # Format 2: Direct parameters array
    if not image_data:
        parameters = event.get('parameters', [])
        logger.debug(f"Format 2 - parameters: {len(parameters)} items found", stage="request_parsing")
        for param in parameters:
            if param.get('name') == 'image_data':
                image_data = param.get('value')
                logger.debug("Found image_data in Format 2", stage="request_parsing")
            elif param.get('name') == 'prompt':
                prompt = param.get('value', prompt)
                logger.debug("Found custom prompt in Format 2", stage="request_parsing")
    
    # Format 3: Direct in requestBody
    if not image_data:
        request_body = event.get('requestBody', {})
        logger.debug(f"Format 3 - requestBody keys: {list(request_body.keys())}", stage="request_parsing")
        image_data = request_body.get('image_data')
        if image_data:
            logger.debug("Found image_data in Format 3", stage="request_parsing")
        prompt = request_body.get('prompt', prompt)
    
    # Format 4: Direct in event root
    if not image_data:
        image_data = event.get('image_data')
        if image_data:
            logger.debug("Found image_data in Format 4", stage="request_parsing")
        prompt = event.get('prompt', prompt)
    
    # Format 5: Bedrock Agent function calling format
    if not image_data:
        function_input = event.get('input', {})
        if isinstance(function_input, dict):
            image_data = function_input.get('image_data')
            if image_data:
                logger.debug("Found image_data in Format 5", stage="request_parsing")
            prompt = function_input.get('prompt', prompt)
    
    logger.debug(f"Final parsing result - image_data: {'present' if image_data else 'missing'}, prompt length: {len(prompt)}", 
                stage="request_parsing")
    
    return image_data, prompt

def validate_and_preprocess_image(image_data: str) -> str:
    """
    Validate image format and size, then preprocess for optimal vision model input.
    
    Args:
        image_data: Base64 encoded image string
        
    Returns:
        Preprocessed base64 image data
        
    Raises:
        ImageValidationError: If image validation fails
    """
    try:
        # Basic validation
        if not image_data or not isinstance(image_data, str):
            raise ImageValidationError("Invalid image data format")
        
        logger.debug("Starting image validation", stage="image_preprocessing")
        
        # Remove data URL prefix if present
        if image_data.startswith('data:'):
            if ';base64,' in image_data:
                image_data = image_data.split(';base64,')[1]
                logger.debug("Removed data URL prefix", stage="image_preprocessing")
            else:
                raise ImageValidationError("Invalid data URL format")
        
        # Check approximate size (base64 is ~33% larger than original)
        estimated_size = len(image_data) * 3 // 4
        logger.debug(f"Estimated image size: {estimated_size} bytes", stage="image_preprocessing")
        
        if estimated_size > config.MAX_IMAGE_SIZE:
            raise ImageValidationError(f"Image size ({estimated_size // (1024*1024)}MB) exceeds maximum allowed size ({config.get_max_size_mb()}MB)")
        
        if estimated_size < config.MIN_IMAGE_SIZE:
            raise ImageValidationError("Image data appears to be too small or corrupted")
        
        # Assess image quality
        logger.debug("Assessing image quality", stage="image_preprocessing")
        success, error, quality, metrics = assess_image_quality_from_base64(image_data)
        if not success:
            logger.warning(f"Image quality assessment failed: {error}", stage="image_preprocessing")
        else:
            logger.info(f"Image quality: {quality.value}, metrics: {metrics}", stage="image_preprocessing")
        
        # Optimize image for vision model
        logger.debug("Optimizing image for vision model", stage="image_preprocessing")
        success, message, optimized_data = convert_base64_to_optimized_image(image_data)
        if not success:
            logger.warning(f"Image optimization failed: {message}, using original", stage="image_preprocessing")
            return image_data
        else:
            logger.info(f"Image optimization: {message}", stage="image_preprocessing")
            return optimized_data
        
    except ImageValidationError:
        logger.error("Image validation failed", stage="image_preprocessing", include_traceback=True)
        raise
    except Exception as e:
        logger.error(f"Image validation/preprocessing error: {str(e)}", stage="image_preprocessing", include_traceback=True)
        raise ImageValidationError(f"Image processing failed: {str(e)}")

def analyze_image_with_vision_model(image_data: str, prompt: str) -> Dict[str, Any]:
    """
    Analyze image using the vision model and extract medication information.
    
    Args:
        image_data: Base64 encoded image data
        prompt: Analysis prompt for the vision model
        
    Returns:
        Dictionary containing medication identification results
        
    Raises:
        VisionModelError: If vision model analysis fails
    """
    try:
        logger.debug("Initializing vision model client", stage="vision_analysis")
        
        # Initialize vision model client
        vision_client = VisionModelClient()
        medication_extractor = MedicationExtractor()
        
        # Detect media type
        media_type = vision_client.detect_media_type(image_data)
        logger.debug(f"Detected media type: {media_type}", stage="vision_analysis")
        
        # Analyze image
        logger.debug(f"Calling vision model with prompt length: {len(prompt)}", stage="vision_analysis")
        vision_response = vision_client.analyze_image(image_data, prompt, media_type)
        
        if not vision_response.success:
            logger.error(f"Vision model analysis failed: {vision_response.error}", stage="vision_analysis")
            raise VisionModelError(f"Vision model analysis failed: {vision_response.error}")
        
        logger.debug(f"Vision model response received in {vision_response.processing_time:.2f}s", stage="vision_analysis")
        
        # Extract medication information
        logger.debug("Extracting medication information from vision response", stage="vision_analysis")
        medication_info = medication_extractor.extract_medication_info(vision_response.response_text)
        
        # Convert to dictionary format
        results = medication_info.to_dict()
        results['vision_processing_time'] = vision_response.processing_time
        results['vision_usage'] = vision_response.usage
        
        logger.info(f"Medication identified: {medication_info.medication_name} (confidence: {medication_info.confidence:.2f})", 
                   stage="vision_analysis")
        
        return results
        
    except VisionModelError:
        logger.error("Vision model error occurred", stage="vision_analysis", include_traceback=True)
        raise
    except Exception as e:
        logger.error(f"Vision model analysis error: {str(e)}", stage="vision_analysis", include_traceback=True)
        raise VisionModelError(f"Vision analysis failed: {str(e)}")

def build_response(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to build the standard Bedrock Agent response.
    This follows the same pattern as the DrugInfoTool.
    
    Args:
        event: Original Lambda event
        body: Response body data
        
    Returns:
        Formatted Bedrock Agent response
    """
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'image_analysis_tool'),
            'apiPath': event.get('apiPath', '/analyze-medication'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(body)
                }
            }
        }
    }

# Health check function for testing
def health_check(event, context):
    """
    Simple health check function for testing the Lambda deployment.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Health status response
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'healthy',
            'service': 'image_analysis_tool',
            'timestamp': time.time(),
            'version': '1.0.0'
        })
    }