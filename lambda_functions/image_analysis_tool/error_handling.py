"""
Comprehensive error handling framework for the image analysis tool.
This module provides error classification, user-friendly messaging, and privacy-compliant logging.
"""

import logging
import json
import time
import traceback
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, asdict

from models import (
    ImageAnalysisError,
    ImageValidationError,
    VisionModelError,
    DrugInfoError
)

class ErrorCategory(Enum):
    """Categories of errors for classification and handling"""
    IMAGE_PROCESSING = "image_processing"
    VISION_ANALYSIS = "vision_analysis"
    DRUG_LOOKUP = "drug_lookup"
    SYSTEM_ERROR = "system_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    NETWORK_ERROR = "network_error"

class ErrorSeverity(Enum):
    """Severity levels for error classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorContext:
    """Context information for error handling"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: float = None
    operation: str = ""
    input_size: int = 0
    processing_stage: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ErrorDetails:
    """Detailed error information for internal use"""
    category: ErrorCategory
    severity: ErrorSeverity
    error_code: str
    internal_message: str
    user_message: str
    suggestions: List[str]
    context: ErrorContext
    retry_possible: bool = False
    retry_delay: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = asdict(self)
        result['category'] = self.category.value
        result['severity'] = self.severity.value
        result['context'] = asdict(self.context)
        return result

