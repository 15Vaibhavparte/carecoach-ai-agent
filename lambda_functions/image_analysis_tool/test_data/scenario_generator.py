"""
Scenario-based test data generator for medication image identification.
Creates realistic test scenarios with expected outcomes and validation criteria.
"""

import json
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .mock_responses import MockResponseGenerator, MOCK_VISION_RESPONSES, MOCK_DRUG_INFO_RESPONSES
from .fixtures import BASE64_TEST_IMAGES, EXPECTED_RESULTS

class ScenarioGenerator:
    """Generates comprehensive test scenarios for different use cases"""
    
    def __init__(self):
        self.scenarios = {}
        self._initialize_base_scenarios()
    
    def _initialize_base_scenarios(self):
        """Initialize base scenario templates"""
        self.scenarios = {
            'happy_path': self._create_happy_path_scenarios(),
            'error_handling': self._create_error_scenarios(),
            'edge_cases': self._create_edge_case_scenarios(),
            'performance': self._create_performance_scenarios(),
            'integration': self._create_integration_scenarios(),
            'security': self._create_security_scenarios(),
            'user_experience': self._create_ux_scenarios()
        }
    
    def _create_happy_path_scenarios(self) -> List[Dict]:
        """Create successful identification scenarios"""
        return [
            {
                'scenario_id': 'hp_001',
                'name': 'Clear Brand Name Medication',
                'description': 'User uploads clear image of brand name medication',
                'user_story': 'As a user, I want to identify a clear brand name medication so I can get drug information',
                'test_steps': [
                    'User uploads clear image of Advil tablet',
                    'System processes image with vision model',
                    'System identifies medication with high confidence',
                    'System retrieves drug information',
                    'System returns combined response'
                ],
                'test_data': {
                    'input': {
                        'image_data': BASE64_TEST_IMAGES.get('advil_clear', ''),
                        'prompt': 'Identify the medication name and dosage in this image'
                    },
                    'expected_vision_response': MOCK_VISION_RESPONSES['advil_clear'],
                    'expected_drug_info': MOCK_DRUG_INFO_RESPONSES['advil'],
                    'expected_final_response': {
                        'success': True,
                        'identification': {
                            'medication_name': 'Advil',
                            'dosage': '200mg',
                            'confidence': 0.95,
                            'image_quality': 'good'
                        },
                        'drug_info': {
                            'brand_name': 'Advil',
                            'generic_name': 'Ibuprofen',
                            'purpose': 'Pain reliever/fever reducer (NSAID)'
                        }
                    }
                },
                'validation_criteria': {
                    'min_confidence': 0.8,
                    'required_fields': ['medication_name', 'dosage', 'confidence', 'drug_info'],
                    'max_processing_time': 5.0,
                    'should_succeed': True
                }
            },
            {
                'scenario_id': 'hp_002',
                'name': 'Generic Medication Identification',
                'description': 'User uploads image of generic medication',
                'user_story': 'As a user, I want to identify generic medications so I can get the same drug information',
                'test_steps': [
                    'User uploads image of generic ibuprofen',
                    'System processes with vision model',
                    'System identifies generic name',
                    'System retrieves drug information',
                    'System returns response with generic information'
                ],
                'test_data': {
                    'input': {
                        'image_data': BASE64_TEST_IMAGES.get('ibuprofen_generic', ''),
                        'prompt': 'Identify the medication name and dosage in this image'
                    },
                    'expected_vision_response': MOCK_VISION_RESPONSES['ibuprofen_generic'],
                    'expected_drug_info': MOCK_DRUG_INFO_RESPONSES['ibuprofen'],
                    'expected_final_response': {
                        'success': True,
                        'identification': {
                            'medication_name': 'Ibuprofen',
                            'dosage': '400mg',
                            'confidence': 0.88,
                            'image_quality': 'good'
                        }
                    }
                },
                'validation_criteria': {
                    'min_confidence': 0.7,
                    'required_fields': ['medication_name', 'confidence'],
                    'max_processing_time': 5.0,
                    'should_succeed': True
                }
            },
            {
                'scenario_id': 'hp_003',
                'name': 'Multiple Format Support',
                'description': 'System handles different image formats correctly',
                'user_story': 'As a user, I want to upload images in different formats so I have flexibility',
                'test_steps': [
                    'User uploads JPEG image',
                    'System processes successfully',
                    'User uploads PNG image',
                    'System processes successfully',
                    'Results are consistent across formats'
                ],
                'test_data': {
                    'formats_to_test': ['jpeg', 'png', 'webp'],
                    'base_medication': 'Tylenol',
                    'expected_consistency': True
                },
                'validation_criteria': {
                    'format_support': ['jpeg', 'png', 'webp'],
                    'consistent_results': True,
                    'max_variance': 0.1
                }
            }
        ]
    
    def _create_error_scenarios(self) -> List[Dict]:
        """Create error handling scenarios"""
        return [
            {
                'scenario_id': 'err_001',
                'name': 'Poor Image Quality',
                'description': 'System handles blurry or poor quality images gracefully',
                'user_story': 'As a user, I want helpful feedback when my image is too blurry to identify',
                'test_steps': [
                    'User uploads blurry medication image',
                    'System attempts vision analysis',
                    'System detects low confidence',
                    'System returns error with helpful suggestions'
                ],
                'test_data': {
                    'input': {
                        'image_data': BASE64_TEST_IMAGES.get('blurry_medication', ''),
                        'prompt': 'Identify the medication name and dosage in this image'
                    },
                    'expected_vision_response': MOCK_VISION_RESPONSES['blurry_medication'],
                    'expected_final_response': {
                        'success': False,
                        'error_type': 'low_confidence',
                        'error_message': 'Unable to identify medication with sufficient confidence.',
                        'suggestions': [
                            'Retake photo with better lighting',
                            'Ensure medication text is clearly visible',
                            'Try a different angle'
                        ]
                    }
                },
                'validation_criteria': {
                    'should_fail': True,
                    'error_type': 'low_confidence',
                    'has_suggestions': True,
                    'max_confidence': 0.5
                }
            },
            {
                'scenario_id': 'err_002',
                'name': 'No Medication Detected',
                'description': 'System handles images with no medication present',
                'user_story': 'As a user, I want clear feedback when no medication is detected in my image',
                'test_steps': [
                    'User uploads image without medication',
                    'System processes with vision model',
                    'System detects no medication',
                    'System returns appropriate error message'
                ],
                'test_data': {
                    'input': {
                        'image_data': BASE64_TEST_IMAGES.get('no_medication', ''),
                        'prompt': 'Identify the medication name and dosage in this image'
                    },
                    'expected_vision_response': MOCK_VISION_RESPONSES['no_medication'],
                    'expected_final_response': {
                        'success': False,
                        'error_type': 'no_medication_detected',
                        'error_message': 'No medication detected in the image.',
                        'suggestions': [
                            'Ensure medication is clearly visible in the frame',
                            'Retake the photo'
                        ]
                    }
                },
                'validation_criteria': {
                    'should_fail': True,
                    'error_type': 'no_medication_detected',
                    'has_suggestions': True
                }
            },
            {
                'scenario_id': 'err_003',
                'name': 'Invalid Image Format',
                'description': 'System handles unsupported image formats',
                'user_story': 'As a user, I want clear guidance when I upload an unsupported file format',
                'test_steps': [
                    'User uploads unsupported file format',
                    'System validates file format',
                    'System rejects with clear error message',
                    'System suggests supported formats'
                ],
                'test_data': {
                    'input': {
                        'image_data': 'invalid_format_data',
                        'prompt': 'Identify medication'
                    },
                    'expected_final_response': {
                        'success': False,
                        'error_type': 'invalid_format',
                        'error_message': 'Unsupported image format. Please use JPEG, PNG, or WebP.',
                        'suggestions': [
                            'Convert image to supported format',
                            'Check file extension'
                        ]
                    }
                },
                'validation_criteria': {
                    'should_fail': True,
                    'error_type': 'invalid_format',
                    'has_format_suggestions': True
                }
            },
            {
                'scenario_id': 'err_004',
                'name': 'DrugInfo Service Unavailable',
                'description': 'System handles DrugInfoTool service failures',
                'user_story': 'As a user, I want to still get identification results even if drug info is unavailable',
                'test_steps': [
                    'User uploads valid medication image',
                    'System identifies medication successfully',
                    'DrugInfoTool service fails',
                    'System returns identification with service error note'
                ],
                'test_data': {
                    'input': {
                        'image_data': BASE64_TEST_IMAGES.get('advil_clear', ''),
                        'prompt': 'Identify medication'
                    },
                    'mock_drug_info_error': True,
                    'expected_final_response': {
                        'success': True,
                        'identification': {
                            'medication_name': 'Advil',
                            'confidence': 0.95
                        },
                        'drug_info_error': 'Drug information service temporarily unavailable',
                        'suggestions': [
                            'Try again later for detailed drug information',
                            'Consult healthcare provider'
                        ]
                    }
                },
                'validation_criteria': {
                    'should_succeed_partially': True,
                    'has_identification': True,
                    'has_drug_info_error': True
                }
            }
        ]
    
    def _create_edge_case_scenarios(self) -> List[Dict]:
        """Create edge case scenarios"""
        return [
            {
                'scenario_id': 'edge_001',
                'name': 'Multiple Medications in Image',
                'description': 'System handles images with multiple medications',
                'user_story': 'As a user, I want guidance when multiple medications are in one image',
                'test_steps': [
                    'User uploads image with multiple medications',
                    'System detects multiple items',
                    'System identifies primary medication',
                    'System suggests photographing items separately'
                ],
                'test_data': {
                    'input': {
                        'image_data': BASE64_TEST_IMAGES.get('multiple_medications', ''),
                        'prompt': 'Identify medication'
                    },
                    'expected_vision_response': MOCK_VISION_RESPONSES['multiple_medications'],
                    'expected_final_response': {
                        'success': True,
                        'identification': {
                            'medication_name': 'Aspirin',
                            'confidence': 0.78,
                            'multiple_items_detected': True
                        },
                        'warnings': [
                            'Multiple medications detected',
                            'Recommend photographing each medication separately'
                        ]
                    }
                },
                'validation_criteria': {
                    'should_succeed': True,
                    'has_warnings': True,
                    'confidence_reflects_complexity': True
                }
            },
            {
                'scenario_id': 'edge_002',
                'name': 'Partial Text Visibility',
                'description': 'System handles partially visible medication text',
                'user_story': 'As a user, I want reasonable results even when text is partially obscured',
                'test_steps': [
                    'User uploads image with partial text',
                    'System attempts identification',
                    'System provides best guess with appropriate confidence',
                    'System suggests better image if confidence is low'
                ],
                'test_data': {
                    'input': {
                        'image_data': BASE64_TEST_IMAGES.get('partial_text', ''),
                        'prompt': 'Identify medication'
                    },
                    'expected_vision_response': MOCK_VISION_RESPONSES['partial_text'],
                    'expected_final_response': {
                        'success': True,
                        'identification': {
                            'medication_name': 'Metformin',
                            'confidence': 0.65,
                            'partial_identification': True
                        },
                        'warnings': [
                            'Partial text visibility detected',
                            'Consider retaking photo for better accuracy'
                        ]
                    }
                },
                'validation_criteria': {
                    'should_succeed': True,
                    'confidence_range': [0.5, 0.8],
                    'has_warnings': True
                }
            },
            {
                'scenario_id': 'edge_003',
                'name': 'Maximum File Size',
                'description': 'System handles images at maximum allowed size',
                'user_story': 'As a user, I want to upload high-resolution images up to the size limit',
                'test_steps': [
                    'User uploads image at maximum size limit',
                    'System accepts and processes image',
                    'System completes processing within time limits',
                    'System returns successful identification'
                ],
                'test_data': {
                    'input': {
                        'image_data': 'large_image_base64_data',  # Would be generated
                        'file_size': 10485760,  # 10MB
                        'prompt': 'Identify medication'
                    },
                    'expected_final_response': {
                        'success': True,
                        'processing_notes': ['Large file processed successfully']
                    }
                },
                'validation_criteria': {
                    'max_processing_time': 10.0,
                    'memory_efficient': True,
                    'should_succeed': True
                }
            }
        ]
    
    def _create_performance_scenarios(self) -> List[Dict]:
        """Create performance testing scenarios"""
        return [
            {
                'scenario_id': 'perf_001',
                'name': 'Concurrent Request Handling',
                'description': 'System handles multiple concurrent requests efficiently',
                'user_story': 'As a system, I want to handle multiple users simultaneously without degradation',
                'test_steps': [
                    'Send multiple concurrent requests',
                    'Monitor response times',
                    'Verify all requests complete successfully',
                    'Check for resource leaks'
                ],
                'test_data': {
                    'concurrent_requests': 10,
                    'request_interval': 0.1,
                    'test_duration': 30,
                    'expected_success_rate': 0.95
                },
                'validation_criteria': {
                    'max_avg_response_time': 5.0,
                    'min_success_rate': 0.95,
                    'no_memory_leaks': True,
                    'consistent_performance': True
                }
            },
            {
                'scenario_id': 'perf_002',
                'name': 'Load Testing',
                'description': 'System maintains performance under sustained load',
                'user_story': 'As a system, I want to maintain performance during peak usage',
                'test_steps': [
                    'Generate sustained load for extended period',
                    'Monitor system metrics',
                    'Verify response times remain acceptable',
                    'Check error rates stay low'
                ],
                'test_data': {
                    'requests_per_second': 5,
                    'test_duration': 300,  # 5 minutes
                    'ramp_up_time': 60
                },
                'validation_criteria': {
                    'max_response_time': 8.0,
                    'max_error_rate': 0.05,
                    'stable_performance': True
                }
            }
        ]
    
    def _create_integration_scenarios(self) -> List[Dict]:
        """Create integration testing scenarios"""
        return [
            {
                'scenario_id': 'int_001',
                'name': 'End-to-End Workflow',
                'description': 'Complete workflow from image upload to final response',
                'user_story': 'As a user, I want a seamless experience from upload to results',
                'test_steps': [
                    'User uploads image via web interface',
                    'Image is processed by Lambda function',
                    'Vision model analyzes image',
                    'DrugInfoTool retrieves drug data',
                    'Combined response is returned to user'
                ],
                'test_data': {
                    'full_workflow': True,
                    'include_ui_validation': True
                },
                'validation_criteria': {
                    'end_to_end_success': True,
                    'data_consistency': True,
                    'proper_error_propagation': True
                }
            },
            {
                'scenario_id': 'int_002',
                'name': 'DrugInfoTool Integration',
                'description': 'Proper integration with existing DrugInfoTool service',
                'user_story': 'As a system, I want seamless integration with existing drug information services',
                'test_steps': [
                    'Identify medication from image',
                    'Format request for DrugInfoTool',
                    'Call DrugInfoTool with proper parameters',
                    'Parse and integrate response',
                    'Return combined data'
                ],
                'test_data': {
                    'test_medications': ['Advil', 'Tylenol', 'Aspirin'],
                    'verify_data_mapping': True
                },
                'validation_criteria': {
                    'proper_api_calls': True,
                    'data_transformation': True,
                    'error_handling': True
                }
            }
        ]
    
    def _create_security_scenarios(self) -> List[Dict]:
        """Create security testing scenarios"""
        return [
            {
                'scenario_id': 'sec_001',
                'name': 'Input Validation',
                'description': 'System properly validates and sanitizes all inputs',
                'user_story': 'As a system, I want to protect against malicious inputs',
                'test_steps': [
                    'Send malformed base64 data',
                    'Send oversized payloads',
                    'Send injection attempts',
                    'Verify proper rejection and logging'
                ],
                'test_data': {
                    'malicious_inputs': [
                        'javascript:alert(1)',
                        '<script>alert(1)</script>',
                        '../../etc/passwd',
                        'x' * 100000  # Very large input
                    ]
                },
                'validation_criteria': {
                    'input_sanitization': True,
                    'no_code_execution': True,
                    'proper_error_handling': True,
                    'security_logging': True
                }
            },
            {
                'scenario_id': 'sec_002',
                'name': 'Data Privacy',
                'description': 'System protects user data and maintains privacy',
                'user_story': 'As a user, I want my medical images to be handled securely',
                'test_steps': [
                    'Upload medical image',
                    'Verify no persistent storage',
                    'Check logging for sensitive data',
                    'Verify secure transmission'
                ],
                'test_data': {
                    'privacy_checks': [
                        'no_image_storage',
                        'minimal_logging',
                        'secure_transmission',
                        'data_encryption'
                    ]
                },
                'validation_criteria': {
                    'no_data_persistence': True,
                    'secure_logging': True,
                    'encryption_in_transit': True,
                    'hipaa_compliance': True
                }
            }
        ]
    
    def _create_ux_scenarios(self) -> List[Dict]:
        """Create user experience scenarios"""
        return [
            {
                'scenario_id': 'ux_001',
                'name': 'User-Friendly Error Messages',
                'description': 'System provides helpful, non-technical error messages',
                'user_story': 'As a user, I want clear guidance when something goes wrong',
                'test_steps': [
                    'Trigger various error conditions',
                    'Verify error messages are user-friendly',
                    'Check that suggestions are actionable',
                    'Ensure no technical jargon'
                ],
                'test_data': {
                    'error_scenarios': [
                        'blurry_image',
                        'no_medication',
                        'invalid_format',
                        'service_unavailable'
                    ]
                },
                'validation_criteria': {
                    'clear_language': True,
                    'actionable_suggestions': True,
                    'no_technical_jargon': True,
                    'helpful_guidance': True
                }
            },
            {
                'scenario_id': 'ux_002',
                'name': 'Response Time Expectations',
                'description': 'System provides feedback during processing',
                'user_story': 'As a user, I want to know the system is working on my request',
                'test_steps': [
                    'Upload image',
                    'Monitor processing indicators',
                    'Verify reasonable response times',
                    'Check for timeout handling'
                ],
                'test_data': {
                    'response_time_targets': {
                        'acknowledgment': 0.5,
                        'processing_start': 1.0,
                        'final_response': 5.0
                    }
                },
                'validation_criteria': {
                    'quick_acknowledgment': True,
                    'progress_indicators': True,
                    'reasonable_timeouts': True,
                    'user_feedback': True
                }
            }
        ]
    
    def get_scenario(self, category: str, scenario_id: str = None) -> Optional[Dict]:
        """Get a specific scenario or all scenarios in a category"""
        if category not in self.scenarios:
            return None
        
        if scenario_id:
            scenarios = self.scenarios[category]
            return next((s for s in scenarios if s['scenario_id'] == scenario_id), None)
        
        return self.scenarios[category]
    
    def get_all_scenarios(self) -> Dict[str, List[Dict]]:
        """Get all scenarios organized by category"""
        return self.scenarios
    
    def generate_test_suite_from_scenarios(self, categories: List[str] = None) -> List[Dict]:
        """Generate executable test cases from scenarios"""
        if categories is None:
            categories = list(self.scenarios.keys())
        
        test_cases = []
        
        for category in categories:
            if category in self.scenarios:
                for scenario in self.scenarios[category]:
                    test_case = self._convert_scenario_to_test_case(scenario)
                    test_cases.append(test_case)
        
        return test_cases
    
    def _convert_scenario_to_test_case(self, scenario: Dict) -> Dict:
        """Convert a scenario to an executable test case"""
        return {
            'name': scenario['scenario_id'],
            'description': scenario['description'],
            'input': scenario['test_data'].get('input', {}),
            'expected': scenario['test_data'].get('expected_final_response', {}),
            'validation_criteria': scenario['validation_criteria'],
            'scenario_metadata': {
                'category': scenario.get('category', 'unknown'),
                'user_story': scenario.get('user_story', ''),
                'test_steps': scenario.get('test_steps', [])
            }
        }
    
    def export_scenarios(self, filename: str = 'test_scenarios.json') -> str:
        """Export all scenarios to JSON file"""
        export_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_scenarios': sum(len(scenarios) for scenarios in self.scenarios.values()),
                'categories': list(self.scenarios.keys())
            },
            'scenarios': self.scenarios
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filename

# Global instance for easy access
scenario_generator = ScenarioGenerator()

# Convenience functions
def get_happy_path_scenarios() -> List[Dict]:
    """Get all happy path scenarios"""
    return scenario_generator.get_scenario('happy_path')

def get_error_scenarios() -> List[Dict]:
    """Get all error handling scenarios"""
    return scenario_generator.get_scenario('error_handling')

def get_performance_scenarios() -> List[Dict]:
    """Get all performance testing scenarios"""
    return scenario_generator.get_scenario('performance')

def generate_comprehensive_test_suite() -> List[Dict]:
    """Generate a comprehensive test suite covering all scenarios"""
    return scenario_generator.generate_test_suite_from_scenarios()