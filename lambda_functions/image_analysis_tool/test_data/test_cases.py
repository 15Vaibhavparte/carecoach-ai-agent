"""
Comprehensive test cases for medication image identification.
Includes expected results, validation criteria, and test scenarios.
"""

from .sample_images import ALL_TEST_IMAGES
import json

class TestCase:
    """Represents a single test case for medication identification"""
    
    def __init__(self, name, image_data, expected_result, validation_criteria=None):
        self.name = name
        self.image_data = image_data
        self.expected_result = expected_result
        self.validation_criteria = validation_criteria or {}
    
    def to_dict(self):
        return {
            'name': self.name,
            'image_data': self.image_data,
            'expected_result': self.expected_result,
            'validation_criteria': self.validation_criteria
        }

# Generate test cases from sample images
def create_test_cases():
    """Create comprehensive test cases from sample images"""
    test_cases = []
    
    for image_name, image_data in ALL_TEST_IMAGES.items():
        # Create expected result structure
        expected_result = {
            'success': image_data.get('expected_name') is not None,
            'medication_name': image_data.get('expected_name'),
            'dosage': image_data.get('expected_dosage'),
            'confidence': image_data.get('expected_confidence', 0.0),
            'error_type': image_data.get('expected_error'),
            'image_quality': _determine_image_quality(image_data)
        }
        
        # Create validation criteria
        validation_criteria = {
            'min_confidence': _get_min_confidence(image_data),
            'max_confidence': _get_max_confidence(image_data),
            'should_succeed': expected_result['success'],
            'required_fields': _get_required_fields(image_data),
            'error_handling': _get_error_handling_criteria(image_data)
        }
        
        test_case = TestCase(
            name=image_name,
            image_data={
                'base64': image_data['base64'],
                'format': image_data['format'],
                'description': image_data['description']
            },
            expected_result=expected_result,
            validation_criteria=validation_criteria
        )
        
        test_cases.append(test_case)
    
    return test_cases

def _determine_image_quality(image_data):
    """Determine expected image quality based on test category"""
    category = image_data.get('test_category', '')
    if 'poor_quality' in category or 'blurry' in image_data.get('description', '').lower():
        return 'poor'
    elif 'clear' in image_data.get('description', '').lower():
        return 'good'
    else:
        return 'fair'

def _get_min_confidence(image_data):
    """Get minimum expected confidence for validation"""
    expected_confidence = image_data.get('expected_confidence', 0.0)
    if expected_confidence >= 0.8:
        return 0.7  # Allow some variance for high confidence cases
    elif expected_confidence >= 0.5:
        return 0.4  # Allow more variance for medium confidence
    else:
        return 0.0  # No minimum for low confidence cases

def _get_max_confidence(image_data):
    """Get maximum expected confidence for validation"""
    expected_confidence = image_data.get('expected_confidence', 1.0)
    if expected_confidence <= 0.3:
        return 0.5  # Cap low confidence cases
    else:
        return 1.0  # No maximum for higher confidence cases

def _get_required_fields(image_data):
    """Get required fields based on expected success"""
    if image_data.get('expected_name'):
        return ['medication_name', 'confidence']
    else:
        return ['confidence', 'error_type']

def _get_error_handling_criteria(image_data):
    """Get error handling validation criteria"""
    expected_error = image_data.get('expected_error')
    if expected_error:
        return {
            'should_have_error': True,
            'expected_error_type': expected_error,
            'should_have_suggestions': True
        }
    else:
        return {
            'should_have_error': False,
            'should_have_drug_info': True
        }

# Predefined test scenarios
TEST_SCENARIOS = {
    'happy_path': {
        'name': 'Happy Path - Clear Medication Images',
        'description': 'Test successful identification of clear medication images',
        'test_cases': ['advil_clear', 'tylenol_clear', 'ibuprofen_generic'],
        'success_criteria': {
            'min_success_rate': 0.9,
            'min_avg_confidence': 0.8,
            'required_fields': ['medication_name', 'dosage', 'confidence']
        }
    },
    
    'edge_cases': {
        'name': 'Edge Cases - Error Handling',
        'description': 'Test proper handling of problematic images',
        'test_cases': ['blurry_medication', 'no_medication', 'empty_image'],
        'success_criteria': {
            'should_fail_gracefully': True,
            'should_provide_error_messages': True,
            'should_suggest_alternatives': True
        }
    },
    
    'format_validation': {
        'name': 'Format Validation',
        'description': 'Test support for different image formats',
        'test_cases': ['jpeg_high_quality', 'png_transparent'],
        'success_criteria': {
            'all_formats_supported': True,
            'consistent_results': True
        }
    },
    
    'multiple_items': {
        'name': 'Multiple Items Handling',
        'description': 'Test handling of images with multiple medications',
        'test_cases': ['multiple_medications'],
        'success_criteria': {
            'identifies_primary_medication': True,
            'confidence_reflects_complexity': True
        }
    },
    
    'partial_visibility': {
        'name': 'Partial Visibility',
        'description': 'Test handling of partially visible or obscured text',
        'test_cases': ['partial_text'],
        'success_criteria': {
            'handles_incomplete_data': True,
            'provides_appropriate_confidence': True
        }
    }
}

def get_test_scenario(scenario_name):
    """Get a specific test scenario"""
    return TEST_SCENARIOS.get(scenario_name)

def get_all_test_scenarios():
    """Get all predefined test scenarios"""
    return TEST_SCENARIOS

def create_test_suite():
    """Create a complete test suite with all test cases and scenarios"""
    test_cases = create_test_cases()
    
    return {
        'metadata': {
            'total_test_cases': len(test_cases),
            'total_scenarios': len(TEST_SCENARIOS),
            'created_at': '2024-01-01T00:00:00Z',
            'version': '1.0.0'
        },
        'test_cases': [tc.to_dict() for tc in test_cases],
        'scenarios': TEST_SCENARIOS,
        'validation_rules': {
            'confidence_range': [0.0, 1.0],
            'required_response_fields': ['success', 'confidence'],
            'error_response_fields': ['error_type', 'error_message'],
            'success_response_fields': ['medication_name', 'drug_info']
        }
    }

# Export test data as JSON for external use
def export_test_data(filename='test_data.json'):
    """Export test suite as JSON file"""
    test_suite = create_test_suite()
    with open(filename, 'w') as f:
        json.dump(test_suite, f, indent=2)
    return filename

# Performance test cases
PERFORMANCE_TEST_CASES = {
    'large_image': {
        'description': 'Test with maximum allowed image size',
        'image_size': (2048, 1536),  # Large but within limits
        'expected_processing_time': 5.0,  # seconds
        'memory_limit': 512  # MB
    },
    
    'concurrent_requests': {
        'description': 'Test concurrent processing of multiple images',
        'concurrent_count': 5,
        'expected_avg_response_time': 3.0,
        'timeout_limit': 30.0
    },
    
    'batch_processing': {
        'description': 'Test processing multiple images in sequence',
        'batch_size': 10,
        'expected_total_time': 25.0,
        'memory_efficiency': True
    }
}

def get_performance_test_cases():
    """Get performance test case definitions"""
    return PERFORMANCE_TEST_CASES