class PrivacyCompliantLogger:
    """Logger that maintains privacy compliance by sanitizing sensitive data"""
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self.sensitive_fields = {
            'image_data', 'base64', 'user_id', 'session_id', 
            'personal_info', 'medication_name', 'patient_data',
            'user_info', 'personal', 'sensitive'
        }
    
    def sanitize_data(self, data: Any) -> Any:
        """Remove or mask sensitive information from log data"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                    if key.lower() == 'image_data':
                        sanitized[key] = f"[IMAGE_DATA:{len(str(value)) if value else 0}_bytes]"
                    elif 'id' in key.lower():
                        sanitized[key] = f"[{key.upper()}_MASKED]"
                    else:
                        sanitized[key] = "[SENSITIVE_DATA_MASKED]"
                else:
                    sanitized[key] = self.sanitize_data(value)
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_data(item) for item in data]
        elif isinstance(data, str) and len(data) > 1000:
            # Truncate very long strings that might contain sensitive data
            return f"[LONG_STRING_TRUNCATED:{len(data)}_chars]"
        else:
            return data
    
    def log_error(self, error_details: ErrorDetails, include_traceback: bool = False):
        """Log error with privacy compliance"""
        log_data = {
            'error_code': error_details.error_code,
            'category': error_details.category.value,
            'severity': error_details.severity.value,
            'operation': error_details.context.operation,
            'processing_stage': error_details.context.processing_stage,
            'timestamp': error_details.context.timestamp,
            'retry_possible': error_details.retry_possible,
            'metadata': self.sanitize_data(error_details.metadata)
        }
        
        if include_traceback:
            log_data['traceback'] = traceback.format_exc()
        
        sanitized_log = self.sanitize_data(log_data)
        
        if error_details.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(f"Error occurred: {json.dumps(sanitized_log, indent=2)}")
        elif error_details.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Warning: {json.dumps(sanitized_log, indent=2)}")
        else:
            self.logger.info(f"Info: {json.dumps(sanitized_log, indent=2)}")
    
    def log_operation(self, operation: str, context: Dict[str, Any], level: str = "info"):
        """Log operation with privacy compliance"""
        sanitized_context = self.sanitize_data(context)
        log_message = f"Operation: {operation} - Context: {json.dumps(sanitized_context)}"
        
        if level == "error":
            self.logger.error(log_message)
        elif level == "warning":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

class ErrorClassifier:
    """Classifies errors and determines appropriate handling strategies"""
    
    def __init__(self):
        self.error_mappings = {
            # Image processing errors
            "invalid_format": (ErrorCategory.IMAGE_PROCESSING, ErrorSeverity.LOW),
            "file_too_large": (ErrorCategory.IMAGE_PROCESSING, ErrorSeverity.LOW),
            "corrupted_image": (ErrorCategory.IMAGE_PROCESSING, ErrorSeverity.LOW),
            "no_image_data": (ErrorCategory.VALIDATION_ERROR, ErrorSeverity.MEDIUM),
            "preprocessing_failed": (ErrorCategory.IMAGE_PROCESSING, ErrorSeverity.MEDIUM),
            
            # Vision model errors
            "vision_api_timeout": (ErrorCategory.TIMEOUT_ERROR, ErrorSeverity.MEDIUM),
            "vision_api_error": (ErrorCategory.VISION_ANALYSIS, ErrorSeverity.MEDIUM),
            "low_confidence": (ErrorCategory.VISION_ANALYSIS, ErrorSeverity.LOW),
            "no_medication_detected": (ErrorCategory.VISION_ANALYSIS, ErrorSeverity.LOW),
            "model_unavailable": (ErrorCategory.VISION_ANALYSIS, ErrorSeverity.HIGH),
            "rate_limit_exceeded": (ErrorCategory.RATE_LIMIT_ERROR, ErrorSeverity.MEDIUM),
            
            # Drug info errors
            "drug_not_found": (ErrorCategory.DRUG_LOOKUP, ErrorSeverity.LOW),
            "drug_api_error": (ErrorCategory.DRUG_LOOKUP, ErrorSeverity.MEDIUM),
            "drug_api_timeout": (ErrorCategory.TIMEOUT_ERROR, ErrorSeverity.MEDIUM),
            
            # System errors
            "unexpected_error": (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH),
            "memory_error": (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH),
            "network_error": (ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
            "authentication_error": (ErrorCategory.AUTHENTICATION_ERROR, ErrorSeverity.HIGH),
        }
    
    def classify_error(self, error: Exception, error_code: str = None) -> Tuple[ErrorCategory, ErrorSeverity]:
        """Classify an error based on its type and code"""
        if error_code and error_code in self.error_mappings:
            return self.error_mappings[error_code]
        
        # Classify based on exception type
        if isinstance(error, ImageValidationError):
            return ErrorCategory.IMAGE_PROCESSING, ErrorSeverity.LOW
        elif isinstance(error, VisionModelError):
            return ErrorCategory.VISION_ANALYSIS, ErrorSeverity.MEDIUM
        elif isinstance(error, DrugInfoError):
            return ErrorCategory.DRUG_LOOKUP, ErrorSeverity.MEDIUM
        elif isinstance(error, TimeoutError):
            return ErrorCategory.TIMEOUT_ERROR, ErrorSeverity.MEDIUM
        elif isinstance(error, MemoryError):
            return ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH
        elif isinstance(error, ConnectionError):
            return ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM
        else:
            return ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH

class UserMessageGenerator:
    """Generates user-friendly error messages and suggestions"""
    
    def __init__(self):
        self.message_templates = {
            ErrorCategory.IMAGE_PROCESSING: {
                "invalid_format": {
                    "message": "The uploaded file format is not supported.",
                    "suggestions": [
                        "Please use JPEG, PNG, or WebP format",
                        "Try converting your image to a supported format",
                        "Ensure the file is not corrupted"
                    ]
                },
                "file_too_large": {
                    "message": "The uploaded image is too large.",
                    "suggestions": [
                        "Please reduce the image size to under 10MB",
                        "Try compressing the image",
                        "Use a lower resolution image"
                    ]
                },
                "corrupted_image": {
                    "message": "The uploaded image appears to be corrupted.",
                    "suggestions": [
                        "Please try uploading a different image",
                        "Check if the original image opens correctly",
                        "Try taking a new photo of the medication"
                    ]
                },
                "preprocessing_failed": {
                    "message": "Unable to process the uploaded image.",
                    "suggestions": [
                        "Please try again with a different image",
                        "Ensure the image is clear and well-lit",
                        "Try taking a new photo"
                    ]
                }
            },
            ErrorCategory.VISION_ANALYSIS: {
                "low_confidence": {
                    "message": "Unable to clearly identify the medication in the image.",
                    "suggestions": [
                        "Try taking a clearer photo with better lighting",
                        "Ensure the medication label is fully visible",
                        "Remove any obstructions from the medication",
                        "Try a different angle or closer shot"
                    ]
                },
                "no_medication_detected": {
                    "message": "No medication was detected in the image.",
                    "suggestions": [
                        "Ensure the medication is clearly visible in the photo",
                        "Try taking a closer shot of the medication",
                        "Make sure the medication label is readable",
                        "Check that you're photographing the right item"
                    ]
                },
                "vision_api_error": {
                    "message": "Unable to analyze the image at this time.",
                    "suggestions": [
                        "Please try again in a few moments",
                        "Check your internet connection",
                        "Try with a different image if the problem persists"
                    ]
                },
                "model_unavailable": {
                    "message": "The image analysis service is temporarily unavailable.",
                    "suggestions": [
                        "Please try again later",
                        "Contact support if the issue persists"
                    ]
                }
            },
            ErrorCategory.DRUG_LOOKUP: {
                "drug_not_found": {
                    "message": "Detailed information for this medication is not available.",
                    "suggestions": [
                        "Try searching manually in the drug database",
                        "Consult with your healthcare provider",
                        "Check the medication packaging for information"
                    ]
                },
                "drug_api_error": {
                    "message": "Unable to retrieve detailed drug information.",
                    "suggestions": [
                        "The medication was identified but detailed info is unavailable",
                        "Please try again later",
                        "Consult your healthcare provider for information"
                    ]
                }
            },
            ErrorCategory.TIMEOUT_ERROR: {
                "default": {
                    "message": "The request took too long to process.",
                    "suggestions": [
                        "Please try again with a smaller image",
                        "Check your internet connection",
                        "Try again in a few moments"
                    ]
                }
            },
            ErrorCategory.RATE_LIMIT_ERROR: {
                "default": {
                    "message": "Too many requests. Please wait before trying again.",
                    "suggestions": [
                        "Wait a few minutes before submitting another image",
                        "Try again later"
                    ]
                }
            },
            ErrorCategory.NETWORK_ERROR: {
                "default": {
                    "message": "Network connection issue occurred.",
                    "suggestions": [
                        "Check your internet connection",
                        "Try again in a few moments",
                        "Contact support if the issue persists"
                    ]
                }
            },
            ErrorCategory.SYSTEM_ERROR: {
                "default": {
                    "message": "An unexpected error occurred.",
                    "suggestions": [
                        "Please try again",
                        "Contact support if the issue persists",
                        "Try with a different image"
                    ]
                }
            }
        }
    
    def generate_user_message(self, category: ErrorCategory, error_code: str = "default") -> Dict[str, Any]:
        """Generate user-friendly message and suggestions"""
        category_messages = self.message_templates.get(category, {})
        message_data = category_messages.get(error_code, category_messages.get("default", {
            "message": "An error occurred while processing your request.",
            "suggestions": ["Please try again", "Contact support if the issue persists"]
        }))
        
        return {
            "message": message_data["message"],
            "suggestions": message_data["suggestions"]
        }

class ErrorHandler:
    """Main error handling coordinator"""
    
    def __init__(self):
        self.logger = PrivacyCompliantLogger()
        self.classifier = ErrorClassifier()
        self.message_generator = UserMessageGenerator()
    
    def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        error_code: str = None,
        include_traceback: bool = False
    ) -> ErrorDetails:
        """Handle an error with full classification and logging"""
        
        # Classify the error
        category, severity = self.classifier.classify_error(error, error_code)
        
        # Generate user-friendly message
        user_message_data = self.message_generator.generate_user_message(category, error_code)
        
        # Create error details
        error_details = ErrorDetails(
            category=category,
            severity=severity,
            error_code=error_code or "unknown",
            internal_message=str(error),
            user_message=user_message_data["message"],
            suggestions=user_message_data["suggestions"],
            context=context,
            retry_possible=self._is_retry_possible(category),
            retry_delay=self._get_retry_delay(category)
        )
        
        # Add error-specific metadata
        error_details.metadata.update({
            "error_type": type(error).__name__,
            "error_module": getattr(error, '__module__', 'unknown')
        })
        
        # Add context metadata if available
        if hasattr(context, 'metadata') and context.metadata:
            error_details.metadata.update(context.metadata)
        
        # Log the error
        self.logger.log_error(error_details, include_traceback)
        
        return error_details
    
    def _is_retry_possible(self, category: ErrorCategory) -> bool:
        """Determine if retry is possible for this error category"""
        retry_categories = {
            ErrorCategory.TIMEOUT_ERROR,
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.VISION_ANALYSIS,
            ErrorCategory.DRUG_LOOKUP
        }
        return category in retry_categories
    
    def _get_retry_delay(self, category: ErrorCategory) -> int:
        """Get recommended retry delay in seconds"""
        delay_map = {
            ErrorCategory.RATE_LIMIT_ERROR: 60,
            ErrorCategory.TIMEOUT_ERROR: 5,
            ErrorCategory.NETWORK_ERROR: 3,
            ErrorCategory.VISION_ANALYSIS: 2,
            ErrorCategory.DRUG_LOOKUP: 2
        }
        return delay_map.get(category, 0)
    
    def create_error_response(self, error_details: ErrorDetails, event: Dict[str, Any]) -> Dict[str, Any]:
        """Create a standardized error response for the Lambda function"""
        response_body = {
            "success": False,
            "error": error_details.user_message,
            "error_code": error_details.error_code,
            "suggestions": error_details.suggestions,
            "retry_possible": error_details.retry_possible
        }
        
        if error_details.retry_possible and error_details.retry_delay > 0:
            response_body["retry_after"] = error_details.retry_delay
        
        # Handle None event gracefully
        if event is None:
            event = {}
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup'),
                'apiPath': event.get('apiPath'),
                'httpMethod': event.get('httpMethod'),
                'httpStatusCode': 400 if error_details.severity != ErrorSeverity.CRITICAL else 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(response_body)
                    }
                }
            }
        }

# Global error handler instance
error_handler = ErrorHandler()

def handle_lambda_error(error: Exception, event: Dict[str, Any], context_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convenience function for handling errors in Lambda functions"""
    error_context = ErrorContext(
        request_id=context_info.get('request_id') if context_info else None,
        operation=context_info.get('operation', 'lambda_handler') if context_info else 'lambda_handler',
        processing_stage=context_info.get('stage', 'unknown') if context_info else 'unknown'
    )
    
    error_details = error_handler.handle_error(error, error_context, include_traceback=True)
    return error_handler.create_error_response(error_details, event)