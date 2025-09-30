"""
Unit tests for the vision model client.
Tests vision model API interactions, response parsing, and error handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import base64
from botocore.exceptions import ClientError, BotoCoreError

from vision_client import VisionModelClient, MedicationExtractor
from models import VisionModelResponse, MedicationIdentification, ImageQuality

class TestVisionModelClient(unittest.TestCase):
    """Test cases for VisionModelClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = VisionModelClient()
        self.sample_image_data = base64.b64encode(b"fake_image_data").decode('utf-8')
    
    @patch('vision_client.boto3.client')
    def test_init_with_defaults(self, mock_boto_client):
        """Test client initialization with default parameters"""
        client = VisionModelClient()
        
        self.assertIsNotNone(client.model_id)
        self.assertIsNotNone(client.region)
        self.assertIsNotNone(client.bedrock_client)
        self.assertIn('standard', client.prompt_templates)
        self.assertIn('detailed', client.prompt_templates)
        self.assertIn('confidence_check', client.prompt_templates)
    
    @patch('vision_client.boto3.client')
    def test_init_with_custom_params(self, mock_boto_client):
        """Test client initialization with custom parameters"""
        custom_model = "custom-model-id"
        custom_region = "us-west-2"
        
        client = VisionModelClient(model_id=custom_model, region=custom_region)
        
        self.assertEqual(client.model_id, custom_model)
        self.assertEqual(client.region, custom_region)
        mock_boto_client.assert_called_with('bedrock-runtime', region_name=custom_region)
    
    @patch('vision_client.time.time')
    def test_analyze_image_success(self, mock_time):
        """Test successful image analysis"""
        # Mock time for processing time calculation
        mock_time.side_effect = [0.0, 1.5]  # Start and end times
        
        # Mock successful Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'This is Advil 200mg with high confidence'}],
            'usage': {'input_tokens': 100, 'output_tokens': 50}
        }).encode('utf-8')
        
        self.client.bedrock_client.invoke_model = Mock(return_value=mock_response)
        
        # Test the analysis
        result = self.client.analyze_image(self.sample_image_data, "Test prompt")
        
        # Verify the result
        self.assertIsInstance(result, VisionModelResponse)
        self.assertTrue(result.success)
        self.assertEqual(result.response_text, 'This is Advil 200mg with high confidence')
        self.assertEqual(result.processing_time, 1.5)
        self.assertEqual(result.usage['input_tokens'], 100)
        self.assertEqual(result.usage['output_tokens'], 50)
        
        # Verify the API call
        self.client.bedrock_client.invoke_model.assert_called_once()
        call_args = self.client.bedrock_client.invoke_model.call_args
        self.assertIn('modelId', call_args.kwargs)
        self.assertIn('body', call_args.kwargs)
    
    @patch('vision_client.time.time')
    def test_analyze_image_client_error(self, mock_time):
        """Test handling of AWS ClientError"""
        mock_time.side_effect = [0.0, 0.5]
        
        # Mock ClientError
        error_response = {
            'Error': {
                'Code': 'ValidationException',
                'Message': 'Invalid model ID'
            }
        }
        self.client.bedrock_client.invoke_model = Mock(
            side_effect=ClientError(error_response, 'InvokeModel')
        )
        
        result = self.client.analyze_image(self.sample_image_data, "Test prompt")
        
        self.assertFalse(result.success)
        self.assertIn('Invalid model ID', result.error)
        self.assertEqual(result.processing_time, 0.5)
    
    @patch('vision_client.time.time')
    def test_analyze_image_botocore_error(self, mock_time):
        """Test handling of BotoCoreError"""
        mock_time.side_effect = [0.0, 0.3]
        
        self.client.bedrock_client.invoke_model = Mock(
            side_effect=BotoCoreError()
        )
        
        result = self.client.analyze_image(self.sample_image_data, "Test prompt")
        
        self.assertFalse(result.success)
        self.assertIn('connection error', result.error)
        self.assertEqual(result.processing_time, 0.3)
    
    @patch('vision_client.time.time')
    def test_analyze_image_unexpected_error(self, mock_time):
        """Test handling of unexpected errors"""
        mock_time.side_effect = [0.0, 0.2]
        
        self.client.bedrock_client.invoke_model = Mock(
            side_effect=Exception("Unexpected error")
        )
        
        result = self.client.analyze_image(self.sample_image_data, "Test prompt")
        
        self.assertFalse(result.success)
        self.assertIn('Unexpected error', result.error)
        self.assertEqual(result.processing_time, 0.2)
    
    def test_analyze_with_confidence_check(self):
        """Test confidence-focused analysis"""
        with patch.object(self.client, 'analyze_image') as mock_analyze:
            mock_analyze.return_value = VisionModelResponse(success=True)
            
            result = self.client.analyze_with_confidence_check(self.sample_image_data)
            
            mock_analyze.assert_called_once()
            call_args = mock_analyze.call_args
            self.assertEqual(call_args.kwargs['image_data'], self.sample_image_data)
            self.assertIn('confidence', call_args.kwargs['prompt'].lower())
    
    def test_analyze_detailed(self):
        """Test detailed analysis"""
        with patch.object(self.client, 'analyze_image') as mock_analyze:
            mock_analyze.return_value = VisionModelResponse(success=True)
            
            result = self.client.analyze_detailed(self.sample_image_data)
            
            mock_analyze.assert_called_once()
            call_args = mock_analyze.call_args
            self.assertEqual(call_args.kwargs['image_data'], self.sample_image_data)
            self.assertIn('comprehensive', call_args.kwargs['prompt'].lower())
    
    def test_detect_media_type_jpeg(self):
        """Test JPEG media type detection"""
        # JPEG magic number: FF D8 FF
        jpeg_data = base64.b64encode(b'\xff\xd8\xff\xe0\x00\x10JFIF').decode('utf-8')
        
        media_type = self.client.detect_media_type(jpeg_data)
        
        self.assertEqual(media_type, "image/jpeg")
    
    def test_detect_media_type_png(self):
        """Test PNG media type detection"""
        # PNG magic number: 89 50 4E 47 0D 0A 1A 0A
        png_data = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR').decode('utf-8')
        
        media_type = self.client.detect_media_type(png_data)
        
        self.assertEqual(media_type, "image/png")
    
    def test_detect_media_type_webp(self):
        """Test WebP media type detection"""
        # WebP magic number: RIFF...WEBP
        webp_data = base64.b64encode(b'RIFF\x00\x00\x00\x00WEBPVP8 ').decode('utf-8')
        
        media_type = self.client.detect_media_type(webp_data)
        
        self.assertEqual(media_type, "image/webp")
    
    def test_detect_media_type_unknown(self):
        """Test unknown media type defaults to JPEG"""
        unknown_data = base64.b64encode(b'unknown_format_data').decode('utf-8')
        
        media_type = self.client.detect_media_type(unknown_data)
        
        self.assertEqual(media_type, "image/jpeg")
    
    def test_detect_media_type_invalid_base64(self):
        """Test handling of invalid base64 data"""
        invalid_data = "invalid_base64_data!"
        
        media_type = self.client.detect_media_type(invalid_data)
        
        self.assertEqual(media_type, "image/jpeg")  # Should default to JPEG
    
    def test_prompt_templates_exist(self):
        """Test that all required prompt templates exist"""
        required_templates = ['standard', 'detailed', 'confidence_check']
        
        for template_name in required_templates:
            self.assertIn(template_name, self.client.prompt_templates)
            self.assertIsInstance(self.client.prompt_templates[template_name], str)
            self.assertGreater(len(self.client.prompt_templates[template_name]), 50)

