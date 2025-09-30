"""
Test fixtures and utilities for medication image identification testing.
Provides base64 encoded test images and validation helpers.
"""

import base64
import json
import os
from typing import Dict, List, Optional, Any
from .sample_images import ALL_TEST_IMAGES, TEST_CASE_METADATA
from .test_cases import create_test_cases, TEST_SCENARIOS

class TestFixtures:
    """Centralized test fixtures for image analysis testing"""
    
    def __init__(self):
        self.test_cases = create_test_cases()
        self.sample_images = ALL_TEST_IMAGES
        self.scenarios = TEST_SCENARIOS
        
    def get_base64_image(self, image_name: str) -> Optional[str]:
        """Get base64 encoded image by name"""
        image_data = self.sample_images.get(image_name)
        return image_data['base64'] if image_data else None
    
    def get_test_case(self, case_name: str) -> Optional[Dict]:
        """Get complete test case by name"""
        for test_case in self.test_cases:
            if test_case.name == case_name:
                return test_case.to_dict()
        return None
    
    def get_test_cases_by_category(self, category: str) -> List[Dict]:
        """Get all test cases for a specific category"""
        return [
            tc.to_dict() for tc in self.test_cases 
            if self.sample_images.get(tc.name, {}).get('test_category') == category
        ]
    
    def get_successful_test_cases(self) -> List[Dict]:
        """Get test cases that should succeed"""
        return [
            tc.to_dict() for tc in self.test_cases 
            if tc.expected_result.get('success', False)
        ]
    
    def get_error_test_cases(self) -> List[Dict]:
        """Get test cases that should produce errors"""
        return [
            tc.to_dict() for tc in self.test_cases 
            if not tc.expected_result.get('success', True)
        ]

# Global fixtures instance
fixtures = TestFixtures()

# Base64 encoded test images for direct use in tests
BASE64_TEST_IMAGES = {
    name: data['base64'] 
    for name, data in ALL_TEST_IMAGES.items()
}

# Expected results for validation
EXPECTED_RESULTS = {
    name: {
        'medication_name': data.get('expected_name'),
        'dosage': data.get('expected_dosage'), 
        'confidence': data.get('expected_confidence', 0.0),
        'should_succeed': data.get('expected_name') is not None,
        'error_type': data.get('expected_error')
    }
    for name, data in ALL_TEST_IMAGES.items()
}

# Test request templates
TEST_REQUEST_TEMPLATES = {
    'bedrock_agent_format': {
        "input": {
            "RequestBody": {
                "content": {
                    "application/json": {
                        "properties": [
                            {
                                "name": "image_data",
                                "value": "{base64_image}"
                            },
                            {
                                "name": "prompt", 
                                "value": "Identify the medication name and dosage in this image"
                            }
                        ]
                    }
                }
            }
        }
    },
    
    'direct_format': {
        "image_data": "{base64_image}",
        "prompt": "Identify the medication name and dosage in this image"
    },
    
    'lambda_event_format': {
        "body": json.dumps({
            "image_data": "{base64_image}",
            "prompt": "Identify the medication name and dosage in this image"
        }),
        "headers": {
            "Content-Type": "application/json"
        }
    }
}

def create_test_request(image_name: str, format_type: str = 'bedrock_agent_format') -> Dict:
    """Create a test request with the specified image and format"""
    base64_image = fixtures.get_base64_image(image_name)
    if not base64_image:
        raise ValueError(f"Image '{image_name}' not found in test fixtures")
    
    template = TEST_REQUEST_TEMPLATES.get(format_type)
    if not template:
        raise ValueError(f"Format type '{format_type}' not supported")
    
    # Replace placeholder with actual base64 image
    request_str = json.dumps(template).replace('{base64_image}', base64_image)
    return json.loads(request_str)

def create_batch_test_requests(image_names: List[str], format_type: str = 'bedrock_agent_format') -> List[Dict]:
    """Create multiple test requests for batch testing"""
    return [create_test_request(name, format_type) for name in image_names]

