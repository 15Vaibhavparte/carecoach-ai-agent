"""
Image preprocessing utilities for the medication identification system.
This module provides image conversion, quality assessment, and optimization
for vision model input.
"""

import base64
import io
import logging
from typing import Tuple, Dict, Any, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from enum import Enum
import math

from models import ImageQuality, ImageValidationResult
from config import config

logger = logging.getLogger(__name__)

class ImageOptimizationLevel(Enum):
    """Enumeration for image optimization levels"""
    NONE = "none"
    BASIC = "basic"
    ENHANCED = "enhanced"
    AGGRESSIVE = "aggressive"

class ImagePreprocessor:
    """
    Comprehensive image preprocessing utility class.
    Handles base64 conversion, quality assessment, and optimization.
    """
    
    # Optimal dimensions for vision models
    OPTIMAL_WIDTH = 1024
    OPTIMAL_HEIGHT = 1024
    MAX_DIMENSION = 2048
    MIN_DIMENSION = 224
    
    # Quality assessment thresholds
    QUALITY_THRESHOLDS = {
        'blur_threshold': 100.0,  # Laplacian variance threshold
        'brightness_min': 50,     # Minimum average brightness
        'brightness_max': 200,    # Maximum average brightness
        'contrast_min': 30,       # Minimum contrast
        'min_file_size': 5000,    # Minimum file size for good quality
    }
    
    def __init__(self, optimization_level: ImageOptimizationLevel = ImageOptimizationLevel.BASIC):
        """
        Initialize the image preprocessor.
        
        Args:
            optimization_level: Level of optimization to apply
        """
        self.optimization_level = optimization_level
    
    def base64_to_image(self, base64_data: str) -> Tuple[bool, str, Optional[Image.Image]]:
        """
        Convert base64 string to PIL Image object.
        
        Args:
            base64_data: Base64 encoded image string
            
        Returns:
            Tuple of (success, error_message, image_object)
        """
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:'):
                if ';base64,' in base64_data:
                    base64_data = base64_data.split(';base64,')[1]
                else:
                    return False, "Invalid data URL format", None
            
            # Clean base64 string
            base64_data = base64_data.strip().replace('\n', '').replace('\r', '').replace(' ', '')
            
            # Add padding if needed
            if len(base64_data) % 4 != 0:
                base64_data += '=' * (4 - len(base64_data) % 4)
            
            # Decode base64
            image_bytes = base64.b64decode(base64_data, validate=True)
            
            # Create PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary (handles RGBA, P, etc.)
            if image.mode not in ('RGB', 'L'):
                if image.mode == 'RGBA':
                    # Create white background for transparency
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                    image = background
                elif image.mode == 'P':
                    image = image.convert('RGB')
                elif image.mode in ('LA', 'CMYK'):
                    image = image.convert('RGB')
            
            return True, "", image
            
        except Exception as e:
            logger.error(f"Base64 to image conversion failed: {str(e)}")
            return False, f"Failed to convert base64 to image: {str(e)}", None
    
    def image_to_base64(self, image: Image.Image, format: str = 'JPEG', quality: int = 85) -> Tuple[bool, str, str]:
        """
        Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            format: Output format (JPEG, PNG, WebP)
            quality: JPEG quality (1-100)
            
        Returns:
            Tuple of (success, error_message, base64_string)
        """
        try:
            buffer = io.BytesIO()
            
            # Ensure RGB mode for JPEG
            if format.upper() == 'JPEG' and image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save with appropriate parameters
            save_kwargs = {}
            if format.upper() == 'JPEG':
                save_kwargs = {'quality': quality, 'optimize': True}
            elif format.upper() == 'PNG':
                save_kwargs = {'optimize': True}
            elif format.upper() == 'WEBP':
                save_kwargs = {'quality': quality, 'optimize': True}
            
            image.save(buffer, format=format.upper(), **save_kwargs)
            
            # Convert to base64
            base64_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return True, "", base64_string
            
        except Exception as e:
            logger.error(f"Image to base64 conversion failed: {str(e)}")
            return False, f"Failed to convert image to base64: {str(e)}", ""
    
    def assess_image_quality(self, image: Image.Image) -> Tuple[ImageQuality, Dict[str, Any]]:
        """
        Assess image quality using various metrics.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (quality_enum, quality_metrics)
        """
        try:
            metrics = {}
            
            # Convert to grayscale for some analyses
            gray_image = image.convert('L') if image.mode != 'L' else image
            
            # 1. Blur detection using Laplacian variance
            import numpy as np
            gray_array = np.array(gray_image)
            laplacian_var = self._calculate_laplacian_variance(gray_array)
            metrics['blur_score'] = laplacian_var
            
            # 2. Brightness analysis
            brightness = self._calculate_brightness(gray_array)
            metrics['brightness'] = brightness
            
            # 3. Contrast analysis
            contrast = self._calculate_contrast(gray_array)
            metrics['contrast'] = contrast
            
            # 4. Resolution analysis
            total_pixels = image.width * image.height
            metrics['resolution'] = total_pixels
            metrics['dimensions'] = (image.width, image.height)
            
            # 5. File size estimation (approximate)
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            estimated_size = len(buffer.getvalue())
            metrics['estimated_file_size'] = estimated_size
            
            # 6. Color richness (for RGB images)
            if image.mode == 'RGB':
                color_richness = self._calculate_color_richness(image)
                metrics['color_richness'] = color_richness
            
            # Determine overall quality
            quality = self._determine_quality_level(metrics)
            
            return quality, metrics
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {str(e)}")
            return ImageQuality.UNKNOWN, {'error': str(e)}
    
    def _calculate_laplacian_variance(self, gray_array) -> float:
        """Calculate Laplacian variance for blur detection"""
        try:
            import numpy as np
            from scipy import ndimage
            
            # Apply Laplacian filter
            laplacian = ndimage.laplace(gray_array)
            return float(np.var(laplacian))
        except ImportError:
            # Fallback without scipy
            import numpy as np
            # Simple edge detection
            edges_x = np.abs(np.diff(gray_array, axis=1))
            edges_y = np.abs(np.diff(gray_array, axis=0))
            return float(np.mean(edges_x) + np.mean(edges_y))
    
    def _calculate_brightness(self, gray_array) -> float:
        """Calculate average brightness"""
        import numpy as np
        return float(np.mean(gray_array))
    
    def _calculate_contrast(self, gray_array) -> float:
        """Calculate image contrast"""
        import numpy as np
        return float(np.std(gray_array))
    
    def _calculate_color_richness(self, image: Image.Image) -> float:
        """Calculate color richness/diversity"""
        try:
            import numpy as np
            # Convert to numpy array
            img_array = np.array(image)
            
            # Calculate unique colors (simplified)
            # Reduce color space to make calculation feasible
            reduced = img_array // 32  # Reduce to 8 levels per channel
            unique_colors = len(np.unique(reduced.reshape(-1, 3), axis=0))
            
            # Normalize by theoretical maximum (8^3 = 512)
            return min(unique_colors / 512.0, 1.0)
        except Exception:
            return 0.5  # Default moderate richness
    
    def _determine_quality_level(self, metrics: Dict[str, Any]) -> ImageQuality:
        """Determine overall quality level from metrics"""
        score = 0
        max_score = 0
        
        # Blur score (higher is better)
        if 'blur_score' in metrics:
            max_score += 1
            if metrics['blur_score'] > self.QUALITY_THRESHOLDS['blur_threshold']:
                score += 1
            elif metrics['blur_score'] > self.QUALITY_THRESHOLDS['blur_threshold'] * 0.5:
                score += 0.5
        
        # Brightness (should be in reasonable range)
        if 'brightness' in metrics:
            max_score += 1
            brightness = metrics['brightness']
            if (self.QUALITY_THRESHOLDS['brightness_min'] <= brightness <= 
                self.QUALITY_THRESHOLDS['brightness_max']):
                score += 1
            elif brightness > 30 and brightness < 220:  # Acceptable range
                score += 0.5
        
        # Contrast (higher is generally better)
        if 'contrast' in metrics:
            max_score += 1
            if metrics['contrast'] > self.QUALITY_THRESHOLDS['contrast_min']:
                score += 1
            elif metrics['contrast'] > self.QUALITY_THRESHOLDS['contrast_min'] * 0.5:
                score += 0.5
        
        # Resolution (adequate pixel count)
        if 'resolution' in metrics:
            max_score += 1
            if metrics['resolution'] > 500000:  # > 0.5MP
                score += 1
            elif metrics['resolution'] > 100000:  # > 0.1MP
                score += 0.5
        
        # File size (not too small)
        if 'estimated_file_size' in metrics:
            max_score += 1
            if metrics['estimated_file_size'] > self.QUALITY_THRESHOLDS['min_file_size']:
                score += 1
            elif metrics['estimated_file_size'] > self.QUALITY_THRESHOLDS['min_file_size'] * 0.5:
                score += 0.5
        
        # Calculate percentage
        if max_score == 0:
            return ImageQuality.UNKNOWN
        
        percentage = score / max_score
        
        if percentage >= 0.8:
            return ImageQuality.GOOD
        elif percentage >= 0.5:
            return ImageQuality.FAIR
        else:
            return ImageQuality.POOR
    
    def optimize_for_vision_model(self, image: Image.Image) -> Tuple[bool, str, Optional[Image.Image]]:
        """
        Optimize image for vision model input.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (success, message, optimized_image)
        """
        try:
            optimized = image.copy()
            optimizations_applied = []
            
            # 1. Resize if necessary
            if (image.width > self.MAX_DIMENSION or 
                image.height > self.MAX_DIMENSION or
                image.width < self.MIN_DIMENSION or 
                image.height < self.MIN_DIMENSION):
                
                optimized = self._resize_image(optimized)
                optimizations_applied.append("resized")
            
            # Apply optimization based on level
            if self.optimization_level == ImageOptimizationLevel.BASIC:
                optimized = self._apply_basic_optimization(optimized)
                optimizations_applied.append("basic_enhancement")
                
            elif self.optimization_level == ImageOptimizationLevel.ENHANCED:
                optimized = self._apply_enhanced_optimization(optimized)
                optimizations_applied.append("enhanced_processing")
                
            elif self.optimization_level == ImageOptimizationLevel.AGGRESSIVE:
                optimized = self._apply_aggressive_optimization(optimized)
                optimizations_applied.append("aggressive_processing")
            
            message = f"Applied optimizations: {', '.join(optimizations_applied)}"
            return True, message, optimized
            
        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            return False, f"Optimization failed: {str(e)}", None
    
    def _resize_image(self, image: Image.Image) -> Image.Image:
        """Resize image to optimal dimensions"""
        # Calculate new dimensions maintaining aspect ratio
        aspect_ratio = image.width / image.height
        
        if image.width > self.MAX_DIMENSION or image.height > self.MAX_DIMENSION:
            # Scale down
            if aspect_ratio > 1:  # Wider than tall
                new_width = self.MAX_DIMENSION
                new_height = int(self.MAX_DIMENSION / aspect_ratio)
            else:  # Taller than wide
                new_height = self.MAX_DIMENSION
                new_width = int(self.MAX_DIMENSION * aspect_ratio)
        elif image.width < self.MIN_DIMENSION or image.height < self.MIN_DIMENSION:
            # Scale up
            if aspect_ratio > 1:  # Wider than tall
                new_height = self.MIN_DIMENSION
                new_width = int(self.MIN_DIMENSION * aspect_ratio)
            else:  # Taller than wide
                new_width = self.MIN_DIMENSION
                new_height = int(self.MIN_DIMENSION / aspect_ratio)
        else:
            # Try to get closer to optimal size
            target_pixels = self.OPTIMAL_WIDTH * self.OPTIMAL_HEIGHT
            current_pixels = image.width * image.height
            
            if current_pixels < target_pixels * 0.5:  # Much smaller than optimal
                scale_factor = math.sqrt(target_pixels / current_pixels)
                new_width = int(image.width * scale_factor)
                new_height = int(image.height * scale_factor)
            else:
                return image  # Size is acceptable
        
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _apply_basic_optimization(self, image: Image.Image) -> Image.Image:
        """Apply basic image enhancements"""
        # Slight sharpening
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
        # Slight contrast enhancement
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.05)
        
        return image
    
    def _apply_enhanced_optimization(self, image: Image.Image) -> Image.Image:
        """Apply enhanced image processing"""
        # Auto-level (normalize histogram)
        image = ImageOps.autocontrast(image, cutoff=1)
        
        # Moderate sharpening
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # Brightness adjustment if needed
        quality, metrics = self.assess_image_quality(image)
        if 'brightness' in metrics:
            brightness = metrics['brightness']
            if brightness < 80:  # Too dark
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(1.2)
            elif brightness > 180:  # Too bright
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(0.9)
        
        return image
    
    def _apply_aggressive_optimization(self, image: Image.Image) -> Image.Image:
        """Apply aggressive image processing"""
        # Start with enhanced optimization
        image = self._apply_enhanced_optimization(image)
        
        # Additional noise reduction
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # More aggressive sharpening
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)
        
        # Color enhancement
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.1)
        
        return image

