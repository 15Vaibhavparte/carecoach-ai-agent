"""
End-to-end validation tests for the medication image identification system.
This module performs comprehensive testing of the complete workflow with real images and API calls.

Tests cover:
1. Complete workflow with real images and API calls
2. Integration with existing CareCoach infrastructure
3. Security and privacy compliance validation
4. Error scenarios and recovery mechanisms
"""

import unittest
import json
import time
import base64
import os
import sys
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from app import lambda_handler, health_check
from models import ImageAnalysisRequest, MedicationIdentification
from config import config
from test_data.fixtures import TestFixtures, BASE64_TEST_IMAGES
from test_data.mock_responses import MockResponseGenerator
from test_data.test_utilities import TestExecutor, MockManager

class EndToEndValidationTests(unittest.TestCase):
    """
    Comprehensive end-to-end validation tests for the medication image identification system.
    """
    
    def setUp(self):
        """Set up test fixtures and utilities"""
        self.test_fixtures = TestFixtures()
        self.mock_generator = MockResponseGenerator()
        self.test_executor = TestExecutor()
        self.mock_manager = MockManager()
        
        # Get available test images
        self.available_images = list(BASE64_TEST_IMAGES.keys())
        if not self.available_images:
            raise ValueError("No test images available in fixtures")
        
        # Test configuration
        self.test_config = {
            'timeout_seconds': 30,
            'max_retries': 3,
            'performance_thresholds': {
                'total_processing_time': 15.0,  # seconds
                'vision_analysis_time': 10.0,
                'drug_info_lookup_time': 5.0
            }
        }
    
    def test_complete_workflow_with_clear_medication_image(self):
        """
        Test the complete workflow with a clear medication image.
        Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.5
        """
        print("\n=== Testing Complete Workflow with Clear Medication Image ===")
        
        # Prepare test event with clear medication image
        # Use first available image as test case
        test_image = BASE64_TEST_IMAGES[self.available_images[0]]
        test_event = self._create_test_event(
            image_data=test_image,
            prompt="Identify the medication name and dosage in this image"
        )
        
        start_time = time.time()
        
        # Execute the complete workflow
        response = lambda_handler(test_event, self._create_mock_context())
        
        processing_time = time.time() - start_time
        
        # Validate response structure
        self.assertIsInstance(response, dict)
        self.assertIn('messageVersion', response)
        self.assertIn('response', response)
        self.assertEqual(response['messageVersion'], '1.0')
        
        # Extract response body
        response_body = json.loads(
            response['response']['responseBody']['application/json']['body']
        )
        
        # Validate successful identification
        self.assertTrue(response_body.get('success', False))
        self.assertIn('medication_identification', response_body)
        self.assertIn('drug_information', response_body)
        
        # Validate medication identification
        med_id = response_body['medication_identification']
        self.assertIsNotNone(med_id.get('medication_name'))
        self.assertGreater(med_id.get('confidence', 0), 0.7)  # High confidence expected
        
        # Validate drug information integration
        drug_info = response_body['drug_information']
        self.assertTrue(drug_info.get('available', False))
        self.assertIn('brand_name', drug_info)
        self.assertIn('purpose', drug_info)
        
        # Validate performance
        self.assertLess(processing_time, self.test_config['performance_thresholds']['total_processing_time'])
        
        # Validate response includes required metadata
        self.assertIn('processing_time', response_body)
        self.assertIn('request_id', response_body)
        
        print(f"✓ Complete workflow successful in {processing_time:.2f}s")
        print(f"✓ Medication identified: {med_id.get('medication_name')} (confidence: {med_id.get('confidence', 0):.2f})")
        print(f"✓ Drug information retrieved: {drug_info.get('brand_name', 'N/A')}")
    
    def test_workflow_with_blurry_medication_image(self):
        """
        Test workflow with blurry/poor quality image.
        Requirements: 2.4, 6.1, 6.2
        """
        print("\n=== Testing Workflow with Blurry Medication Image ===")
        
        # Use second available image or first if only one available
        test_image = BASE64_TEST_IMAGES[self.available_images[min(1, len(self.available_images)-1)]]
        test_event = self._create_test_event(
            image_data=test_image,
            prompt="Identify the medication name and dosage in this image"
        )
        
        response = lambda_handler(test_event, self._create_mock_context())
        response_body = json.loads(
            response['response']['responseBody']['application/json']['body']
        )
        
        # Should handle gracefully with appropriate messaging
        if response_body.get('success', False):
            # If successful, confidence should be lower
            med_id = response_body['medication_identification']
            confidence = med_id.get('confidence', 0)
            self.assertLess(confidence, 0.8)  # Lower confidence expected
        else:
            # If unsuccessful, should provide helpful error message
            self.assertIn('error', response_body)
            error_msg = response_body['error'].lower()
            self.assertTrue(
                any(keyword in error_msg for keyword in ['quality', 'clear', 'blur', 'retake']),
                f"Error message should mention image quality: {response_body['error']}"
            )
        
        print("✓ Blurry image handled appropriately")
    
    def test_workflow_with_no_medication_image(self):
        """
        Test workflow with image containing no medication.
        Requirements: 6.1
        """
        print("\n=== Testing Workflow with No Medication Image ===")
        
        # Use third available image or cycle back to first
        test_image = BASE64_TEST_IMAGES[self.available_images[min(2, len(self.available_images)-1)]]
        test_event = self._create_test_event(
            image_data=test_image,
            prompt="Identify the medication name and dosage in this image"
        )
        
        response = lambda_handler(test_event, self._create_mock_context())
        response_body = json.loads(
            response['response']['responseBody']['application/json']['body']
        )
        
        # Should detect no medication and provide appropriate guidance
        if response_body.get('success', False):
            med_id = response_body['medication_identification']
            self.assertIsNone(med_id.get('medication_name'))
        else:
            self.assertIn('error', response_body)
            error_msg = response_body['error'].lower()
            self.assertTrue(
                any(keyword in error_msg for keyword in ['no medication', 'not found', 'detected']),
                f"Error message should indicate no medication found: {response_body['error']}"
            )
        
        print("✓ No medication image handled appropriately")
    
    def test_workflow_with_multiple_medications(self):
        """
        Test workflow with image containing multiple medications.
        Requirements: 2.5
        """
        print("\n=== Testing Workflow with Multiple Medications ===")
        
        # Use fourth available image or cycle back
        test_image = BASE64_TEST_IMAGES[self.available_images[min(3, len(self.available_images)-1)]]
        test_event = self._create_test_event(
            image_data=test_image,
            prompt="Identify the primary medication name and dosage in this image"
        )
        
        response = lambda_handler(test_event, self._create_mock_context())
        response_body = json.loads(
            response['response']['responseBody']['application/json']['body']
        )
        
        # Should identify the primary/most prominent medication
        if response_body.get('success', False):
            med_id = response_body['medication_identification']
            self.assertIsNotNone(med_id.get('medication_name'))
            # May include information about multiple medications detected
            
        print("✓ Multiple medications image handled appropriately")
    
    def test_invalid_image_formats_handling(self):
        """
        Test handling of invalid image formats.
        Requirements: 1.1, 1.3, 6.3
        """
        print("\n=== Testing Invalid Image Formats Handling ===")
        
        invalid_formats = [
            ("invalid_base64", "not_base64_data"),
            ("empty_data", ""),
            ("wrong_format", "data:text/plain;base64,SGVsbG8gV29ybGQ="),  # Text file
            ("corrupted_image", "data:image/jpeg;base64,corrupted_data_here")
        ]
        
        for format_name, image_data in invalid_formats:
            with self.subTest(format=format_name):
                test_event = self._create_test_event(
                    image_data=image_data,
                    prompt="Identify the medication"
                )
                
                response = lambda_handler(test_event, self._create_mock_context())
                response_body = json.loads(
                    response['response']['responseBody']['application/json']['body']
                )
                
                # Should fail gracefully with clear error message
                self.assertFalse(response_body.get('success', True))
                self.assertIn('error', response_body)
                
                print(f"✓ Invalid format '{format_name}' handled with error: {response_body['error'][:50]}...")
    
    def test_large_image_size_handling(self):
        """
        Test handling of images that exceed size limits.
        Requirements: 1.3, 6.3
        """
        print("\n=== Testing Large Image Size Handling ===")
        
        # Create oversized image data
        from test_data.fixtures import generate_oversized_image_base64
        oversized_image = generate_oversized_image_base64()
        
        test_event = self._create_test_event(
            image_data=oversized_image,
            prompt="Identify the medication"
        )
        
        response = lambda_handler(test_event, self._create_mock_context())
        response_body = json.loads(
            response['response']['responseBody']['application/json']['body']
        )
        
        # Should reject with size limit error
        self.assertFalse(response_body.get('success', True))
        self.assertIn('error', response_body)
        error_msg = response_body['error'].lower()
        self.assertTrue(
            any(keyword in error_msg for keyword in ['size', 'large', 'limit', 'exceed']),
            f"Error message should mention size limit: {response_body['error']}"
        )
        
        print("✓ Large image size handled with appropriate error")
    
    def test_drug_info_integration_failure_handling(self):
        """
        Test handling when DrugInfoTool integration fails.
        Requirements: 3.4, 6.3
        """
        print("\n=== Testing DrugInfo Integration Failure Handling ===")
        
        # Mock DrugInfoTool to fail
        with patch('drug_info_integration.get_drug_information') as mock_drug_info:
            mock_drug_info.return_value = {
                'success': False,
                'error': 'Drug information service unavailable',
                'drug_info': None
            }
            
            test_image = BASE64_TEST_IMAGES[self.available_images[0]]
            test_event = self._create_test_event(
                image_data=test_image,
                prompt="Identify the medication"
            )
            
            response = lambda_handler(test_event, self._create_mock_context())
            response_body = json.loads(
                response['response']['responseBody']['application/json']['body']
            )
            
            # Should still provide medication identification even if drug info fails
            if response_body.get('success', False):
                self.assertIn('medication_identification', response_body)
                drug_info = response_body.get('drug_information', {})
                self.assertFalse(drug_info.get('available', True))
            
        print("✓ DrugInfo integration failure handled gracefully")
    
    def test_vision_model_timeout_handling(self):
        """
        Test handling of vision model timeouts.
        Requirements: 6.4, 6.5
        """
        print("\n=== Testing Vision Model Timeout Handling ===")
        
        # Mock vision client to timeout
        with patch('vision_client.VisionModelClient.analyze_image') as mock_analyze:
            mock_analyze.side_effect = TimeoutError("Vision model request timed out")
            
            test_image = BASE64_TEST_IMAGES[self.available_images[0]]
            test_event = self._create_test_event(
                image_data=test_image,
                prompt="Identify the medication"
            )
            
            response = lambda_handler(test_event, self._create_mock_context())
            response_body = json.loads(
                response['response']['responseBody']['application/json']['body']
            )
            
            # Should handle timeout gracefully
            self.assertFalse(response_body.get('success', True))
            self.assertIn('error', response_body)
            error_msg = response_body['error'].lower()
            self.assertTrue(
                any(keyword in error_msg for keyword in ['timeout', 'time', 'retry']),
                f"Error message should mention timeout: {response_body['error']}"
            )
        
        print("✓ Vision model timeout handled appropriately")
    
    def test_concurrent_request_handling(self):
        """
        Test system behavior under concurrent requests.
        Requirements: 5.1, 5.2, 5.5
        """
        print("\n=== Testing Concurrent Request Handling ===")
        
        import threading
        import queue
        
        # Prepare multiple test events
        test_image = BASE64_TEST_IMAGES[self.available_images[0]]
        test_events = [
            self._create_test_event(
                image_data=test_image,
                prompt=f"Test request {i}"
            )
            for i in range(5)
        ]
        
        results_queue = queue.Queue()
        
        def process_request(event, request_id):
            try:
                start_time = time.time()
                response = lambda_handler(event, self._create_mock_context())
                processing_time = time.time() - start_time
                
                results_queue.put({
                    'request_id': request_id,
                    'success': True,
                    'response': response,
                    'processing_time': processing_time
                })
            except Exception as e:
                results_queue.put({
                    'request_id': request_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Start concurrent requests
        threads = []
        for i, event in enumerate(test_events):
            thread = threading.Thread(target=process_request, args=(event, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Validate all requests completed successfully
        self.assertEqual(len(results), len(test_events))
        successful_requests = [r for r in results if r['success']]
        self.assertEqual(len(successful_requests), len(test_events))
        
        # Validate performance under load
        avg_processing_time = sum(r['processing_time'] for r in successful_requests) / len(successful_requests)
        self.assertLess(avg_processing_time, self.test_config['performance_thresholds']['total_processing_time'] * 1.5)
        
        print(f"✓ {len(successful_requests)} concurrent requests processed successfully")
        print(f"✓ Average processing time: {avg_processing_time:.2f}s")
    
    def test_security_and_privacy_compliance(self):
        """
        Test security and privacy compliance measures.
        Requirements: 5.1, 5.2, 5.4, 5.5
        """
        print("\n=== Testing Security and Privacy Compliance ===")
        
        # Test 1: Verify no image data is logged
        with patch('monitoring.structured_logger') as mock_logger:
            test_image = BASE64_TEST_IMAGES[self.available_images[0]]
            test_event = self._create_test_event(
                image_data=test_image,
                prompt="Test security compliance"
            )
            
            lambda_handler(test_event, self._create_mock_context())
            
            # Check that no log calls contain actual image data (but metadata is OK)
            for call in mock_logger.info.call_args_list + mock_logger.debug.call_args_list:
                args, kwargs = call
                log_message = str(args) + str(kwargs)
                
                # Check for actual base64 image data (long strings)
                # We allow metadata like "has_image_data": true but not the actual data
                if 'base64' in log_message.lower():
                    # Look for long base64 strings that would indicate actual image data
                    import re
                    base64_patterns = re.findall(r'[A-Za-z0-9+/]{100,}', log_message)
                    if base64_patterns:
                        self.fail(f"Log message contains actual base64 image data: {base64_patterns[0][:50]}...")
                
                # Allow metadata about image_data but not the actual data
                if 'image_data' in log_message.lower():
                    # Check if this is just metadata (short references are OK)
                    if len(log_message) > 5000:  # Very long messages might contain actual data
                        self.fail(f"Log message is suspiciously long and contains image_data reference: {len(log_message)} chars")
        
        # Test 2: Verify response doesn't leak sensitive information
        test_image = BASE64_TEST_IMAGES[self.available_images[0]]
        test_event = self._create_test_event(
            image_data=test_image,
            prompt="Test privacy compliance"
        )
        
        response = lambda_handler(test_event, self._create_mock_context())
        response_str = json.dumps(response)
        
        # Response should not contain raw image data
        self.assertNotIn('base64', response_str.lower())
        self.assertNotIn('image_data', response_str.lower())
        
        # Test 3: Verify proper error handling doesn't expose internals
        test_event = self._create_test_event(
            image_data="invalid_data",
            prompt="Test error privacy"
        )
        
        response = lambda_handler(test_event, self._create_mock_context())
        response_body = json.loads(
            response['response']['responseBody']['application/json']['body']
        )
        
        if 'error' in response_body:
            error_msg = response_body['error']
            # Error should be user-friendly, not expose internal details
            self.assertNotIn('traceback', error_msg.lower())
            self.assertNotIn('exception', error_msg.lower())
            self.assertNotIn('stack', error_msg.lower())
        
        print("✓ Security and privacy compliance validated")
    
    def test_health_check_functionality(self):
        """
        Test the health check endpoint functionality.
        Requirements: 5.5
        """
        print("\n=== Testing Health Check Functionality ===")
        
        # Test health check
        health_response = health_check({}, self._create_mock_context())
        
        self.assertEqual(health_response['statusCode'], 200)
        
        body = json.loads(health_response['body'])
        self.assertEqual(body['status'], 'healthy')
        self.assertEqual(body['service'], 'image_analysis_tool')
        self.assertIn('timestamp', body)
        self.assertIn('version', body)
        
        print("✓ Health check functionality working correctly")
    
    def test_performance_benchmarks(self):
        """
        Test performance benchmarks for the complete system.
        Requirements: 5.4, 5.5
        """
        print("\n=== Testing Performance Benchmarks ===")
        
        # Test with different image sizes and complexities
        # Use available images, cycling through them
        test_cases = []
        case_names = ["small_clear", "medium_clear", "large_clear"]
        for i, case_name in enumerate(case_names):
            image_key = self.available_images[i % len(self.available_images)]
            test_cases.append((case_name, BASE64_TEST_IMAGES[image_key]))
        
        performance_results = {}
        
        for case_name, image_data in test_cases:
            test_event = self._create_test_event(
                image_data=image_data,
                prompt="Performance test"
            )
            
            # Run multiple iterations for average
            times = []
            for _ in range(3):
                start_time = time.time()
                response = lambda_handler(test_event, self._create_mock_context())
                processing_time = time.time() - start_time
                times.append(processing_time)
            
            avg_time = sum(times) / len(times)
            performance_results[case_name] = {
                'avg_time': avg_time,
                'min_time': min(times),
                'max_time': max(times)
            }
            
            # Validate against thresholds
            self.assertLess(avg_time, self.test_config['performance_thresholds']['total_processing_time'])
        
        # Print performance summary
        for case_name, results in performance_results.items():
            print(f"✓ {case_name}: avg={results['avg_time']:.2f}s, min={results['min_time']:.2f}s, max={results['max_time']:.2f}s")
    
    def test_integration_with_carecoach_infrastructure(self):
        """
        Test integration with existing CareCoach infrastructure patterns.
        Requirements: 5.1, 5.2, 5.3
        """
        print("\n=== Testing CareCoach Infrastructure Integration ===")
        
        # Test 1: Verify Bedrock Agent response format compatibility
        test_image = BASE64_TEST_IMAGES[self.available_images[0]]
        test_event = self._create_test_event(
            image_data=test_image,
            prompt="Test infrastructure integration"
        )
        
        response = lambda_handler(test_event, self._create_mock_context())
        
        # Validate Bedrock Agent response structure
        required_fields = ['messageVersion', 'response']
        for field in required_fields:
            self.assertIn(field, response)
        
        self.assertEqual(response['messageVersion'], '1.0')
        
        response_obj = response['response']
        required_response_fields = ['actionGroup', 'apiPath', 'httpMethod', 'httpStatusCode', 'responseBody']
        for field in required_response_fields:
            self.assertIn(field, response_obj)
        
        # Test 2: Verify consistent error handling patterns
        invalid_event = self._create_test_event(
            image_data="invalid",
            prompt="Test error patterns"
        )
        
        error_response = lambda_handler(invalid_event, self._create_mock_context())
        
        # Should maintain same response structure even for errors
        self.assertIn('messageVersion', error_response)
        self.assertIn('response', error_response)
        
        print("✓ CareCoach infrastructure integration validated")
    
    def _create_test_event(self, image_data: str, prompt: str) -> Dict[str, Any]:
        """Create a test Lambda event with the specified image data and prompt"""
        return {
            'input': {
                'RequestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {
                                    'name': 'image_data',
                                    'value': image_data
                                },
                                {
                                    'name': 'prompt',
                                    'value': prompt
                                }
                            ]
                        }
                    }
                }
            },
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
    
    def _create_mock_context(self):
        """Create a mock Lambda context object"""
        # Create a simple object instead of MagicMock to avoid JSON serialization issues
        context = type('MockContext', (), {
            'function_name': 'image_analysis_tool',
            'function_version': '1.0',
            'invoked_function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:image_analysis_tool',
            'memory_limit_in_mb': 512,
            'remaining_time_in_millis': lambda: 30000,
            'aws_request_id': 'test-request-id-12345'
        })()
        return context

