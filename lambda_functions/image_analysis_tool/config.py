"""
Configuration settings for the image analysis tool.
This module centralizes all configuration parameters and settings.
"""

import os
from typing import List, Dict, Any

class Config:
    """Configuration class for image analysis tool"""
    
    # Image processing settings
    MAX_IMAGE_SIZE = int(os.environ.get('MAX_IMAGE_SIZE', 10 * 1024 * 1024))  # 10MB default
    SUPPORTED_FORMATS = ['jpeg', 'jpg', 'png', 'webp']
    MIN_IMAGE_SIZE = 100  # Minimum reasonable image size in bytes
    
    # Vision model settings
    BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
    MAX_TOKENS = int(os.environ.get('MAX_TOKENS', 1000))
    VISION_TIMEOUT = int(os.environ.get('VISION_TIMEOUT', 30))  # seconds
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = float(os.environ.get('HIGH_CONFIDENCE_THRESHOLD', 0.8))
    LOW_CONFIDENCE_THRESHOLD = float(os.environ.get('LOW_CONFIDENCE_THRESHOLD', 0.3))
    
    # DrugInfoTool integration settings
    DRUG_INFO_TIMEOUT = int(os.environ.get('DRUG_INFO_TIMEOUT', 10))  # seconds
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
    
    # AWS settings
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Default prompts
    DEFAULT_ANALYSIS_PROMPT = """
    Analyze this image of a medication and extract the following information:
    1. Medication name (brand name if visible, generic name if available)
    2. Dosage strength (e.g., 200mg, 500mg)
    3. Confidence level in identification (high, medium, low)
    
    If multiple medications are visible, focus on the most prominent one.
    If the image is unclear or no medication is identifiable, indicate this clearly.
    
    Return the information in a structured format with clear labels.
    """
    
    # Error messages
    ERROR_MESSAGES = {
        'no_image_data': 'No image data provided. Please upload an image of the medication.',
        'invalid_format': 'Invalid image format. Please use JPEG, PNG, or WebP format.',
        'file_too_large': f'Image size exceeds maximum allowed size of {MAX_IMAGE_SIZE // (1024*1024)}MB.',
        'file_too_small': 'Image data appears to be too small or corrupted.',
        'vision_model_error': 'Unable to analyze image. Please try again with a clearer image.',
        'drug_info_error': 'Medication identified but detailed information unavailable.',
        'no_medication_found': 'No medication detected in the image. Please retake the photo.',
        'low_confidence': 'Medication identification has low confidence. Please try a clearer image.',
        'system_error': 'Temporary system issue. Please try again.'
    }
    
    # Success messages
    SUCCESS_MESSAGES = {
        'high_confidence': 'Medication successfully identified with high confidence.',
        'medium_confidence': 'Medication identified with moderate confidence.',
        'processing_complete': 'Image analysis completed successfully.'
    }
    
    @classmethod
    def get_supported_formats_string(cls) -> str:
        """Get supported formats as a comma-separated string"""
        return ', '.join(cls.SUPPORTED_FORMATS)
    
    @classmethod
    def get_max_size_mb(cls) -> int:
        """Get maximum file size in MB"""
        return cls.MAX_IMAGE_SIZE // (1024 * 1024)
    
    @classmethod
    def is_debug_enabled(cls) -> bool:
        """Check if debug mode is enabled"""
        return cls.DEBUG_MODE
    
    @classmethod
    def get_vision_model_config(cls) -> Dict[str, Any]:
        """Get vision model configuration"""
        return {
            'model_id': cls.BEDROCK_MODEL_ID,
            'max_tokens': cls.MAX_TOKENS,
            'timeout': cls.VISION_TIMEOUT
        }
    
    @classmethod
    def get_confidence_thresholds(cls) -> Dict[str, float]:
        """Get confidence threshold configuration"""
        return {
            'high': cls.HIGH_CONFIDENCE_THRESHOLD,
            'low': cls.LOW_CONFIDENCE_THRESHOLD
        }

# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG_MODE = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG_MODE = False
    LOG_LEVEL = 'INFO'

class TestConfig(Config):
    """Test environment configuration"""
    DEBUG_MODE = True
    LOG_LEVEL = 'DEBUG'
    MAX_IMAGE_SIZE = 1024 * 1024  # 1MB for testing
    VISION_TIMEOUT = 5  # Shorter timeout for tests

# Configuration factory
def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.environ.get('ENVIRONMENT', 'production').lower()
    
    if env == 'development':
        return DevelopmentConfig()
    elif env == 'test':
        return TestConfig()
    else:
        return ProductionConfig()

# Global configuration instance
config = get_config()