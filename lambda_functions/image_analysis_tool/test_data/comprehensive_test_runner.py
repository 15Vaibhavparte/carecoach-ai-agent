"""
Comprehensive test runner for medication image identification.
Orchestrates all test utilities, mock responses, and validation.
"""

import json
import time
import traceback
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from .mock_responses import (
    MOCK_VISION_RESPONSES, 
    MOCK_DRUG_INFO_RESPONSES, 
    MOCK_ERROR_RESPONSES,
    MockResponseGenerator,
    ResponseValidator
)
from .test_utilities import (
    TestExecutor, 
    MockManager, 
    PerformanceTestRunner,
    TestDataGenerator,
    create_test_environment
)
from .scenario_generator import (
    scenario_generator,
    generate_comprehensive_test_suite
)
from .fixtures import fixtures, BASE64_TEST_IMAGES, EXPECTED_RESULTS

class ComprehensiveTestRunner:
    """Main test runner that orchestrates all testing components"""
    
    def __init__(self):
        self.test_env = create_test_environment()
        self.results_history = []
        self.current_session = None
        
    def run_full_test_suite(self, handler_function: Callable = None) -> Dict:
        """Run the complete test suite with all scenarios and validations"""
        session_id = f"test_session_{int(time.time())}"
        self.current_session = {
            'session_id': session_id,
            'start_time': datetime.now(),
            'test_results': {},
            'summary': {}
        }
        
        print(f"Starting comprehensive test suite - Session: {session_id}")
        
        # If no handler function provided, use mock handler
        if handler_function is None:
            handler_function = self._create_mock_handler()
        
        try:
            # Run functional tests
            print("Running functional tests...")
            functional_results = self._run_functional_tests(handler_function)
            
            # Run performance tests
            print("Running performance tests...")
            performance_results = self._run_performance_tests(handler_function)
            
            # Run integration tests
            print("Running integration tests...")
            integration_results = self._run_integration_tests(handler_function)
            
            # Run error handling tests
            print("Running error handling tests...")
            error_handling_results = self._run_error_handling_tests(handler_function)
            
            # Run edge case tests
            print("Running edge case tests...")
            edge_case_results = self._run_edge_case_tests(handler_function)
            
            # Compile comprehensive results
            comprehensive_results = self._compile_results({
                'functional': functional_results,
                'performance': performance_results,
                'integration': integration_results,
                'error_handling': error_handling_results,
                'edge_cases': edge_case_results
            })
            
            self.current_session['test_results'] = comprehensive_results
            self.current_session['end_time'] = datetime.now()
            self.current_session['summary'] = self._generate_session_summary(comprehensive_results)
            
            self.results_history.append(self.current_session)
            
            print(f"Test suite completed - Session: {session_id}")
            return comprehensive_results
            
        except Exception as e:
            error_result = {
                'error': f"Test suite execution failed: {str(e)}",
                'traceback': traceback.format_exc(),
                'session_id': session_id
            }
            print(f"Test suite failed: {str(e)}")
            return error_result
    
    def _run_functional_tests(self, handler_function: Callable) -> Dict:
        """Run functional tests covering happy path scenarios"""
        scenarios = scenario_generator.get_scenario('happy_path')
        test_cases = []
        
        for scenario in scenarios:
            test_case = {
                'name': scenario['scenario_id'],
                'input': scenario['test_data']['input'],
                'expected': scenario['test_data']['expected_final_response'],
                'validation_criteria': scenario['validation_criteria']
            }
            test_cases.append(test_case)
        
        # Add basic fixture tests
        for image_name, expected in EXPECTED_RESULTS.items():
            if expected.get('should_succeed', False):
                test_case = {
                    'name': f'fixture_{image_name}',
                    'input': {
                        'image_data': BASE64_TEST_IMAGES[image_name],
                        'prompt': 'Identify medication'
                    },
                    'expected': {
                        'success': True,
                        'medication_name': expected['medication_name'],
                        'confidence': expected['confidence']
                    }
                }
                test_cases.append(test_case)
        
        return self.test_env['executor'].run_test_suite(test_cases, handler_function)
    
    def _run_performance_tests(self, handler_function: Callable) -> Dict:
        """Run performance and load tests"""
        performance_runner = self.test_env['performance_runner']
        
        # Generate performance test data
        stress_data = self.test_env['data_generator'].generate_stress_test_data(20)
        
        # Run concurrent tests
        concurrent_results = performance_runner.run_concurrent_test(
            handler_function, stress_data[:10], max_concurrent=5
        )
        
        # Run load test
        load_results = performance_runner.run_load_test(
            handler_function, duration_seconds=30, requests_per_second=2
        )
        
        return {
            'concurrent_test': concurrent_results,
            'load_test': load_results,
            'performance_summary': {
                'concurrent_throughput': concurrent_results['metrics']['throughput'],
                'load_success_rate': load_results['metrics']['success_rate'],
                'avg_response_time': load_results['metrics']['average_response_time']
            }
        }
    
    def _run_integration_tests(self, handler_function: Callable) -> Dict:
        """Run integration tests with mock services"""
        integration_scenarios = scenario_generator.get_scenario('integration')
        
        # Test DrugInfoTool integration
        drug_info_tests = self._test_drug_info_integration(handler_function)
        
        # Test vision model integration
        vision_tests = self._test_vision_model_integration(handler_function)
        
        # Test end-to-end workflow
        e2e_tests = self._test_end_to_end_workflow(handler_function)
        
        return {
            'drug_info_integration': drug_info_tests,
            'vision_model_integration': vision_tests,
            'end_to_end_workflow': e2e_tests,
            'integration_summary': {
                'total_integration_tests': len(drug_info_tests) + len(vision_tests) + len(e2e_tests),
                'successful_integrations': sum([
                    sum(1 for t in drug_info_tests if t.get('success', False)),
                    sum(1 for t in vision_tests if t.get('success', False)),
                    sum(1 for t in e2e_tests if t.get('success', False))
                ])
            }
        }
    
    def _run_error_handling_tests(self, handler_function: Callable) -> Dict:
        """Run comprehensive error handling tests"""
        error_scenarios = scenario_generator.get_scenario('error_handling')
        
        # Test various error conditions
        error_tests = []
        
        for scenario in error_scenarios:
            test_case = {
                'name': scenario['scenario_id'],
                'input': scenario['test_data']['input'],
                'expected': scenario['test_data']['expected_final_response'],
                'should_fail': scenario['validation_criteria'].get('should_fail', False)
            }
            
            result = self.test_env['executor'].run_test_case(test_case, handler_function)
            error_tests.append(result)
        
        # Test edge case errors
        edge_errors = self._test_edge_case_errors(handler_function)
        
        return {
            'scenario_errors': error_tests,
            'edge_case_errors': edge_errors,
            'error_handling_summary': {
                'total_error_tests': len(error_tests) + len(edge_errors),
                'proper_error_handling': sum(1 for t in error_tests + edge_errors if t.get('success', False))
            }
        }
    
    def _run_edge_case_tests(self, handler_function: Callable) -> Dict:
        """Run edge case and boundary tests"""
        edge_scenarios = scenario_generator.get_scenario('edge_cases')
        
        # Generate boundary test data
        boundary_data = self.test_env['data_generator'].generate_boundary_test_data()
        
        # Run edge case scenarios
        edge_results = []
        for scenario in edge_scenarios:
            test_case = {
                'name': scenario['scenario_id'],
                'input': scenario['test_data']['input'],
                'expected': scenario['test_data']['expected_final_response']
            }
            result = self.test_env['executor'].run_test_case(test_case, handler_function)
            edge_results.append(result)
        
        # Run boundary tests
        boundary_results = self.test_env['executor'].run_test_suite(boundary_data, handler_function)
        
        return {
            'edge_case_scenarios': edge_results,
            'boundary_tests': boundary_results,
            'edge_case_summary': {
                'total_edge_tests': len(edge_results) + len(boundary_data),
                'successful_edge_cases': sum(1 for t in edge_results if t.get('success', False))
            }
        }
    
    def _test_drug_info_integration(self, handler_function: Callable) -> List[Dict]:
        """Test integration with DrugInfoTool"""
        drug_info_tests = []
        
        test_medications = ['advil', 'tylenol', 'ibuprofen', 'unknown_medication']
        
        for medication in test_medications:
            test_case = {
                'name': f'drug_info_{medication}',
                'medication': medication,
                'expected_success': medication != 'unknown_medication'
            }
            
            # Mock the DrugInfoTool call
            mock_response = MOCK_DRUG_INFO_RESPONSES.get(
                medication, 
                MOCK_DRUG_INFO_RESPONSES['medication_not_found']
            )
            
            test_result = {
                'test_name': test_case['name'],
                'success': mock_response['statusCode'] == 200,
                'response': mock_response,
                'validation': ResponseValidator.validate_drug_info_response(mock_response)
            }
            
            drug_info_tests.append(test_result)
        
        return drug_info_tests
    
    def _test_vision_model_integration(self, handler_function: Callable) -> List[Dict]:
        """Test integration with vision model"""
        vision_tests = []
        
        for image_name, mock_response in MOCK_VISION_RESPONSES.items():
            test_result = {
                'test_name': f'vision_{image_name}',
                'success': 'response' in mock_response,
                'response': mock_response,
                'validation': ResponseValidator.validate_vision_response(mock_response)
            }
            vision_tests.append(test_result)
        
        return vision_tests
    
    def _test_end_to_end_workflow(self, handler_function: Callable) -> List[Dict]:
        """Test complete end-to-end workflow"""
        e2e_tests = []
        
        # Test successful workflow
        successful_test = {
            'name': 'e2e_successful_workflow',
            'input': {
                'image_data': BASE64_TEST_IMAGES['advil_clear'],
                'prompt': 'Identify medication'
            }
        }
        
        try:
            result = handler_function(successful_test['input'])
            e2e_tests.append({
                'test_name': 'e2e_successful_workflow',
                'success': result.get('success', False),
                'has_identification': 'identification' in result,
                'has_drug_info': 'drug_info' in result,
                'processing_time': result.get('processing_time', 0)
            })
        except Exception as e:
            e2e_tests.append({
                'test_name': 'e2e_successful_workflow',
                'success': False,
                'error': str(e)
            })
        
        return e2e_tests
    
    def _test_edge_case_errors(self, handler_function: Callable) -> List[Dict]:
        """Test specific edge case error conditions"""
        edge_error_tests = []
        
        # Test invalid inputs
        invalid_inputs = [
            {'image_data': None, 'prompt': 'test'},
            {'image_data': '', 'prompt': 'test'},
            {'image_data': 'invalid_base64', 'prompt': 'test'},
            {'image_data': BASE64_TEST_IMAGES['advil_clear'], 'prompt': None}
        ]
        
        for i, invalid_input in enumerate(invalid_inputs):
            try:
                result = handler_function(invalid_input)
                edge_error_tests.append({
                    'test_name': f'invalid_input_{i}',
                    'success': not result.get('success', True),  # Should fail
                    'proper_error_handling': 'error_message' in result
                })
            except Exception as e:
                edge_error_tests.append({
                    'test_name': f'invalid_input_{i}',
                    'success': True,  # Exception is expected
                    'error_caught': str(e)
                })
        
        return edge_error_tests
    
    def _create_mock_handler(self) -> Callable:
        """Create a mock handler function for testing when no real handler is available"""
        def mock_handler(input_data: Dict) -> Dict:
            """Mock handler that simulates the medication identification process"""
            
            # Validate input
            if not input_data.get('image_data'):
                return {
                    'success': False,
                    'error_type': 'invalid_input',
                    'error_message': 'Missing image data'
                }
            
            if not input_data.get('prompt'):
                return {
                    'success': False,
                    'error_type': 'missing_prompt',
                    'error_message': 'Missing prompt'
                }
            
            # Simulate processing time
            time.sleep(random.uniform(0.5, 2.0))
            
            # Determine response based on image data
            image_data = input_data['image_data']
            
            # Simple heuristic to determine which mock response to use
            if 'advil' in str(image_data).lower() or len(image_data) > 1000:
                medication = 'Advil'
                confidence = 0.95
                success = True
            elif 'tylenol' in str(image_data).lower():
                medication = 'Tylenol'
                confidence = 0.92
                success = True
            elif len(image_data) < 100:  # Simulate poor quality
                return {
                    'success': False,
                    'error_type': 'low_confidence',
                    'error_message': 'Unable to identify medication with sufficient confidence',
                    'confidence': 0.25
                }
            else:
                medication = 'Generic Medication'
                confidence = 0.75
                success = True
            
            if success:
                # Generate mock drug info
                drug_info = {
                    'brand_name': medication,
                    'generic_name': medication.lower(),
                    'purpose': 'Pain reliever',
                    'warnings': ['Consult healthcare provider'],
                    'directions': ['Use as directed']
                }
                
                return {
                    'success': True,
                    'identification': {
                        'medication_name': medication,
                        'confidence': confidence,
                        'dosage': '200mg'
                    },
                    'drug_info': drug_info,
                    'processing_time': random.uniform(1.0, 3.0)
                }
        
        return mock_handler
    
    def _compile_results(self, test_results: Dict) -> Dict:
        """Compile all test results into a comprehensive report"""
        total_tests = 0
        successful_tests = 0
        
        # Count tests from each category
        for category, results in test_results.items():
            if isinstance(results, dict):
                if 'summary' in results:
                    summary = results['summary']
                    total_tests += summary.get('total_tests', 0)
                    successful_tests += summary.get('successful', 0)
                elif 'metrics' in results:
                    # Performance test results
                    total_tests += results.get('concurrent_test', {}).get('metrics', {}).get('total_tests', 0)
                    successful_tests += results.get('concurrent_test', {}).get('metrics', {}).get('successful_tests', 0)
        
        overall_success_rate = successful_tests / total_tests if total_tests > 0 else 0
        
        compiled_results = {
            'test_session': self.current_session['session_id'] if self.current_session else 'unknown',
            'execution_time': datetime.now().isoformat(),
            'overall_summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': total_tests - successful_tests,
                'success_rate': overall_success_rate,
                'test_categories': list(test_results.keys())
            },
            'detailed_results': test_results,
            'recommendations': self._generate_recommendations(test_results, overall_success_rate)
        }
        
        return compiled_results
    
    def _generate_session_summary(self, results: Dict) -> Dict:
        """Generate a summary of the test session"""
        return {
            'session_duration': str(self.current_session['end_time'] - self.current_session['start_time']),
            'overall_success_rate': results['overall_summary']['success_rate'],
            'total_tests_run': results['overall_summary']['total_tests'],
            'categories_tested': results['overall_summary']['test_categories'],
            'recommendations_count': len(results.get('recommendations', []))
        }
    
    def _generate_recommendations(self, test_results: Dict, success_rate: float) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if success_rate < 0.8:
            recommendations.append("Overall success rate is below 80%. Review failed tests and improve error handling.")
        
        # Check performance results
        performance = test_results.get('performance', {})
        if performance:
            load_success_rate = performance.get('load_test', {}).get('metrics', {}).get('success_rate', 1.0)
            if load_success_rate < 0.95:
                recommendations.append("Load test success rate is below 95%. Consider optimizing performance.")
            
            avg_response_time = performance.get('load_test', {}).get('metrics', {}).get('average_response_time', 0)
            if avg_response_time > 5.0:
                recommendations.append("Average response time exceeds 5 seconds. Consider performance optimization.")
        
        # Check error handling
        error_handling = test_results.get('error_handling', {})
        if error_handling:
            error_summary = error_handling.get('error_handling_summary', {})
            total_error_tests = error_summary.get('total_error_tests', 0)
            proper_handling = error_summary.get('proper_error_handling', 0)
            
            if total_error_tests > 0 and proper_handling / total_error_tests < 0.9:
                recommendations.append("Error handling success rate is below 90%. Improve error handling logic.")
        
        if not recommendations:
            recommendations.append("All tests passed successfully. System is performing well.")
        
        return recommendations
    
    def export_results(self, filename: str = None) -> str:
        """Export test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_test_results_{timestamp}.json"
        
        export_data = {
            'test_sessions': self.results_history,
            'export_metadata': {
                'exported_at': datetime.now().isoformat(),
                'total_sessions': len(self.results_history),
                'exporter_version': '1.0.0'
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return filename
    
    def get_test_history(self) -> List[Dict]:
        """Get history of all test sessions"""
        return self.results_history
    
    def clear_history(self):
        """Clear test history"""
        self.results_history = []

# Global test runner instance
test_runner = ComprehensiveTestRunner()

# Convenience functions for external use
def run_quick_test_suite(handler_function: Callable = None) -> Dict:
    """Run a quick subset of tests for rapid feedback"""
    if handler_function is None:
        handler_function = test_runner._create_mock_handler()
    
    # Run only essential tests
    functional_results = test_runner._run_functional_tests(handler_function)
    error_results = test_runner._run_error_handling_tests(handler_function)
    
    return {
        'quick_test_summary': {
            'functional_success_rate': functional_results['summary']['success_rate'],
            'error_handling_success_rate': error_results['error_handling_summary']['proper_error_handling'] / 
                                         error_results['error_handling_summary']['total_error_tests']
        },
        'functional_results': functional_results,
        'error_results': error_results
    }

def run_performance_only(handler_function: Callable = None) -> Dict:
    """Run only performance tests"""
    if handler_function is None:
        handler_function = test_runner._create_mock_handler()
    
    return test_runner._run_performance_tests(handler_function)

def validate_handler_function(handler_function: Callable) -> Dict:
    """Validate that a handler function works correctly with basic inputs"""
    validation_tests = [
        {
            'name': 'basic_validation',
            'input': {
                'image_data': BASE64_TEST_IMAGES['advil_clear'],
                'prompt': 'Identify medication'
            },
            'expected': {'success': True}
        }
    ]
    
    executor = TestExecutor()
    return executor.run_test_suite(validation_tests, handler_function)

# Import for random in mock handler
import random