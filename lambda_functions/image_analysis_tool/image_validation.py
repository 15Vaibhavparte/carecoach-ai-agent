"""
Image validation utilities for the medication identification system.
This module provides comprehensive image validation including format checking,
size validation, and base64 decoding validation.
"""

import base64
import io
import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
from models import ImageValidationResult, ImageValidationError
from config import config

logger = logging.getLogger(__name__)

class ImageValidator:
    """
    Comprehensive image validation utility class.
    Handles format validation, size checking, and base64 decoding.
    """
    
    # Magic bytes for format detection
    FORMAT_SIGNATURES = {
        'jpeg': [b'\xff\xd8\xff'],
        'png': [b'\x89PNG\r\n\x1a\n'],
        'webp': [b'RIFF', b'WEBP'],  # WEBP has RIFF header followed by WEBP
        'gif': [b'GIF87a', b'GIF89a'],
        'bmp': [b'BM'],
        'tiff': [b'II*\x00', b'MM\x00*']
    }
    
    # MIME type mappings
    MIME_TYPE_MAP = {
        'jpeg': 'image/jpeg',
        'jpg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'tiff': 'image/tiff'
    }
    
    def __init__(self, max_size: int = None, allowed_formats: List[str] = None):
        """
        Initialize the image validator.
        
        Args:
            max_size: Maximum allowed file size in bytes
            allowed_formats: List of allowed image formats
        """
        self.max_size = max_size or config.MAX_IMAGE_SIZE
        self.allowed_formats = allowed_formats or config.SUPPORTED_FORMATS
        self.min_size = config.MIN_IMAGE_SIZE
    
    def validate_base64_string(self, base64_data: str) -> Tuple[bool, str, bytes]:
        """
        Validate and decode base64 string.
        
        Args:
            base64_data: Base64 encoded image string
            
        Returns:
            Tuple of (is_valid, error_message, decoded_bytes)
        """
        try:
            if not base64_data:
                return False, "Empty base64 data provided", b''
            
            # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
            if base64_data.startswith('data:'):
                if ';base64,' in base64_data:
                    base64_data = base64_data.split(';base64,')[1]
                else:
                    return False, "Invalid data URL format", b''
            
            # Remove whitespace and newlines
            base64_data = base64_data.strip().replace('\n', '').replace('\r', '').replace(' ', '')
            
            # Validate base64 format
            if len(base64_data) % 4 != 0:
                # Add padding if needed
                base64_data += '=' * (4 - len(base64_data) % 4)
            
            # Decode base64
            decoded_bytes = base64.b64decode(base64_data, validate=True)
            
            if len(decoded_bytes) == 0:
                return False, "Decoded image data is empty", b''
            
            return True, "", decoded_bytes
            
        except Exception as e:
            logger.error(f"Base64 decoding failed: {str(e)}")
            return False, f"Invalid base64 encoding: {str(e)}", b''
    
    def detect_image_format(self, image_bytes: bytes) -> str:
        """
        Detect image format from byte signature.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Detected format string or 'unknown'
        """
        if len(image_bytes) < 12:  # Need at least 12 bytes for WEBP detection
            return 'unknown'
        
        # Check each format signature
        for format_name, signatures in self.FORMAT_SIGNATURES.items():
            for signature in signatures:
                if format_name == 'webp':
                    # Special handling for WEBP (RIFF header + WEBP identifier)
                    if (image_bytes.startswith(b'RIFF') and 
                        len(image_bytes) >= 12 and 
                        image_bytes[8:12] == b'WEBP'):
                        return 'webp'
                else:
                    if image_bytes.startswith(signature):
                        return format_name
        
        return 'unknown'
    
    def validate_image_format(self, image_bytes: bytes, detected_format: str) -> Tuple[bool, str]:
        """
        Validate that the detected format is allowed.
        
        Args:
            image_bytes: Raw image bytes
            detected_format: Format detected from byte signature
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if detected_format == 'unknown':
            return False, f"Unsupported or unrecognized image format. Supported formats: {', '.join(self.allowed_formats)}"
        
        # Normalize format names (jpg -> jpeg)
        normalized_format = 'jpeg' if detected_format == 'jpg' else detected_format
        normalized_allowed = ['jpeg' if f == 'jpg' else f for f in self.allowed_formats]
        
        if normalized_format not in normalized_allowed:
            return False, f"Image format '{detected_format}' not allowed. Supported formats: {', '.join(self.allowed_formats)}"
        
        # Additional validation using PIL for more thorough format checking
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                pil_format = img.format.lower() if img.format else 'unknown'
                
                # PIL uses 'jpeg' for both jpg and jpeg
                if pil_format == 'jpeg' and detected_format in ['jpg', 'jpeg']:
                    return True, ""
                elif pil_format == detected_format:
                    return True, ""
                else:
                    logger.warning(f"Format mismatch: signature={detected_format}, PIL={pil_format}")
                    # If PIL can open it and it matches our allowed formats, accept it
                    if pil_format in normalized_allowed:
                        return True, ""
                    else:
                        return False, f"Image format validation failed: detected={detected_format}, actual={pil_format}"
        
        except Exception as e:
            logger.error(f"PIL format validation failed: {str(e)}")
            return False, f"Image appears to be corrupted or invalid: {str(e)}"
    
    def validate_image_size(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate image file size.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        size = len(image_bytes)
        
        if size < self.min_size:
            return False, f"Image too small ({size} bytes). Minimum size: {self.min_size} bytes"
        
        if size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            current_mb = size / (1024 * 1024)
            return False, f"Image too large ({current_mb:.1f}MB). Maximum size: {max_mb:.1f}MB"
        
        return True, ""
    
    def validate_image_content(self, image_bytes: bytes) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate image content and extract metadata.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Tuple of (is_valid, error_message, metadata)
        """
        metadata = {}
        
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Basic image properties
                metadata.update({
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                })
                
                # Validate minimum dimensions
                min_dimension = 32  # Minimum reasonable dimension
                if img.width < min_dimension or img.height < min_dimension:
                    return False, f"Image dimensions too small ({img.width}x{img.height}). Minimum: {min_dimension}x{min_dimension}", metadata
                
                # Check for reasonable aspect ratio (prevent extremely thin images)
                aspect_ratio = max(img.width, img.height) / min(img.width, img.height)
                max_aspect_ratio = 10.0  # Maximum aspect ratio
                if aspect_ratio > max_aspect_ratio:
                    return False, f"Image aspect ratio too extreme ({aspect_ratio:.1f}:1). Maximum: {max_aspect_ratio}:1", metadata
                
                # Validate color mode
                if img.mode not in ('RGB', 'RGBA', 'L', 'LA', 'P'):
                    return False, f"Unsupported color mode: {img.mode}. Supported: RGB, RGBA, L, LA, P", metadata
                
                return True, "", metadata
                
        except Exception as e:
            logger.error(f"Image content validation failed: {str(e)}")
            return False, f"Image content validation failed: {str(e)}", metadata
    
    def validate_image(self, base64_data: str) -> ImageValidationResult:
        """
        Perform comprehensive image validation.
        
        Args:
            base64_data: Base64 encoded image string
            
        Returns:
            ImageValidationResult with validation results
        """
        try:
            # Step 1: Validate and decode base64
            is_valid_b64, b64_error, image_bytes = self.validate_base64_string(base64_data)
            if not is_valid_b64:
                return ImageValidationResult(
                    valid=False,
                    error=b64_error,
                    size=0,
                    format_detected='unknown'
                )
            
            # Step 2: Validate file size
            is_valid_size, size_error = self.validate_image_size(image_bytes)
            if not is_valid_size:
                return ImageValidationResult(
                    valid=False,
                    error=size_error,
                    size=len(image_bytes),
                    format_detected='unknown'
                )
            
            # Step 3: Detect and validate format
            detected_format = self.detect_image_format(image_bytes)
            is_valid_format, format_error = self.validate_image_format(image_bytes, detected_format)
            if not is_valid_format:
                return ImageValidationResult(
                    valid=False,
                    error=format_error,
                    size=len(image_bytes),
                    format_detected=detected_format
                )
            
            # Step 4: Validate image content
            is_valid_content, content_error, metadata = self.validate_image_content(image_bytes)
            if not is_valid_content:
                return ImageValidationResult(
                    valid=False,
                    error=content_error,
                    size=len(image_bytes),
                    format_detected=detected_format
                )
            
            # All validations passed
            result = ImageValidationResult(
                valid=True,
                size=len(image_bytes),
                format_detected=detected_format
            )
            
            # Add metadata to result
            for key, value in metadata.items():
                setattr(result, key, value)
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error during image validation: {str(e)}")
            return ImageValidationResult(
                valid=False,
                error=f"Validation failed due to unexpected error: {str(e)}",
                size=0,
                format_detected='unknown'
            )