class EndToEndValidationSuite:
    """
    Test suite runner for end-to-end validation tests.
    """
    
    @staticmethod
    def run_validation_suite():
        """Run the complete end-to-end validation suite"""
        
        print("=" * 80)
        print("END-TO-END VALIDATION SUITE FOR MEDICATION IMAGE IDENTIFICATION")
        print("=" * 80)
        print()
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(EndToEndValidationTests)
        
        # Run tests with detailed output
        runner = unittest.TextTestRunner(
            verbosity=2,
            buffer=True,
            stream=sys.stdout
        )
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # Print comprehensive summary
        print("\n" + "=" * 80)
        print("END-TO-END VALIDATION RESULTS")
        print("=" * 80)
        
        print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / max(result.testsRun, 1)) * 100:.1f}%")
        
        # Print detailed failure/error information
        if result.failures:
            print(f"\nFAILURES ({len(result.failures)}):")
            for test, traceback in result.failures:
                print(f"  - {test}")
                print(f"    {traceback.split('AssertionError:')[-1].strip()}")
        
        if result.errors:
            print(f"\nERRORS ({len(result.errors)}):")
            for test, traceback in result.errors:
                print(f"  - {test}")
                print(f"    {traceback.split('Exception:')[-1].strip()}")
        
        # Final validation status
        overall_success = len(result.failures) == 0 and len(result.errors) == 0
        
        print(f"\n{'='*80}")
        if overall_success:
            print("🎉 END-TO-END VALIDATION PASSED!")
            print("The medication image identification system is ready for production deployment.")
        else:
            print("❌ END-TO-END VALIDATION FAILED!")
            print("Please review and fix the issues above before deployment.")
        print(f"{'='*80}")
        
        return overall_success

if __name__ == '__main__':
    # Run the end-to-end validation suite
    success = EndToEndValidationSuite.run_validation_suite()
    sys.exit(0 if success else 1)