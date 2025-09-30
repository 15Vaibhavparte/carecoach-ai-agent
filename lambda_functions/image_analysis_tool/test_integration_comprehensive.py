"""
Comprehensive integration tests for the image analysis tool.
Tests end-to-end workflows, DrugInfoTool integration, performance, and load handling.
"""

import unittest
import json
import time
import base64
import io
import threading
import concurrent.futures
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

# Import all modules for integration testing
from app import lambda_handler, parse_request, validate_and_preprocess_image, analyze_image_with_vision_model
from drug_info_integration import get_drug_information, call_drug_info_tool
from vision_client import VisionModelClient, MedicationExtractor
from image_validation import ImageValidator
from image_preprocessing import ImagePreprocessor
from response_synthesis import combine_results, format_bedrock_response
from error_handling import ErrorHandler
from models import (
    VisionModelResponse, 
    MedicationIdentification, 
    ImageQuality,
    ImageValidationError,
    VisionModelError,
    DrugInfoError
)
from config import config

class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration tests with sample images"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_context = Mock()
        self.mock_context.aws_request_id = 'test-request-id'
        self.mock_context.function_name = 'image_analysis_tool'
        self.mock_context.remaining_time_in_millis = lambda: 30000
        
        # Create test images
        self.test_images = self._create_test_images()
    
    def _create_test_images(self):
        """Create various test images for different scenarios"""
        images = {}
        
        # Good quality image
        good_img = Image.new('RGB', (800, 600), color=(255, 255, 255))
        # Add some text-like patterns
        for i in range(0, 800, 50):
            for j in range(0, 600, 50):
                if (i + j) % 100 == 0:
                    for x in range(i, min(i+30, 800)):
                        for y in range(j, min(j+20, 600)):
                            good_img.putpixel((x, y), (0, 0, 0))
        
        buffer = io.BytesIO()
        good_img.save(buffer, format='JPEG', quality=95)
        images['good_quality'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Poor quality image (small and blurry)
        poor_img = Image.new('RGB', (100, 75), color=(128, 128, 128))
        buffer = io.BytesIO()
        poor_img.save(buffer, format='JPEG', quality=30)
        images['poor_quality'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Large image
        large_img = Image.new('RGB', (2000, 1500), color=(200, 200, 200))
        buffer = io.BytesIO()
        large_img.save(buffer, format='JPEG', quality=85)
        images['large_image'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # PNG with transparency
        png_img = Image.new('RGBA', (400, 300), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        png_img.save(buffer, format='PNG')
        images['png_transparent'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return images
    
    def _create_test_event(self, image_key='good_quality', prompt=None):
        """Create test event with specified image"""
        if prompt is None:
            prompt = "Identify the medication in this image"
        
        return {
            'input': {
                'RequestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'image_data', 'value': self.test_images[image_key]},
                                {'name': 'prompt', 'value': prompt}
                            ]
                        }
                    }
                }
            },
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
    
    @patch('app.get_drug_information')
    @patch('app.VisionModelClient')
    @patch('app.MedicationExtractor')
    def test_successful_end_to_end_workflow(self, mock_extractor_class, mock_client_class, mock_drug_info):
        """Test complete successful workflow from image to final response"""
        # Mock vision analysis
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.detect_media_type.return_value = "image/jpeg"
        mock_client.analyze_image.return_value = VisionModelResponse(
            success=True,
            response_text="I can clearly identify this medication as Advil 200mg with high confidence.",
            processing_time=1.5,
            usage={'input_tokens': 150, 'output_tokens': 75}
        )
        
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_medication_info.return_value = MedicationIdentification(
            medication_name="Advil",
            dosage="200mg",
            confidence=0.9,
            image_quality=ImageQuality.GOOD.value,
            alternative_names=["Ibuprofen"]
        )
        
        # Mock drug info
        mock_drug_info.return_value = {
            'success': True,
            'drug_info': {
                'brand_name': 'Advil',
                'generic_name': 'Ibuprofen',
                'purpose': 'Pain reliever/fever reducer',
                'warnings': 'Do not exceed recommended dose. May cause stomach bleeding.',
                'indications_and_usage': 'For temporary relief of minor aches and pains'
            }
        }
        
        # Execute end-to-end test
        event = self._create_test_event('good_quality')
        start_time = time.time()
        response = lambda_handler(event, self.mock_context)
        end_time = time.time()
        
        # Verify response structure
        self.assertEqual(response['messageVersion'], '1.0')
        self.assertEqual(response['response']['httpStatusCode'], 200)
        
        # Parse and verify response body
        response_body = json.loads(response['response']['responseBody']['application/json']['body'])
        
        # Verify success
        self.assertTrue(response_body['success'])
        
        # Verify identification results
        self.assertEqual(response_body['medication_name'], 'Advil')
        self.assertEqual(response_body['dosage'], '200mg')
        self.assertEqual(response_body['confidence'], 0.9)
        
        # Verify drug information
        self.assertTrue(response_body['drug_info_available'])
        self.assertIn('drug_info', response_body)
        self.assertEqual(response_body['drug_info']['brand_name'], 'Advil')
        self.assertEqual(response_body['drug_info']['generic_name'], 'Ibuprofen')
        
        # Verify user response
        self.assertIn('user_response', response_body)
        self.assertIn('Advil', response_body['user_response'])
        self.assertIn('high confidence', response_body['user_response'])
        
        # Verify performance metadata
        self.assertIn('processing_time', response_body)
        self.assertGreater(response_body['processing_time'], 0)
        
        # Verify reasonable processing time (should be fast with mocks)
        total_time = end_time - start_time
        self.assertLess(total_time, 5.0)  # Should complete within 5 seconds
    
    @patch('app.get_drug_information')
    @patch('app.VisionModelClient')
    @patch('app.MedicationExtractor')
    def test_low_confidence_workflow(self, mock_extractor_class, mock_client_class, mock_drug_info):
        """Test workflow with low confidence identification"""
        # Mock low confidence vision analysis
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.detect_media_type.return_value = "image/jpeg"
        mock_client.analyze_image.return_value = VisionModelResponse(
            success=True,
            response_text="The image is blurry and I cannot clearly identify the medication.",
            processing_time=1.2
        )
        
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_medication_info.return_value = MedicationIdentification(
            medication_name="Unknown",
            dosage="",
            confidence=0.2,
            image_quality=ImageQuality.POOR.value
        )
        
        event = self._create_test_event('poor_quality')
        response = lambda_handler(event, self.mock_context)
        
        response_body = json.loads(response['response']['responseBody']['application/json']['body'])
        
        # Should still return success but with warnings
        self.assertTrue(response_body['success'])
        self.assertEqual(response_body['confidence'], 0.2)
        self.assertFalse(response_body['drug_info_available'])
        
        # Should not call drug info for low confidence
        mock_drug_info.assert_not_called()
        
        # User response should indicate low confidence
        self.assertIn('not very confident', response_body['user_response'])
    
    def test_invalid_image_data_workflow(self):
        """Test workflow with invalid image data"""
        event = {
            'input': {
                'RequestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'image_data', 'value': 'invalid_base64_data!'},
                                {'name': 'prompt', 'value': 'Identify medication'}
                            ]
                        }
                    }
                }
            },
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
        
        response = lambda_handler(event, self.mock_context)
        
        # Should return error response
        self.assertIn(response['response']['httpStatusCode'], [400, 500])
        
        response_body = json.loads(response['response']['responseBody']['application/json']['body'])
        self.assertFalse(response_body['success'])
        self.assertIn('error', response_body)
    
    def test_multiple_image_formats(self):
        """Test workflow with different image formats"""
        formats_to_test = ['good_quality', 'png_transparent']
        
        for image_format in formats_to_test:
            with self.subTest(format=image_format):
                with patch('app.VisionModelClient') as mock_client_class:
                    with patch('app.MedicationExtractor') as mock_extractor_class:
                        with patch('app.get_drug_information') as mock_drug_info:
                            # Setup mocks
                            mock_client = Mock()
                            mock_client_class.return_value = mock_client
                            mock_client.detect_media_type.return_value = "image/jpeg"
                            mock_client.analyze_image.return_value = VisionModelResponse(success=True)
                            
                            mock_extractor = Mock()
                            mock_extractor_class.return_value = mock_extractor
                            mock_extractor.extract_medication_info.return_value = MedicationIdentification(
                                medication_name="Test Med",
                                confidence=0.8
                            )
                            
                            mock_drug_info.return_value = {'success': False}
                            
                            event = self._create_test_event(image_format)
                            response = lambda_handler(event, self.mock_context)
                            
                            # Should handle different formats successfully
                            self.assertEqual(response['response']['httpStatusCode'], 200)

