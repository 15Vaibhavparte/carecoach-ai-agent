"""
Unit tests for error scenario handlers.
Tests specific error scenarios, timeout/retry logic, and error handling workflows.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Callable

from error_scenarios import (
    RetryConfig,
    TimeoutHandler,
    RetryHandler,
    ImageProcessingErrorHandler,
    VisionModelErrorHandler,
    DrugInfoErrorHandler,
    NetworkErrorHandler,
    ErrorScenarioManager,
    handle_image_validation_error,
    handle_vision_model_error,
    handle_drug_info_error,
    create_safe_operation
)
from error_handling import ErrorCategory, ErrorContext
from models import (
    ImageValidationError,
    VisionModelError,
    DrugInfoError
)

class TestRetryConfig:
    """Test retry configuration"""
    
    def test_default_config(self):
        """Test default retry configuration"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_custom_config(self):
        """Test custom retry configuration"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=1.5,
            jitter=False
        )
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter is False
    
    def test_get_delay_exponential(self):
        """Test exponential backoff delay calculation"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        assert config.get_delay(0) == 0
        assert config.get_delay(1) == 1.0
        assert config.get_delay(2) == 2.0
        assert config.get_delay(3) == 4.0
    
    def test_get_delay_max_cap(self):
        """Test that delay is capped at max_delay"""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, exponential_base=2.0, jitter=False)
        
        assert config.get_delay(1) == 10.0
        assert config.get_delay(2) == 15.0  # Capped at max_delay
        assert config.get_delay(3) == 15.0  # Still capped
    
    def test_get_delay_with_jitter(self):
        """Test that jitter adds randomness to delay"""
        config = RetryConfig(base_delay=10.0, jitter=True)
        
        delays = [config.get_delay(1) for _ in range(10)]
        
        # All delays should be around 10.0 but with some variation
        assert all(9.0 <= delay <= 11.0 for delay in delays)
        # Should have some variation (not all exactly the same)
        assert len(set(delays)) > 1

class TestTimeoutHandler:
    """Test timeout handling"""
    
    def test_default_timeout(self):
        """Test default timeout configuration"""
        handler = TimeoutHandler()
        assert handler.default_timeout == 30.0
        assert handler.get_timeout('unknown_operation') == 30.0
    
    def test_operation_specific_timeouts(self):
        """Test operation-specific timeouts"""
        handler = TimeoutHandler()
        assert handler.get_timeout('image_validation') == 5.0
        assert handler.get_timeout('vision_analysis') == 30.0
        assert handler.get_timeout('drug_info_lookup') == 15.0
    
    def test_with_timeout_decorator_success(self):
        """Test timeout decorator with successful operation"""
        handler = TimeoutHandler()
        
        @handler.with_timeout('image_validation')
        def fast_operation():
            time.sleep(0.1)
            return "success"
        
        result = fast_operation()
        assert result == "success"
    
    def test_with_timeout_decorator_timeout(self):
        """Test timeout decorator with operation that times out"""
        handler = TimeoutHandler()
        handler.operation_timeouts['test_operation'] = 0.1  # Very short timeout
        
        @handler.with_timeout('test_operation')
        def slow_operation():
            time.sleep(0.2)  # Longer than timeout
            return "success"
        
        with pytest.raises(TimeoutError) as exc_info:
            slow_operation()
        
        assert "took too long" in str(exc_info.value)

class TestRetryHandler:
    """Test retry handling"""
    
    def test_successful_operation_no_retry(self):
        """Test that successful operations don't retry"""
        handler = RetryHandler()
        call_count = 0
        
        @handler.with_retry()
        def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_operation()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_exception(self):
        """Test retry behavior on exceptions"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        handler = RetryHandler(config)
        call_count = 0
        
        @handler.with_retry(retry_on=(ValueError,))
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = failing_operation()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """Test behavior when all retry attempts are exhausted"""
        config = RetryConfig(max_attempts=2, base_delay=0.01, jitter=False)
        handler = RetryHandler(config)
        call_count = 0
        
        @handler.with_retry(retry_on=(ValueError,))
        def always_failing_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError) as exc_info:
            always_failing_operation()
        
        assert "Always fails" in str(exc_info.value)
        assert call_count == 2
    
    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried"""
        handler = RetryHandler()
        call_count = 0
        
        @handler.with_retry(retry_on=(ValueError,))
        def operation_with_non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Non-retryable error")
        
        with pytest.raises(TypeError):
            operation_with_non_retryable_error()
        
        assert call_count == 1  # Should not retry

