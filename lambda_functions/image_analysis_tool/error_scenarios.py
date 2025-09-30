"""
Specific error scenario handlers for the image analysis tool.
This module implements handlers for image processing errors, vision model failures,
DrugInfoTool integration errors, and timeout/retry logic with exponential backoff.
"""

import time
import random
import asyncio
from typing import Dict, Any, Optional, Callable, Tuple
from functools import wraps
import logging

from error_handling import (
    ErrorCategory,
    ErrorSeverity,
    ErrorContext,
    ErrorDetails,
    ErrorHandler,
    error_handler
)
from models import (
    ImageAnalysisError,
    ImageValidationError,
    VisionModelError,
    DrugInfoError,
    ImageValidationResult,
    VisionModelResponse,
    DrugInfoResult
)

logger = logging.getLogger(__name__)

class RetryConfig:
    """Configuration for retry logic"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number"""
        if attempt <= 0:
            return 0
        
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)

class TimeoutHandler:
    """Handles timeout scenarios with configurable timeouts"""
    
    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self.operation_timeouts = {
            'image_validation': 5.0,
            'image_preprocessing': 10.0,
            'vision_analysis': 30.0,
            'drug_info_lookup': 15.0,
            'response_synthesis': 5.0
        }
    
    def get_timeout(self, operation: str) -> float:
        """Get timeout for specific operation"""
        return self.operation_timeouts.get(operation, self.default_timeout)
    
    def with_timeout(self, operation: str):
        """Decorator to add timeout to operations"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                timeout = self.get_timeout(operation)
                start_time = time.time()
                
                try:
                    # For synchronous functions, we'll use a simple time check
                    result = func(*args, **kwargs)
                    
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        raise TimeoutError(f"Operation '{operation}' exceeded timeout of {timeout}s (took {elapsed:.2f}s)")
                    
                    return result
                    
                except Exception as e:
                    elapsed = time.time() - start_time
                    if elapsed > timeout or isinstance(e, TimeoutError):
                        context = ErrorContext(
                            operation=operation,
                            processing_stage='timeout_check',
                            metadata={'timeout': timeout, 'elapsed': elapsed}
                        )
                        error_details = error_handler.handle_error(
                            TimeoutError(f"Operation '{operation}' timed out after {elapsed:.2f}s"),
                            context,
                            f"{operation}_timeout"
                        )
                        raise TimeoutError(error_details.user_message) from e
                    raise
            
            return wrapper
        return decorator

class RetryHandler:
    """Handles retry logic with exponential backoff"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
    
    def with_retry(
        self,
        retry_on: Tuple[type, ...] = (Exception,),
        config: RetryConfig = None
    ):
        """Decorator to add retry logic to operations"""
        retry_config = config or self.config
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(1, retry_config.max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    
                    except retry_on as e:
                        last_exception = e
                        
                        if attempt == retry_config.max_attempts:
                            # Final attempt failed, don't retry
                            break
                        
                        delay = retry_config.get_delay(attempt)
                        
                        logger.warning(
                            f"Attempt {attempt}/{retry_config.max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.2f}s"
                        )
                        
                        time.sleep(delay)
                    
                    except Exception as e:
                        # Non-retryable exception
                        raise e
                
                # All attempts failed
                raise last_exception
            
            return wrapper
        return decorator

class ImageProcessingErrorHandler:
    """Handles image processing specific errors"""
    
    def __init__(self):
        self.timeout_handler = TimeoutHandler()
        self.retry_handler = RetryHandler()
    
    def handle_validation_error(self, error: Exception, image_data: str, context: ErrorContext) -> ErrorDetails:
        """Handle image validation errors"""
        error_code = self._classify_validation_error(error, image_data)
        
        return error_handler.handle_error(
            ImageValidationError(str(error)),
            context,
            error_code
        )
    
    def handle_preprocessing_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle image preprocessing errors"""
        error_code = "preprocessing_failed"
        
        if "memory" in str(error).lower():
            error_code = "memory_error"
        elif "format" in str(error).lower():
            error_code = "invalid_format"
        elif "corrupted" in str(error).lower():
            error_code = "corrupted_image"
        
        return error_handler.handle_error(
            ImageValidationError(str(error)),
            context,
            error_code
        )
    
    def _classify_validation_error(self, error: Exception, image_data: str) -> str:
        """Classify validation error based on error message and image data"""
        error_msg = str(error).lower()
        
        if "format" in error_msg or "invalid" in error_msg:
            return "invalid_format"
        elif "size" in error_msg or "large" in error_msg:
            return "file_too_large"
        elif "corrupted" in error_msg or "damaged" in error_msg:
            return "corrupted_image"
        elif not image_data or image_data.strip() == "":
            return "no_image_data"
        else:
            return "preprocessing_failed"
    
    @TimeoutHandler().with_timeout('image_validation')
    def validate_with_timeout(self, validator_func: Callable, *args, **kwargs):
        """Validate image with timeout protection"""
        return validator_func(*args, **kwargs)
    
    @RetryHandler().with_retry(retry_on=(ConnectionError, TimeoutError))
    def preprocess_with_retry(self, preprocessor_func: Callable, *args, **kwargs):
        """Preprocess image with retry logic"""
        return preprocessor_func(*args, **kwargs)

class VisionModelErrorHandler:
    """Handles vision model specific errors"""
    
    def __init__(self):
        self.timeout_handler = TimeoutHandler()
        self.retry_handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0)
        )
    
    def handle_vision_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle vision model errors"""
        error_code = self._classify_vision_error(error)
        
        return error_handler.handle_error(
            VisionModelError(str(error)),
            context,
            error_code
        )
    
    def handle_low_confidence(self, confidence: float, threshold: float, context: ErrorContext) -> ErrorDetails:
        """Handle low confidence identification"""
        context.metadata.update({
            'confidence': confidence,
            'threshold': threshold
        })
        
        return error_handler.handle_error(
            VisionModelError(f"Low confidence identification: {confidence:.2f} < {threshold:.2f}"),
            context,
            "low_confidence"
        )
    
    def handle_no_medication_detected(self, context: ErrorContext) -> ErrorDetails:
        """Handle case where no medication is detected"""
        return error_handler.handle_error(
            VisionModelError("No medication detected in image"),
            context,
            "no_medication_detected"
        )
    
    def _classify_vision_error(self, error: Exception) -> str:
        """Classify vision model error based on error message"""
        error_msg = str(error).lower()
        
        if "timeout" in error_msg:
            return "vision_api_timeout"
        elif "rate limit" in error_msg or "throttle" in error_msg:
            return "rate_limit_exceeded"
        elif "unavailable" in error_msg or "service" in error_msg:
            return "model_unavailable"
        elif "authentication" in error_msg or "unauthorized" in error_msg:
            return "authentication_error"
        elif "network" in error_msg or "connection" in error_msg:
            return "network_error"
        else:
            return "vision_api_error"
    
    @TimeoutHandler().with_timeout('vision_analysis')
    def analyze_with_timeout(self, vision_func: Callable, *args, **kwargs):
        """Analyze image with timeout protection"""
        return vision_func(*args, **kwargs)
    
    @RetryHandler().with_retry(
        retry_on=(ConnectionError, TimeoutError, VisionModelError),
        config=RetryConfig(max_attempts=3, base_delay=2.0)
    )
    def analyze_with_retry(self, vision_func: Callable, *args, **kwargs):
        """Analyze image with retry logic"""
        return vision_func(*args, **kwargs)

class DrugInfoErrorHandler:
    """Handles DrugInfoTool integration errors"""
    
    def __init__(self):
        self.timeout_handler = TimeoutHandler()
        self.retry_handler = RetryHandler(
            RetryConfig(max_attempts=2, base_delay=1.0, max_delay=10.0)
        )
    
    def handle_drug_info_error(self, error: Exception, drug_name: str, context: ErrorContext) -> ErrorDetails:
        """Handle drug information retrieval errors"""
        error_code = self._classify_drug_info_error(error, drug_name)
        
        context.metadata.update({
            'drug_name': drug_name,
            'search_attempted': True
        })
        
        return error_handler.handle_error(
            DrugInfoError(str(error)),
            context,
            error_code
        )
    
    def handle_drug_not_found(self, drug_name: str, context: ErrorContext) -> ErrorDetails:
        """Handle case where drug is not found in database"""
        context.metadata.update({
            'drug_name': drug_name,
            'search_attempted': True,
            'found': False
        })
        
        return error_handler.handle_error(
            DrugInfoError(f"Drug '{drug_name}' not found in database"),
            context,
            "drug_not_found"
        )
    
    def _classify_drug_info_error(self, error: Exception, drug_name: str) -> str:
        """Classify drug info error based on error message"""
        error_msg = str(error).lower()
        
        if "not found" in error_msg or "404" in error_msg:
            return "drug_not_found"
        elif "timeout" in error_msg:
            return "drug_api_timeout"
        elif "network" in error_msg or "connection" in error_msg:
            return "network_error"
        elif "authentication" in error_msg or "unauthorized" in error_msg:
            return "authentication_error"
        else:
            return "drug_api_error"
    
    @TimeoutHandler().with_timeout('drug_info_lookup')
    def lookup_with_timeout(self, lookup_func: Callable, *args, **kwargs):
        """Lookup drug info with timeout protection"""
        return lookup_func(*args, **kwargs)
    
    @RetryHandler().with_retry(
        retry_on=(ConnectionError, TimeoutError),
        config=RetryConfig(max_attempts=2, base_delay=1.0)
    )
    def lookup_with_retry(self, lookup_func: Callable, *args, **kwargs):
        """Lookup drug info with retry logic"""
        return lookup_func(*args, **kwargs)

class NetworkErrorHandler:
    """Handles network-related errors"""
    
    def __init__(self):
        self.retry_handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=1.0, max_delay=15.0)
        )
    
    def handle_network_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle network errors"""
        error_code = self._classify_network_error(error)
        
        return error_handler.handle_error(
            error,
            context,
            error_code
        )
    
    def _classify_network_error(self, error: Exception) -> str:
        """Classify network error"""
        error_msg = str(error).lower()
        
        if "timeout" in error_msg:
            return "network_timeout"
        elif "connection" in error_msg:
            return "connection_error"
        elif "dns" in error_msg:
            return "dns_error"
        else:
            return "network_error"
    
    @RetryHandler().with_retry(
        retry_on=(ConnectionError, TimeoutError),
        config=RetryConfig(max_attempts=3, base_delay=2.0, exponential_base=1.5)
    )
    def request_with_retry(self, request_func: Callable, *args, **kwargs):
        """Make network request with retry logic"""
        return request_func(*args, **kwargs)

class ErrorScenarioManager:
    """Main manager for all error scenarios"""
    
    def __init__(self):
        self.image_handler = ImageProcessingErrorHandler()
        self.vision_handler = VisionModelErrorHandler()
        self.drug_info_handler = DrugInfoErrorHandler()
        self.network_handler = NetworkErrorHandler()
    
    def handle_error_by_category(
        self,
        error: Exception,
        category: ErrorCategory,
        context: ErrorContext,
        **kwargs
    ) -> ErrorDetails:
        """Route error to appropriate handler based on category"""
        
        if category == ErrorCategory.IMAGE_PROCESSING:
            if 'image_data' in kwargs:
                return self.image_handler.handle_validation_error(error, kwargs['image_data'], context)
            else:
                return self.image_handler.handle_preprocessing_error(error, context)
        
        elif category == ErrorCategory.VISION_ANALYSIS:
            return self.vision_handler.handle_vision_error(error, context)
        
        elif category == ErrorCategory.DRUG_LOOKUP:
            drug_name = kwargs.get('drug_name', 'unknown')
            return self.drug_info_handler.handle_drug_info_error(error, drug_name, context)
        
        elif category == ErrorCategory.NETWORK_ERROR:
            return self.network_handler.handle_network_error(error, context)
        
        else:
            # Fallback to general error handler
            return error_handler.handle_error(error, context)
    
    def create_safe_operation(
        self,
        operation_name: str,
        func: Callable,
        error_category: ErrorCategory,
        use_timeout: bool = True,
        use_retry: bool = True,
        retry_config: RetryConfig = None,
        **handler_kwargs
    ) -> Callable:
        """Create a safe version of an operation with error handling, timeout, and retry"""
        
        def safe_operation(*args, **kwargs):
            context = ErrorContext(
                operation=operation_name,
                processing_stage='execution'
            )
            
            try:
                # Apply timeout if requested
                if use_timeout:
                    timeout_handler = TimeoutHandler()
                    func_with_timeout = timeout_handler.with_timeout(operation_name)(func)
                else:
                    func_with_timeout = func
                
                # Apply retry if requested
                if use_retry:
                    retry_handler = RetryHandler(retry_config or RetryConfig())
                    func_with_retry = retry_handler.with_retry()(func_with_timeout)
                else:
                    func_with_retry = func_with_timeout
                
                return func_with_retry(*args, **kwargs)
            
            except Exception as e:
                error_details = self.handle_error_by_category(
                    e, error_category, context, **handler_kwargs
                )
                
                # Re-raise with user-friendly message
                raise type(e)(error_details.user_message) from e
        
        return safe_operation

# Global error scenario manager
error_scenario_manager = ErrorScenarioManager()

# Convenience functions for common error scenarios
def handle_image_validation_error(error: Exception, image_data: str, context: ErrorContext) -> ErrorDetails:
    """Convenience function for handling image validation errors"""
    return error_scenario_manager.image_handler.handle_validation_error(error, image_data, context)

def handle_vision_model_error(error: Exception, context: ErrorContext) -> ErrorDetails:
    """Convenience function for handling vision model errors"""
    return error_scenario_manager.vision_handler.handle_vision_error(error, context)

def handle_drug_info_error(error: Exception, drug_name: str, context: ErrorContext) -> ErrorDetails:
    """Convenience function for handling drug info errors"""
    return error_scenario_manager.drug_info_handler.handle_drug_info_error(error, drug_name, context)

def create_safe_operation(operation_name: str, func: Callable, error_category: ErrorCategory, **kwargs) -> Callable:
    """Convenience function for creating safe operations"""
    return error_scenario_manager.create_safe_operation(operation_name, func, error_category, **kwargs)