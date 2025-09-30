"""
Unit tests for image preprocessing utilities.
Tests image conversion, quality assessment, and optimization functions.
"""

import unittest
import base64
import io
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from image_preprocessing import (
    ImagePreprocessor,
    ImageOptimizationLevel,
    convert_base64_to_optimized_image,
    assess_image_quality_from_base64,
    get_optimal_image_format
)
from models import ImageQuality

class TestImagePreprocessor(unittest.TestCase):
    """Test cases for ImagePreprocessor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.preprocessor = ImagePreprocessor()
        
        # Create test images
        self.test_images = {}
        
        # Small RGB image
        rgb_img = Image.new('RGB', (200, 200), color=(255, 0, 0))
        rgb_buffer = io.BytesIO()
        rgb_img.save(rgb_buffer, format='JPEG')
        self.test_images['rgb_jpeg'] = base64.b64encode(rgb_buffer.getvalue()).decode('utf-8')
        
        # RGBA image with transparency
        rgba_img = Image.new('RGBA', (200, 200), color=(0, 255, 0, 128))
        rgba_buffer = io.BytesIO()
        rgba_img.save(rgba_buffer, format='PNG')
        self.test_images['rgba_png'] = base64.b64encode(rgba_buffer.getvalue()).decode('utf-8')
        
        # Very small image
        tiny_img = Image.new('RGB', (50, 50), color=(0, 0, 255))
        tiny_buffer = io.BytesIO()
        tiny_img.save(tiny_buffer, format='JPEG')
        self.test_images['tiny'] = base64.b64encode(tiny_buffer.getvalue()).decode('utf-8')
        
        # Large image
        large_img = Image.new('RGB', (3000, 2000), color=(128, 128, 128))
        large_buffer = io.BytesIO()
        large_img.save(large_buffer, format='JPEG', quality=50)  # Compress to reduce size
        self.test_images['large'] = base64.b64encode(large_buffer.getvalue()).decode('utf-8')
        
        # High contrast image
        contrast_img = Image.new('RGB', (200, 200), color=(255, 255, 255))
        # Add some black squares for contrast
        for i in range(0, 200, 40):
            for j in range(0, 200, 40):
                if (i + j) % 80 == 0:
                    for x in range(i, min(i+20, 200)):
                        for y in range(j, min(j+20, 200)):
                            contrast_img.putpixel((x, y), (0, 0, 0))
        contrast_buffer = io.BytesIO()
        contrast_img.save(contrast_buffer, format='JPEG')
        self.test_images['high_contrast'] = base64.b64encode(contrast_buffer.getvalue()).decode('utf-8')
    
    def test_base64_to_image_valid(self):
        """Test conversion of valid base64 to PIL Image"""
        success, error, image = self.preprocessor.base64_to_image(self.test_images['rgb_jpeg'])
        
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.mode, 'RGB')
        self.assertEqual(image.size, (200, 200))
    
    def test_base64_to_image_with_data_url(self):
        """Test conversion with data URL prefix"""
        data_url = f"data:image/jpeg;base64,{self.test_images['rgb_jpeg']}"
        success, error, image = self.preprocessor.base64_to_image(data_url)
        
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertIsInstance(image, Image.Image)
    
    def test_base64_to_image_rgba_conversion(self):
        """Test RGBA to RGB conversion"""
        success, error, image = self.preprocessor.base64_to_image(self.test_images['rgba_png'])
        
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertEqual(image.mode, 'RGB')  # Should be converted from RGBA
    
    def test_base64_to_image_invalid(self):
        """Test conversion of invalid base64"""
        success, error, image = self.preprocessor.base64_to_image("invalid_base64!")
        
        self.assertFalse(success)
        self.assertIn("Failed to convert", error)
        self.assertIsNone(image)
    
    def test_image_to_base64_jpeg(self):
        """Test conversion of PIL Image to base64 JPEG"""
        # First convert base64 to image
        success, error, image = self.preprocessor.base64_to_image(self.test_images['rgb_jpeg'])
        self.assertTrue(success)
        
        # Convert back to base64
        success, error, base64_result = self.preprocessor.image_to_base64(image, 'JPEG', 85)
        
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertIsInstance(base64_result, str)
        self.assertGreater(len(base64_result), 0)
        
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(base64_result)
            self.assertGreater(len(decoded), 0)
        except Exception:
            self.fail("Generated base64 is invalid")
    
    def test_image_to_base64_png(self):
        """Test conversion of PIL Image to base64 PNG"""
        success, error, image = self.preprocessor.base64_to_image(self.test_images['rgba_png'])
        self.assertTrue(success)
        
        success, error, base64_result = self.preprocessor.image_to_base64(image, 'PNG')
        
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertIsInstance(base64_result, str)
    
    def test_assess_image_quality_good(self):
        """Test quality assessment for good quality image"""
        success, error, image = self.preprocessor.base64_to_image(self.test_images['high_contrast'])
        self.assertTrue(success)
        
        quality, metrics = self.preprocessor.assess_image_quality(image)
        
        self.assertIsInstance(quality, ImageQuality)
        self.assertIsInstance(metrics, dict)
        self.assertIn('blur_score', metrics)
        self.assertIn('brightness', metrics)
        self.assertIn('contrast', metrics)
        self.assertIn('resolution', metrics)
        self.assertIn('dimensions', metrics)
        
        # High contrast image should have good metrics
        self.assertGreater(metrics['contrast'], 20)  # Should have decent contrast
        self.assertEqual(metrics['dimensions'], (200, 200))
    
    def test_assess_image_quality_poor(self):
        """Test quality assessment for poor quality image"""
        success, error, image = self.preprocessor.base64_to_image(self.test_images['tiny'])
        self.assertTrue(success)
        
        quality, metrics = self.preprocessor.assess_image_quality(image)
        
        # Tiny image should have poor quality due to low resolution
        self.assertIn(quality, [ImageQuality.POOR, ImageQuality.FAIR])
        self.assertEqual(metrics['dimensions'], (50, 50))
        self.assertLess(metrics['resolution'], 10000)  # Low pixel count
    
    def test_optimize_for_vision_model_resize_large(self):
        """Test optimization that requires resizing large image"""
        success, error, image = self.preprocessor.base64_to_image(self.test_images['large'])
        self.assertTrue(success)
        
        success, message, optimized = self.preprocessor.optimize_for_vision_model(image)
        
        self.assertTrue(success)
        self.assertIn("resized", message)
        self.assertIsInstance(optimized, Image.Image)
        
        # Should be resized to within limits
        self.assertLessEqual(max(optimized.size), self.preprocessor.MAX_DIMENSION)
        self.assertGreaterEqual(min(optimized.size), self.preprocessor.MIN_DIMENSION)
    
    def test_optimize_for_vision_model_resize_small(self):
        """Test optimization that requires resizing small image"""
        success, error, image = self.preprocessor.base64_to_image(self.test_images['tiny'])
        self.assertTrue(success)
        
        success, message, optimized = self.preprocessor.optimize_for_vision_model(image)
        
        self.assertTrue(success)
        self.assertIn("resized", message)
        self.assertIsInstance(optimized, Image.Image)
        
        # Should be resized to at least minimum dimension
        self.assertGreaterEqual(min(optimized.size), self.preprocessor.MIN_DIMENSION)
    
    def test_optimization_levels(self):
        """Test different optimization levels"""
        success, error, image = self.preprocessor.base64_to_image(self.test_images['rgb_jpeg'])
        self.assertTrue(success)
        
        # Test each optimization level
        levels = [
            ImageOptimizationLevel.NONE,
            ImageOptimizationLevel.BASIC,
            ImageOptimizationLevel.ENHANCED,
            ImageOptimizationLevel.AGGRESSIVE
        ]
        
        for level in levels:
            preprocessor = ImagePreprocessor(level)
            success, message, optimized = preprocessor.optimize_for_vision_model(image)
            
            self.assertTrue(success, f"Optimization failed for level {level}")
            self.assertIsInstance(optimized, Image.Image)
            
            if level != ImageOptimizationLevel.NONE:
                self.assertIn("optimization", message.lower())
    
    def test_resize_image_aspect_ratio_preservation(self):
        """Test that aspect ratio is preserved during resizing"""
        # Create image with specific aspect ratio
        original_img = Image.new('RGB', (400, 200), color=(255, 0, 0))  # 2:1 aspect ratio
        
        resized = self.preprocessor._resize_image(original_img)
        
        # Calculate aspect ratios
        original_ratio = original_img.width / original_img.height
        resized_ratio = resized.width / resized.height
        
        # Should be approximately equal (within small tolerance)
        self.assertAlmostEqual(original_ratio, resized_ratio, places=2)
    
    def test_quality_metrics_calculation(self):
        """Test individual quality metric calculations"""
        # Create test array
        test_array = np.array([[100, 150, 200], [50, 100, 150], [0, 50, 100]], dtype=np.uint8)
        
        # Test brightness calculation
        brightness = self.preprocessor._calculate_brightness(test_array)
        expected_brightness = np.mean(test_array)
        self.assertAlmostEqual(brightness, expected_brightness, places=1)
        
        # Test contrast calculation
        contrast = self.preprocessor._calculate_contrast(test_array)
        expected_contrast = np.std(test_array)
        self.assertAlmostEqual(contrast, expected_contrast, places=1)
        
        # Test Laplacian variance (blur detection)
        blur_score = self.preprocessor._calculate_laplacian_variance(test_array)
        self.assertIsInstance(blur_score, float)
        self.assertGreaterEqual(blur_score, 0)
    
    def test_color_richness_calculation(self):
        """Test color richness calculation"""
        # Create image with limited colors
        limited_color_img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        richness_limited = self.preprocessor._calculate_color_richness(limited_color_img)
        
        # Create image with more colors
        rich_color_img = Image.new('RGB', (100, 100))
        for x in range(100):
            for y in range(100):
                rich_color_img.putpixel((x, y), (x * 2, y * 2, (x + y) % 256))
        richness_rich = self.preprocessor._calculate_color_richness(rich_color_img)
        
        # Rich image should have higher color richness
        self.assertGreater(richness_rich, richness_limited)
        self.assertLessEqual(richness_rich, 1.0)
        self.assertGreaterEqual(richness_limited, 0.0)

class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a test image
        img = Image.new('RGB', (300, 300), color=(128, 128, 128))
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        self.test_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def test_convert_base64_to_optimized_image(self):
        """Test base64 to optimized image conversion"""
        success, message, optimized_base64 = convert_base64_to_optimized_image(
            self.test_base64, 
            ImageOptimizationLevel.BASIC
        )
        
        self.assertTrue(success)
        self.assertIsInstance(message, str)
        self.assertIsInstance(optimized_base64, str)
        self.assertGreater(len(optimized_base64), 0)
        
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(optimized_base64)
            self.assertGreater(len(decoded), 0)
        except Exception:
            self.fail("Optimized base64 is invalid")
    
    def test_convert_base64_to_optimized_image_invalid(self):
        """Test conversion with invalid input"""
        success, message, optimized_base64 = convert_base64_to_optimized_image("invalid_data")
        
        self.assertFalse(success)
        self.assertIn("Failed to convert", message)
        self.assertIsNone(optimized_base64)
    
    def test_assess_image_quality_from_base64(self):
        """Test quality assessment from base64"""
        success, error, quality, metrics = assess_image_quality_from_base64(self.test_base64)
        
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertIsInstance(quality, ImageQuality)
        self.assertIsInstance(metrics, dict)
        self.assertIn('brightness', metrics)
        self.assertIn('contrast', metrics)
    
    def test_assess_image_quality_from_base64_invalid(self):
        """Test quality assessment with invalid input"""
        success, error, quality, metrics = assess_image_quality_from_base64("invalid_data")
        
        self.assertFalse(success)
        self.assertIn("Failed to convert", error)
        self.assertEqual(quality, ImageQuality.UNKNOWN)
        self.assertEqual(metrics, {})
    
    def test_get_optimal_image_format(self):
        """Test optimal format selection"""
        # Test with good quality, no transparency
        format_good = get_optimal_image_format(ImageQuality.GOOD, False)
        self.assertEqual(format_good, 'JPEG')
        
        # Test with poor quality, no transparency
        format_poor = get_optimal_image_format(ImageQuality.POOR, False)
        self.assertEqual(format_poor, 'PNG')
        
        # Test with transparency
        format_transparent = get_optimal_image_format(ImageQuality.GOOD, True)
        self.assertEqual(format_transparent, 'PNG')

class TestImagePreprocessingIntegration(unittest.TestCase):
    """Integration tests for image preprocessing"""
    
    def test_full_preprocessing_workflow(self):
        """Test complete preprocessing workflow"""
        # Create test image
        original_img = Image.new('RGB', (100, 100), color=(200, 100, 50))
        buffer = io.BytesIO()
        original_img.save(buffer, format='JPEG')
        test_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        preprocessor = ImagePreprocessor(ImageOptimizationLevel.ENHANCED)
        
        # Step 1: Convert to PIL Image
        success, error, image = preprocessor.base64_to_image(test_base64)
        self.assertTrue(success)
        
        # Step 2: Assess quality
        quality, metrics = preprocessor.assess_image_quality(image)
        self.assertIsInstance(quality, ImageQuality)
        
        # Step 3: Optimize
        success, message, optimized = preprocessor.optimize_for_vision_model(image)
        self.assertTrue(success)
        
        # Step 4: Convert back to base64
        success, error, final_base64 = preprocessor.image_to_base64(optimized)
        self.assertTrue(success)
        
        # Verify final result
        self.assertIsInstance(final_base64, str)
        self.assertGreater(len(final_base64), 0)
    
    def test_requirements_compliance(self):
        """Test that preprocessing meets specified requirements"""
        # Requirement 1.2: Convert to base64 format for API transmission
        test_img = Image.new('RGB', (200, 200), color=(255, 0, 0))
        buffer = io.BytesIO()
        test_img.save(buffer, format='JPEG')
        test_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        preprocessor = ImagePreprocessor()
        
        # Should handle base64 input and output
        success, error, image = preprocessor.base64_to_image(test_base64)
        self.assertTrue(success)
        
        success, error, output_base64 = preprocessor.image_to_base64(image)
        self.assertTrue(success)
        
        # Requirement 6.2: Provide guidance on improving image quality
        quality, metrics = preprocessor.assess_image_quality(image)
        self.assertIn('brightness', metrics)
        self.assertIn('contrast', metrics)
        self.assertIn('blur_score', metrics)
        
        # These metrics can be used to provide quality guidance
        self.assertIsInstance(metrics['brightness'], (int, float))
        self.assertIsInstance(metrics['contrast'], (int, float))
    
    def test_error_handling(self):
        """Test error handling in preprocessing"""
        preprocessor = ImagePreprocessor()
        
        # Test with various invalid inputs
        invalid_inputs = [
            "",
            "not_base64",
            "data:image/jpeg,invalid",
            None
        ]
        
        for invalid_input in invalid_inputs:
            if invalid_input is not None:
                success, error, image = preprocessor.base64_to_image(invalid_input)
                self.assertFalse(success)
                self.assertIsInstance(error, str)
                self.assertGreater(len(error), 0)
    
    @patch('image_preprocessing.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are properly logged"""
        preprocessor = ImagePreprocessor()
        
        # Test with invalid data that should trigger logging
        preprocessor.base64_to_image("invalid_data")
        mock_logger.error.assert_called()

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)