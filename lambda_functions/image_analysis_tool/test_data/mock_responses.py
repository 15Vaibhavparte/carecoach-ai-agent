"""
Mock responses for vision model and DrugInfoTool for testing.
Provides realistic mock data for unit and integration testing.
"""

import json
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Mock Vision Model Responses
MOCK_VISION_RESPONSES = {
    'advil_clear': {
        'response': {
            'content': [
                {
                    'text': '''Based on the image analysis, I can identify the following medication:

**Medication Name:** Advil
**Generic Name:** Ibuprofen  
**Dosage:** 200mg
**Confidence:** 0.95

The image shows a clear view of Advil tablets with visible branding and dosage information. The medication is easily identifiable with high confidence.'''
                }
            ]
        },
        'usage': {
            'input_tokens': 1250,
            'output_tokens': 85
        }
    },
    
    'tylenol_clear': {
        'response': {
            'content': [
                {
                    'text': '''Medication identification results:

**Medication Name:** Tylenol
**Generic Name:** Acetaminophen
**Dosage:** 500mg
**Confidence:** 0.92

The image clearly shows Tylenol Extra Strength tablets. The packaging and pill markings are clearly visible, allowing for confident identification.'''
                }
            ]
        },
        'usage': {
            'input_tokens': 1180,
            'output_tokens': 78
        }
    },
    
    'ibuprofen_generic': {
        'response': {
            'content': [
                {
                    'text': '''Medication Analysis:

**Medication Name:** Ibuprofen
**Generic Name:** Ibuprofen
**Dosage:** 400mg
**Confidence:** 0.88

This appears to be a generic ibuprofen tablet. The imprint and shape are consistent with standard 400mg ibuprofen tablets, though the generic nature makes identification slightly less certain than branded medications.'''
                }
            ]
        },
        'usage': {
            'input_tokens': 1200,
            'output_tokens': 82
        }
    },
    
    'blurry_medication': {
        'response': {
            'content': [
                {
                    'text': '''Image Analysis Results:

**Medication Name:** Unable to determine
**Confidence:** 0.25

The image quality is too poor to make a reliable identification. The text and markings on the medication are not clearly visible due to blur or poor lighting. Please retake the photo with better focus and lighting for accurate identification.'''
                }
            ]
        },
        'usage': {
            'input_tokens': 1100,
            'output_tokens': 65
        }
    },
    
    'no_medication': {
        'response': {
            'content': [
                {
                    'text': '''Image Analysis Results:

**Medication Name:** No medication detected
**Confidence:** 0.05

I cannot identify any medication in this image. The image appears to show other objects but no pharmaceutical products are visible. Please ensure the medication is clearly visible in the frame and retake the photo.'''
                }
            ]
        },
        'usage': {
            'input_tokens': 950,
            'output_tokens': 58
        }
    },
    
    'multiple_medications': {
        'response': {
            'content': [
                {
                    'text': '''Multiple Medications Detected:

**Primary Medication:** Aspirin
**Dosage:** 325mg
**Confidence:** 0.78

**Secondary Items:** Additional medications visible but focusing on the most prominent item. Multiple medications detected in image - recommend photographing each medication separately for more accurate identification.'''
                }
            ]
        },
        'usage': {
            'input_tokens': 1350,
            'output_tokens': 95
        }
    },
    
    'partial_text': {
        'response': {
            'content': [
                {
                    'text': '''Partial Identification Results:

**Medication Name:** Likely Metformin
**Dosage:** Partially visible, appears to be 500mg
**Confidence:** 0.65

The medication text is partially obscured or cut off in the image. Based on visible portions, this appears to be Metformin, but complete identification requires a clearer view of all text and markings.'''
                }
            ]
        },
        'usage': {
            'input_tokens': 1150,
            'output_tokens': 72
        }
    },
    
    'empty_image': {
        'response': {
            'content': [
                {
                    'text': '''Image Analysis Error:

**Status:** No content detected
**Confidence:** 0.00

The provided image appears to be empty or contains no visible content. Please ensure you have uploaded a valid image file containing a medication and try again.'''
                }
            ]
        },
        'usage': {
            'input_tokens': 800,
            'output_tokens': 45
        }
    }
}