class TestImageProcessingErrorHandler:
    """Test image processing error handling"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = ImageProcessingErrorHandler()
        self.context = ErrorContext(operation="image_processing")
    
    def test_handle_validation_error_invalid_format(self):
        """Test handling invalid format error"""
        error = Exception("Invalid image format")
        image_data = "invalid_base64_data"
        
        error_details = self.handler.handle_validation_error(error, image_data, self.context)
        
        assert error_details.category == ErrorCategory.IMAGE_PROCESSING
        assert error_details.error_code == "invalid_format"
        assert "format is not supported" in error_details.user_message
    
    def test_handle_validation_error_file_too_large(self):
        """Test handling file too large error"""
        error = Exception("File size exceeds limit")
        image_data = "base64_data"
        
        error_details = self.handler.handle_validation_error(error, image_data, self.context)
        
        assert error_details.error_code == "file_too_large"
        assert "too large" in error_details.user_message
    
    def test_handle_validation_error_no_image_data(self):
        """Test handling no image data error"""
        error = Exception("No image provided")
        image_data = ""
        
        error_details = self.handler.handle_validation_error(error, image_data, self.context)
        
        assert error_details.error_code == "no_image_data"
    
    def test_handle_preprocessing_error_memory(self):
        """Test handling memory error during preprocessing"""
        error = Exception("Out of memory during processing")
        
        error_details = self.handler.handle_preprocessing_error(error, self.context)
        
        assert error_details.error_code == "memory_error"
    
    def test_handle_preprocessing_error_format(self):
        """Test handling format error during preprocessing"""
        error = Exception("Invalid format detected")
        
        error_details = self.handler.handle_preprocessing_error(error, self.context)
        
        assert error_details.error_code == "invalid_format"
    
    def test_validate_with_timeout(self):
        """Test validation with timeout"""
        def mock_validator(data):
            return f"validated_{data}"
        
        result = self.handler.validate_with_timeout(mock_validator, "test_data")
        assert result == "validated_test_data"
    
    @patch('time.sleep')
    def test_preprocess_with_retry(self, mock_sleep):
        """Test preprocessing with retry logic"""
        call_count = 0
        
        def mock_preprocessor(data):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network issue")
            return f"processed_{data}"
        
        result = self.handler.preprocess_with_retry(mock_preprocessor, "test_data")
        assert result == "processed_test_data"
        assert call_count == 2
        mock_sleep.assert_called_once()

class TestVisionModelErrorHandler:
    """Test vision model error handling"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = VisionModelErrorHandler()
        self.context = ErrorContext(operation="vision_analysis")
    
    def test_handle_vision_error_timeout(self):
        """Test handling vision model timeout error"""
        error = Exception("Request timeout occurred")
        
        error_details = self.handler.handle_vision_error(error, self.context)
        
        assert error_details.category == ErrorCategory.TIMEOUT_ERROR
        assert error_details.error_code == "vision_api_timeout"
    
    def test_handle_vision_error_rate_limit(self):
        """Test handling rate limit error"""
        error = Exception("Rate limit exceeded")
        
        error_details = self.handler.handle_vision_error(error, self.context)
        
        assert error_details.category == ErrorCategory.RATE_LIMIT_ERROR
        assert error_details.error_code == "rate_limit_exceeded"
    
    def test_handle_vision_error_unavailable(self):
        """Test handling service unavailable error"""
        error = Exception("Service temporarily unavailable")
        
        error_details = self.handler.handle_vision_error(error, self.context)
        
        assert error_details.error_code == "model_unavailable"
    
    def test_handle_low_confidence(self):
        """Test handling low confidence identification"""
        confidence = 0.3
        threshold = 0.8
        
        error_details = self.handler.handle_low_confidence(confidence, threshold, self.context)
        
        assert error_details.error_code == "low_confidence"
        assert error_details.context.metadata['confidence'] == confidence
        assert error_details.context.metadata['threshold'] == threshold
    
    def test_handle_no_medication_detected(self):
        """Test handling no medication detected"""
        error_details = self.handler.handle_no_medication_detected(self.context)
        
        assert error_details.error_code == "no_medication_detected"
        assert "No medication" in error_details.user_message
    
    def test_analyze_with_timeout(self):
        """Test vision analysis with timeout"""
        def mock_vision_func(image_data):
            return f"analyzed_{image_data}"
        
        result = self.handler.analyze_with_timeout(mock_vision_func, "test_image")
        assert result == "analyzed_test_image"
    
    @patch('time.sleep')
    def test_analyze_with_retry(self, mock_sleep):
        """Test vision analysis with retry logic"""
        call_count = 0
        
        def mock_vision_func(image_data):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise VisionModelError("Temporary vision model error")
            return f"analyzed_{image_data}"
        
        result = self.handler.analyze_with_retry(mock_vision_func, "test_image")
        assert result == "analyzed_test_image"
        assert call_count == 2
        mock_sleep.assert_called_once()