class TestDrugInfoToolIntegration(unittest.TestCase):
    """Test integration with DrugInfoTool with real API calls"""
    
    def setUp(self):
        """Set up test fixtures"""
        # These tests would use real DrugInfoTool calls in a real environment
        # For unit testing, we'll mock the external dependencies but test the integration logic
        pass
    
    @patch('drug_info_integration.drug_info_handler')
    def test_successful_drug_lookup(self, mock_handler):
        """Test successful drug information lookup"""
        # Mock successful DrugInfoTool response
        mock_response = {
            'response': {
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'brand_name': 'Advil',
                            'generic_name': 'Ibuprofen',
                            'purpose': 'Pain reliever/fever reducer',
                            'warnings': 'Do not exceed recommended dose',
                            'indications_and_usage': 'For temporary relief of minor aches'
                        })
                    }
                }
            }
        }
        mock_handler.return_value = mock_response
        
        result = get_drug_information("Advil")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['drug_info']['brand_name'], 'Advil')
        self.assertEqual(result['drug_info']['generic_name'], 'Ibuprofen')
        
        # Verify the handler was called with correct format
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args[0][0]
        self.assertIn('input', call_args)
    
    @patch('drug_info_integration.drug_info_handler')
    def test_drug_not_found_handling(self, mock_handler):
        """Test handling when drug is not found"""
        mock_response = {
            'response': {
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'error': 'No information found for drug',
                            'suggestion': 'Try using generic name'
                        })
                    }
                }
            }
        }
        mock_handler.return_value = mock_response
        
        result = get_drug_information("UnknownDrug")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'No information found for drug')
        self.assertEqual(result['suggestion'], 'Try using generic name')
    
    @patch('drug_info_integration.drug_info_handler')
    def test_drug_info_timeout_handling(self, mock_handler):
        """Test handling of DrugInfoTool timeout"""
        mock_handler.side_effect = TimeoutError("Request timed out")
        
        result = get_drug_information("Aspirin")
        
        self.assertFalse(result['success'])
        self.assertIn('timeout', result['error'].lower())
    
    def test_drug_name_validation(self):
        """Test drug name validation before lookup"""
        invalid_names = ["", None, "A", "  ", "123"]
        
        for invalid_name in invalid_names:
            with self.subTest(name=invalid_name):
                result = get_drug_information(invalid_name)
                self.assertFalse(result['success'])
                self.assertIn('Invalid drug name', result['error'])