# Mock DrugInfoTool Responses
MOCK_DRUG_INFO_RESPONSES = {
    'advil': {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'data': {
                'brand_name': 'Advil',
                'generic_name': 'Ibuprofen',
                'purpose': 'Pain reliever/fever reducer (NSAID)',
                'active_ingredient': 'Ibuprofen 200mg',
                'warnings': [
                    'Allergy alert: Ibuprofen may cause a severe allergic reaction',
                    'Stomach bleeding warning: This product contains an NSAID',
                    'Do not use if you have ever had an allergic reaction to any pain reliever/fever reducer'
                ],
                'directions': [
                    'Adults and children 12 years and over: take 1 capsule every 4 to 6 hours while symptoms persist',
                    'If pain or fever does not respond to 1 capsule, 2 capsules may be used',
                    'Do not exceed 6 capsules in 24 hours unless directed by a doctor'
                ],
                'indications_and_usage': 'Temporarily relieves minor aches and pains due to headache, muscular aches, minor pain of arthritis, toothache, backache, the common cold, menstrual cramps, and temporarily reduces fever',
                'inactive_ingredients': 'Croscarmellose sodium, corn starch, FD&C red no. 40, FD&C yellow no. 6, hypromellose, iron oxide, polyethylene glycol, polysorbate 80, silicon dioxide, sodium lauryl sulfate, stearic acid, titanium dioxide'
            }
        })
    },
    
    'tylenol': {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'data': {
                'brand_name': 'Tylenol',
                'generic_name': 'Acetaminophen',
                'purpose': 'Pain reliever/fever reducer',
                'active_ingredient': 'Acetaminophen 500mg',
                'warnings': [
                    'Liver warning: This product contains acetaminophen',
                    'Severe or recurring liver damage may occur if you take more than 4,000 mg of acetaminophen in 24 hours',
                    'Do not use with other drugs containing acetaminophen'
                ],
                'directions': [
                    'Adults and children 12 years and over: take 2 caplets every 6 hours while symptoms last',
                    'Do not take more than 6 caplets in 24 hours',
                    'Do not use for more than 10 days unless directed by a doctor'
                ],
                'indications_and_usage': 'Temporarily reduces fever and relieves minor aches and pains due to headache, muscular aches, backache, minor pain of arthritis, the common cold, toothache, and premenstrual and menstrual cramps',
                'inactive_ingredients': 'Corn starch, hypromellose, magnesium stearate, microcrystalline cellulose, polyethylene glycol, polysorbate 80, sodium starch glycolate, titanium dioxide'
            }
        })
    },
    
    'ibuprofen': {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'data': {
                'brand_name': 'Ibuprofen',
                'generic_name': 'Ibuprofen',
                'purpose': 'Pain reliever/fever reducer (NSAID)',
                'active_ingredient': 'Ibuprofen 400mg',
                'warnings': [
                    'NSAID Warning: This product contains an NSAID, which may cause severe stomach bleeding',
                    'Allergy alert: Ibuprofen may cause a severe allergic reaction',
                    'Heart attack and stroke warning: NSAIDs may increase your risk of heart attack or stroke'
                ],
                'directions': [
                    'Adults: take 1 tablet every 4 to 6 hours while symptoms persist',
                    'If pain or fever does not respond to 1 tablet, 2 tablets may be used',
                    'Do not exceed 6 tablets in 24 hours unless directed by a doctor'
                ],
                'indications_and_usage': 'Temporarily relieves minor aches and pains due to headache, toothache, backache, menstrual cramps, the common cold, muscular aches, and minor pain of arthritis, and temporarily reduces fever',
                'inactive_ingredients': 'Colloidal silicon dioxide, corn starch, croscarmellose sodium, hypromellose, magnesium stearate, microcrystalline cellulose, polydextrose, polyethylene glycol, stearic acid, titanium dioxide'
            }
        })
    },
    
    'aspirin': {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'data': {
                'brand_name': 'Aspirin',
                'generic_name': 'Aspirin',
                'purpose': 'Pain reliever/fever reducer',
                'active_ingredient': 'Aspirin 325mg',
                'warnings': [
                    'Reye\'s syndrome: Children and teenagers who have or are recovering from chicken pox or flu-like symptoms should not use this product',
                    'Allergy alert: Aspirin may cause a severe allergic reaction',
                    'Stomach bleeding warning: This product contains an NSAID'
                ],
                'directions': [
                    'Adults and children 12 years and over: take 1 to 2 tablets every 4 hours while symptoms persist',
                    'Do not take more than 12 tablets in 24 hours',
                    'Children under 12 years: consult a doctor'
                ],
                'indications_and_usage': 'For the temporary relief of minor aches and pains associated with headache, muscular aches, minor arthritis pain, toothache, and menstrual cramps, and to reduce fever',
                'inactive_ingredients': 'Corn starch, hypromellose, powdered cellulose, triacetin'
            }
        })
    },
    
    'metformin': {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'data': {
                'brand_name': 'Metformin',
                'generic_name': 'Metformin Hydrochloride',
                'purpose': 'Antidiabetic agent',
                'active_ingredient': 'Metformin Hydrochloride 500mg',
                'warnings': [
                    'Prescription medication - use only as directed by healthcare provider',
                    'Lactic acidosis warning: Rare but serious metabolic complication',
                    'Kidney function monitoring required during treatment'
                ],
                'directions': [
                    'Take exactly as prescribed by your doctor',
                    'Usually taken with meals to reduce stomach upset',
                    'Do not crush, chew, or break extended-release tablets'
                ],
                'indications_and_usage': 'Used to treat type 2 diabetes mellitus as an adjunct to diet and exercise to improve glycemic control in adults and pediatric patients 10 years of age and older',
                'inactive_ingredients': 'Hypromellose, magnesium stearate, microcrystalline cellulose, polyethylene glycol, povidone'
            }
        })
    },
    
    'medication_not_found': {
        'statusCode': 404,
        'body': json.dumps({
            'success': False,
            'error': 'Medication not found in database',
            'message': 'The specified medication could not be found in our drug information database. Please verify the medication name and try again.',
            'suggestions': [
                'Check the spelling of the medication name',
                'Try using the generic name instead of brand name',
                'Consult with a healthcare provider for unknown medications'
            ]
        })
    },
    
    'api_error': {
        'statusCode': 500,
        'body': json.dumps({
            'success': False,
            'error': 'Internal server error',
            'message': 'An error occurred while retrieving drug information. Please try again later.',
            'retry_after': 30
        })
    },
    
    'rate_limit_error': {
        'statusCode': 429,
        'body': json.dumps({
            'success': False,
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please wait before making another request.',
            'retry_after': 60
        })
    }
}

