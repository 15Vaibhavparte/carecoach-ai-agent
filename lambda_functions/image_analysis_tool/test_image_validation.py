"""
Unit tests for image validation utilities.
Tests all aspects of image validation including format checking,
size validation, and base64 decoding.
"""

import unittest
import base64
import io
from unittest.mock import patch, MagicMock
from PIL import Image
import tempfile
import os

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from image_validation import (
    ImageValidator,
    validate_image_format_only,
    validate_image_size_only,
    decode_and_validate_base64,
    get_image_info
)
from models import ImageValidationResult
from config import config

class TestImageValidator(unittest.TestCase):
    """Test cases for ImageValidator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ImageValidator()
        
        # Create test images in memory
        self.test_images = {}
        
        # Create a small JPEG image
        jpeg_img = Image.new('RGB', (100, 100), color='red')
        jpeg_buffer = io.BytesIO()
        jpeg_img.save(jpeg_buffer, format='JPEG')
        self.test_images['jpeg'] = base64.b64encode(jpeg_buffer.getvalue()).decode('utf-8')
        
        # Create a small PNG image
        png_img = Image.new('RGBA', (100, 100), color=(0, 255, 0, 128))
        png_buffer = io.BytesIO()
        png_img.save(png_buffer, format='PNG')
        self.test_images['png'] = base64.b64encode(png_buffer.getvalue()).decode('utf-8')
        
        # Create a small WebP image (if supported)
        try:
            webp_img = Image.new('RGB', (100, 100), color='blue')
            webp_buffer = io.BytesIO()
            webp_img.save(webp_buffer, format='WEBP')
            self.test_images['webp'] = base64.b64encode(webp_buffer.getvalue()).decode('utf-8')
        except Exception:
            # WebP might not be supported in test environment
            self.test_images['webp'] = None
    
    def test_validate_base64_string_valid(self):
        """Test validation of valid base64 strings"""
        # Test valid JPEG base64
        is_valid, error, decoded = self.validator.validate_base64_string(self.test_images['jpeg'])
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        self.assertGreater(len(decoded), 0)
        
        # Test with data URL prefix
        data_url = f"data:image/jpeg;base64,{self.test_images['jpeg']}"
        is_valid, error, decoded = self.validator.validate_base64_string(data_url)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        self.assertGreater(len(decoded), 0)
    
    def test_validate_base64_string_invalid(self):
        """Test validation of invalid base64 strings"""
        # Test empty string
        is_valid, error, decoded = self.validator.validate_base64_string("")
        self.assertFalse(is_valid)
        self.assertIn("Empty base64 data", error)
        self.assertEqual(len(decoded), 0)
        
        # Test invalid base64
        is_valid, error, decoded = self.validator.validate_base64_string("invalid_base64!")
        self.assertFalse(is_valid)
        self.assertIn("Invalid base64 encoding", error)
        
        # Test invalid data URL
        is_valid, error, decoded = self.validator.validate_base64_string("data:image/jpeg,invalid")
        self.assertFalse(is_valid)
        self.assertIn("Invalid data URL format", error)
    
    def test_detect_image_format(self):
        """Test image format detection from byte signatures"""
        # Test JPEG detection
        jpeg_bytes = base64.b64decode(self.test_images['jpeg'])
        format_detected = self.validator.detect_image_format(jpeg_bytes)
        self.assertEqual(format_detected, 'jpeg')
        
        # Test PNG detection
        png_bytes = base64.b64decode(self.test_images['png'])
        format_detected = self.validator.detect_image_format(png_bytes)
        self.assertEqual(format_detected, 'png')
        
        # Test WebP detection (if available)
        if self.test_images['webp']:
            webp_bytes = base64.b64decode(self.test_images['webp'])
            format_detected = self.validator.detect_image_format(webp_bytes)
            self.assertEqual(format_detected, 'webp')
        
        # Test unknown format
        unknown_bytes = b'unknown_format_data'
        format_detected = self.validator.detect_image_format(unknown_bytes)
        self.assertEqual(format_detected, 'unknown')
        
        # Test insufficient data
        short_bytes = b'abc'
        format_detected = self.validator.detect_image_format(short_bytes)
        self.assertEqual(format_detected, 'unknown')
    
    def test_validate_image_format_allowed(self):
        """Test validation of allowed image formats"""
        jpeg_bytes = base64.b64decode(self.test_images['jpeg'])
        
        # Test allowed format
        is_valid, error = self.validator.validate_image_format(jpeg_bytes, 'jpeg')
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        
        # Test disallowed format
        validator_restricted = ImageValidator(allowed_formats=['png'])
        is_valid, error = validator_restricted.validate_image_format(jpeg_bytes, 'jpeg')
        self.assertFalse(is_valid)
        self.assertIn("not allowed", error)
        
        # Test unknown format
        is_valid, error = self.validator.validate_image_format(jpeg_bytes, 'unknown')
        self.assertFalse(is_valid)
        self.assertIn("Unsupported or unrecognized", error)
    
    def test_validate_image_size(self):
        """Test image size validation"""
        jpeg_bytes = base64.b64decode(self.test_images['jpeg'])
        
        # Test valid size
        is_valid, error = self.validator.validate_image_size(jpeg_bytes)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        
        # Test too large
        validator_small = ImageValidator(max_size=100)  # Very small limit
        is_valid, error = validator_small.validate_image_size(jpeg_bytes)
        self.assertFalse(is_valid)
        self.assertIn("too large", error)
        
        # Test too small
        tiny_bytes = b'x' * 50  # Below minimum
        is_valid, error = self.validator.validate_image_size(tiny_bytes)
        self.assertFalse(is_valid)
        self.assertIn("too small", error)
    
    def test_validate_image_content(self):
        """Test image content validation"""
        jpeg_bytes = base64.b64decode(self.test_images['jpeg'])
        
        # Test valid content
        is_valid, error, metadata = self.validator.validate_image_content(jpeg_bytes)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        self.assertIn('width', metadata)
        self.assertIn('height', metadata)
        self.assertEqual(metadata['width'], 100)
        self.assertEqual(metadata['height'], 100)
        
        # Test invalid image data
        invalid_bytes = b'not_an_image'
        is_valid, error, metadata = self.validator.validate_image_content(invalid_bytes)
        self.assertFalse(is_valid)
        self.assertIn("validation failed", error)
    
    def test_validate_image_content_dimensions(self):
        """Test image content validation for dimensions"""
        # Create very small image (below minimum)
        tiny_img = Image.new('RGB', (10, 10), color='red')
        tiny_buffer = io.BytesIO()
        tiny_img.save(tiny_buffer, format='JPEG')
        tiny_bytes = tiny_buffer.getvalue()
        
        is_valid, error, metadata = self.validator.validate_image_content(tiny_bytes)
        self.assertFalse(is_valid)
        self.assertIn("dimensions too small", error)
        
        # Create image with extreme aspect ratio (but above minimum dimensions)
        extreme_img = Image.new('RGB', (1100, 100), color='red')  # 11:1 aspect ratio (exceeds 10:1 limit)
        extreme_buffer = io.BytesIO()
        extreme_img.save(extreme_buffer, format='JPEG')
        extreme_bytes = extreme_buffer.getvalue()
        
        is_valid, error, metadata = self.validator.validate_image_content(extreme_bytes)
        self.assertFalse(is_valid)
        self.assertIn("aspect ratio too extreme", error)
    
    def test_validate_image_complete(self):
        """Test complete image validation workflow"""
        # Test valid image
        result = self.validator.validate_image(self.test_images['jpeg'])
        self.assertIsInstance(result, ImageValidationResult)
        self.assertTrue(result.valid)
        self.assertEqual(result.format_detected, 'jpeg')
        self.assertGreater(result.size, 0)
        
        # Test invalid base64
        result = self.validator.validate_image("invalid_base64!")
        self.assertFalse(result.valid)
        self.assertIn("Invalid base64 encoding", result.error)
        
        # Test empty input
        result = self.validator.validate_image("")
        self.assertFalse(result.valid)
        self.assertIn("Empty base64 data", result.error)
    
    def test_validate_image_with_data_url(self):
        """Test validation with data URL format"""
        data_url = f"data:image/jpeg;base64,{self.test_images['jpeg']}"
        result = self.validator.validate_image(data_url)
        self.assertTrue(result.valid)
        self.assertEqual(result.format_detected, 'jpeg')
    
    def test_validate_image_png_with_transparency(self):
        """Test PNG validation with transparency"""
        result = self.validator.validate_image(self.test_images['png'])
        self.assertTrue(result.valid)
        self.assertEqual(result.format_detected, 'png')
        # Check if transparency metadata is captured
        if hasattr(result, 'has_transparency'):
            self.assertTrue(result.has_transparency)
    
    @patch('image_validation.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are properly logged"""
        # Test with invalid data that should trigger logging
        self.validator.validate_image("invalid_data")
        mock_logger.error.assert_called()
    
    def test_custom_configuration(self):
        """Test validator with custom configuration"""
        custom_validator = ImageValidator(
            max_size=1024 * 1024,  # 1MB
            allowed_formats=['jpeg', 'png']
        )
        
        self.assertEqual(custom_validator.max_size, 1024 * 1024)
        self.assertEqual(custom_validator.allowed_formats, ['jpeg', 'png'])
        
        # Test that WebP is rejected with custom config
        if self.test_images['webp']:
            result = custom_validator.validate_image(self.test_images['webp'])
            self.assertFalse(result.valid)
            self.assertIn("not allowed", result.error)

