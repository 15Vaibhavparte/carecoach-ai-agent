"""
Example integration of the comprehensive error handling framework with the main Lambda handler.
This demonstrates how to use the error handling and error scenarios in the main application.
"""

import json
import time
from typing import Dict, List, Optional, Any
import logging

# Import local modules
from models import (
    ImageAnalysisRequest,
    MedicationIdentification,
    CombinedResponse,
    VisionModelResponse,
    DrugInfoResult,
    ImageValidationResult,
    ImageQuality,
    ImageAnalysisError,
    ImageValidationError,
    VisionModelError,
    DrugInfoError
)
from config import config
from image_validation import ImageValidator
from image_preprocessing import ImagePreprocessor, ImageOptimizationLevel
from vision_client import VisionModelClient, MedicationExtractor

# Import error handling framework
from error_handling import (
    ErrorContext,
    handle_lambda_error,
    error_handler
)
from error_scenarios import (
    ErrorScenarioManager,
    handle_image_validation_error,
    handle_vision_model_error,
    handle_drug_info_error
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(getattr(logging, config.LOG_LEVEL))

class EnhancedImageAnalysisHandler:
    """Enhanced handler with comprehensive error handling"""
    
    def __init__(self):
        self.image_validator = ImageValidator()
        self.image_preprocessor = ImagePreprocessor(ImageOptimizationLevel.BASIC)
        self.vision_client = VisionModelClient()
        self.medication_extractor = MedicationExtractor()
        self.error_manager = ErrorScenarioManager()
    
    def validate_image_safely(self, image_data: str, max_size: int, allowed_formats: List[str]) -> ImageValidationResult:
        """Validate image with comprehensive error handling"""
        context = ErrorContext(
            operation="image_validation",
            processing_stage="format_and_size_check",
            input_size=len(image_data) if image_data else 0
        )
        
        try:
            validator = ImageValidator(max_size=max_size, allowed_formats=allowed_formats)
            return validator.validate_image(image_data)
            
        except Exception as e:
            error_details = handle_image_validation_error(e, image_data, context)
            
            # Return validation result with error details
            return ImageValidationResult(
                valid=False,
                error=error_details.user_message,
                size=len(image_data) if image_data else 0,
                format_detected='unknown'
            )
    
    def process_image_with_vision_model_safely(self, image_data: str, prompt: str) -> VisionModelResponse:
        """Process image with vision model using error handling and retry logic"""
        context = ErrorContext(
            operation="vision_analysis",
            processing_stage="model_inference"
        )
        
        try:
            # Use the error scenario manager to create a safe operation
            safe_vision_analysis = self.error_manager.vision_handler.analyze_with_retry(
                self._vision_analysis_operation
            )
            
            return safe_vision_analysis(image_data, prompt)
            
        except Exception as e:
            error_details = handle_vision_model_error(e, context)
            
            return VisionModelResponse(
                success=False,
                error=error_details.user_message,
                processing_time=0.0
            )
    
    def _vision_analysis_operation(self, image_data: str, prompt: str) -> VisionModelResponse:
        """Internal vision analysis operation"""
        media_type = self.vision_client.detect_media_type(image_data)
        return self.vision_client.analyze_image(image_data, prompt, media_type)
    
    def call_drug_info_tool_safely(self, drug_name: str) -> DrugInfoResult:
        """Call DrugInfoTool with comprehensive error handling and retry logic"""
        context = ErrorContext(
            operation="drug_info_lookup",
            processing_stage="api_call"
        )
        
        try:
            # Use the error scenario manager to create a safe operation
            safe_drug_lookup = self.error_manager.drug_info_handler.lookup_with_retry(
                self._drug_info_lookup_operation
            )
            
            return safe_drug_lookup(drug_name)
            
        except Exception as e:
            error_details = handle_drug_info_error(e, drug_name, context)
            
            return DrugInfoResult(
                success=False,
                error=error_details.user_message,
                source="DrugInfoTool"
            )
    
    def _drug_info_lookup_operation(self, drug_name: str) -> DrugInfoResult:
        """Internal drug info lookup operation"""
        try:
            # Import the existing drug info tool
            import sys
            import os
            
            # Add the drug_info_tool directory to the path
            drug_info_path = os.path.join(os.path.dirname(__file__), '..', 'drug_info_tool')
            sys.path.insert(0, drug_info_path)
            
            from app import lambda_handler as drug_info_handler
            
            # Create event structure that matches DrugInfoTool expectations
            drug_info_event = {
                'input': {
                    'RequestBody': {
                        'content': {
                            'application/json': {
                                'properties': [
                                    {
                                        'name': 'drug_name',
                                        'value': drug_name
                                    }
                                ]
                            }
                        }
                    }
                },
                'actionGroup': 'drug_info',
                'apiPath': '/drug-info',
                'httpMethod': 'POST'
            }
            
            # Call the drug info handler
            drug_response = drug_info_handler(drug_info_event, None)
            
            # Extract the response body
            response_body = drug_response.get('response', {}).get('responseBody', {}).get('application/json', {}).get('body', '{}')
            drug_info = json.loads(response_body)
            
            return DrugInfoResult(
                success=True,
                data=drug_info,
                source="DrugInfoTool"
            )
            
        except Exception as e:
            raise DrugInfoError(f"Failed to retrieve drug information: {str(e)}") from e

def enhanced_lambda_handler(event, context):
    """
    Enhanced Lambda handler with comprehensive error handling.
    Demonstrates integration of the error handling framework.
    """
    # Create error context for the entire request
    request_context = ErrorContext(
        request_id=getattr(context, 'aws_request_id', None) if context else None,
        operation="lambda_handler",
        processing_stage="initialization"
    )
    
    try:
        # Debug logging
        logger.info(f"Incoming event: {json.dumps(event, indent=2)}")
        logger.info(f"Context: {context}")
        
        # Extract image_data parameter from the agent's input
        image_data = None
        prompt = "Identify the medication name and dosage in this image"
        
        # Handle None event gracefully
        if event is None:
            event = {}
        
        # Format 1: New Bedrock Agent format
        properties = event.get('input', {}).get('RequestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
        
        for prop in properties:
            if prop.get('name') == 'image_data':
                image_data = prop.get('value')
                break
            elif prop.get('name') == 'prompt':
                prompt = prop.get('value', prompt)
        
        # Try other formats if not found
        if not image_data:
            parameters = event.get('parameters', [])
            for param in parameters:
                if param.get('name') == 'image_data':
                    image_data = param.get('value')
                    break
        
        if not image_data:
            request_body = event.get('requestBody', {})
            image_data = request_body.get('image_data')
        
        if not image_data:
            image_data = event.get('image_data')
        
        if not image_data:
            # Use error handling framework for missing image data
            error_details = error_handler.handle_error(
                ImageValidationError("No image data provided"),
                request_context,
                "no_image_data"
            )
            return error_handler.create_error_response(error_details, event)
        
        # Update processing stage
        request_context.processing_stage = "image_analysis"
        
        # Initialize the enhanced handler
        handler = EnhancedImageAnalysisHandler()
        
        # Create request object
        analysis_request = ImageAnalysisRequest(
            image_data=image_data,
            prompt=prompt,
            max_file_size=config.MAX_IMAGE_SIZE,
            allowed_formats=config.SUPPORTED_FORMATS
        )
        
        # Validate the image with error handling
        request_context.processing_stage = "image_validation"
        validation_result = handler.validate_image_safely(
            image_data, 
            analysis_request.max_file_size, 
            analysis_request.allowed_formats
        )
        
        if not validation_result.valid:
            error_details = error_handler.handle_error(
                ImageValidationError(validation_result.error),
                request_context,
                "invalid_image"
            )
            return error_handler.create_error_response(error_details, event)
        
        # Preprocess the image (with existing error handling)
        request_context.processing_stage = "image_preprocessing"
        try:
            success, error, preprocessed_image = handler.image_preprocessor.base64_to_image(image_data)
            if not success:
                error_details = error_handler.handle_error(
                    ImageValidationError(f"Image preprocessing failed: {error}"),
                    request_context,
                    "preprocessing_failed"
                )
                return error_handler.create_error_response(error_details, event)
            
            # Assess and optimize image quality
            quality, quality_metrics = handler.image_preprocessor.assess_image_quality(preprocessed_image)
            success, optimization_message, optimized_image = handler.image_preprocessor.optimize_for_vision_model(preprocessed_image)
            
            if success:
                success, error, optimized_base64 = handler.image_preprocessor.image_to_base64(optimized_image, 'JPEG', 85)
                if success:
                    image_data = optimized_base64
                    
        except Exception as e:
            logger.warning(f"Image preprocessing encountered an error: {str(e)}")
            quality = ImageQuality.UNKNOWN
            quality_metrics = {}
        
        # Process image with vision model using enhanced error handling
        request_context.processing_stage = "vision_analysis"
        vision_result = handler.process_image_with_vision_model_safely(image_data, prompt)
        
        if not vision_result.success:
            error_details = error_handler.handle_error(
                VisionModelError(vision_result.error),
                request_context,
                "vision_analysis_failed"
            )
            return error_handler.create_error_response(error_details, event)
        
        # Extract medication information
        request_context.processing_stage = "medication_extraction"
        medication_info = handler.medication_extractor.extract_medication_info(vision_result.response_text)
        
        # Get detailed drug information with enhanced error handling
        request_context.processing_stage = "drug_info_lookup"
        drug_info = {}
        if medication_info.has_valid_identification():
            drug_result = handler.call_drug_info_tool_safely(medication_info.medication_name)
            if drug_result.success:
                drug_info = drug_result.data
            else:
                # Log the drug info error but don't fail the entire request
                logger.warning(f"Drug info lookup failed: {drug_result.error}")
        
        # Build combined response
        request_context.processing_stage = "response_synthesis"
        combined_response = CombinedResponse(
            identification=medication_info,
            drug_info=drug_info,
            processing_time=vision_result.processing_time,
            success=True
        )
        
        # Add metadata
        combined_response.add_metadata('vision_model_usage', vision_result.usage)
        combined_response.add_metadata('image_size', validation_result.size)
        combined_response.add_metadata('image_format', validation_result.format_detected)
        combined_response.add_metadata('image_quality', quality.value if 'quality' in locals() and hasattr(quality, 'value') else 'unknown')
        if 'quality_metrics' in locals() and quality_metrics:
            combined_response.add_metadata('quality_metrics', quality_metrics)
        
        return build_response(event, combined_response.to_dict())
        
    except Exception as e:
        # Use the comprehensive error handling for any unexpected errors
        logger.error(f"Unexpected error in enhanced_lambda_handler: {str(e)}")
        return handle_lambda_error(e, event, {
            'request_id': getattr(context, 'aws_request_id', None) if context else None,
            'operation': 'enhanced_lambda_handler',
            'stage': request_context.processing_stage if 'request_context' in locals() else 'unknown'
        })

def build_response(event, body):
    """Helper function to build the standard Bedrock Agent response."""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup'),
            'apiPath': event.get('apiPath'),
            'httpMethod': event.get('httpMethod'),
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(body)
                }
            }
        }
    }

# For backward compatibility, keep the original lambda_handler
# but users can switch to enhanced_lambda_handler for better error handling
lambda_handler = enhanced_lambda_handler