# Convenience functions

def convert_base64_to_optimized_image(base64_data: str, 
                                    optimization_level: ImageOptimizationLevel = ImageOptimizationLevel.BASIC) -> Tuple[bool, str, Optional[str]]:
    """
    Convert base64 to optimized image for vision model.
    
    Args:
        base64_data: Base64 encoded image
        optimization_level: Level of optimization to apply
        
    Returns:
        Tuple of (success, message, optimized_base64)
    """
    preprocessor = ImagePreprocessor(optimization_level)
    
    # Convert to PIL Image
    success, error, image = preprocessor.base64_to_image(base64_data)
    if not success:
        return False, error, None
    
    # Optimize image
    success, message, optimized_image = preprocessor.optimize_for_vision_model(image)
    if not success:
        return False, message, None
    
    # Convert back to base64
    success, error, optimized_base64 = preprocessor.image_to_base64(optimized_image)
    if not success:
        return False, error, None
    
    return True, message, optimized_base64

def assess_image_quality_from_base64(base64_data: str) -> Tuple[bool, str, ImageQuality, Dict[str, Any]]:
    """
    Assess image quality from base64 data.
    
    Args:
        base64_data: Base64 encoded image
        
    Returns:
        Tuple of (success, error_message, quality, metrics)
    """
    preprocessor = ImagePreprocessor()
    
    # Convert to PIL Image
    success, error, image = preprocessor.base64_to_image(base64_data)
    if not success:
        return False, error, ImageQuality.UNKNOWN, {}
    
    # Assess quality
    quality, metrics = preprocessor.assess_image_quality(image)
    return True, "", quality, metrics

def get_optimal_image_format(image_quality: ImageQuality, has_transparency: bool = False) -> str:
    """
    Get optimal output format based on image quality and characteristics.
    
    Args:
        image_quality: Assessed image quality
        has_transparency: Whether image has transparency
        
    Returns:
        Recommended format string
    """
    if has_transparency:
        return 'PNG'
    
    if image_quality == ImageQuality.GOOD:
        return 'JPEG'  # Good compression for high quality
    elif image_quality == ImageQuality.FAIR:
        return 'JPEG'  # Still good for moderate quality
    else:
        return 'PNG'   # Lossless for poor quality to avoid further degradation