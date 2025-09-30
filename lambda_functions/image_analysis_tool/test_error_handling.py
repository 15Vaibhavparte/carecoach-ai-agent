"""
Unit tests for the error handling framework.
Tests error classification, user message generation, privacy-compliant logging, and error handling workflows.
"""

import pytest
import json
import time
import logging
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from error_handling import (
    ErrorCategory,
    ErrorSeverity,
    ErrorContext,
    ErrorDetails,
    PrivacyCompliantLogger,
    ErrorClassifier,
    UserMessageGenerator,
    ErrorHandler,
    handle_lambda_error
)
from models import (
    ImageAnalysisError,
    ImageValidationError,
    VisionModelError,
    DrugInfoError
)

class TestErrorContext:
    """Test ErrorContext data class"""
    
    def test_error_context_creation(self):
        """Test creating ErrorContext with default values"""
        context = ErrorContext()
        assert context.user_id is None
        assert context.session_id is None
        assert context.request_id is None
        assert context.timestamp is not None
        assert context.operation == ""
        assert context.input_size == 0
        assert context.processing_stage == ""
    
    def test_error_context_with_values(self):
        """Test creating ErrorContext with specific values"""
        timestamp = time.time()
        context = ErrorContext(
            user_id="user123",
            session_id="session456",
            request_id="req789",
            timestamp=timestamp,
            operation="image_analysis",
            input_size=1024,
            processing_stage="validation"
        )
        
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.request_id == "req789"
        assert context.timestamp == timestamp
        assert context.operation == "image_analysis"
        assert context.input_size == 1024
        assert context.processing_stage == "validation"

class TestErrorDetails:
    """Test ErrorDetails data class"""
    
    def test_error_details_creation(self):
        """Test creating ErrorDetails with required fields"""
        context = ErrorContext(operation="test")
        details = ErrorDetails(
            category=ErrorCategory.IMAGE_PROCESSING,
            severity=ErrorSeverity.LOW,
            error_code="test_error",
            internal_message="Internal error message",
            user_message="User-friendly message",
            suggestions=["Try again"],
            context=context
        )
        
        assert details.category == ErrorCategory.IMAGE_PROCESSING
        assert details.severity == ErrorSeverity.LOW
        assert details.error_code == "test_error"
        assert details.internal_message == "Internal error message"
        assert details.user_message == "User-friendly message"
        assert details.suggestions == ["Try again"]
        assert details.context == context
        assert details.retry_possible is False
        assert details.retry_delay == 0
        assert details.metadata == {}
    
    def test_error_details_to_dict(self):
        """Test converting ErrorDetails to dictionary"""
        context = ErrorContext(operation="test")
        details = ErrorDetails(
            category=ErrorCategory.VISION_ANALYSIS,
            severity=ErrorSeverity.MEDIUM,
            error_code="vision_error",
            internal_message="Vision failed",
            user_message="Cannot analyze image",
            suggestions=["Try clearer image"],
            context=context,
            retry_possible=True,
            retry_delay=5
        )
        
        result = details.to_dict()
        assert result['category'] == 'vision_analysis'
        assert result['severity'] == 'medium'
        assert result['error_code'] == 'vision_error'
        assert result['retry_possible'] is True
        assert result['retry_delay'] == 5
        assert 'context' in result