class TestPerformanceTests(unittest.TestCase):
    """Performance tests for image processing and API calls"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test image
        test_img = Image.new('RGB', (800, 600), color=(255, 255, 255))
        buffer = io.BytesIO()
        test_img.save(buffer, format='JPEG')
        self.test_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def test_image_validation_performance(self):
        """Test image validation performance"""
        validator = ImageValidator()
        
        start_time = time.time()
        for _ in range(10):
            result = validator.validate_image(self.test_image_base64)
            self.assertTrue(result.valid)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10
        self.assertLess(avg_time, 0.1)  # Should validate in under 100ms
    
    def test_image_preprocessing_performance(self):
        """Test image preprocessing performance"""
        preprocessor = ImagePreprocessor()
        
        start_time = time.time()
        for _ in range(5):
            success, error, image = preprocessor.base64_to_image(self.test_image_base64)
            self.assertTrue(success)
            
            success, message, optimized = preprocessor.optimize_for_vision_model(image)
            self.assertTrue(success)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 5
        self.assertLess(avg_time, 1.0)  # Should preprocess in under 1 second
    
    @patch('vision_client.boto3.client')
    def test_vision_model_response_time(self, mock_boto_client):
        """Test vision model response time simulation"""
        # Mock Bedrock client
        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance
        
        # Mock response with realistic delay
        def mock_invoke_model(*args, **kwargs):
            time.sleep(0.1)  # Simulate 100ms API call
            mock_response = {
                'body': Mock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'content': [{'text': 'Medication: Advil 200mg'}],
                'usage': {'input_tokens': 100, 'output_tokens': 50}
            }).encode('utf-8')
            return mock_response
        
        mock_client_instance.invoke_model = mock_invoke_model
        
        client = VisionModelClient()
        
        start_time = time.time()
        result = client.analyze_image(self.test_image_base64, "Test prompt")
        end_time = time.time()
        
        self.assertTrue(result.success)
        self.assertLess(end_time - start_time, 1.0)  # Should complete within 1 second
    
    def test_memory_usage_large_image(self):
        """Test memory usage with large images"""
        # Create a larger image
        large_img = Image.new('RGB', (2000, 1500), color=(128, 128, 128))
        buffer = io.BytesIO()
        large_img.save(buffer, format='JPEG', quality=95)
        large_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        validator = ImageValidator()
        preprocessor = ImagePreprocessor()
        
        # This should not cause memory issues
        validation_result = validator.validate_image(large_image_base64)
        self.assertTrue(validation_result.valid)
        
        success, error, image = preprocessor.base64_to_image(large_image_base64)
        self.assertTrue(success)
        
        # Optimization should handle large images
        success, message, optimized = preprocessor.optimize_for_vision_model(image)
        self.assertTrue(success)
        
        # Optimized image should be smaller than original
        self.assertLessEqual(max(optimized.size), preprocessor.MAX_DIMENSION)

class TestConcurrentRequestHandling(unittest.TestCase):
    """Load tests for concurrent request handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test image
        test_img = Image.new('RGB', (400, 300), color=(200, 200, 200))
        buffer = io.BytesIO()
        test_img.save(buffer, format='JPEG')
        self.test_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        self.mock_context = Mock()
        self.mock_context.aws_request_id = 'test-request-id'
        self.mock_context.remaining_time_in_millis = lambda: 30000
    
    def _create_test_event(self):
        """Create test event"""
        return {
            'input': {
                'RequestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'image_data', 'value': self.test_image_base64},
                                {'name': 'prompt', 'value': 'Identify medication'}
                            ]
                        }
                    }
                }
            },
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
    
    @patch('app.get_drug_information')
    @patch('app.VisionModelClient')
    @patch('app.MedicationExtractor')
    def test_concurrent_image_validation(self, mock_extractor_class, mock_client_class, mock_drug_info):
        """Test concurrent image validation requests"""
        # Setup mocks for successful processing
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.detect_media_type.return_value = "image/jpeg"
        mock_client.analyze_image.return_value = VisionModelResponse(success=True, response_text="Test")
        
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_medication_info.return_value = MedicationIdentification(
            medication_name="Test", confidence=0.8
        )
        
        mock_drug_info.return_value = {'success': False}
        
        def process_request():
            event = self._create_test_event()
            return lambda_handler(event, self.mock_context)
        
        # Run 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_request) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for result in results:
            self.assertEqual(result['response']['httpStatusCode'], 200)
    
    def test_concurrent_image_preprocessing(self):
        """Test concurrent image preprocessing"""
        preprocessor = ImagePreprocessor()
        
        def preprocess_image():
            success, error, image = preprocessor.base64_to_image(self.test_image_base64)
            if success:
                success, message, optimized = preprocessor.optimize_for_vision_model(image)
                return success
            return False
        
        # Run 10 concurrent preprocessing operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(preprocess_image) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All preprocessing should succeed
        self.assertTrue(all(results))
    
    def test_thread_safety_validation(self):
        """Test thread safety of validation operations"""
        validator = ImageValidator()
        results = []
        
        def validate_image():
            result = validator.validate_image(self.test_image_base64)
            results.append(result.valid)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=validate_image)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All validations should succeed
        self.assertTrue(all(results))
        self.assertEqual(len(results), 10)
    
    @patch('app.get_drug_information')
    def test_drug_info_concurrent_calls(self, mock_drug_info):
        """Test concurrent drug information lookups"""
        # Mock drug info responses
        mock_drug_info.return_value = {
            'success': True,
            'drug_info': {'brand_name': 'Test Drug'}
        }
        
        def lookup_drug(drug_name):
            return get_drug_information(drug_name)
        
        drug_names = ['Advil', 'Tylenol', 'Aspirin', 'Motrin', 'Aleve']
        
        # Run concurrent lookups
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(lookup_drug, name) for name in drug_names]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All lookups should succeed
        for result in results:
            self.assertTrue(result['success'])
        
        # Should have made 5 calls
        self.assertEqual(mock_drug_info.call_count, 5)

