"""
Sample test images encoded as base64 strings for testing medication identification.
These are minimal test images created programmatically to avoid copyright issues.
"""

import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import json

def create_test_image(text, size=(200, 100), format='JPEG'):
    """Create a simple test image with text"""
    img = Image.new('RGB', size, color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Calculate text position to center it
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    draw.text((x, y), text, fill='black', font=font)
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

# Test image fixtures with known expected results
TEST_IMAGES = {
    "advil_clear": {
        "base64": create_test_image("ADVIL\n200mg", format='JPEG'),
        "format": "JPEG",
        "expected_name": "Advil",
        "expected_dosage": "200mg",
        "expected_confidence": 0.9,
        "description": "Clear image of Advil 200mg medication",
        "test_category": "clear_single_medication"
    },
    
    "tylenol_clear": {
        "base64": create_test_image("TYLENOL\n500mg", format='PNG'),
        "format": "PNG", 
        "expected_name": "Tylenol",
        "expected_dosage": "500mg",
        "expected_confidence": 0.85,
        "description": "Clear image of Tylenol 500mg medication",
        "test_category": "clear_single_medication"
    },
    
    "ibuprofen_generic": {
        "base64": create_test_image("Ibuprofen\n400mg", format='JPEG'),
        "format": "JPEG",
        "expected_name": "Ibuprofen", 
        "expected_dosage": "400mg",
        "expected_confidence": 0.8,
        "description": "Generic ibuprofen medication image",
        "test_category": "generic_medication"
    },
    
    "aspirin_webp": {
        "base64": create_test_image("ASPIRIN\n81mg", format='JPEG'),  # WebP not supported by PIL by default
        "format": "JPEG",
        "expected_name": "Aspirin",
        "expected_dosage": "81mg", 
        "expected_confidence": 0.75,
        "description": "Aspirin low-dose medication",
        "test_category": "low_dose_medication"
    }
}

# Edge case test images
EDGE_CASE_IMAGES = {
    "blurry_medication": {
        "base64": create_test_image("BLUR MED\n???mg", format='JPEG'),
        "format": "JPEG",
        "expected_name": None,
        "expected_dosage": None,
        "expected_confidence": 0.3,
        "expected_error": "low_confidence",
        "description": "Blurry medication image that should be hard to read",
        "test_category": "poor_quality"
    },
    
    "multiple_medications": {
        "base64": create_test_image("ADVIL 200mg\nTYLENOL 500mg", (300, 150), format='JPEG'),
        "format": "JPEG",
        "expected_name": "Advil",  # Should identify the most prominent one
        "expected_dosage": "200mg",
        "expected_confidence": 0.6,
        "description": "Image with multiple medications visible",
        "test_category": "multiple_items"
    },
    
    "no_medication": {
        "base64": create_test_image("RANDOM TEXT\nNOT MEDICINE", format='JPEG'),
        "format": "JPEG",
        "expected_name": None,
        "expected_dosage": None,
        "expected_confidence": 0.1,
        "expected_error": "no_medication_detected",
        "description": "Image with no medication present",
        "test_category": "no_medication"
    },
    
    "empty_image": {
        "base64": create_test_image("", format='JPEG'),
        "format": "JPEG",
        "expected_name": None,
        "expected_dosage": None,
        "expected_confidence": 0.0,
        "expected_error": "no_content",
        "description": "Empty/blank image",
        "test_category": "empty_content"
    },
    
    "partial_text": {
        "base64": create_test_image("ADV...\n2..mg", format='JPEG'),
        "format": "JPEG",
        "expected_name": None,
        "expected_dosage": None,
        "expected_confidence": 0.4,
        "expected_error": "partial_text",
        "description": "Partially visible medication text",
        "test_category": "partial_visibility"
    }
}

# Format variation test images
FORMAT_TEST_IMAGES = {
    "jpeg_high_quality": {
        "base64": create_test_image("MOTRIN\n600mg", (400, 200), format='JPEG'),
        "format": "JPEG",
        "expected_name": "Motrin",
        "expected_dosage": "600mg",
        "expected_confidence": 0.9,
        "description": "High quality JPEG image",
        "test_category": "format_validation"
    },
    
    "png_transparent": {
        "base64": create_test_image("ALEVE\n220mg", format='PNG'),
        "format": "PNG",
        "expected_name": "Aleve",
        "expected_dosage": "220mg", 
        "expected_confidence": 0.85,
        "description": "PNG format image",
        "test_category": "format_validation"
    }
}

# All test images combined
ALL_TEST_IMAGES = {
    **TEST_IMAGES,
    **EDGE_CASE_IMAGES, 
    **FORMAT_TEST_IMAGES
}

def get_test_image(image_name):
    """Get a specific test image by name"""
    return ALL_TEST_IMAGES.get(image_name)

def get_test_images_by_category(category):
    """Get all test images for a specific category"""
    return {name: data for name, data in ALL_TEST_IMAGES.items() 
            if data.get('test_category') == category}

def get_clear_medication_images():
    """Get images that should successfully identify medications"""
    return get_test_images_by_category('clear_single_medication')

def get_edge_case_images():
    """Get images that represent edge cases and error conditions"""
    categories = ['poor_quality', 'multiple_items', 'no_medication', 'empty_content', 'partial_visibility']
    result = {}
    for category in categories:
        result.update(get_test_images_by_category(category))
    return result

def get_format_validation_images():
    """Get images for testing different formats"""
    return get_test_images_by_category('format_validation')

# Test case metadata
TEST_CASE_METADATA = {
    "total_images": len(ALL_TEST_IMAGES),
    "clear_medications": len(get_clear_medication_images()),
    "edge_cases": len(get_edge_case_images()),
    "format_tests": len(get_format_validation_images()),
    "supported_formats": ["JPEG", "PNG", "WebP"],
    "test_categories": [
        "clear_single_medication",
        "generic_medication", 
        "low_dose_medication",
        "poor_quality",
        "multiple_items",
        "no_medication",
        "empty_content",
        "partial_visibility",
        "format_validation"
    ]
}