# Convenience functions for common validation tasks

def validate_image_format_only(image_bytes: bytes, allowed_formats: List[str] = None) -> Tuple[bool, str, str]:
    """
    Quick format validation for image bytes.
    
    Args:
        image_bytes: Raw image bytes
        allowed_formats: List of allowed formats
        
    Returns:
        Tuple of (is_valid, error_message, detected_format)
    """
    validator = ImageValidator(allowed_formats=allowed_formats)
    detected_format = validator.detect_image_format(image_bytes)
    is_valid, error = validator.validate_image_format(image_bytes, detected_format)
    return is_valid, error, detected_format

def validate_image_size_only(image_bytes: bytes, max_size: int = None) -> Tuple[bool, str]:
    """
    Quick size validation for image bytes.
    
    Args:
        image_bytes: Raw image bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = ImageValidator(max_size=max_size)
    return validator.validate_image_size(image_bytes)

def decode_and_validate_base64(base64_data: str) -> Tuple[bool, str, bytes]:
    """
    Quick base64 decoding and validation.
    
    Args:
        base64_data: Base64 encoded string
        
    Returns:
        Tuple of (is_valid, error_message, decoded_bytes)
    """
    validator = ImageValidator()
    return validator.validate_base64_string(base64_data)

def get_image_info(base64_data: str) -> Dict[str, Any]:
    """
    Get comprehensive image information without strict validation.
    
    Args:
        base64_data: Base64 encoded image string
        
    Returns:
        Dictionary with image information
    """
    validator = ImageValidator()
    result = validator.validate_image(base64_data)
    
    info = {
        'valid': result.valid,
        'size': result.size,
        'format': result.format_detected,
        'error': result.error
    }
    
    # Add any additional metadata
    for attr in ['width', 'height', 'mode', 'has_transparency']:
        if hasattr(result, attr):
            info[attr] = getattr(result, attr)
    
    return info