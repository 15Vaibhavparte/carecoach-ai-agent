"""
Additional unit tests for medication extraction logic.
Tests advanced parsing scenarios and edge cases.
"""

import unittest
from vision_client import MedicationExtractor
from models import MedicationIdentification, ImageQuality

class TestAdvancedMedicationExtraction(unittest.TestCase):
    """Advanced test cases for medication extraction logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.extractor = MedicationExtractor()
    
    def test_complex_medication_response(self):
        """Test extraction from complex, realistic vision model response"""
        response = """
        Based on my analysis of this medication image, I can provide the following information:
        
        **Medication Identification:**
        - Brand name: Advil
        - Generic name: Ibuprofen
        - Manufacturer: Pfizer
        
        **Dosage Information:**
        - Strength: 200mg
        - Form: Tablet
        - Quantity visible: Multiple tablets in bottle
        
        **Visual Characteristics:**
        - Color: Brown/orange coating
        - Shape: Oval tablets
        - Markings: "ADVIL" imprinted on tablets
        
        **Image Quality Assessment:**
        - Clarity: Good - image is clear and well-lit
        - All text is clearly readable
        
        **Confidence Assessment:**
        - Overall confidence: High (90% confident)
        - The brand name "Advil" is clearly visible on both packaging and tablets
        - Dosage "200mg" is clearly printed on the label
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "Advil")
        self.assertEqual(result.dosage, "200mg")
        self.assertEqual(result.confidence, 0.9)
        self.assertEqual(result.image_quality, ImageQuality.GOOD.value)
        self.assertIn("Ibuprofen", result.alternative_names)
    
    def test_partial_identification_response(self):
        """Test extraction when only partial information is available"""
        response = """
        I can see this is a medication bottle, but the image quality makes it challenging to read all details clearly.
        
        What I can determine:
        - This appears to be Tylenol based on the visible packaging colors and partial text
        - The dosage seems to be 500mg, though this is somewhat unclear
        - Moderate confidence in this identification due to image limitations
        
        The image has fair quality - some text is readable but other parts are blurry.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "Tylenol")
        self.assertEqual(result.dosage, "500mg")
        self.assertGreaterEqual(result.confidence, 0.6)
        self.assertLess(result.confidence, 0.8)
        self.assertEqual(result.image_quality, ImageQuality.FAIR.value)
    
    def test_no_medication_detected_response(self):
        """Test extraction when no medication is detected"""
        response = """
        I cannot identify any medication in this image. The image appears to show:
        - Some unclear objects that might be household items
        - No visible medication packaging or pills
        - No readable text that would indicate medication names or dosages
        
        Low confidence - I cannot determine if this contains medication.
        The image quality is poor with insufficient lighting and blur.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "")
        self.assertEqual(result.dosage, "")
        self.assertLessEqual(result.confidence, 0.4)
        self.assertEqual(result.image_quality, ImageQuality.POOR.value)
    
    def test_multiple_medications_response(self):
        """Test extraction when multiple medications are visible"""
        response = """
        I can see multiple medications in this image. Focusing on the most prominent one:
        
        Primary medication (most visible):
        - Medication name: Aspirin
        - Dosage: 325mg
        - This is clearly visible in the foreground
        
        Other medications visible:
        - There appears to be Tylenol in the background
        - Another bottle that might be vitamins
        
        High confidence in the Aspirin identification as it's clearly visible and well-lit.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "Aspirin")
        self.assertEqual(result.dosage, "325mg")
        self.assertGreaterEqual(result.confidence, 0.8)
    
    def test_liquid_medication_response(self):
        """Test extraction for liquid medications"""
        response = """
        This is a liquid medication bottle.
        
        Medication name: Children's Tylenol
        Dosage: 160mg/5ml
        Form: Oral suspension
        
        The label is clearly readable with good image quality.
        High confidence in this identification.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "Children's Tylenol")
        self.assertEqual(result.dosage, "160mg/5ml")
        self.assertGreaterEqual(result.confidence, 0.8)
    
    def test_generic_medication_response(self):
        """Test extraction for generic medications"""
        response = """
        This appears to be a generic medication.
        
        Generic name: Acetaminophen
        Brand name: Not clearly visible, appears to be store brand
        Dosage: 500mg
        
        Moderate confidence - the generic name is clear but brand information is limited.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "Acetaminophen")
        self.assertEqual(result.dosage, "500mg")
        self.assertGreaterEqual(result.confidence, 0.6)
        self.assertLess(result.confidence, 0.8)
    
    def test_prescription_medication_response(self):
        """Test extraction for prescription medications"""
        response = """
        This is a prescription medication bottle.
        
        Medication name: Lisinopril
        Dosage: 10mg
        Form: Tablet
        
        The prescription label is clearly visible with patient information (redacted for privacy).
        High confidence in medication identification.
        Image quality is good with clear text.
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "Lisinopril")
        self.assertEqual(result.dosage, "10mg")
        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertEqual(result.image_quality, ImageQuality.GOOD.value)
    
    def test_confidence_scoring_edge_cases(self):
        """Test confidence scoring for various edge cases"""
        test_cases = [
            ("I am 95% confident this is Advil", 0.95),
            ("75% confidence in this identification", 0.75),
            ("Low confidence identification", 0.3),
            ("High confidence result", 0.9),
            ("Medium confidence assessment", 0.7),
            ("Uncertain about this medication", 0.3),
            ("Clearly visible medication name", 0.9),
            ("Blurry and difficult to read", 0.3),
            ("Appears to be medication", 0.7),
            ("Definite identification", 0.9)
        ]
        
        for response, expected_confidence in test_cases:
            with self.subTest(response=response):
                result = self.extractor.extract_medication_info(response)
                self.assertAlmostEqual(result.confidence, expected_confidence, places=1)
    
    def test_dosage_extraction_variations(self):
        """Test dosage extraction for various formats"""
        test_cases = [
            ("Dosage: 200mg", "200mg"),
            ("Strength: 500mg", "500mg"),
            ("Contains 10mg per tablet", "10mg"),
            ("2.5mg dosage", "2.5mg"),
            ("1000mcg strength", "1000mcg"),
            ("5ml liquid dose", "5ml"),
            ("250mg/5ml concentration", "250mg/5ml"),
            ("10mg/ml solution", "10mg/ml"),
            ("100 units per dose", "100 units"),
            ("0.5mg tablet", "0.5mg")
        ]
        
        for response, expected_dosage in test_cases:
            with self.subTest(response=response):
                result = self.extractor.extract_medication_info(response)
                self.assertEqual(result.dosage, expected_dosage)
    
    def test_medication_name_cleaning(self):
        """Test medication name cleaning and normalization"""
        test_cases = [
            ("Medication name: Advil 200mg tablet", "Advil"),
            ("Brand name: Tylenol Extra Strength", "Tylenol Extra Strength"),
            ("Drug name: Ibuprofen with coating", "Ibuprofen"),
            ("This is Aspirin and other ingredients", "Aspirin"),
            ("Identified as Motrin liquid", "Motrin")
        ]
        
        for response, expected_name in test_cases:
            with self.subTest(response=response):
                result = self.extractor.extract_medication_info(response)
                self.assertEqual(result.medication_name, expected_name)
    
    def test_image_quality_inference_from_confidence(self):
        """Test image quality inference when not explicitly mentioned"""
        test_cases = [
            ("95% confident identification", ImageQuality.GOOD.value),
            ("70% confidence level", ImageQuality.FAIR.value),
            ("25% confidence due to blur", ImageQuality.POOR.value),
            ("High confidence result", ImageQuality.GOOD.value),
            ("Low confidence identification", ImageQuality.POOR.value)
        ]
        
        for response, expected_quality in test_cases:
            with self.subTest(response=response):
                result = self.extractor.extract_medication_info(response)
                self.assertEqual(result.image_quality, expected_quality)
    
    def test_alternative_names_extraction(self):
        """Test extraction of alternative medication names"""
        response = """
        Primary identification:
        Brand name: Advil
        Generic name: Ibuprofen
        Also known as Motrin in some markets
        Alternative: Nurofen (international brand)
        """
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.medication_name, "Advil")
        self.assertIn("Ibuprofen", result.alternative_names)
        self.assertIn("Motrin", result.alternative_names)
        self.assertIn("Nurofen", result.alternative_names)
    
    def test_raw_response_preservation(self):
        """Test that raw response is preserved for debugging"""
        response = "This is a test response for medication identification."
        
        result = self.extractor.extract_medication_info(response)
        
        self.assertEqual(result.raw_response, response)
    
    def test_has_valid_identification_method(self):
        """Test the has_valid_identification helper method"""
        # Valid identification
        valid_result = MedicationIdentification(
            medication_name="Advil",
            dosage="200mg",
            confidence=0.9
        )
        self.assertTrue(valid_result.has_valid_identification())
        
        # Invalid identifications
        invalid_cases = [
            MedicationIdentification(medication_name="", dosage="200mg"),
            MedicationIdentification(medication_name="unknown", dosage="200mg"),
            MedicationIdentification(medication_name="not found", dosage="200mg"),
            MedicationIdentification(medication_name="Unknown", dosage="200mg")
        ]
        
        for invalid_result in invalid_cases:
            with self.subTest(medication_name=invalid_result.medication_name):
                self.assertFalse(invalid_result.has_valid_identification())
    
    def test_is_high_confidence_method(self):
        """Test the is_high_confidence helper method"""
        # Test with default threshold (0.8)
        high_confidence = MedicationIdentification(medication_name="Test", confidence=0.9)
        medium_confidence = MedicationIdentification(medication_name="Test", confidence=0.7)
        
        self.assertTrue(high_confidence.is_high_confidence())
        self.assertFalse(medium_confidence.is_high_confidence())
        
        # Test with custom threshold
        self.assertTrue(medium_confidence.is_high_confidence(threshold=0.6))
        self.assertFalse(medium_confidence.is_high_confidence(threshold=0.8))

if __name__ == '__main__':
    unittest.main()