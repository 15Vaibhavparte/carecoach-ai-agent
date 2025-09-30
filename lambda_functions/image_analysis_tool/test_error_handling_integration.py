"""
Integration tests for the error handling framework with the main application.
Tests the complete error handling flow in realistic scenarios.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from app_with_error_handling import enhanced_lambda_handler, EnhancedImageAnalysisHandler
from error_handling import ErrorContext
from models import ImageValidationError, VisionModelError, DrugInfoError

class TestEnhancedImageAnalysisHandler:
    """Test the enhanced handler with error handling"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = EnhancedImageAnalysisHandler()
    
    @patch('app_with_error_handling.ImageValidator')
    def test_validate_image_safely_success(self, mock_validator_class):
        """Test successful image validation"""
        # Mock successful validation
        mock_validator = Mock()
        mock_validator.validate_image.return_value = Mock(
            valid=True,
            error="",
            size=1024,
            format_detected="jpeg"
        )
        mock_validator_class.return_value = mock_validator
        
        result = self.handler.validate_image_safely(
            "valid_image_data",
            max_size=10*1024*1024,
            allowed_formats=['jpeg', 'jpg', 'png']
        )
        
        assert result.valid is True
        assert result.error == ""
    
    def test_validate_image_safely_error(self):
        """Test image validation with error handling"""
        # Invalid image data
        invalid_image_data = "invalid_base64_data"
        
        result = self.handler.validate_image_safely(
            invalid_image_data,
            max_size=10*1024*1024,
            allowed_formats=['jpeg', 'jpg', 'png']
        )
        
        assert result.valid is False
        assert result.error != ""
        assert "format" in result.error.lower() or "invalid" in result.error.lower()
    
    @patch('app_with_error_handling.VisionModelClient')
    def test_process_image_with_vision_model_safely_success(self, mock_vision_client):
        """Test successful vision model processing"""
        # Mock successful vision model response
        mock_client_instance = Mock()
        mock_client_instance.detect_media_type.return_value = "image/jpeg"
        mock_client_instance.analyze_image.return_value = Mock(
            success=True,
            response_text="Medication: Aspirin 325mg",
            usage={},
            error="",
            processing_time=1.5
        )
        mock_vision_client.return_value = mock_client_instance
        
        # Replace the handler's vision client
        self.handler.vision_client = mock_client_instance
        
        # Mock the error manager's retry handler to not retry
        with patch.object(self.handler.error_manager.vision_handler, 'analyze_with_retry') as mock_retry:
            mock_retry.side_effect = lambda func: func
            
            result = self.handler.process_image_with_vision_model_safely(
                "valid_image_data",
                "Identify medication"
            )
        
        assert result.success is True
        assert result.response_text == "Medication: Aspirin 325mg"
    
    @patch('app_with_error_handling.VisionModelClient')
    def test_process_image_with_vision_model_safely_error(self, mock_vision_client):
        """Test vision model processing with error handling"""
        # Mock vision model error
        mock_client_instance = Mock()
        mock_client_instance.detect_media_type.return_value = "image/jpeg"
        mock_client_instance.analyze_image.side_effect = VisionModelError("API timeout")
        mock_vision_client.return_value = mock_client_instance
        self.handler.vision_client = mock_client_instance
        
        result = self.handler.process_image_with_vision_model_safely(
            "valid_image_data",
            "Identify medication"
        )
        
        assert result.success is False
        assert result.error != ""
    
    @patch('sys.path')
    @patch('builtins.__import__')
    def test_call_drug_info_tool_safely_success(self, mock_import, mock_sys_path):
        """Test successful drug info lookup"""
        # Mock successful drug info response
        mock_drug_handler = Mock()
        mock_drug_handler.return_value = {
            'response': {
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'brand_name': 'Aspirin',
                            'generic_name': 'Acetylsalicylic acid',
                            'purpose': 'Pain reliever'
                        })
                    }
                }
            }
        }
        
        # Mock the import
        mock_app_module = Mock()
        mock_app_module.lambda_handler = mock_drug_handler
        mock_import.return_value = mock_app_module
        
        # Mock the error manager's retry handler to not retry
        with patch.object(self.handler.error_manager.drug_info_handler, 'lookup_with_retry') as mock_retry:
            mock_retry.side_effect = lambda func: func
            
            result = self.handler.call_drug_info_tool_safely("Aspirin")
        
        assert result.success is True
        assert result.data['brand_name'] == 'Aspirin'
    
    @patch('sys.path')
    @patch('builtins.__import__')
    def test_call_drug_info_tool_safely_error(self, mock_import, mock_sys_path):
        """Test drug info lookup with error handling"""
        # Mock import error
        mock_import.side_effect = ImportError("Module not found")
        
        result = self.handler.call_drug_info_tool_safely("Aspirin")
        
        assert result.success is False
        assert result.error != ""

