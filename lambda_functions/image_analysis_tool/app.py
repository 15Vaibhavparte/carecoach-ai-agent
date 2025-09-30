import json
import base64
import boto3
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

# Configure logging
logger = logging.getLogger()
logger.setLevel(getattr(logging, config.LOG_LEVEL))

class ImageAnalysisHandler:
    """Core handler for image analysis operations"""
    
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=config.AWS_REGION)
        self.model_id = config.BEDROCK_MODEL_ID
        self.image_validator = ImageValidator()
        self.image_preprocessor = ImagePreprocessor(ImageOptimizationLevel.BASIC)
    
    def validate_image(self, image_data: str, max_size: int, allowed_formats: List[str]) -> ImageValidationResult:
        """Validate image format and size using the comprehensive validator"""
        try:
            # Use the new comprehensive image validator
            validator = ImageValidator(max_size=max_size, allowed_formats=allowed_formats)
            return validator.validate_image(image_data)
            
        except Exception as e:
            logger.error(f"Image validation failed: {str(e)}")
            return ImageValidationResult(
                valid=False,
                error=f"Image validation failed: {str(e)}",
                size=0,
                format_detected='unknown'
            )
    
    def process_image_with_vision_model(self, image_data: str, prompt: str) -> VisionModelResponse:
        """Send image to vision model for analysis"""
        start_time = time.time()
        
        try:
            # Prepare the request for Claude 3 Sonnet
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": config.MAX_TOKENS,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",  # Will need to detect actual type in future enhancement
                                    "data": image_data
                                }
                            }
                        ]
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            processing_time = time.time() - start_time
            
            return VisionModelResponse(
                success=True,
                response_text=response_body.get('content', [{}])[0].get('text', ''),
                usage=response_body.get('usage', {}),
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Vision model processing failed: {str(e)}")
            return VisionModelResponse(
                success=False,
                error=f"Vision model processing failed: {str(e)}",
                processing_time=processing_time
            )
    
    def extract_medication_info(self, vision_response: str) -> MedicationIdentification:
        """Parse vision model response to extract medication information"""
        try:
            # This is a simplified extraction - in practice, this would be more sophisticated
            # and might use structured prompting or additional parsing logic
            
            medication_name = ""
            dosage = ""
            confidence = 0.0
            image_quality = ImageQuality.UNKNOWN.value
            
            # Basic parsing logic (to be enhanced in later tasks)
            response_lower = vision_response.lower()
            
            # Simple confidence assessment based on response content
            if any(phrase in response_lower for phrase in ["clearly visible", "confident", "high confidence"]):
                confidence = 0.9
                image_quality = ImageQuality.GOOD.value
            elif any(phrase in response_lower for phrase in ["likely", "appears to be", "moderate confidence"]):
                confidence = 0.7
                image_quality = ImageQuality.FAIR.value
            elif any(phrase in response_lower for phrase in ["unclear", "difficult", "low confidence", "blurry"]):
                confidence = 0.3
                image_quality = ImageQuality.POOR.value
            else:
                confidence = 0.5
                image_quality = ImageQuality.FAIR.value
            
            # Extract medication name (simplified - will be enhanced in later tasks)
            if "medication" in response_lower:
                # This is a placeholder - actual implementation would use more sophisticated parsing
                medication_name = "Unknown"
                dosage = "Unknown"
            
            return MedicationIdentification(
                medication_name=medication_name,
                dosage=dosage,
                confidence=confidence,
                image_quality=image_quality,
                raw_response=vision_response
            )
            
        except Exception as e:
            logger.error(f"Failed to extract medication info: {str(e)}")
            return MedicationIdentification(
                medication_name="",
                dosage="",
                confidence=0.0,
                image_quality=ImageQuality.POOR.value,
                raw_response=vision_response
            )
    
    def call_drug_info_tool(self, drug_name: str) -> DrugInfoResult:
        """Call the existing DrugInfoTool to get detailed drug information"""
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
            logger.error(f"Failed to call DrugInfoTool: {str(e)}")
            return DrugInfoResult(
                success=False,
                error=f"Failed to retrieve drug information: {str(e)}",
                source="DrugInfoTool"
            )

def lambda_handler(event, context):
    """
    Main Lambda handler for image analysis and medication identification.
    Follows the same pattern as DrugInfoTool for Bedrock Agent compatibility.
    """
    # Debug logging
    logger.info(f"Incoming event: {json.dumps(event, indent=2)}")
    logger.info(f"Context: {context}")
    
    try:
        # Extract image_data parameter from the agent's input
        # Following the same multi-format approach as DrugInfoTool
        image_data = None
        prompt = "Identify the medication name and dosage in this image"
        
        # Format 1: New Bedrock Agent format
        properties = event.get('input', {}).get('RequestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
        logger.info(f"Format 1 - properties: {json.dumps(properties, indent=2)}")
        
        for prop in properties:
            if prop.get('name') == 'image_data':
                image_data = prop.get('value')
                logger.info(f"Found image_data in Format 1")
                break
            elif prop.get('name') == 'prompt':
                prompt = prop.get('value', prompt)
        
        # Format 2: Direct parameters array
        if not image_data:
            parameters = event.get('parameters', [])
            logger.info(f"Format 2 - parameters: {json.dumps(parameters, indent=2)}")
            for param in parameters:
                if param.get('name') == 'image_data':
                    image_data = param.get('value')
                    logger.info(f"Found image_data in Format 2")
                    break
        
        # Format 3: Direct in requestBody
        if not image_data:
            request_body = event.get('requestBody', {})
            logger.info(f"Format 3 - requestBody keys: {list(request_body.keys())}")
            image_data = request_body.get('image_data')
            if image_data:
                logger.info(f"Found image_data in Format 3")
        
        # Format 4: Direct in event root
        if not image_data:
            image_data = event.get('image_data')
            if image_data:
                logger.info(f"Found image_data in Format 4")
        
        logger.info(f"Final image_data present: {bool(image_data)}")
        
        if not image_data:
            logger.error("No image data found in any format")
            return build_response(event, {
                "error": "No image data provided. Please upload an image of the medication.",
                "debug_info": "No image_data parameter found in the request"
            })
        
        # Initialize the handler
        handler = ImageAnalysisHandler()
        
        # Create request object
        analysis_request = ImageAnalysisRequest(
            image_data=image_data,
            prompt=prompt,
            max_file_size=config.MAX_IMAGE_SIZE,
            allowed_formats=config.SUPPORTED_FORMATS
        )
        
        # Validate the image
        validation_result = handler.validate_image(
            image_data, 
            analysis_request.max_file_size, 
            analysis_request.allowed_formats
        )
        
        if not validation_result.valid:
            return build_response(event, {
                "error": validation_result.error,
                "suggestion": f"Please ensure your image is in {config.get_supported_formats_string()} format and under {config.get_max_size_mb()}MB."
            })
        
        # Preprocess the image for optimal vision model input
        try:
            success, error, preprocessed_image = handler.image_preprocessor.base64_to_image(image_data)
            if not success:
                return build_response(event, {
                    "error": f"Image preprocessing failed: {error}",
                    "suggestion": "Please try again with a different image."
                })
            
            # Assess image quality
            quality, quality_metrics = handler.image_preprocessor.assess_image_quality(preprocessed_image)
            
            # Optimize image for vision model
            success, optimization_message, optimized_image = handler.image_preprocessor.optimize_for_vision_model(preprocessed_image)
            if not success:
                logger.warning(f"Image optimization failed: {optimization_message}")
                optimized_image = preprocessed_image  # Use original if optimization fails
            
            # Convert optimized image back to base64
            success, error, optimized_base64 = handler.image_preprocessor.image_to_base64(optimized_image, 'JPEG', 85)
            if not success:
                logger.warning(f"Failed to convert optimized image to base64: {error}")
                optimized_base64 = image_data  # Use original if conversion fails
            else:
                image_data = optimized_base64  # Use optimized image for vision model
                
        except Exception as e:
            logger.warning(f"Image preprocessing encountered an error: {str(e)}")
            # Continue with original image if preprocessing fails
            quality = ImageQuality.UNKNOWN
            quality_metrics = {}
        
        # Process image with vision model
        vision_result = handler.process_image_with_vision_model(image_data, prompt)
        
        if not vision_result.success:
            return build_response(event, {
                "error": vision_result.error,
                "suggestion": "Please try again with a clearer image of the medication."
            })
        
        # Extract medication information
        medication_info = handler.extract_medication_info(vision_result.response_text)
        
        # If medication was identified, get detailed drug information
        drug_info = {}
        if medication_info.has_valid_identification():
            drug_result = handler.call_drug_info_tool(medication_info.medication_name)
            if drug_result.success:
                drug_info = drug_result.data
        
        # Build combined response
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
        combined_response.add_metadata('image_quality', quality.value if 'quality' in locals() else 'unknown')
        if 'quality_metrics' in locals() and quality_metrics:
            combined_response.add_metadata('quality_metrics', quality_metrics)
        
        return build_response(event, combined_response.to_dict())
        
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}")
        return build_response(event, {
            "error": f"An unexpected error occurred: {str(e)}",
            "success": False
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