class TestMedicationExtractor(unittest.TestCase):
    """Test cases for MedicationExtractor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.extractor = MedicationExtractor()
    
    def test_extract_high_confidence_medication(self):
        """Test extraction of high confidence medication identification"""
        response = """
        I can clearly identify this medication with high confidence.
        Medication name: Advil
        Dosage: 200mg
        The image is clear and well-lit, showing obvious markings.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertIsInstance(result, MedicationIdentification)
        self.assertEqual(result.medication_name, "Advil")
        self.assertEqual(result.dosage, "200mg")
        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertEqual(result.image_quality, ImageQuality.GOOD.value)
    
    def test_extract_medium_confidence_medication(self):
        """Test extraction of medium confidence medication identification"""
        response = """
        This appears to be a medication, likely Tylenol.
        The dosage seems to be 500mg based on what I can see.
        Moderate confidence in this identification.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "Tylenol")
        self.assertEqual(result.dosage, "500mg")
        self.assertGreaterEqual(result.confidence, 0.6)
        self.assertLess(result.confidence, 0.8)
    
    def test_extract_low_confidence_medication(self):
        """Test extraction of low confidence medication identification"""
        response = """
        The image is blurry and unclear.
        I cannot determine the medication name with certainty.
        Low confidence in any identification.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertLessEqual(result.confidence, 0.4)
        self.assertEqual(result.image_quality, ImageQuality.POOR.value)
    
    def test_extract_confidence_from_percentage(self):
        """Test confidence extraction from percentage values"""
        response = "I am 85% confident this is Aspirin 325mg."
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.confidence, 0.85)
    
    def test_extract_dosage_patterns(self):
        """Test various dosage pattern extractions"""
        test_cases = [
            ("Dosage: 200mg", "200mg"),
            ("Strength: 500mg", "500mg"),
            ("This is 10mg tablets", "10mg"),
            ("Dose: 2.5mg", "2.5mg"),
            ("Contains 1000mcg", "1000mcg"),
            ("5ml liquid", "5ml")
        ]
        
        for response, expected_dosage in test_cases:
            with self.subTest(response=response):
                result = self.extractor.extract_medication_info(response)
                self.assertEqual(result.dosage, expected_dosage)
    
    def test_extract_medication_name_patterns(self):
        """Test various medication name pattern extractions"""
        test_cases = [
            ("Medication name: Ibuprofen", "Ibuprofen"),
            ("Brand name: Advil", "Advil"),
            ("Generic name: Acetaminophen", "Acetaminophen"),
            ("This is Tylenol", "Tylenol"),
            ("Identified as Aspirin", "Aspirin"),
            ("Appears to be Motrin", "Motrin")
        ]
        
        for response, expected_name in test_cases:
            with self.subTest(response=response):
                result = self.extractor.extract_medication_info(response)
                self.assertEqual(result.medication_name, expected_name)
    
    def test_extract_alternative_names(self):
        """Test extraction of alternative medication names"""
        response = """
        Brand name: Advil
        Generic name: Ibuprofen
        Also known as Motrin
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertIn("Ibuprofen", result.alternative_names)
        self.assertIn("Motrin", result.alternative_names)
    
    def test_image_quality_determination(self):
        """Test image quality determination from response content"""
        test_cases = [
            ("The image is clear and sharp", ImageQuality.GOOD.value),
            ("Somewhat clear image", ImageQuality.FAIR.value),
            ("The image is blurry and unclear", ImageQuality.POOR.value)
        ]
        
        for response, expected_quality in test_cases:
            with self.subTest(response=response):
                result = self.extractor.extract_medication_info(response)
                self.assertEqual(result.image_quality, expected_quality)
    
    def test_extract_with_no_medication_found(self):
        """Test extraction when no medication is found"""
        response = """
        I cannot identify any medication in this image.
        The image shows unclear objects.
        No medication visible.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "")
        self.assertEqual(result.dosage, "")
        self.assertLessEqual(result.confidence, 0.5)
    
    def test_extract_with_exception_handling(self):
        """Test extraction with malformed response that causes exceptions"""
        # This should not raise an exception
        result = self.extractor.extract_medication_info(None)
        
        self.assertIsInstance(result, MedicationIdentification)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.image_quality, ImageQuality.POOR.value)
    
    def test_confidence_keywords_classification(self):
        """Test confidence classification based on keywords"""
        high_confidence_phrases = [
            "clearly visible medication",
            "confident identification",
            "high confidence in this result",
            "certain this is Advil",
            "definite identification"
        ]
        
        medium_confidence_phrases = [
            "likely to be Tylenol",
            "appears to be medication",
            "moderate confidence",
            "probably Aspirin",
            "seems to be 200mg"
        ]
        
        low_confidence_phrases = [
            "unclear image",
            "difficult to determine",
            "low confidence",
            "blurry medication",
            "uncertain identification"
        ]
        
        for phrase in high_confidence_phrases:
            with self.subTest(phrase=phrase):
                result = self.extractor.extract_medication_info(phrase)
                self.assertGreaterEqual(result.confidence, 0.8)
        
        for phrase in medium_confidence_phrases:
            with self.subTest(phrase=phrase):
                result = self.extractor.extract_medication_info(phrase)
                self.assertGreaterEqual(result.confidence, 0.6)
                self.assertLess(result.confidence, 0.8)
        
        for phrase in low_confidence_phrases:
            with self.subTest(phrase=phrase):
                result = self.extractor.extract_medication_info(phrase)
                self.assertLessEqual(result.confidence, 0.4)

class TestVisionClientIntegration(unittest.TestCase):
    """Integration tests for vision client components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = VisionModelClient()
        self.extractor = MedicationExtractor()
    
    def test_end_to_end_mock_workflow(self):
        """Test complete workflow with mocked responses"""
        # Mock a successful vision model response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Medication name: Advil\nDosage: 200mg\nHigh confidence identification'}],
            'usage': {'input_tokens': 150, 'output_tokens': 75}
        }).encode('utf-8')
        
        self.client.bedrock_client.invoke_model = Mock(return_value=mock_response)
        
        # Test the complete workflow
        vision_result = self.client.analyze_image(
            base64.b64encode(b"fake_image").decode('utf-8'),
            "Identify this medication"
        )
        
        self.assertTrue(vision_result.success)
        
        # Extract medication information
        medication_info = self.extractor.extract_medication_info(vision_result.response_text)
        
        self.assertEqual(medication_info.medication_name, "Advil")
        self.assertEqual(medication_info.dosage, "200mg")
        self.assertGreaterEqual(medication_info.confidence, 0.8)

if __name__ == '__main__':
    unittest.main()