class TestEnhancedLambdaHandler:
    """Test the enhanced lambda handler"""
    
    def test_enhanced_lambda_handler_no_image_data(self):
        """Test handler with no image data"""
        event = {
            'actionGroup': 'image_analysis',
            'apiPath': '/analyze',
            'httpMethod': 'POST'
        }
        context = Mock()
        context.aws_request_id = 'test-request-123'
        
        response = enhanced_lambda_handler(event, context)
        
        assert response['response']['httpStatusCode'] == 400
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['success'] is False
        assert 'error' in body
    
    @patch('app_with_error_handling.EnhancedImageAnalysisHandler')
    def test_enhanced_lambda_handler_validation_error(self, mock_handler_class):
        """Test handler with image validation error"""
        # Mock handler that returns validation error
        mock_handler = Mock()
        mock_handler.validate_image_safely.return_value = Mock(
            valid=False,
            error="Invalid image format"
        )
        mock_handler_class.return_value = mock_handler
        
        event = {
            'input': {
                'RequestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {
                                    'name': 'image_data',
                                    'value': 'invalid_image_data'
                                }
                            ]
                        }
                    }
                }
            },
            'actionGroup': 'image_analysis',
            'apiPath': '/analyze',
            'httpMethod': 'POST'
        }
        context = Mock()
        context.aws_request_id = 'test-request-123'
        
        response = enhanced_lambda_handler(event, context)
        
        assert response['response']['httpStatusCode'] == 400
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['success'] is False
        assert 'error' in body
    
    @patch('app_with_error_handling.EnhancedImageAnalysisHandler')
    @patch('app_with_error_handling.config')
    def test_enhanced_lambda_handler_success_flow(self, mock_config, mock_handler_class):
        """Test successful processing flow"""
        # Mock config
        mock_config.MAX_IMAGE_SIZE = 10*1024*1024
        mock_config.SUPPORTED_FORMATS = ['jpeg', 'jpg', 'png']
        
        # Mock successful handler responses
        mock_handler = Mock()
        
        # Mock successful validation
        mock_handler.validate_image_safely.return_value = Mock(
            valid=True,
            error="",
            size=1024,
            format_detected="jpeg"
        )
        
        # Mock successful image preprocessing
        mock_handler.image_preprocessor.base64_to_image.return_value = (True, "", Mock())
        mock_handler.image_preprocessor.assess_image_quality.return_value = ("good", {})
        mock_handler.image_preprocessor.optimize_for_vision_model.return_value = (True, "", Mock())
        mock_handler.image_preprocessor.image_to_base64.return_value = (True, "", "optimized_image_data")
        
        # Mock successful vision processing
        mock_handler.process_image_with_vision_model_safely.return_value = Mock(
            success=True,
            response_text="Aspirin 325mg detected",
            usage={},
            processing_time=1.5
        )
        
        # Mock medication extraction with proper data structure
        from models import MedicationIdentification, DrugInfoResult
        mock_medication_info = MedicationIdentification(
            medication_name="Aspirin",
            dosage="325mg",
            confidence=0.9
        )
        mock_handler.medication_extractor.extract_medication_info.return_value = mock_medication_info
        
        # Mock successful drug info lookup with proper data structure
        mock_handler.call_drug_info_tool_safely.return_value = DrugInfoResult(
            success=True,
            data={'brand_name': 'Aspirin', 'purpose': 'Pain reliever'},
            source="DrugInfoTool"
        )
        
        mock_handler_class.return_value = mock_handler
        
        event = {
            'input': {
                'RequestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {
                                    'name': 'image_data',
                                    'value': 'valid_image_data'
                                }
                            ]
                        }
                    }
                }
            },
            'actionGroup': 'image_analysis',
            'apiPath': '/analyze',
            'httpMethod': 'POST'
        }
        context = Mock()
        context.aws_request_id = 'test-request-123'
        
        response = enhanced_lambda_handler(event, context)
        
        assert response['response']['httpStatusCode'] == 200
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['success'] is True
        assert 'identification' in body
        assert 'drug_info' in body
    
    def test_enhanced_lambda_handler_unexpected_error(self):
        """Test handler with unexpected error"""
        # Create an event that will cause an unexpected error
        event = None  # This will cause an error when trying to access event.get()
        context = Mock()
        context.aws_request_id = 'test-request-123'
        
        response = enhanced_lambda_handler(event, context)
        
        # Should handle the error gracefully
        assert 'response' in response
        assert response['response']['httpStatusCode'] in [400, 500]
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['success'] is False
        assert 'error' in body