class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        self.test_image_bytes = buffer.getvalue()
        self.test_image_b64 = base64.b64encode(self.test_image_bytes).decode('utf-8')
    
    def test_validate_image_format_only(self):
        """Test format-only validation function"""
        is_valid, error, detected = validate_image_format_only(self.test_image_bytes)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        self.assertEqual(detected, 'jpeg')
        
        # Test with restricted formats
        is_valid, error, detected = validate_image_format_only(
            self.test_image_bytes, 
            allowed_formats=['png']
        )
        self.assertFalse(is_valid)
        self.assertIn("not allowed", error)
        self.assertEqual(detected, 'jpeg')
    
    def test_validate_image_size_only(self):
        """Test size-only validation function"""
        is_valid, error = validate_image_size_only(self.test_image_bytes)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        
        # Test with small size limit
        is_valid, error = validate_image_size_only(self.test_image_bytes, max_size=100)
        self.assertFalse(is_valid)
        self.assertIn("too large", error)
    
    def test_decode_and_validate_base64(self):
        """Test base64 decoding function"""
        is_valid, error, decoded = decode_and_validate_base64(self.test_image_b64)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        self.assertEqual(decoded, self.test_image_bytes)
        
        # Test invalid base64
        is_valid, error, decoded = decode_and_validate_base64("invalid!")
        self.assertFalse(is_valid)
        self.assertIn("Invalid base64 encoding", error)
        self.assertEqual(len(decoded), 0)
    
    def test_get_image_info(self):
        """Test image info extraction function"""
        info = get_image_info(self.test_image_b64)
        
        self.assertIsInstance(info, dict)
        self.assertIn('valid', info)
        self.assertIn('size', info)
        self.assertIn('format', info)
        self.assertTrue(info['valid'])
        self.assertEqual(info['format'], 'jpeg')
        self.assertGreater(info['size'], 0)
        
        # Test with invalid data
        info = get_image_info("invalid_data")
        self.assertFalse(info['valid'])
        self.assertIn('error', info)