class TestErrorRecoveryIntegration(unittest.TestCase):
    """Test error recovery and resilience"""
    
    def setUp(self):
        """Set up test fixtures"""
        test_img = Image.new('RGB', (200, 200), color=(255, 255, 255))
        buffer = io.BytesIO()
        test_img.save(buffer, format='JPEG')
        self.test_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        self.mock_context = Mock()
        self.mock_context.aws_request_id = 'test-request-id'
    
    @patch('app.VisionModelClient')
    def test_vision_model_failure_recovery(self, mock_client_class):
        """Test recovery from vision model failures"""
        # Mock vision model failure
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.detect_media_type.return_value = "image/jpeg"
        mock_client.analyze_image.return_value = VisionModelResponse(
            success=False,
            error="Vision model timeout"
        )
        
        event = {
            'input': {
                'RequestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'image_data', 'value': self.test_image_base64}
                            ]
                        }
                    }
                }
            },
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
        
        response = lambda_handler(event, self.mock_context)
        
        # Should handle error gracefully
        self.assertIn(response['response']['httpStatusCode'], [400, 500])
        
        response_body = json.loads(response['response']['responseBody']['application/json']['body'])
        self.assertFalse(response_body['success'])
        self.assertIn('error', response_body)
    
    def test_malformed_request_handling(self):
        """Test handling of malformed requests"""
        malformed_events = [
            {},  # Empty event
            {'invalid': 'structure'},  # Invalid structure
            {'input': {}},  # Missing required fields
            {'input': {'RequestBody': {}}},  # Incomplete structure
        ]
        
        for event in malformed_events:
            with self.subTest(event=event):
                response = lambda_handler(event, self.mock_context)
                
                # Should handle gracefully with error response
                self.assertIn(response['response']['httpStatusCode'], [400, 500])
                
                response_body = json.loads(response['response']['responseBody']['application/json']['body'])
                self.assertFalse(response_body['success'])

