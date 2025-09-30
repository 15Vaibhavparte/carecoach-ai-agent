"""
Test utilities for medication image identification testing.
Provides helper functions for test execution, validation, and data generation.
"""

import json
import time
import random
import hashlib
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from .mock_responses import (
    MOCK_VISION_RESPONSES, 
    MOCK_DRUG_INFO_RESPONSES, 
    MOCK_ERROR_RESPONSES,
    MockResponseGenerator,
    ResponseValidator
)
from .fixtures import fixtures, BASE64_TEST_IMAGES, EXPECTED_RESULTS

class TestExecutor:
    """Utility class for executing and managing test cases"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
        
    def run_test_case(self, test_case: Dict, handler_function: Callable) -> Dict:
        """Execute a single test case and return results"""
        test_start = time.time()
        
        try:
            # Execute the test
            result = handler_function(test_case['input'])
            
            # Validate result
            validation = self._validate_test_result(result, test_case['expected'])
            
            test_result = {
                'test_name': test_case.get('name', 'unnamed_test'),
                'success': validation['valid'],
                'execution_time': time.time() - test_start,
                'result': result,
                'validation': validation,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            test_result = {
                'test_name': test_case.get('name', 'unnamed_test'),
                'success': False,
                'execution_time': time.time() - test_start,
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }
        
        self.results.append(test_result)
        return test_result
    
    def run_test_suite(self, test_cases: List[Dict], handler_function: Callable) -> Dict:
        """Execute a complete test suite"""
        self.start_time = time.time()
        self.results = []
        
        for test_case in test_cases:
            self.run_test_case(test_case, handler_function)
        
        self.end_time = time.time()
        
        return self.get_test_summary()
    
    def get_test_summary(self) -> Dict:
        """Get summary of test execution results"""
        if not self.results:
            return {'error': 'No test results available'}
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - successful_tests
        
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        avg_execution_time = sum(r['execution_time'] for r in self.results) / total_tests
        
        return {
            'summary': {
                'total_tests': total_tests,
                'successful': successful_tests,
                'failed': failed_tests,
                'success_rate': successful_tests / total_tests,
                'total_execution_time': total_time,
                'average_test_time': avg_execution_time
            },
            'results': self.results,
            'failed_tests': [r for r in self.results if not r['success']],
            'execution_metadata': {
                'start_time': self.start_time,
                'end_time': self.end_time,
                'test_environment': 'mock'
            }
        }
    
    def _validate_test_result(self, result: Dict, expected: Dict) -> Dict:
        """Validate test result against expected outcome"""
        validation = {'valid': True, 'errors': [], 'warnings': []}
        
        # Check if test should succeed or fail
        should_succeed = expected.get('success', True)
        actually_succeeded = result.get('success', False)
        
        if should_succeed != actually_succeeded:
            validation['errors'].append(
                f"Expected success={should_succeed}, got success={actually_succeeded}"
            )
            validation['valid'] = False
        
        # Validate specific fields if test should succeed
        if should_succeed and actually_succeeded:
            self._validate_success_fields(result, expected, validation)
        elif not should_succeed:
            self._validate_error_fields(result, expected, validation)
        
        return validation
    
    def _validate_success_fields(self, result: Dict, expected: Dict, validation: Dict):
        """Validate fields for successful responses"""
        # Check medication name
        if 'medication_name' in expected:
            expected_name = expected['medication_name'].lower()
            actual_name = result.get('identification', {}).get('medication_name', '').lower()
            if expected_name not in actual_name and actual_name not in expected_name:
                validation['warnings'].append(
                    f"Medication name mismatch: expected '{expected_name}', got '{actual_name}'"
                )
        
        # Check confidence range
        confidence = result.get('identification', {}).get('confidence', 0)
        if not (0 <= confidence <= 1):
            validation['errors'].append(f"Confidence {confidence} outside valid range [0, 1]")
            validation['valid'] = False
        
        # Check for drug info if expected
        if expected.get('include_drug_info', True):
            if 'drug_info' not in result:
                validation['warnings'].append("Missing drug information in response")
    
    def _validate_error_fields(self, result: Dict, expected: Dict, validation: Dict):
        """Validate fields for error responses"""
        if 'error_message' not in result:
            validation['errors'].append("Missing error_message in error response")
            validation['valid'] = False
        
        expected_error_type = expected.get('error_type')
        actual_error_type = result.get('error_type')
        if expected_error_type and actual_error_type != expected_error_type:
            validation['warnings'].append(
                f"Error type mismatch: expected '{expected_error_type}', got '{actual_error_type}'"
            )

class MockManager:
    """Manages mock responses and patches for testing"""
    
    def __init__(self):
        self.active_patches = []
        self.response_history = []
    
    def setup_vision_model_mock(self, response_mapping: Dict[str, str] = None):
        """Set up mock for vision model API calls"""
        if response_mapping is None:
            response_mapping = {
                'advil_clear': 'advil_clear',
                'tylenol_clear': 'tylenol_clear',
                'blurry_medication': 'blurry_medication'
            }
        
        def mock_vision_call(*args, **kwargs):
            # Determine which response to return based on input
            image_data = kwargs.get('image_data', '')
            
            # Simple heuristic to determine response type
            image_hash = hashlib.md5(image_data.encode()).hexdigest()[:8]
            response_key = response_mapping.get(image_hash, 'advil_clear')
            
            response = MOCK_VISION_RESPONSES.get(response_key, MOCK_VISION_RESPONSES['advil_clear'])
            self.response_history.append({
                'type': 'vision_model',
                'input_hash': image_hash,
                'response_key': response_key,
                'timestamp': datetime.now().isoformat()
            })
            
            return response
        
        # This would be patched in actual tests
        return mock_vision_call
    
    def setup_drug_info_mock(self, response_mapping: Dict[str, str] = None):
        """Set up mock for DrugInfoTool calls"""
        if response_mapping is None:
            response_mapping = {
                'advil': 'advil',
                'tylenol': 'tylenol',
                'ibuprofen': 'ibuprofen'
            }
        
        def mock_drug_info_call(*args, **kwargs):
            # Extract medication name from call
            medication_name = kwargs.get('medication_name', '').lower()
            
            response_key = response_mapping.get(medication_name, 'medication_not_found')
            response = MOCK_DRUG_INFO_RESPONSES.get(response_key, MOCK_DRUG_INFO_RESPONSES['medication_not_found'])
            
            self.response_history.append({
                'type': 'drug_info',
                'medication_name': medication_name,
                'response_key': response_key,
                'timestamp': datetime.now().isoformat()
            })
            
            return response
        
        return mock_drug_info_call
    
    def setup_error_scenario_mock(self, error_type: str):
        """Set up mock to simulate specific error scenarios"""
        def mock_error_call(*args, **kwargs):
            if error_type == 'timeout':
                time.sleep(0.1)  # Simulate delay
                raise TimeoutError("Request timed out")
            elif error_type == 'api_error':
                raise Exception("API service unavailable")
            elif error_type == 'rate_limit':
                return MOCK_DRUG_INFO_RESPONSES['rate_limit_error']
            else:
                return MOCK_ERROR_RESPONSES.get(error_type, MOCK_ERROR_RESPONSES['vision_api_error'])
        
        return mock_error_call
    
    def get_response_history(self) -> List[Dict]:
        """Get history of mock responses"""
        return self.response_history
    
    def clear_history(self):
        """Clear response history"""
        self.response_history = []

class PerformanceTestRunner:
    """Specialized test runner for performance testing"""
    
    def __init__(self):
        self.metrics = []
    
    def run_concurrent_test(self, test_function: Callable, test_data: List[Dict], 
                          max_concurrent: int = 5) -> Dict:
        """Run concurrent tests to measure performance under load"""
        import threading
        import queue
        
        results_queue = queue.Queue()
        start_time = time.time()
        
        def worker(test_case):
            thread_start = time.time()
            try:
                result = test_function(test_case)
                execution_time = time.time() - thread_start
                results_queue.put({
                    'success': True,
                    'execution_time': execution_time,
                    'result': result,
                    'test_case': test_case.get('name', 'unnamed')
                })
            except Exception as e:
                execution_time = time.time() - thread_start
                results_queue.put({
                    'success': False,
                    'execution_time': execution_time,
                    'error': str(e),
                    'test_case': test_case.get('name', 'unnamed')
                })
        
        # Create and start threads
        threads = []
        for i in range(0, len(test_data), max_concurrent):
            batch = test_data[i:i + max_concurrent]
            batch_threads = []
            
            for test_case in batch:
                thread = threading.Thread(target=worker, args=(test_case,))
                thread.start()
                batch_threads.append(thread)
            
            # Wait for batch to complete
            for thread in batch_threads:
                thread.join()
            
            threads.extend(batch_threads)
        
        total_time = time.time() - start_time
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Calculate metrics
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        execution_times = [r['execution_time'] for r in results]
        
        performance_metrics = {
            'total_tests': len(results),
            'successful_tests': len(successful_results),
            'failed_tests': len(failed_results),
            'total_execution_time': total_time,
            'average_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'min_execution_time': min(execution_times) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0,
            'throughput': len(results) / total_time if total_time > 0 else 0,
            'concurrent_limit': max_concurrent
        }
        
        return {
            'metrics': performance_metrics,
            'results': results,
            'failed_tests': failed_results
        }
    
    def run_load_test(self, test_function: Callable, duration_seconds: int = 60,
                     requests_per_second: int = 2) -> Dict:
        """Run load test for specified duration"""
        start_time = time.time()
        end_time = start_time + duration_seconds
        results = []
        
        request_interval = 1.0 / requests_per_second
        
        while time.time() < end_time:
            request_start = time.time()
            
            # Use a random test case
            test_case = {
                'name': f'load_test_{len(results)}',
                'input': {
                    'image_data': random.choice(list(BASE64_TEST_IMAGES.values())),
                    'prompt': 'Identify medication'
                }
            }
            
            try:
                result = test_function(test_case['input'])
                execution_time = time.time() - request_start
                
                results.append({
                    'success': True,
                    'execution_time': execution_time,
                    'timestamp': time.time(),
                    'result': result
                })
            except Exception as e:
                execution_time = time.time() - request_start
                results.append({
                    'success': False,
                    'execution_time': execution_time,
                    'timestamp': time.time(),
                    'error': str(e)
                })
            
            # Wait for next request interval
            elapsed = time.time() - request_start
            if elapsed < request_interval:
                time.sleep(request_interval - elapsed)
        
        # Calculate load test metrics
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r['success'])
        failed_requests = total_requests - successful_requests
        
        execution_times = [r['execution_time'] for r in results]
        
        load_metrics = {
            'duration_seconds': duration_seconds,
            'target_rps': requests_per_second,
            'actual_rps': total_requests / duration_seconds,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
            'average_response_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'min_response_time': min(execution_times) if execution_times else 0,
            'max_response_time': max(execution_times) if execution_times else 0
        }
        
        return {
            'metrics': load_metrics,
            'results': results
        }

class TestDataGenerator:
    """Generates various types of test data for comprehensive testing"""
    
    @staticmethod
    def generate_edge_case_data() -> List[Dict]:
        """Generate edge case test data"""
        edge_cases = []
        
        # Empty/null data cases
        edge_cases.extend([
            {
                'name': 'empty_image_data',
                'input': {'image_data': '', 'prompt': 'Identify medication'},
                'expected': {'success': False, 'error_type': 'invalid_input'}
            },
            {
                'name': 'null_image_data',
                'input': {'image_data': None, 'prompt': 'Identify medication'},
                'expected': {'success': False, 'error_type': 'invalid_input'}
            },
            {
                'name': 'missing_prompt',
                'input': {'image_data': BASE64_TEST_IMAGES['advil_clear']},
                'expected': {'success': False, 'error_type': 'missing_prompt'}
            }
        ])
        
        # Invalid format cases
        edge_cases.extend([
            {
                'name': 'invalid_base64',
                'input': {'image_data': 'invalid_base64_string!@#', 'prompt': 'Identify medication'},
                'expected': {'success': False, 'error_type': 'invalid_format'}
            },
            {
                'name': 'non_image_base64',
                'input': {'image_data': 'VGhpcyBpcyBub3QgYW4gaW1hZ2U=', 'prompt': 'Identify medication'},
                'expected': {'success': False, 'error_type': 'invalid_format'}
            }
        ])
        
        return edge_cases
    
    @staticmethod
    def generate_boundary_test_data() -> List[Dict]:
        """Generate boundary condition test data"""
        boundary_cases = []
        
        # Confidence boundary cases
        confidence_levels = [0.0, 0.1, 0.49, 0.5, 0.51, 0.8, 0.9, 1.0]
        
        for confidence in confidence_levels:
            boundary_cases.append({
                'name': f'confidence_boundary_{confidence}',
                'input': {'image_data': BASE64_TEST_IMAGES['advil_clear'], 'prompt': 'Identify medication'},
                'expected': {
                    'success': confidence >= 0.5,
                    'confidence': confidence,
                    'medication_name': 'Advil' if confidence >= 0.5 else None
                },
                'mock_confidence': confidence
            })
        
        return boundary_cases
    
    @staticmethod
    def generate_stress_test_data(count: int = 100) -> List[Dict]:
        """Generate large dataset for stress testing"""
        medications = ['Advil', 'Tylenol', 'Aspirin', 'Ibuprofen', 'Acetaminophen', 'Motrin', 'Aleve']
        dosages = ['200mg', '325mg', '500mg', '400mg', '650mg', '220mg']
        
        stress_data = []
        for i in range(count):
            medication = random.choice(medications)
            dosage = random.choice(dosages)
            confidence = random.uniform(0.3, 0.95)
            
            stress_data.append({
                'name': f'stress_test_{i+1}',
                'input': {
                    'image_data': random.choice(list(BASE64_TEST_IMAGES.values())),
                    'prompt': 'Identify medication'
                },
                'expected': {
                    'success': confidence > 0.5,
                    'medication_name': medication if confidence > 0.5 else None,
                    'dosage': dosage if confidence > 0.5 else None,
                    'confidence': confidence
                },
                'mock_response': MockResponseGenerator.generate_combined_response(
                    medication, confidence, dosage
                )
            })
        
        return stress_data
    
    @staticmethod
    def generate_regression_test_data() -> List[Dict]:
        """Generate regression test data based on known good cases"""
        regression_cases = []
        
        # Known good cases that should always work
        known_good = [
            ('advil_clear', 'Advil', '200mg', 0.95),
            ('tylenol_clear', 'Tylenol', '500mg', 0.92),
            ('ibuprofen_generic', 'Ibuprofen', '400mg', 0.88)
        ]
        
        for image_key, medication, dosage, confidence in known_good:
            regression_cases.append({
                'name': f'regression_{image_key}',
                'input': {
                    'image_data': BASE64_TEST_IMAGES.get(image_key, BASE64_TEST_IMAGES['advil_clear']),
                    'prompt': 'Identify medication'
                },
                'expected': {
                    'success': True,
                    'medication_name': medication,
                    'dosage': dosage,
                    'confidence': confidence
                },
                'regression_baseline': True
            })
        
        return regression_cases

# Utility functions for test execution
def create_test_environment() -> Dict:
    """Create a complete test environment with all utilities"""
    return {
        'executor': TestExecutor(),
        'mock_manager': MockManager(),
        'performance_runner': PerformanceTestRunner(),
        'data_generator': TestDataGenerator(),
        'validator': ResponseValidator()
    }

def run_comprehensive_test_suite(handler_function: Callable) -> Dict:
    """Run a comprehensive test suite covering all scenarios"""
    env = create_test_environment()
    
    # Generate all test data
    test_data = []
    test_data.extend(env['data_generator'].generate_edge_case_data())
    test_data.extend(env['data_generator'].generate_boundary_test_data())
    test_data.extend(env['data_generator'].generate_regression_test_data())
    
    # Run tests
    results = env['executor'].run_test_suite(test_data, handler_function)
    
    # Add performance metrics
    performance_data = env['data_generator'].generate_stress_test_data(10)
    performance_results = env['performance_runner'].run_concurrent_test(
        handler_function, performance_data, max_concurrent=3
    )
    
    return {
        'functional_tests': results,
        'performance_tests': performance_results,
        'test_environment': 'comprehensive',
        'total_test_cases': len(test_data) + len(performance_data)
    }

def export_test_results(results: Dict, filename: str = 'test_results.json') -> str:
    """Export test results to JSON file"""
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    return filename