class TestPrivacyCompliantLogger:
    """Test privacy-compliant logging functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.logger = PrivacyCompliantLogger("test_logger")
    
    def test_sanitize_sensitive_data(self):
        """Test sanitization of sensitive data"""
        sensitive_data = {
            "image_data": "base64encodedimagedata",
            "user_id": "user123",
            "session_id": "session456",
            "medication_name": "Aspirin",
            "normal_field": "normal_value"
        }
        
        sanitized = self.logger.sanitize_data(sensitive_data)
        
        assert "[IMAGE_DATA:" in sanitized["image_data"]
        assert "USER_ID_MASKED" in sanitized["user_id"]
        assert "SESSION_ID_MASKED" in sanitized["session_id"]
        assert sanitized["medication_name"] == "[SENSITIVE_DATA_MASKED]"
        assert sanitized["normal_field"] == "normal_value"
    
    def test_sanitize_nested_data(self):
        """Test sanitization of nested data structures"""
        nested_data = {
            "request": {
                "image_data": "sensitive_image_data",
                "metadata": {
                    "user_id": "user123",
                    "size": 1024
                }
            },
            "response": ["item1", "item2"]
        }
        
        sanitized = self.logger.sanitize_data(nested_data)
        
        assert "[IMAGE_DATA:" in sanitized["request"]["image_data"]
        assert "USER_ID_MASKED" in sanitized["request"]["metadata"]["user_id"]
        assert sanitized["request"]["metadata"]["size"] == 1024
        assert sanitized["response"] == ["item1", "item2"]
    
    def test_sanitize_long_strings(self):
        """Test sanitization of very long strings"""
        long_string = "x" * 2000
        data = {"long_field": long_string}
        
        sanitized = self.logger.sanitize_data(data)
        
        assert "[LONG_STRING_TRUNCATED:2000_chars]" in sanitized["long_field"]
    
    @patch('logging.getLogger')
    def test_log_error_different_severities(self, mock_get_logger):
        """Test logging errors with different severity levels"""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance
        
        logger = PrivacyCompliantLogger("test")
        context = ErrorContext(operation="test")
        
        # Test critical error
        critical_error = ErrorDetails(
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.CRITICAL,
            error_code="critical_error",
            internal_message="Critical failure",
            user_message="System error",
            suggestions=["Contact support"],
            context=context
        )
        
        logger.log_error(critical_error)
        mock_logger_instance.error.assert_called()
        
        # Test low severity error
        low_error = ErrorDetails(
            category=ErrorCategory.IMAGE_PROCESSING,
            severity=ErrorSeverity.LOW,
            error_code="low_error",
            internal_message="Minor issue",
            user_message="Please retry",
            suggestions=["Try again"],
            context=context
        )
        
        logger.log_error(low_error)
        mock_logger_instance.info.assert_called()

class TestErrorClassifier:
    """Test error classification functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.classifier = ErrorClassifier()
    
    def test_classify_by_error_code(self):
        """Test error classification by error code"""
        error = Exception("Test error")
        
        category, severity = self.classifier.classify_error(error, "invalid_format")
        assert category == ErrorCategory.IMAGE_PROCESSING
        assert severity == ErrorSeverity.LOW
        
        category, severity = self.classifier.classify_error(error, "vision_api_timeout")
        assert category == ErrorCategory.TIMEOUT_ERROR
        assert severity == ErrorSeverity.MEDIUM
        
        category, severity = self.classifier.classify_error(error, "unexpected_error")
        assert category == ErrorCategory.SYSTEM_ERROR
        assert severity == ErrorSeverity.HIGH
    
    def test_classify_by_exception_type(self):
        """Test error classification by exception type"""
        # Test ImageValidationError
        img_error = ImageValidationError("Invalid image")
        category, severity = self.classifier.classify_error(img_error)
        assert category == ErrorCategory.IMAGE_PROCESSING
        assert severity == ErrorSeverity.LOW
        
        # Test VisionModelError
        vision_error = VisionModelError("Vision model failed")
        category, severity = self.classifier.classify_error(vision_error)
        assert category == ErrorCategory.VISION_ANALYSIS
        assert severity == ErrorSeverity.MEDIUM
        
        # Test DrugInfoError
        drug_error = DrugInfoError("Drug info failed")
        category, severity = self.classifier.classify_error(drug_error)
        assert category == ErrorCategory.DRUG_LOOKUP
        assert severity == ErrorSeverity.MEDIUM
        
        # Test TimeoutError
        timeout_error = TimeoutError("Request timed out")
        category, severity = self.classifier.classify_error(timeout_error)
        assert category == ErrorCategory.TIMEOUT_ERROR
        assert severity == ErrorSeverity.MEDIUM
        
        # Test MemoryError
        memory_error = MemoryError("Out of memory")
        category, severity = self.classifier.classify_error(memory_error)
        assert category == ErrorCategory.SYSTEM_ERROR
        assert severity == ErrorSeverity.HIGH
        
        # Test generic Exception
        generic_error = Exception("Unknown error")
        category, severity = self.classifier.classify_error(generic_error)
        assert category == ErrorCategory.SYSTEM_ERROR
        assert severity == ErrorSeverity.HIGH
    
    def test_error_code_priority(self):
        """Test that error code takes priority over exception type"""
        # Even though this is a VisionModelError, the error code should take priority
        vision_error = VisionModelError("Vision failed")
        category, severity = self.classifier.classify_error(vision_error, "file_too_large")
        
        assert category == ErrorCategory.IMAGE_PROCESSING
        assert severity == ErrorSeverity.LOW

