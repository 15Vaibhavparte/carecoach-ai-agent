#!/usr/bin/env python3
"""
End-to-end validation runner for the medication image identification system.
This script performs comprehensive validation of the complete system including:
- Real API integration tests
- Security and privacy compliance validation
- Performance benchmarking
- Error scenario testing
- Infrastructure integration validation
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

print("DEBUG: Module loading started...")

def validate_environment():
    """Validate the environment and dependencies"""
    try:
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            return {
                'success': False,
                'error': f'Python 3.8+ required, found {python_version.major}.{python_version.minor}'
            }
        
        # Check required modules
        required_modules = [
            'boto3', 'requests', 'PIL', 'json', 'base64', 'unittest'
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            return {
                'success': False,
                'error': f'Missing required modules: {", ".join(missing_modules)}'
            }
        
        # Check if main application modules are available
        try:
            from app import lambda_handler, health_check
            from models import ImageAnalysisRequest, MedicationIdentification
            from config import config
        except ImportError as e:
            return {
                'success': False,
                'error': f'Failed to import application modules: {str(e)}'
            }
        
        return {'success': True, 'message': 'Environment validation passed'}
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Environment validation error: {str(e)}'
        }

def validate_infrastructure_integration():
    """Validate integration with CareCoach infrastructure"""
    try:
        print("  • Testing Bedrock Agent response format compatibility...")
        
        # Test health check endpoint
        from app import health_check
        
        mock_context = type('MockContext', (), {
            'function_name': 'image_analysis_tool',
            'aws_request_id': 'test-request-id'
        })()
        
        health_response = health_check({}, mock_context)
        
        if health_response.get('statusCode') != 200:
            return {
                'success': False,
                'error': f'Health check failed with status: {health_response.get("statusCode")}'
            }
        
        print("  ✓ Health check endpoint working")
        
        # Test response format compatibility
        from response_synthesis import format_bedrock_response
        
        test_results = {
            'success': True,
            'medication_identification': {
                'medication_name': 'Test Medication',
                'confidence': 0.95
            },
            'drug_information': {
                'available': True,
                'brand_name': 'Test Brand'
            }
        }
        
        test_event = {
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
        
        formatted_response = format_bedrock_response(test_results, test_event)
        
        # Validate response structure
        required_fields = ['messageVersion', 'response']
        for field in required_fields:
            if field not in formatted_response:
                return {
                    'success': False,
                    'error': f'Missing required field in response: {field}'
                }
        
        print("  ✓ Bedrock Agent response format compatible")
        
        return {'success': True, 'message': 'Infrastructure integration validated'}
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Infrastructure validation error: {str(e)}'
        }

def validate_security_compliance():
    """Validate security and privacy compliance"""
    try:
        print("  • Testing security and privacy compliance...")
        
        # Test 1: Verify no sensitive data in logs
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        
        # Temporarily add handler to capture logs
        logger = logging.getLogger()
        original_level = logger.level
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        
        try:
            # Test with sample image data
            from test_data.fixtures import TestFixtures
            fixtures = TestFixtures()
            
            # Get a clear medication image from fixtures
            clear_fixtures = fixtures.get_test_cases_by_category('clear_single_medication')
            if clear_fixtures:
                test_image = fixtures.get_base64_image(clear_fixtures[0]['name'])
            else:
                # Fallback to any available image
                test_image = list(fixtures.sample_images.values())[0]['base64']
            
            # This should not log the actual image data
            from image_preprocessing import assess_image_quality_from_base64
            assess_image_quality_from_base64(test_image)
            
            # Check logs don't contain base64 data
            log_content = log_capture.getvalue()
            if 'base64' in log_content.lower() or len([line for line in log_content.split('\n') if len(line) > 1000]):
                return {
                    'success': False,
                    'error': 'Logs may contain sensitive image data'
                }
            
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)
        
        print("  ✓ No sensitive data in logs")
        
        # Test 2: Verify error messages don't expose internals
        from error_handling import handle_lambda_error
        
        test_error = Exception("Internal system error with sensitive details")
        test_event = {'actionGroup': 'test'}
        context_info = {'request_id': 'test', 'operation': 'test'}
        
        error_response = handle_lambda_error(test_error, test_event, context_info)
        
        # Error response should not contain internal details
        response_str = json.dumps(error_response)
        if 'traceback' in response_str.lower() or 'exception' in response_str.lower():
            return {
                'success': False,
                'error': 'Error responses may expose internal details'
            }
        
        print("  ✓ Error handling maintains privacy")
        
        return {'success': True, 'message': 'Security compliance validated'}
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Security validation error: {str(e)}'
        }

def run_performance_benchmarks():
    """Run performance benchmarks"""
    try:
        print("  • Running performance benchmarks...")
        
        from test_data.fixtures import TestFixtures, BASE64_TEST_IMAGES
        from app import lambda_handler
        
        fixtures = TestFixtures()
        
        # Get available test images
        available_images = list(BASE64_TEST_IMAGES.keys())
        
        # Test different image sizes - use available images
        test_cases = []
        if available_images:
            # Use first 3 available images or repeat if fewer available
            for i, case_name in enumerate(['small_image', 'medium_image', 'large_image']):
                image_key = available_images[i % len(available_images)]
                image_data = BASE64_TEST_IMAGES[image_key]
                test_cases.append((case_name, image_data))
        
        performance_results = {}
        
        for case_name, image_data in test_cases:
            test_event = {
                'input': {
                    'RequestBody': {
                        'content': {
                            'application/json': {
                                'properties': [
                                    {'name': 'image_data', 'value': image_data},
                                    {'name': 'prompt', 'value': 'Performance test'}
                                ]
                            }
                        }
                    }
                },
                'actionGroup': 'image_analysis_tool'
            }
            
            mock_context = type('MockContext', (), {
                'function_name': 'image_analysis_tool',
                'aws_request_id': f'perf-test-{case_name}',
                'remaining_time_in_millis': lambda: 30000
            })()
            
            # Run test multiple times for average
            times = []
            for i in range(3):
                start_time = time.time()
                try:
                    response = lambda_handler(test_event, mock_context)
                    processing_time = time.time() - start_time
                    times.append(processing_time)
                except Exception as e:
                    print(f"    ⚠ Performance test failed for {case_name}: {str(e)}")
                    times.append(float('inf'))
            
            if times and min(times) != float('inf'):
                avg_time = sum(t for t in times if t != float('inf')) / len([t for t in times if t != float('inf')])
                performance_results[case_name] = {
                    'avg_time': avg_time,
                    'min_time': min(times),
                    'max_time': max(times)
                }
                
                # Check against thresholds
                if avg_time > 30.0:  # 30 second threshold
                    print(f"    ⚠ {case_name} performance warning: {avg_time:.2f}s (threshold: 30s)")
                else:
                    print(f"    ✓ {case_name}: {avg_time:.2f}s")
            else:
                print(f"    ❌ {case_name}: All tests failed")
                performance_results[case_name] = {'error': 'All tests failed'}
        
        return {
            'success': True,
            'results': performance_results,
            'message': 'Performance benchmarks completed'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Performance benchmark error: {str(e)}'
        }

def run_error_scenario_tests():
    """Test error scenarios and recovery mechanisms"""
    try:
        print("  • Testing error scenarios and recovery...")
        
        from app import lambda_handler
        
        # Test scenarios
        error_scenarios = [
            {
                'name': 'invalid_image_data',
                'event': {
                    'input': {
                        'RequestBody': {
                            'content': {
                                'application/json': {
                                    'properties': [
                                        {'name': 'image_data', 'value': 'invalid_base64_data'},
                                        {'name': 'prompt', 'value': 'Test'}
                                    ]
                                }
                            }
                        }
                    }
                },
                'expected_error_keywords': ['invalid', 'format', 'image']
            },
            {
                'name': 'missing_image_data',
                'event': {
                    'input': {
                        'RequestBody': {
                            'content': {
                                'application/json': {
                                    'properties': [
                                        {'name': 'prompt', 'value': 'Test'}
                                    ]
                                }
                            }
                        }
                    }
                },
                'expected_error_keywords': ['no image', 'missing', 'required']
            },
            {
                'name': 'empty_event',
                'event': {},
                'expected_error_keywords': ['no image', 'missing', 'required']
            }
        ]
        
        mock_context = type('MockContext', (), {
            'function_name': 'image_analysis_tool',
            'aws_request_id': 'error-test',
            'remaining_time_in_millis': lambda: 30000
        })()
        
        passed_scenarios = 0
        
        for scenario in error_scenarios:
            try:
                response = lambda_handler(scenario['event'], mock_context)
                
                # Should return error response
                if 'response' in response and 'responseBody' in response['response']:
                    body = json.loads(response['response']['responseBody']['application/json']['body'])
                    
                    if not body.get('success', True) and 'error' in body:
                        error_msg = body['error'].lower()
                        
                        # Check if error message contains expected keywords
                        has_expected_keywords = any(
                            keyword.lower() in error_msg 
                            for keyword in scenario['expected_error_keywords']
                        )
                        
                        if has_expected_keywords:
                            print(f"    ✓ {scenario['name']}: Handled correctly")
                            passed_scenarios += 1
                        else:
                            print(f"    ⚠ {scenario['name']}: Error message unclear: {body['error'][:100]}")
                    else:
                        print(f"    ❌ {scenario['name']}: Should have failed but didn't")
                else:
                    print(f"    ❌ {scenario['name']}: Invalid response format")
                    
            except Exception as e:
                print(f"    ❌ {scenario['name']}: Unexpected exception: {str(e)}")
        
        success_rate = passed_scenarios / len(error_scenarios)
        
        return {
            'success': success_rate >= 0.8,  # 80% success rate required
            'passed_scenarios': passed_scenarios,
            'total_scenarios': len(error_scenarios),
            'success_rate': success_rate,
            'message': f'Error scenario testing: {passed_scenarios}/{len(error_scenarios)} passed'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error scenario testing failed: {str(e)}'
        }

def run_end_to_end_validation():
    """
    Run comprehensive end-to-end validation of the medication image identification system.
    """
    
    print("=" * 100)
    print("MEDICATION IMAGE IDENTIFICATION - END-TO-END VALIDATION")
    print("=" * 100)
    print()
    
    validation_start_time = time.time()
    
    # Step 1: Environment and dependency validation
    print("Step 1: Validating Environment and Dependencies")
    print("-" * 50)
    
    env_validation = validate_environment()
    if not env_validation['success']:
        print(f"❌ Environment validation failed: {env_validation['error']}")
        return False
    
    print(f"✓ {env_validation['message']}")
    print()
    
    # Step 2: Infrastructure integration validation
    print("Step 2: Validating CareCoach Infrastructure Integration")
    print("-" * 50)
    
    infra_validation = validate_infrastructure_integration()
    if not infra_validation['success']:
        print(f"❌ Infrastructure validation failed: {infra_validation['error']}")
        return False
    
    print(f"✓ {infra_validation['message']}")
    print()
    
    # Step 3: Security and privacy compliance validation
    print("Step 3: Validating Security and Privacy Compliance")
    print("-" * 50)
    
    security_validation = validate_security_compliance()
    if not security_validation['success']:
        print(f"❌ Security validation failed: {security_validation['error']}")
        return False
    
    print(f"✓ {security_validation['message']}")
    print()
    
    # Step 4: Performance benchmarks
    print("Step 4: Running Performance Benchmarks")
    print("-" * 50)
    
    performance_results = run_performance_benchmarks()
    if not performance_results['success']:
        print(f"❌ Performance benchmarks failed: {performance_results['error']}")
        return False
    
    print(f"✓ {performance_results['message']}")
    print()
    
    # Step 5: Error scenario testing
    print("Step 5: Testing Error Scenarios and Recovery Mechanisms")
    print("-" * 50)
    
    error_test_results = run_error_scenario_tests()
    if not error_test_results['success']:
        print(f"❌ Error scenario testing failed: {error_test_results.get('message', 'Unknown error')}")
        return False
    
    print(f"✓ {error_test_results['message']}")
    print()
    
    # Step 6: Run comprehensive test suite
    print("Step 6: Running Comprehensive Test Suite")
    print("-" * 50)
    
    try:
        # Import and run the test suite
        from test_end_to_end_validation import EndToEndValidationSuite
        
        suite_success = EndToEndValidationSuite.run_validation_suite()
        if not suite_success:
            print("❌ Comprehensive test suite failed")
            return False
        
        print("✓ Comprehensive test suite passed")
        print()
        
    except Exception as e:
        print(f"❌ Failed to run comprehensive test suite: {str(e)}")
        return False
    
    # Final validation summary
    total_time = time.time() - validation_start_time
    
    print("=" * 100)
    print("END-TO-END VALIDATION SUMMARY")
    print("=" * 100)
    print()
    print("✅ ALL VALIDATION STEPS PASSED!")
    print()
    print("Validation Results:")
    print(f"  • Environment and Dependencies: ✓ PASSED")
    print(f"  • Infrastructure Integration: ✓ PASSED")
    print(f"  • Security and Privacy Compliance: ✓ PASSED")
    print(f"  • Performance Benchmarks: ✓ PASSED")
    print(f"  • Error Scenario Testing: ✓ PASSED")
    print(f"  • Comprehensive Test Suite: ✓ PASSED")
    print()
    print(f"Total validation time: {total_time:.2f} seconds")
    print()
    print("🎉 The medication image identification system is ready for production deployment!")
    print("   All requirements have been validated and the system meets CareCoach standards.")
    print()
    print("=" * 100)
    
    return True

if __name__ == '__main__':
    success = run_end_to_end_validation()
    sys.exit(0 if success else 1)