# Validation utilities
class ResponseValidator:
    """Utilities for validating API responses"""
    
    @staticmethod
    def validate_success_response(response: Dict, expected: Dict) -> Dict[str, Any]:
        """Validate a successful medication identification response"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required fields
        required_fields = ['medication_name', 'confidence']
        for field in required_fields:
            if field not in response:
                validation_result['errors'].append(f"Missing required field: {field}")
                validation_result['valid'] = False
        
        # Validate confidence range
        confidence = response.get('confidence', 0)
        if not (0 <= confidence <= 1):
            validation_result['errors'].append(f"Confidence {confidence} outside valid range [0, 1]")
            validation_result['valid'] = False
        
        # Check expected medication name (if provided)
        if expected.get('medication_name'):
            actual_name = response.get('medication_name', '').lower()
            expected_name = expected['medication_name'].lower()
            if expected_name not in actual_name and actual_name not in expected_name:
                validation_result['warnings'].append(
                    f"Medication name mismatch: expected '{expected_name}', got '{actual_name}'"
                )
        
        # Check confidence expectations
        expected_confidence = expected.get('confidence', 0)
        actual_confidence = response.get('confidence', 0)
        confidence_diff = abs(actual_confidence - expected_confidence)
        if confidence_diff > 0.3:  # Allow 30% variance
            validation_result['warnings'].append(
                f"Confidence variance: expected ~{expected_confidence}, got {actual_confidence}"
            )
        
        return validation_result
    
    @staticmethod
    def validate_error_response(response: Dict, expected: Dict) -> Dict[str, Any]:
        """Validate an error response"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check that success is False
        if response.get('success', True):
            validation_result['errors'].append("Expected error response but got success=True")
            validation_result['valid'] = False
        
        # Check for error message
        if not response.get('error_message'):
            validation_result['errors'].append("Missing error_message in error response")
            validation_result['valid'] = False
        
        # Check expected error type
        expected_error = expected.get('error_type')
        actual_error = response.get('error_type')
        if expected_error and actual_error != expected_error:
            validation_result['warnings'].append(
                f"Error type mismatch: expected '{expected_error}', got '{actual_error}'"
            )
        
        return validation_result

# Test data generators
def generate_invalid_base64_samples() -> Dict[str, str]:
    """Generate invalid base64 strings for negative testing"""
    return {
        'invalid_characters': 'invalid@base64#string!',
        'incomplete_padding': 'SGVsbG8gV29ybGQ',  # Missing padding
        'empty_string': '',
        'non_image_data': base64.b64encode(b'This is not image data').decode('utf-8'),
        'malformed_json': '{"invalid": json}',
        'null_value': None
    }

def generate_oversized_image_base64() -> str:
    """Generate a base64 string representing an oversized image"""
    # Create a large dummy data string (simulating 15MB image)
    large_data = b'x' * (15 * 1024 * 1024)  # 15MB of dummy data
    return base64.b64encode(large_data).decode('utf-8')

def generate_test_scenarios_data() -> Dict[str, List[str]]:
    """Generate test data organized by scenarios"""
    return {
        scenario_name: scenario_data.get('test_cases', [])
        for scenario_name, scenario_data in TEST_SCENARIOS.items()
    }

# Export functions for external use
def export_fixtures_json(filepath: str = 'test_fixtures.json') -> str:
    """Export all test fixtures as JSON"""
    fixtures_data = {
        'base64_images': BASE64_TEST_IMAGES,
        'expected_results': EXPECTED_RESULTS,
        'test_scenarios': TEST_SCENARIOS,
        'request_templates': TEST_REQUEST_TEMPLATES,
        'metadata': TEST_CASE_METADATA
    }
    
    with open(filepath, 'w') as f:
        json.dump(fixtures_data, f, indent=2)
    
    return filepath

def load_fixtures_from_json(filepath: str) -> Dict:
    """Load test fixtures from JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

# Quick access functions for common test patterns
def get_clear_medication_fixtures() -> List[str]:
    """Get fixture names for clear medication images"""
    return [name for name, data in ALL_TEST_IMAGES.items() 
            if data.get('test_category') == 'clear_single_medication']

def get_error_case_fixtures() -> List[str]:
    """Get fixture names for error test cases"""
    error_categories = ['poor_quality', 'no_medication', 'empty_content', 'partial_visibility']
    return [name for name, data in ALL_TEST_IMAGES.items() 
            if data.get('test_category') in error_categories]

def get_format_test_fixtures() -> List[str]:
    """Get fixture names for format validation tests"""
    return [name for name, data in ALL_TEST_IMAGES.items() 
            if data.get('test_category') == 'format_validation']