# Mock Error Responses for Various Scenarios
MOCK_ERROR_RESPONSES = {
    'invalid_image_format': {
        'success': False,
        'error_type': 'invalid_format',
        'error_message': 'Unsupported image format. Please use JPEG, PNG, or WebP.',
        'suggestions': ['Convert image to supported format', 'Check file extension']
    },
    
    'image_too_large': {
        'success': False,
        'error_type': 'file_too_large',
        'error_message': 'Image file size exceeds maximum limit of 10MB.',
        'suggestions': ['Compress the image', 'Use a smaller resolution']
    },
    
    'corrupted_image': {
        'success': False,
        'error_type': 'corrupted_file',
        'error_message': 'Image file appears to be corrupted or unreadable.',
        'suggestions': ['Try uploading a different image', 'Check file integrity']
    },
    
    'vision_api_timeout': {
        'success': False,
        'error_type': 'api_timeout',
        'error_message': 'Vision analysis timed out. Please try again.',
        'suggestions': ['Retry the request', 'Try with a smaller image']
    },
    
    'vision_api_error': {
        'success': False,
        'error_type': 'vision_api_error',
        'error_message': 'Vision analysis service is temporarily unavailable.',
        'suggestions': ['Try again in a few minutes', 'Contact support if problem persists']
    },
    
    'drug_info_unavailable': {
        'success': False,
        'error_type': 'drug_info_error',
        'error_message': 'Drug information service is currently unavailable.',
        'suggestions': ['Try again later', 'Consult healthcare provider for medication information']
    },
    
    'low_confidence': {
        'success': False,
        'error_type': 'low_confidence',
        'error_message': 'Unable to identify medication with sufficient confidence.',
        'suggestions': ['Retake photo with better lighting', 'Ensure medication text is clearly visible', 'Try a different angle']
    }
}

