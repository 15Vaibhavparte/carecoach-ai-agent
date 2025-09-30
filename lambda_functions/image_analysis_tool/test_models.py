"""
Unit tests for data models and interfaces.
Tests all data models, enums, and interface definitions.
"""

import unittest
from dataclasses import asdict
from models import (
    ImageQuality,
    ProcessingStatus,
    ImageAnalysisRequest,
    ImageValidationResult,
    MedicationIdentification,
    VisionModelResponse,
    DrugInfoResult,
    CombinedResponse,
    ImageAnalysisError,
    ImageValidationError,
    VisionModelError,
    DrugInfoError
)

class TestEnums(unittest.TestCase):
    """Test enumeration classes"""
    
    def test_image_quality_enum(self):
        """Test ImageQuality enum values"""
        self.assertEqual(ImageQuality.GOOD.value, "good")
        self.assertEqual(ImageQuality.FAIR.value, "fair")
        self.assertEqual(ImageQuality.POOR.value, "poor")
        self.assertEqual(ImageQuality.UNKNOWN.value, "unknown")
    
    def test_processing_status_enum(self):
        """Test ProcessingStatus enum values"""
        self.assertEqual(ProcessingStatus.SUCCESS.value, "success")
        self.assertEqual(ProcessingStatus.FAILED.value, "failed")
        self.assertEqual(ProcessingStatus.PARTIAL.value, "partial")

class TestImageAnalysisRequest(unittest.TestCase):
    """Test ImageAnalysisRequest data model"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        request = ImageAnalysisRequest(image_data="test_data")
        
        self.assertEqual(request.image_data, "test_data")
        self.assertEqual(request.prompt, "Identify the medication name and dosage in this image")
        self.assertEqual(request.max_file_size, 10 * 1024 * 1024)
        self.assertEqual(request.allowed_formats, ['jpeg', 'jpg', 'png', 'webp'])
    
    def test_custom_initialization(self):
        """Test initialization with custom values"""
        request = ImageAnalysisRequest(
            image_data="custom_data",
            prompt="Custom prompt",
            max_file_size=5 * 1024 * 1024,
            allowed_formats=['jpeg', 'png']
        )
        
        self.assertEqual(request.image_data, "custom_data")
        self.assertEqual(request.prompt, "Custom prompt")
        self.assertEqual(request.max_file_size, 5 * 1024 * 1024)
        self.assertEqual(request.allowed_formats, ['jpeg', 'png'])
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        request = ImageAnalysisRequest(image_data="test_data")
        result = request.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['image_data'], "test_data")
        self.assertIn('prompt', result)
        self.assertIn('max_file_size', result)
        self.assertIn('allowed_formats', result)

class TestImageValidationResult(unittest.TestCase):
    """Test ImageValidationResult data model"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        result = ImageValidationResult(valid=True)
        
        self.assertTrue(result.valid)
        self.assertEqual(result.error, "")
        self.assertEqual(result.size, 0)
        self.assertEqual(result.format_detected, "")
    
    def test_custom_initialization(self):
        """Test initialization with custom values"""
        result = ImageValidationResult(
            valid=False,
            error="Invalid format",
            size=1024,
            format_detected="jpeg"
        )
        
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "Invalid format")
        self.assertEqual(result.size, 1024)
        self.assertEqual(result.format_detected, "jpeg")
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        result = ImageValidationResult(valid=True, size=1024)
        dict_result = result.to_dict()
        
        self.assertIsInstance(dict_result, dict)
        self.assertTrue(dict_result['valid'])
        self.assertEqual(dict_result['size'], 1024)