class TestSystemIntegration(unittest.TestCase):
    """Test system-level integration scenarios"""
    
    def test_configuration_integration(self):
        """Test that all components use configuration correctly"""
        from config import config
        
        # Test that components respect configuration limits
        validator = ImageValidator()
        self.assertEqual(validator.max_size, config.MAX_IMAGE_SIZE)
        self.assertEqual(validator.allowed_formats, config.SUPPORTED_FORMATS)
        
        # Test vision model configuration
        vision_config = config.get_vision_model_config()
        self.assertIn('model_id', vision_config)
        self.assertIn('timeout', vision_config)
    
    def test_error_handling_integration(self):
        """Test that error handling works across all components"""
        error_handler = ErrorHandler()
        
        # Test different error types
        errors_to_test = [
            (ImageValidationError("Test validation error"), "image_processing"),
            (VisionModelError("Test vision error"), "vision_analysis"),
            (DrugInfoError("Test drug info error"), "drug_lookup")
        ]
        
        for error, expected_category in errors_to_test:
            with self.subTest(error_type=type(error).__name__):
                from error_handling import ErrorContext
                context = ErrorContext(operation="test")
                
                error_details = error_handler.handle_error(error, context)
                
                self.assertIsNotNone(error_details)
                self.assertIn(expected_category, error_details.category.value)
    
    def test_logging_integration(self):
        """Test that logging works across all components"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Test that components can log
            validator = ImageValidator()
            preprocessor = ImagePreprocessor()
            
            # These should not raise exceptions
            validator.validate_image("invalid_data")
            preprocessor.base64_to_image("invalid_data")
            
            # Logger should have been called
            self.assertTrue(mock_get_logger.called)

if __name__ == '__main__':
    # Run tests with different verbosity levels
    unittest.main(verbosity=2)