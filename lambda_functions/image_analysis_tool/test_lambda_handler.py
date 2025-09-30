"""
Integration tests for the main Lambda handler.
Tests the complete workflow from image upload to final response.
"""

import json
import pytest
import base64
import io
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from app import lambda_handler, parse_request, validate_and_preprocess_image, analyze_image_with_vision_model
from models import VisionModelResponse, MedicationIdentification, ImageQuality
from config import config

class TestLambdaHandler:
    """Test cases for the main Lambda handler"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create a simple test image
        self.test_image = Image.new('RGB', (100, 100), color='white')
        buffer = io.BytesIO()
        self.test_image.save(buffer, format='JPEG')
        self.test_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Mock context
        self.mock_context = Mock()
        self.mock_context.aws_request_id = 'test-request-id'
        self.mock_context.function_name = 'image_analysis_tool'
        self.mock_context.remaining_time_in_millis = lambda: 30000
    
    def create_test_event(self, image_data=None, prompt=None, format_type="format1"):
        """Create test event in various formats"""
        if image_data is None:
            image_data = self.test_image_base64
        if prompt is None:
            prompt = "Identify the medication in this image"
        
        if format_type == "format1":
            # New Bedrock Agent format
            return {
                'input': {
                    'RequestBody': {
                        'content': {
                            'application/json': {
                                'properties': [
                                    {'name': 'image_data', 'value': image_data},
                                    {'name': 'prompt', 'value': prompt}
                                ]
                            }
                        }
                    }
                },
                'actionGroup': 'image_analysis_tool',
                'apiPath': '/analyze-medication',
                'httpMethod': 'POST'
            }
        elif format_type == "format2":
            # Parameters array format
            return {
                'parameters': [
                    {'name': 'image_data', 'value': image_data},
                    {'name': 'prompt', 'value': prompt}
                ],
                'actionGroup': 'image_analysis_tool',
                'apiPath': '/analyze-medication',
                'httpMethod': 'POST'
            }
        elif format_type == "format3":
            # Direct requestBody format
            return {
                'requestBody': {
                    'image_data': image_data,
                    'prompt': prompt
                },
                'actionGroup': 'image_analysis_tool',
                'apiPath': '/analyze-medication',
                'httpMethod': 'POST'
            }
        else:
            # Direct event format
            return {
                'image_data': image_data,
                'prompt': prompt,
                'actionGroup': 'image_analysis_tool',
                'apiPath': '/analyze-medication',
                'httpMethod': 'POST'
            }

class TestRequestParsing:
    """Test request parsing functionality"""
    
    def test_parse_request_format1(self):
        """Test parsing Format 1 (New Bedrock Agent format)"""
        event = {
            'input': {
                'RequestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'image_data', 'value': 'test_image_data'},
                                {'name': 'prompt', 'value': 'test_prompt'}
                            ]
                        }
                    }
                }
            }
        }
        
        image_data, prompt = parse_request(event)
        assert image_data == 'test_image_data'
        assert prompt == 'test_prompt'
    
    def test_parse_request_format2(self):
        """Test parsing Format 2 (Parameters array)"""
        event = {
            'parameters': [
                {'name': 'image_data', 'value': 'test_image_data'},
                {'name': 'prompt', 'value': 'test_prompt'}
            ]
        }
        
        image_data, prompt = parse_request(event)
        assert image_data == 'test_image_data'
        assert prompt == 'test_prompt'
    
    def test_parse_request_format3(self):
        """Test parsing Format 3 (Direct requestBody)"""
        event = {
            'requestBody': {
                'image_data': 'test_image_data',
                'prompt': 'test_prompt'
            }
        }
        
        image_data, prompt = parse_request(event)
        assert image_data == 'test_image_data'
        assert prompt == 'test_prompt'
    
    def test_parse_request_format4(self):
        """Test parsing Format 4 (Direct in event root)"""
        event = {
            'image_data': 'test_image_data',
            'prompt': 'test_prompt'
        }
        
        image_data, prompt = parse_request(event)
        assert image_data == 'test_image_data'
        assert prompt == 'test_prompt'
    
    def test_parse_request_no_image_data(self):
        """Test parsing when no image data is found"""
        event = {'some_other_field': 'value'}
        
        image_data, prompt = parse_request(event)
        assert image_data is None
        assert prompt == config.DEFAULT_ANALYSIS_PROMPT
    
    def test_parse_request_default_prompt(self):
        """Test that default prompt is used when none provided"""
        event = {'image_data': 'test_image_data'}
        
        image_data, prompt = parse_request(event)
        assert image_data == 'test_image_data'
        assert prompt == config.DEFAULT_ANALYSIS_PROMPT

class TestImageValidationAndPreprocessing:
    """Test image validation and preprocessing"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='white')
        buffer = io.BytesIO()
        test_image.save(buffer, format='JPEG')
        self.valid_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def test_validate_valid_image(self):
        """Test validation of a valid image"""
        result = validate_and_preprocess_image(self.valid_image_base64)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_validate_data_url_image(self):
        """Test validation of image with data URL prefix"""
        data_url = f"data:image/jpeg;base64,{self.valid_image_base64}"
        result = validate_and_preprocess_image(data_url)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_validate_invalid_data_url(self):
        """Test validation fails for invalid data URL"""
        from models import ImageValidationError
        
        with pytest.raises(ImageValidationError):
            validate_and_preprocess_image("data:image/jpeg,invalid_format")
    
    def test_validate_empty_image_data(self):
        """Test validation fails for empty image data"""
        from models import ImageValidationError
        
        with pytest.raises(ImageValidationError):
            validate_and_preprocess_image("")
    
    def test_validate_none_image_data(self):
        """Test validation fails for None image data"""
        from models import ImageValidationError
        
        with pytest.raises(ImageValidationError):
            validate_and_preprocess_image(None)
    
    def test_validate_too_large_image(self):
        """Test validation fails for oversized image"""
        from models import ImageValidationError
        
        # Create a very large base64 string
        large_data = 'x' * (config.MAX_IMAGE_SIZE + 1000)
        
        with pytest.raises(ImageValidationError):
            validate_and_preprocess_image(large_data)
    
    def test_validate_too_small_image(self):
        """Test validation fails for undersized image"""
        from models import ImageValidationError
        
        # Create a very small base64 string
        small_data = 'x' * 10
        
        with pytest.raises(ImageValidationError):
            validate_and_preprocess_image(small_data)