class TestImageValidationIntegration(unittest.TestCase):
    """Integration tests for image validation"""
    
    def test_requirements_compliance(self):
        """Test that validation meets the specified requirements"""
        validator = ImageValidator()
        
        # Requirement 1.1: Accept common image formats (JPEG, PNG, WebP)
        supported_formats = validator.allowed_formats
        self.assertIn('jpeg', supported_formats)
        self.assertIn('png', supported_formats)
        self.assertIn('webp', supported_formats)
        
        # Requirement 1.2: Convert to base64 format (validation supports base64 input)
        # This is tested in base64 validation tests
        
        # Requirement 1.3: Provide clear error messaging when size limits exceeded
        large_data = 'x' * (validator.max_size + 1000)
        large_b64 = base64.b64encode(large_data.encode()).decode()
        result = validator.validate_image(large_b64)
        self.assertFalse(result.valid)
        self.assertIn("too large", result.error)
        self.assertIn("MB", result.error)  # Should include size information
        
        # Requirement 6.3: Handle invalid formats gracefully
        invalid_result = validator.validate_image("not_base64_image_data")
        self.assertFalse(invalid_result.valid)
        self.assertIn("Invalid base64 encoding", invalid_result.error)
    
    def test_error_message_quality(self):
        """Test that error messages are user-friendly and informative"""
        validator = ImageValidator()
        
        # Test various error scenarios and check message quality
        test_cases = [
            ("", "Empty base64 data"),
            ("invalid!", "Invalid base64 encoding"),
            ("data:image/jpeg,invalid", "Invalid data URL format"),
        ]
        
        for invalid_input, expected_error_part in test_cases:
            result = validator.validate_image(invalid_input)
            self.assertFalse(result.valid)
            self.assertIn(expected_error_part, result.error)
            # Error messages should be descriptive
            self.assertGreater(len(result.error), 10)
    
    def test_configuration_integration(self):
        """Test integration with configuration system"""
        # Test that validator uses config values
        validator = ImageValidator()
        self.assertEqual(validator.max_size, config.MAX_IMAGE_SIZE)
        self.assertEqual(validator.allowed_formats, config.SUPPORTED_FORMATS)
        self.assertEqual(validator.min_size, config.MIN_IMAGE_SIZE)

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)