class TestErrorHandlingIntegrationScenarios:
    """Test realistic error scenarios with the integrated system"""
    
    def test_complete_error_flow_image_validation(self):
        """Test complete error flow for image validation failure"""
        handler = EnhancedImageAnalysisHandler()
        
        # Test with completely invalid image data
        result = handler.validate_image_safely(
            "",  # Empty image data
            max_size=10*1024*1024,
            allowed_formats=['jpeg', 'jpg', 'png']
        )
        
        assert result.valid is False
        assert result.error != ""
        # Should contain user-friendly error message
        assert any(word in result.error.lower() for word in ['image', 'data', 'provided', 'upload'])
    
    @patch('app_with_error_handling.VisionModelClient')
    def test_complete_error_flow_vision_timeout(self, mock_vision_client):
        """Test complete error flow for vision model timeout"""
        handler = EnhancedImageAnalysisHandler()
        
        # Mock timeout error
        mock_client_instance = Mock()
        mock_client_instance.detect_media_type.return_value = "image/jpeg"
        mock_client_instance.analyze_image.side_effect = TimeoutError("Request timed out")
        mock_vision_client.return_value = mock_client_instance
        handler.vision_client = mock_client_instance
        
        result = handler.process_image_with_vision_model_safely(
            "valid_image_data",
            "Identify medication"
        )
        
        assert result.success is False
        assert result.error != ""
        # Should contain user-friendly timeout message
        assert any(word in result.error.lower() for word in ['took', 'long', 'time', 'try', 'again'])
    
    def test_privacy_compliance_in_error_logging(self):
        """Test that error logging maintains privacy compliance"""
        handler = EnhancedImageAnalysisHandler()
        
        # Create a scenario with sensitive data
        sensitive_image_data = "base64_encoded_sensitive_medical_image_data_with_patient_info"
        
        with patch('app_with_error_handling.logger') as mock_logger:
            result = handler.validate_image_safely(
                sensitive_image_data,
                max_size=100,  # Very small limit to trigger error
                allowed_formats=['jpeg']
            )
            
            # Verify error was handled
            assert result.valid is False
            
            # Check that sensitive data was not logged in plain text
            logged_calls = [call for call in mock_logger.method_calls if 'sensitive_medical_image' not in str(call)]
            # All calls should be sanitized (no sensitive data in logs)
            assert len(logged_calls) == len(mock_logger.method_calls)

if __name__ == "__main__":
    pytest.main([__file__])