class TestVisionModelIntegration:
    """Test vision model integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        test_image = Image.new('RGB', (100, 100), color='white')
        buffer = io.BytesIO()
        test_image.save(buffer, format='JPEG')
        self.test_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    @patch('app.VisionModelClient')
    @patch('app.MedicationExtractor')
    def test_analyze_image_success(self, mock_extractor_class, mock_client_class):
        """Test successful image analysis"""
        # Mock vision client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.detect_media_type.return_value = "image/jpeg"
        mock_client.analyze_image.return_value = VisionModelResponse(
            success=True,
            response_text="Medication: Advil 200mg",
            processing_time=1.5,
            usage={'tokens': 100}
        )
        
        # Mock medication extractor
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_medication_info.return_value = MedicationIdentification(
            medication_name="Advil",
            dosage="200mg",
            confidence=0.9,
            image_quality=ImageQuality.GOOD.value
        )
        
        result = analyze_image_with_vision_model(self.test_image_base64, "test prompt")
        
        assert result['medication_name'] == "Advil"
        assert result['dosage'] == "200mg"
        assert result['confidence'] == 0.9
        assert 'vision_processing_time' in result
        assert 'vision_usage' in result
    
    @patch('app.VisionModelClient')
    def test_analyze_image_vision_failure(self, mock_client_class):
        """Test vision model failure"""
        from models import VisionModelError
        
        # Mock vision client failure
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.detect_media_type.return_value = "image/jpeg"
        mock_client.analyze_image.return_value = VisionModelResponse(
            success=False,
            error="API timeout"
        )
        
        with pytest.raises(VisionModelError):
            analyze_image_with_vision_model(self.test_image_base64, "test prompt")

class TestEndToEndWorkflow:
    """Test complete end-to-end workflow"""
    
    def setup_method(self):
        """Set up test fixtures"""
        test_image = Image.new('RGB', (100, 100), color='white')
        buffer = io.BytesIO()
        test_image.save(buffer, format='JPEG')
        self.test_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        self.mock_context = Mock()
        self.mock_context.aws_request_id = 'test-request-id'
        self.mock_context.function_name = 'image_analysis_tool'
        self.mock_context.remaining_time_in_millis = lambda: 30000
    
    def create_test_event(self):
        """Create a test event"""
        return {
            'input': {
                'RequestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'image_data', 'value': self.test_image_base64},
                                {'name': 'prompt', 'value': 'Identify medication'}
                            ]
                        }
                    }
                }
            },
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
    
    @patch('app.get_drug_information')
    @patch('app.VisionModelClient')
    @patch('app.MedicationExtractor')
    def test_successful_workflow(self, mock_extractor_class, mock_client_class, mock_drug_info):
        """Test complete successful workflow"""
        # Mock vision analysis
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.detect_media_type.return_value = "image/jpeg"
        mock_client.analyze_image.return_value = VisionModelResponse(
            success=True,
            response_text="Medication: Advil 200mg",
            processing_time=1.5
        )
        
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_medication_info.return_value = MedicationIdentification(
            medication_name="Advil",
            dosage="200mg",
            confidence=0.9,
            image_quality=ImageQuality.GOOD.value
        )
        
        # Mock drug info
        mock_drug_info.return_value = {
            'success': True,
            'drug_info': {
                'brand_name': 'Advil',
                'generic_name': 'Ibuprofen',
                'purpose': 'Pain reliever',
                'warnings': 'Do not exceed recommended dose'
            }
        }
        
        event = self.create_test_event()
        response = lambda_handler(event, self.mock_context)
        
        # Verify response structure
        assert 'messageVersion' in response
        assert response['messageVersion'] == '1.0'
        assert 'response' in response
        assert response['response']['httpStatusCode'] == 200
        
        # Parse response body
        response_body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert response_body['success'] is True
        assert 'medication_name' in response_body
        assert 'user_response' in response_body
        assert 'processing_time' in response_body
    
    def test_no_image_data_error(self):
        """Test error handling when no image data provided"""
        event = {
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
        
        response = lambda_handler(event, self.mock_context)
        
        # Verify error response
        assert response['response']['httpStatusCode'] == 400
        response_body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert response_body['success'] is False
        assert 'error' in response_body
    
    @patch('app.validate_and_preprocess_image')
    def test_image_validation_error(self, mock_validate):
        """Test error handling for image validation failure"""
        from models import ImageValidationError
        
        mock_validate.side_effect = ImageValidationError("Invalid image format")
        
        event = self.create_test_event()
        response = lambda_handler(event, self.mock_context)
        
        # Verify error response
        assert response['response']['httpStatusCode'] in [400, 500]
        response_body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert response_body['success'] is False
    
    @patch('app.analyze_image_with_vision_model')
    def test_vision_model_error(self, mock_analyze):
        """Test error handling for vision model failure"""
        from models import VisionModelError
        
        mock_analyze.side_effect = VisionModelError("Vision API timeout")
        
        event = self.create_test_event()
        response = lambda_handler(event, self.mock_context)
        
        # Verify error response
        assert response['response']['httpStatusCode'] in [400, 500]
        response_body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert response_body['success'] is False
    
    @patch('app.get_drug_information')
    @patch('app.VisionModelClient')
    @patch('app.MedicationExtractor')
    def test_low_confidence_skips_drug_lookup(self, mock_extractor_class, mock_client_class, mock_drug_info):
        """Test that low confidence identification skips drug lookup"""
        # Mock low confidence vision analysis
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.detect_media_type.return_value = "image/jpeg"
        mock_client.analyze_image.return_value = VisionModelResponse(
            success=True,
            response_text="Unclear medication",
            processing_time=1.5
        )
        
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_medication_info.return_value = MedicationIdentification(
            medication_name="Unknown",
            dosage="",
            confidence=0.2,  # Low confidence
            image_quality=ImageQuality.POOR.value
        )
        
        event = self.create_test_event()
        response = lambda_handler(event, self.mock_context)
        
        # Verify drug info was not called
        mock_drug_info.assert_not_called()
        
        # Verify response indicates low confidence
        response_body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert response_body['drug_info_available'] is False

class TestHealthCheck:
    """Test health check functionality"""
    
    def test_health_check(self):
        """Test health check function"""
        from app import health_check
        
        mock_context = Mock()
        response = health_check({}, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'healthy'
        assert body['service'] == 'image_analysis_tool'
        assert 'timestamp' in body
        assert 'version' in body

if __name__ == '__main__':
    pytest.main([__file__, '-v'])