# Response Generation Utilities
class MockResponseGenerator:
    """Utility class for generating mock responses with realistic variations"""
    
    @staticmethod
    def generate_vision_response(medication_name: str, confidence: float = None, 
                               dosage: str = None, error_type: str = None) -> Dict:
        """Generate a mock vision model response"""
        if error_type:
            return MockResponseGenerator._generate_error_vision_response(error_type)
        
        if confidence is None:
            confidence = random.uniform(0.7, 0.95)
        
        # Generate realistic response text
        response_text = f"""Medication identification results:

**Medication Name:** {medication_name}
**Dosage:** {dosage or 'Not clearly visible'}
**Confidence:** {confidence:.2f}

The image shows {'clear' if confidence > 0.8 else 'partial'} identification of the medication."""
        
        return {
            'response': {
                'content': [{'text': response_text}]
            },
            'usage': {
                'input_tokens': random.randint(1000, 1400),
                'output_tokens': random.randint(60, 100)
            }
        }
    
    @staticmethod
    def _generate_error_vision_response(error_type: str) -> Dict:
        """Generate error response from vision model"""
        error_messages = {
            'no_medication': 'No medication detected in the image.',
            'poor_quality': 'Image quality too poor for reliable identification.',
            'multiple_items': 'Multiple items detected. Please photograph one medication at a time.',
            'unclear_text': 'Medication text is not clearly visible.'
        }
        
        message = error_messages.get(error_type, 'Unable to process image.')
        
        return {
            'response': {
                'content': [{'text': f"Error: {message}"}]
            },
            'usage': {
                'input_tokens': random.randint(800, 1200),
                'output_tokens': random.randint(30, 60)
            }
        }
    
    @staticmethod
    def generate_drug_info_response(medication_name: str, success: bool = True) -> Dict:
        """Generate a mock DrugInfoTool response"""
        if not success:
            return MOCK_DRUG_INFO_RESPONSES['medication_not_found']
        
        # Check if we have a predefined response
        med_key = medication_name.lower().replace(' ', '_')
        if med_key in MOCK_DRUG_INFO_RESPONSES:
            return MOCK_DRUG_INFO_RESPONSES[med_key]
        
        # Generate generic response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'data': {
                    'brand_name': medication_name,
                    'generic_name': medication_name,
                    'purpose': 'Medication information',
                    'active_ingredient': f'{medication_name} (dosage varies)',
                    'warnings': ['Consult healthcare provider before use'],
                    'directions': ['Use as directed by healthcare provider'],
                    'indications_and_usage': 'As prescribed by healthcare provider'
                }
            })
        }
    
    @staticmethod
    def generate_combined_response(medication_name: str, confidence: float,
                                 dosage: str = None, include_drug_info: bool = True,
                                 processing_time: float = None) -> Dict:
        """Generate a complete combined response"""
        if processing_time is None:
            processing_time = random.uniform(1.5, 4.0)
        
        response = {
            'success': True,
            'identification': {
                'medication_name': medication_name,
                'dosage': dosage,
                'confidence': confidence,
                'image_quality': 'good' if confidence > 0.8 else 'fair'
            },
            'processing_time': processing_time,
            'timestamp': datetime.now().isoformat()
        }
        
        if include_drug_info:
            drug_response = MockResponseGenerator.generate_drug_info_response(medication_name)
            if drug_response['statusCode'] == 200:
                response['drug_info'] = json.loads(drug_response['body'])['data']
            else:
                response['drug_info_error'] = 'Drug information unavailable'
        
        return response

# Test Data Generators
def generate_random_test_data(count: int = 10) -> List[Dict]:
    """Generate random test data for stress testing"""
    medications = ['Advil', 'Tylenol', 'Aspirin', 'Ibuprofen', 'Acetaminophen']
    dosages = ['200mg', '325mg', '500mg', '400mg', '650mg']
    
    test_data = []
    for i in range(count):
        medication = random.choice(medications)
        dosage = random.choice(dosages)
        confidence = random.uniform(0.3, 0.95)
        
        test_case = {
            'id': f'random_test_{i+1}',
            'medication_name': medication,
            'dosage': dosage,
            'confidence': confidence,
            'expected_success': confidence > 0.5,
            'mock_response': MockResponseGenerator.generate_combined_response(
                medication, confidence, dosage
            )
        }
        test_data.append(test_case)
    
    return test_data