class TestMedicationIdentification(unittest.TestCase):
    """Test MedicationIdentification data model"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        identification = MedicationIdentification(medication_name="Advil")
        
        self.assertEqual(identification.medication_name, "Advil")
        self.assertEqual(identification.dosage, "")
        self.assertEqual(identification.confidence, 0.0)
        self.assertEqual(identification.alternative_names, [])
        self.assertEqual(identification.image_quality, ImageQuality.UNKNOWN.value)
        self.assertEqual(identification.raw_response, "")
    
    def test_custom_initialization(self):
        """Test initialization with custom values"""
        identification = MedicationIdentification(
            medication_name="Advil",
            dosage="200mg",
            confidence=0.9,
            alternative_names=["Ibuprofen"],
            image_quality=ImageQuality.GOOD.value,
            raw_response="Test response"
        )
        
        self.assertEqual(identification.medication_name, "Advil")
        self.assertEqual(identification.dosage, "200mg")
        self.assertEqual(identification.confidence, 0.9)
        self.assertEqual(identification.alternative_names, ["Ibuprofen"])
        self.assertEqual(identification.image_quality, ImageQuality.GOOD.value)
        self.assertEqual(identification.raw_response, "Test response")
    
    def test_is_high_confidence_default_threshold(self):
        """Test high confidence check with default threshold"""
        high_conf = MedicationIdentification(medication_name="Test", confidence=0.9)
        low_conf = MedicationIdentification(medication_name="Test", confidence=0.7)
        
        self.assertTrue(high_conf.is_high_confidence())
        self.assertFalse(low_conf.is_high_confidence())
    
    def test_is_high_confidence_custom_threshold(self):
        """Test high confidence check with custom threshold"""
        identification = MedicationIdentification(medication_name="Test", confidence=0.7)
        
        self.assertTrue(identification.is_high_confidence(threshold=0.6))
        self.assertFalse(identification.is_high_confidence(threshold=0.8))
    
    def test_has_valid_identification_valid(self):
        """Test valid identification check"""
        valid_cases = [
            MedicationIdentification(medication_name="Advil"),
            MedicationIdentification(medication_name="Tylenol"),
            MedicationIdentification(medication_name="Aspirin 325mg")
        ]
        
        for identification in valid_cases:
            with self.subTest(name=identification.medication_name):
                self.assertTrue(identification.has_valid_identification())
    
    def test_has_valid_identification_invalid(self):
        """Test invalid identification check"""
        invalid_cases = [
            MedicationIdentification(medication_name=""),
            MedicationIdentification(medication_name="unknown"),
            MedicationIdentification(medication_name="not found"),
            MedicationIdentification(medication_name="Unknown")
        ]
        
        for identification in invalid_cases:
            with self.subTest(name=identification.medication_name):
                self.assertFalse(identification.has_valid_identification())
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        identification = MedicationIdentification(
            medication_name="Advil",
            confidence=0.9,
            alternative_names=["Ibuprofen"]
        )
        result = identification.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['medication_name'], "Advil")
        self.assertEqual(result['confidence'], 0.9)
        self.assertEqual(result['alternative_names'], ["Ibuprofen"])

class TestVisionModelResponse(unittest.TestCase):
    """Test VisionModelResponse data model"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        response = VisionModelResponse(success=True)
        
        self.assertTrue(response.success)
        self.assertEqual(response.response_text, "")
        self.assertEqual(response.usage, {})
        self.assertEqual(response.error, "")
        self.assertEqual(response.processing_time, 0.0)
    
    def test_custom_initialization(self):
        """Test initialization with custom values"""
        usage = {'input_tokens': 100, 'output_tokens': 50}
        response = VisionModelResponse(
            success=True,
            response_text="Medication identified",
            usage=usage,
            processing_time=1.5
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.response_text, "Medication identified")
        self.assertEqual(response.usage, usage)
        self.assertEqual(response.processing_time, 1.5)
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        response = VisionModelResponse(success=True, processing_time=1.0)
        result = response.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['processing_time'], 1.0)