class TestUserMessageGenerator:
    """Test user message generation functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.generator = UserMessageGenerator()
    
    def test_generate_image_processing_messages(self):
        """Test generating messages for image processing errors"""
        result = self.generator.generate_user_message(ErrorCategory.IMAGE_PROCESSING, "invalid_format")
        
        assert "format is not supported" in result["message"]
        assert len(result["suggestions"]) > 0
        assert any("JPEG" in suggestion for suggestion in result["suggestions"])
    
    def test_generate_vision_analysis_messages(self):
        """Test generating messages for vision analysis errors"""
        result = self.generator.generate_user_message(ErrorCategory.VISION_ANALYSIS, "low_confidence")
        
        assert "Unable to clearly identify" in result["message"]
        assert len(result["suggestions"]) > 0
        assert any("clearer photo" in suggestion for suggestion in result["suggestions"])
    
    def test_generate_drug_lookup_messages(self):
        """Test generating messages for drug lookup errors"""
        result = self.generator.generate_user_message(ErrorCategory.DRUG_LOOKUP, "drug_not_found")
        
        assert "not available" in result["message"]
        assert len(result["suggestions"]) > 0
        assert any("healthcare provider" in suggestion for suggestion in result["suggestions"])
    
    def test_generate_default_messages(self):
        """Test generating default messages for unknown error codes"""
        result = self.generator.generate_user_message(ErrorCategory.SYSTEM_ERROR, "unknown_code")
        
        assert "unexpected error" in result["message"]
        assert len(result["suggestions"]) > 0
        assert any("try again" in suggestion.lower() for suggestion in result["suggestions"])
    
    def test_generate_timeout_messages(self):
        """Test generating messages for timeout errors"""
        result = self.generator.generate_user_message(ErrorCategory.TIMEOUT_ERROR)
        
        assert "took too long" in result["message"]
        assert len(result["suggestions"]) > 0
        assert any("smaller image" in suggestion for suggestion in result["suggestions"])

class TestErrorHandler:
    """Test the main error handler functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = ErrorHandler()
    
    def test_handle_error_complete_workflow(self):
        """Test complete error handling workflow"""
        error = ImageValidationError("Invalid image format")
        context = ErrorContext(
            operation="image_validation",
            processing_stage="format_check",
            input_size=1024
        )
        
        error_details = self.handler.handle_error(error, context, "invalid_format")
        
        assert error_details.category == ErrorCategory.IMAGE_PROCESSING
        assert error_details.severity == ErrorSeverity.LOW
        assert error_details.error_code == "invalid_format"
        assert error_details.internal_message == "Invalid image format"
        assert "format is not supported" in error_details.user_message
        assert len(error_details.suggestions) > 0
        assert error_details.context == context
        assert "ImageValidationError" in error_details.metadata["error_type"]
    
    def test_retry_logic(self):
        """Test retry possibility and delay logic"""
        # Test retry possible for timeout error
        timeout_error = TimeoutError("Request timed out")
        context = ErrorContext(operation="vision_analysis")
        
        error_details = self.handler.handle_error(timeout_error, context, "vision_api_timeout")
        
        assert error_details.retry_possible is True
        assert error_details.retry_delay > 0
        
        # Test no retry for image processing error
        img_error = ImageValidationError("Invalid format")
        error_details = self.handler.handle_error(img_error, context, "invalid_format")
        
        assert error_details.retry_possible is False
        assert error_details.retry_delay == 0
    
    def test_create_error_response(self):
        """Test creating standardized error response"""
        error = VisionModelError("Vision failed")
        context = ErrorContext(operation="vision_analysis")
        
        error_details = self.handler.handle_error(error, context, "vision_api_error")
        
        event = {
            "actionGroup": "image_analysis",
            "apiPath": "/analyze",
            "httpMethod": "POST"
        }
        
        response = self.handler.create_error_response(error_details, event)
        
        assert response["messageVersion"] == "1.0"
        assert response["response"]["actionGroup"] == "image_analysis"
        assert response["response"]["httpStatusCode"] == 400
        
        body = json.loads(response["response"]["responseBody"]["application/json"]["body"])
        assert body["success"] is False
        assert "error" in body
        assert "suggestions" in body
        assert "retry_possible" in body
    
    def test_critical_error_response_code(self):
        """Test that critical errors return 500 status code"""
        error = Exception("Critical system failure")
        context = ErrorContext(operation="system")
        
        error_details = self.handler.handle_error(error, context, "unexpected_error")
        error_details.severity = ErrorSeverity.CRITICAL
        
        event = {"actionGroup": "test", "apiPath": "/test", "httpMethod": "POST"}
        response = self.handler.create_error_response(error_details, event)
        
        assert response["response"]["httpStatusCode"] == 500