class TestDrugInfoErrorHandler:
    """Test drug info error handling"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = DrugInfoErrorHandler()
        self.context = ErrorContext(operation="drug_lookup")
    
    def test_handle_drug_info_error_not_found(self):
        """Test handling drug not found error"""
        error = Exception("Drug not found in database")
        drug_name = "UnknownDrug"
        
        error_details = self.handler.handle_drug_info_error(error, drug_name, self.context)
        
        assert error_details.error_code == "drug_not_found"
        assert error_details.context.metadata['drug_name'] == drug_name
    
    def test_handle_drug_info_error_timeout(self):
        """Test handling drug info timeout error"""
        error = Exception("Request timeout")
        drug_name = "Aspirin"
        
        error_details = self.handler.handle_drug_info_error(error, drug_name, self.context)
        
        assert error_details.error_code == "drug_api_timeout"
    
    def test_handle_drug_not_found(self):
        """Test handling drug not found scenario"""
        drug_name = "NonExistentDrug"
        
        error_details = self.handler.handle_drug_not_found(drug_name, self.context)
        
        assert error_details.error_code == "drug_not_found"
        assert error_details.context.metadata['drug_name'] == drug_name
        assert error_details.context.metadata['found'] is False
    
    def test_lookup_with_timeout(self):
        """Test drug lookup with timeout"""
        def mock_lookup_func(drug_name):
            return f"info_for_{drug_name}"
        
        result = self.handler.lookup_with_timeout(mock_lookup_func, "Aspirin")
        assert result == "info_for_Aspirin"
    
    @patch('time.sleep')
    def test_lookup_with_retry(self, mock_sleep):
        """Test drug lookup with retry logic"""
        call_count = 0
        
        def mock_lookup_func(drug_name):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return f"info_for_{drug_name}"
        
        result = self.handler.lookup_with_retry(mock_lookup_func, "Aspirin")
        assert result == "info_for_Aspirin"
        assert call_count == 2
        mock_sleep.assert_called_once()

class TestNetworkErrorHandler:
    """Test network error handling"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = NetworkErrorHandler()
        self.context = ErrorContext(operation="network_request")
    
    def test_handle_network_error_timeout(self):
        """Test handling network timeout error"""
        error = Exception("Connection timeout")
        
        error_details = self.handler.handle_network_error(error, self.context)
        
        assert error_details.error_code == "network_timeout"
    
    def test_handle_network_error_connection(self):
        """Test handling connection error"""
        error = Exception("Connection refused")
        
        error_details = self.handler.handle_network_error(error, self.context)
        
        assert error_details.error_code == "connection_error"
    
    def test_handle_network_error_dns(self):
        """Test handling DNS error"""
        error = Exception("DNS resolution failed")
        
        error_details = self.handler.handle_network_error(error, self.context)
        
        assert error_details.error_code == "dns_error"
    
    @patch('time.sleep')
    def test_request_with_retry(self, mock_sleep):
        """Test network request with retry logic"""
        call_count = 0
        
        def mock_request_func(url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return f"response_from_{url}"
        
        result = self.handler.request_with_retry(mock_request_func, "http://example.com")
        assert result == "response_from_http://example.com"
        assert call_count == 3
        assert mock_sleep.call_count == 2

class TestErrorScenarioManager:
    """Test error scenario manager"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = ErrorScenarioManager()
        self.context = ErrorContext(operation="test_operation")
    
    def test_handle_error_by_category_image_processing(self):
        """Test routing image processing errors"""
        error = Exception("Image validation failed")
        
        error_details = self.manager.handle_error_by_category(
            error,
            ErrorCategory.IMAGE_PROCESSING,
            self.context,
            image_data="test_data"
        )
        
        assert error_details.category == ErrorCategory.IMAGE_PROCESSING
    
    def test_handle_error_by_category_vision_analysis(self):
        """Test routing vision analysis errors"""
        error = Exception("Vision model failed")
        
        error_details = self.manager.handle_error_by_category(
            error,
            ErrorCategory.VISION_ANALYSIS,
            self.context
        )
        
        assert error_details.category == ErrorCategory.VISION_ANALYSIS
    
    def test_handle_error_by_category_drug_lookup(self):
        """Test routing drug lookup errors"""
        error = Exception("Drug not found")
        
        error_details = self.manager.handle_error_by_category(
            error,
            ErrorCategory.DRUG_LOOKUP,
            self.context,
            drug_name="Aspirin"
        )
        
        assert error_details.category == ErrorCategory.DRUG_LOOKUP
    
    def test_create_safe_operation_success(self):
        """Test creating safe operation that succeeds"""
        def test_operation(x, y):
            return x + y
        
        safe_op = self.manager.create_safe_operation(
            "test_add",
            test_operation,
            ErrorCategory.SYSTEM_ERROR,
            use_timeout=False,
            use_retry=False
        )
        
        result = safe_op(2, 3)
        assert result == 5
    
    def test_create_safe_operation_with_error(self):
        """Test creating safe operation that handles errors"""
        def failing_operation():
            raise ValueError("Test error")
        
        safe_op = self.manager.create_safe_operation(
            "test_fail",
            failing_operation,
            ErrorCategory.SYSTEM_ERROR,
            use_timeout=False,
            use_retry=False
        )
        
        with pytest.raises(ValueError) as exc_info:
            safe_op()
        
        # Should have user-friendly error message
        assert "unexpected error" in str(exc_info.value).lower()

class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.context = ErrorContext(operation="test")
    
    def test_handle_image_validation_error(self):
        """Test image validation error convenience function"""
        error = Exception("Invalid image")
        image_data = "test_data"
        
        error_details = handle_image_validation_error(error, image_data, self.context)
        
        assert error_details.category == ErrorCategory.IMAGE_PROCESSING
    
    def test_handle_vision_model_error(self):
        """Test vision model error convenience function"""
        error = Exception("Vision failed")
        
        error_details = handle_vision_model_error(error, self.context)
        
        assert error_details.category == ErrorCategory.VISION_ANALYSIS
    
    def test_handle_drug_info_error(self):
        """Test drug info error convenience function"""
        error = Exception("Drug lookup failed")
        drug_name = "Aspirin"
        
        error_details = handle_drug_info_error(error, drug_name, self.context)
        
        assert error_details.category == ErrorCategory.DRUG_LOOKUP
    
    def test_create_safe_operation_convenience(self):
        """Test create safe operation convenience function"""
        def test_func(x):
            return x * 2
        
        safe_func = create_safe_operation(
            "test_multiply",
            test_func,
            ErrorCategory.SYSTEM_ERROR,
            use_timeout=False,
            use_retry=False
        )
        
        result = safe_func(5)
        assert result == 10

class TestErrorScenariosIntegration:
    """Integration tests for error scenarios"""
    
    def test_end_to_end_image_processing_error(self):
        """Test complete image processing error flow"""
        manager = ErrorScenarioManager()
        context = ErrorContext(
            operation="image_validation",
            processing_stage="format_check"
        )
        
        # Simulate image validation error
        error = ImageValidationError("Unsupported image format: BMP")
        
        error_details = manager.handle_error_by_category(
            error,
            ErrorCategory.IMAGE_PROCESSING,
            context,
            image_data="invalid_bmp_data"
        )
        
        assert error_details.category == ErrorCategory.IMAGE_PROCESSING
        assert error_details.error_code == "invalid_format"
        assert "format is not supported" in error_details.user_message
        assert len(error_details.suggestions) > 0
        assert any("JPEG" in suggestion for suggestion in error_details.suggestions)
    
    def test_end_to_end_vision_model_error_with_retry(self):
        """Test complete vision model error flow with retry"""
        handler = VisionModelErrorHandler()
        call_count = 0
        
        def mock_vision_analysis(image_data):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise VisionModelError("Temporary API error")
            return {"medication": "Aspirin", "confidence": 0.9}
        
        with patch('time.sleep'):  # Speed up test
            result = handler.analyze_with_retry(mock_vision_analysis, "test_image")
        
        assert result["medication"] == "Aspirin"
        assert call_count == 3
    
    def test_end_to_end_timeout_scenario(self):
        """Test complete timeout scenario"""
        timeout_handler = TimeoutHandler()
        timeout_handler.operation_timeouts['test_slow_op'] = 0.1
        
        @timeout_handler.with_timeout('test_slow_op')
        def slow_operation():
            time.sleep(0.2)  # Longer than timeout
            return "completed"
        
        with pytest.raises(TimeoutError) as exc_info:
            slow_operation()
        
        assert "took too long" in str(exc_info.value)

if __name__ == "__main__":
    pytest.main([__file__])