class TestDrugInfoResult(unittest.TestCase):
    """Test DrugInfoResult data model"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        result = DrugInfoResult(success=True)
        
        self.assertTrue(result.success)
        self.assertEqual(result.data, {})
        self.assertEqual(result.error, "")
        self.assertEqual(result.source, "DrugInfoTool")
    
    def test_custom_initialization(self):
        """Test initialization with custom values"""
        data = {'brand_name': 'Advil', 'generic_name': 'Ibuprofen'}
        result = DrugInfoResult(
            success=True,
            data=data,
            source="Custom API"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.data, data)
        self.assertEqual(result.source, "Custom API")
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        result = DrugInfoResult(success=True, error="Test error")
        dict_result = result.to_dict()
        
        self.assertIsInstance(dict_result, dict)
        self.assertTrue(dict_result['success'])
        self.assertEqual(dict_result['error'], "Test error")

class TestCombinedResponse(unittest.TestCase):
    """Test CombinedResponse data model"""
    
    def test_initialization(self):
        """Test initialization"""
        identification = MedicationIdentification(medication_name="Advil")
        response = CombinedResponse(identification=identification)
        
        self.assertEqual(response.identification, identification)
        self.assertEqual(response.drug_info, {})
        self.assertEqual(response.processing_time, 0.0)
        self.assertTrue(response.success)
        self.assertEqual(response.error_message, "")
        self.assertEqual(response.metadata, {})
    
    def test_add_metadata(self):
        """Test adding metadata"""
        identification = MedicationIdentification(medication_name="Advil")
        response = CombinedResponse(identification=identification)
        
        response.add_metadata("test_key", "test_value")
        response.add_metadata("confidence_level", "high")
        
        self.assertEqual(response.metadata["test_key"], "test_value")
        self.assertEqual(response.metadata["confidence_level"], "high")
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        identification = MedicationIdentification(medication_name="Advil", confidence=0.9)
        response = CombinedResponse(
            identification=identification,
            processing_time=2.5,
            success=True
        )
        
        result = response.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['processing_time'], 2.5)
        self.assertIsInstance(result['identification'], dict)
        self.assertEqual(result['identification']['medication_name'], "Advil")

class TestExceptionClasses(unittest.TestCase):
    """Test custom exception classes"""
    
    def test_image_analysis_error(self):
        """Test base ImageAnalysisError"""
        error = ImageAnalysisError("Test error")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test error")
    
    def test_image_validation_error(self):
        """Test ImageValidationError inheritance"""
        error = ImageValidationError("Validation failed")
        self.assertIsInstance(error, ImageAnalysisError)
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Validation failed")
    
    def test_vision_model_error(self):
        """Test VisionModelError inheritance"""
        error = VisionModelError("Vision model failed")
        self.assertIsInstance(error, ImageAnalysisError)
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Vision model failed")
    
    def test_drug_info_error(self):
        """Test DrugInfoError inheritance"""
        error = DrugInfoError("Drug info failed")
        self.assertIsInstance(error, ImageAnalysisError)
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Drug info failed")

class TestDataModelIntegration(unittest.TestCase):
    """Integration tests for data models"""
    
    def test_complete_workflow_data_flow(self):
        """Test data flow through complete workflow"""
        # Create request
        request = ImageAnalysisRequest(
            image_data="test_image_data",
            prompt="Identify medication"
        )
        
        # Create validation result
        validation = ImageValidationResult(
            valid=True,
            size=1024,
            format_detected="jpeg"
        )
        
        # Create identification
        identification = MedicationIdentification(
            medication_name="Advil",
            dosage="200mg",
            confidence=0.9,
            image_quality=ImageQuality.GOOD.value
        )
        
        # Create vision response
        vision_response = VisionModelResponse(
            success=True,
            response_text="Identified Advil 200mg",
            processing_time=1.5
        )
        
        # Create drug info result
        drug_info = DrugInfoResult(
            success=True,
            data={'brand_name': 'Advil', 'generic_name': 'Ibuprofen'}
        )
        
        # Create combined response
        combined = CombinedResponse(
            identification=identification,
            drug_info=drug_info.data,
            processing_time=2.0,
            success=True
        )
        
        # Verify all components work together
        self.assertTrue(validation.valid)
        self.assertTrue(identification.is_high_confidence())
        self.assertTrue(identification.has_valid_identification())
        self.assertTrue(vision_response.success)
        self.assertTrue(drug_info.success)
        self.assertTrue(combined.success)
        
        # Test serialization
        request_dict = request.to_dict()
        validation_dict = validation.to_dict()
        identification_dict = identification.to_dict()
        vision_dict = vision_response.to_dict()
        drug_dict = drug_info.to_dict()
        combined_dict = combined.to_dict()
        
        # Verify all can be serialized
        self.assertIsInstance(request_dict, dict)
        self.assertIsInstance(validation_dict, dict)
        self.assertIsInstance(identification_dict, dict)
        self.assertIsInstance(vision_dict, dict)
        self.assertIsInstance(drug_dict, dict)
        self.assertIsInstance(combined_dict, dict)

if __name__ == '__main__':
    unittest.main(verbosity=2)