class TestHandleLambdaError:
    """Test the convenience function for Lambda error handling"""
    
    def test_handle_lambda_error_basic(self):
        """Test basic Lambda error handling"""
        error = ImageValidationError("Invalid image")
        event = {
            "actionGroup": "image_analysis",
            "apiPath": "/analyze",
            "httpMethod": "POST"
        }
        
        response = handle_lambda_error(error, event)
        
        assert "messageVersion" in response
        assert "response" in response
        
        body = json.loads(response["response"]["responseBody"]["application/json"]["body"])
        assert body["success"] is False
        assert "error" in body
    
    def test_handle_lambda_error_with_context(self):
        """Test Lambda error handling with additional context"""
        error = VisionModelError("Vision API failed")
        event = {
            "actionGroup": "image_analysis",
            "apiPath": "/analyze",
            "httpMethod": "POST"
        }
        context_info = {
            "request_id": "req123",
            "operation": "image_analysis",
            "stage": "vision_processing"
        }
        
        response = handle_lambda_error(error, event, context_info)
        
        assert "messageVersion" in response
        body = json.loads(response["response"]["responseBody"]["application/json"]["body"])
        assert body["success"] is False

class TestErrorHandlingIntegration:
    """Integration tests for error handling components"""
    
    def test_end_to_end_error_handling(self):
        """Test complete end-to-end error handling flow"""
        # Simulate a complex error scenario
        original_error = VisionModelError("Vision model timeout")
        context = ErrorContext(
            user_id="user123",
            operation="medication_identification",
            processing_stage="vision_analysis",
            input_size=2048
        )
        
        handler = ErrorHandler()
        
        # Handle the error
        error_details = handler.handle_error(
            original_error, 
            context, 
            "vision_api_timeout",
            include_traceback=True
        )
        
        # Verify all components worked together
        assert error_details.category == ErrorCategory.TIMEOUT_ERROR
        assert error_details.severity == ErrorSeverity.MEDIUM
        assert error_details.retry_possible is True
        assert error_details.retry_delay > 0
        assert len(error_details.suggestions) > 0
        assert "VisionModelError" in error_details.metadata["error_type"]
        
        # Create response
        event = {"actionGroup": "test", "apiPath": "/test", "httpMethod": "POST"}
        response = handler.create_error_response(error_details, event)
        
        body = json.loads(response["response"]["responseBody"]["application/json"]["body"])
        assert body["retry_possible"] is True
        assert "retry_after" in body
    
    def test_privacy_compliance_in_full_flow(self):
        """Test that privacy compliance is maintained throughout the flow"""
        # Create error with sensitive data in context
        error = ImageValidationError("Image validation failed")
        context = ErrorContext(
            user_id="sensitive_user_123",
            session_id="sensitive_session_456",
            operation="image_validation"
        )
        context.metadata = {
            "image_data": "base64_sensitive_image_data",
            "user_info": "sensitive_personal_info"
        }
        
        handler = ErrorHandler()
        
        # Capture log output - invalid_format is LOW severity, so it uses info logging
        with patch.object(handler.logger.logger, 'info') as mock_log:
            error_details = handler.handle_error(error, context, "invalid_format")
            
            # Verify logging was called
            mock_log.assert_called_once()
            
            # Get the logged message
            logged_message = mock_log.call_args[0][0]
            
            # Verify sensitive data was sanitized
            assert "sensitive_user_123" not in logged_message
            assert "sensitive_session_456" not in logged_message
            assert "base64_sensitive_image_data" not in logged_message
            assert "sensitive_personal_info" not in logged_message
            
            # Verify sanitization markers are present
            assert "USER_ID_MASKED" in logged_message or "SENSITIVE_DATA_MASKED" in logged_message

if __name__ == "__main__":
    pytest.main([__file__])