def generate_performance_test_data() -> Dict:
    """Generate test data for performance testing"""
    return {
        'concurrent_requests': [
            {
                'request_id': f'perf_test_{i}',
                'medication': random.choice(['Advil', 'Tylenol', 'Aspirin']),
                'expected_response_time': random.uniform(1.0, 3.0)
            }
            for i in range(10)
        ],
        'large_batch': [
            {
                'batch_id': f'batch_{i}',
                'size': random.randint(5, 20),
                'expected_total_time': random.uniform(10.0, 60.0)
            }
            for i in range(5)
        ]
    }

# Response Validation Utilities
class ResponseValidator:
    """Utilities for validating mock responses against expected formats"""
    
    @staticmethod
    def validate_vision_response(response: Dict) -> Dict[str, Any]:
        """Validate vision model response format"""
        validation_result = {'valid': True, 'errors': []}
        
        # Check required structure
        if 'response' not in response:
            validation_result['errors'].append('Missing response field')
            validation_result['valid'] = False
        
        if 'content' not in response.get('response', {}):
            validation_result['errors'].append('Missing content field')
            validation_result['valid'] = False
        
        content = response.get('response', {}).get('content', [])
        if not content or 'text' not in content[0]:
            validation_result['errors'].append('Missing text content')
            validation_result['valid'] = False
        
        return validation_result
    
    @staticmethod
    def validate_drug_info_response(response: Dict) -> Dict[str, Any]:
        """Validate DrugInfoTool response format"""
        validation_result = {'valid': True, 'errors': []}
        
        # Check status code
        if 'statusCode' not in response:
            validation_result['errors'].append('Missing statusCode')
            validation_result['valid'] = False
        
        # Check body format
        if 'body' not in response:
            validation_result['errors'].append('Missing body')
            validation_result['valid'] = False
        else:
            try:
                body_data = json.loads(response['body'])
                if 'success' not in body_data:
                    validation_result['errors'].append('Missing success field in body')
                    validation_result['valid'] = False
            except json.JSONDecodeError:
                validation_result['errors'].append('Invalid JSON in body')
                validation_result['valid'] = False
        
        return validation_result
    
    @staticmethod
    def validate_combined_response(response: Dict) -> Dict[str, Any]:
        """Validate complete combined response format"""
        validation_result = {'valid': True, 'errors': []}
        
        required_fields = ['success', 'identification', 'processing_time']
        for field in required_fields:
            if field not in response:
                validation_result['errors'].append(f'Missing required field: {field}')
                validation_result['valid'] = False
        
        # Validate identification structure
        identification = response.get('identification', {})
        id_required = ['medication_name', 'confidence']
        for field in id_required:
            if field not in identification:
                validation_result['errors'].append(f'Missing identification field: {field}')
                validation_result['valid'] = False
        
        return validation_result

# Export functions for external use
def get_mock_response(response_type: str, key: str) -> Optional[Dict]:
    """Get a specific mock response by type and key"""
    response_maps = {
        'vision': MOCK_VISION_RESPONSES,
        'drug_info': MOCK_DRUG_INFO_RESPONSES,
        'error': MOCK_ERROR_RESPONSES
    }
    
    response_map = response_maps.get(response_type)
    return response_map.get(key) if response_map else None

def get_all_mock_responses() -> Dict:
    """Get all mock responses organized by type"""
    return {
        'vision_responses': MOCK_VISION_RESPONSES,
        'drug_info_responses': MOCK_DRUG_INFO_RESPONSES,
        'error_responses': MOCK_ERROR_RESPONSES
    }

def export_mock_responses(filename: str = 'mock_responses.json') -> str:
    """Export all mock responses to JSON file"""
    all_responses = get_all_mock_responses()
    with open(filename, 'w') as f:
        json.dump(all_responses, f, indent=2)
    return filename