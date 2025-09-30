"""
Unit tests for response synthesis module
"""

import json
import pytest
from datetime import datetime
from response_synthesis import (
    validate_vision_results,
    validate_drug_info,
    sanitize_text,
    format_confidence_level,
    create_identification_summary,
    format_drug_information,
    create_user_friendly_response,
    combine_results,
    format_bedrock_response,
    create_error_response,
    ResponseSynthesisError
)


class TestValidationFunctions:
    """Test cases for validation functions"""
    
    def test_validate_vision_results_valid(self):
        """Test validation of valid vision results"""
        valid_results = {
            'medication_name': 'Advil',
            'confidence': 0.85,
            'dosage': '200mg'
        }
        assert validate_vision_results(valid_results) is True
    
    def test_validate_vision_results_invalid(self):
        """Test validation of invalid vision results"""
        assert validate_vision_results({}) is False
        assert validate_vision_results({'medication_name': 'Advil'}) is False
        assert validate_vision_results({'confidence': 0.85}) is False
        assert validate_vision_results("not a dict") is False
    
    def test_validate_drug_info_successful(self):
        """Test validation of successful drug info"""
        valid_info = {
            'success': True,
            'drug_info': {
                'brand_name': 'Advil',
                'generic_name': 'Ibuprofen'
            }
        }
        assert validate_drug_info(valid_info) is True
    
    def test_validate_drug_info_error(self):
        """Test validation of error drug info"""
        error_info = {
            'success': False,
            'error': 'Drug not found'
        }
        assert validate_drug_info(error_info) is True
    
    def test_validate_drug_info_invalid(self):
        """Test validation of invalid drug info"""
        assert validate_drug_info({}) is False
        assert validate_drug_info("not a dict") is False


class TestTextSanitization:
    """Test cases for text sanitization"""
    
    def test_sanitize_text_normal(self):
        """Test normal text sanitization"""
        result = sanitize_text("Normal text")
        assert result == "Normal text"
    
    def test_sanitize_text_with_whitespace(self):
        """Test text sanitization with whitespace"""
        result = sanitize_text("  Text with spaces  ")
        assert result == "Text with spaces"
    
    def test_sanitize_text_too_long(self):
        """Test text sanitization with length limit"""
        long_text = "A" * 1500
        result = sanitize_text(long_text, 100)
        assert len(result) == 100
        assert result.endswith("...")
    
    def test_sanitize_text_invalid_input(self):
        """Test text sanitization with invalid input"""
        assert sanitize_text(None) == "Not available"
        assert sanitize_text(123) == "Not available"
        assert sanitize_text("") == "Not available"


class TestConfidenceFormatting:
    """Test cases for confidence level formatting"""
    
    def test_format_confidence_levels(self):
        """Test all confidence level ranges"""
        assert format_confidence_level(0.95) == "Very High"
        assert format_confidence_level(0.85) == "High"
        assert format_confidence_level(0.75) == "Good"
        assert format_confidence_level(0.65) == "Moderate"
        assert format_confidence_level(0.55) == "Low"
        assert format_confidence_level(0.45) == "Very Low"
        assert format_confidence_level(0.0) == "Very Low"


class TestIdentificationSummary:
    """Test cases for identification summary creation"""
    
    def test_create_identification_summary_complete(self):
        """Test creating summary with complete vision results"""
        vision_results = {
            'medication_name': 'Advil',
            'confidence': 0.85,
            'dosage': '200mg',
            'image_quality': 'good',
            'alternative_names': ['Ibuprofen', 'Motrin']
        }
        
        summary = create_identification_summary(vision_results)
        
        assert summary['identified_medication'] == 'Advil'
        assert summary['dosage'] == '200mg'
        assert summary['confidence_score'] == 0.85
        assert summary['confidence_level'] == 'High'
        assert summary['image_quality'] == 'good'
        assert 'alternative_names' in summary
        assert len(summary['alternative_names']) == 2
    
    def test_create_identification_summary_minimal(self):
        """Test creating summary with minimal vision results"""
        vision_results = {
            'medication_name': 'Unknown Drug',
            'confidence': 0.3
        }
        
        summary = create_identification_summary(vision_results)
        
        assert summary['identified_medication'] == 'Unknown Drug'
        assert summary['dosage'] == 'Not specified'
        assert summary['confidence_score'] == 0.3
        assert summary['confidence_level'] == 'Very Low'
    
    def test_create_identification_summary_error(self):
        """Test error handling in summary creation"""
        # This should handle the error gracefully
        summary = create_identification_summary({})
        
        # The function handles missing data gracefully by providing defaults
        assert summary['identified_medication'] == 'Unknown'
        assert summary['confidence_score'] == 0.0
        assert summary['confidence_level'] == 'Very Low'


class TestDrugInformationFormatting:
    """Test cases for drug information formatting"""
    
    def test_format_drug_information_successful(self):
        """Test formatting successful drug information"""
        drug_info = {
            'success': True,
            'drug_info': {
                'brand_name': 'Advil',
                'generic_name': 'Ibuprofen',
                'purpose': 'Pain reliever/fever reducer',
                'warnings': 'Do not exceed recommended dose',
                'indications_and_usage': 'For temporary relief of minor aches'
            }
        }
        
        formatted = format_drug_information(drug_info)
        
        assert formatted['available'] is True
        assert formatted['brand_name'] == 'Advil'
        assert formatted['generic_name'] == 'Ibuprofen'
        assert formatted['purpose'] == 'Pain reliever/fever reducer'
        assert formatted['warnings'] == 'Do not exceed recommended dose'
    
    def test_format_drug_information_error(self):
        """Test formatting error drug information"""
        drug_info = {
            'success': False,
            'error': 'Drug not found',
            'suggestion': 'Try generic name',
            'user_message': 'Could not find drug information'
        }
        
        formatted = format_drug_information(drug_info)
        
        assert formatted['available'] is False
        assert formatted['error'] == 'Drug not found'
        assert formatted['suggestion'] == 'Try generic name'
        assert formatted['user_message'] == 'Could not find drug information'


class TestUserFriendlyResponse:
    """Test cases for user-friendly response creation"""
    
    def test_create_user_friendly_response_high_confidence(self):
        """Test user response with high confidence identification"""
        identification = {
            'identified_medication': 'Advil',
            'confidence_level': 'High',
            'dosage': '200mg'
        }
        
        drug_info = {
            'available': True,
            'brand_name': 'Advil',
            'generic_name': 'Ibuprofen',
            'purpose': 'Pain reliever/fever reducer',
            'warnings': 'Do not exceed recommended dose'
        }
        
        response = create_user_friendly_response(identification, drug_info)
        
        assert 'Advil (200mg)' in response
        assert 'high confidence' in response
        assert 'Pain reliever/fever reducer' in response
        assert '⚠️ Important Warnings' in response
    
    def test_create_user_friendly_response_low_confidence(self):
        """Test user response with low confidence identification"""
        identification = {
            'identified_medication': 'Unknown Drug',
            'confidence_level': 'Low',
            'dosage': 'Not specified'
        }
        
        drug_info = {
            'available': False,
            'error': 'Drug not found'
        }
        
        response = create_user_friendly_response(identification, drug_info)
        
        assert 'not very confident' in response
        assert 'retake the photo' in response
        assert 'Drug not found' in response
    
    def test_create_user_friendly_response_no_drug_info(self):
        """Test user response when drug info is unavailable"""
        identification = {
            'identified_medication': 'Advil',
            'confidence_level': 'High',
            'dosage': '200mg'
        }
        
        drug_info = {
            'available': False,
            'user_message': 'Drug information service unavailable'
        }
        
        response = create_user_friendly_response(identification, drug_info)
        
        assert 'Advil (200mg)' in response
        assert 'high confidence' in response
        assert "couldn't retrieve detailed drug information" in response
        assert 'Drug information service unavailable' in response


class TestCombineResults:
    """Test cases for combining results"""
    
    def test_combine_results_successful(self):
        """Test successful combination of results"""
        vision_results = {
            'medication_name': 'Advil',
            'confidence': 0.85,
            'dosage': '200mg',
            'image_quality': 'good'
        }
        
        drug_info = {
            'success': True,
            'drug_info': {
                'brand_name': 'Advil',
                'generic_name': 'Ibuprofen',
                'purpose': 'Pain reliever',
                'warnings': 'Do not exceed dose',
                'indications_and_usage': 'For pain relief'
            }
        }
        
        result = combine_results(vision_results, drug_info)
        
        assert result['success'] is True
        assert 'timestamp' in result
        assert 'identification' in result
        assert 'drug_information' in result
        assert 'user_response' in result
        assert 'processing_metadata' in result
        
        assert result['identification']['identified_medication'] == 'Advil'
        assert result['drug_information']['available'] is True
        assert 'Advil' in result['user_response']
    
    def test_combine_results_low_confidence(self):
        """Test combination with low confidence results"""
        vision_results = {
            'medication_name': 'Unknown',
            'confidence': 0.3,
            'image_quality': 'poor'
        }
        
        drug_info = {
            'success': False,
            'error': 'Drug not found'
        }
        
        result = combine_results(vision_results, drug_info)
        
        assert result['success'] is True
        assert 'warnings' in result
        assert 'Low confidence identification' in result['warnings'][0]
        assert 'Drug information not available' in result['warnings'][1]
    
    def test_combine_results_invalid_input(self):
        """Test error handling with invalid inputs"""
        with pytest.raises(ResponseSynthesisError):
            combine_results({}, {'success': True})
        
        with pytest.raises(ResponseSynthesisError):
            combine_results({'medication_name': 'Test', 'confidence': 0.8}, {})


class TestBedrockResponseFormatting:
    """Test cases for Bedrock response formatting"""
    
    def test_format_bedrock_response_successful(self):
        """Test formatting successful Bedrock response"""
        combined_results = {
            'success': True,
            'identification': {
                'identified_medication': 'Advil',
                'confidence_score': 0.85,
                'confidence_level': 'High'
            },
            'drug_information': {
                'available': True,
                'brand_name': 'Advil',
                'generic_name': 'Ibuprofen',
                'purpose': 'Pain reliever',
                'warnings': 'Do not exceed dose',
                'indications_and_usage': 'For pain relief'
            },
            'user_response': 'I identified this medication as Advil with high confidence.'
        }
        
        original_event = {
            'actionGroup': 'test_group',
            'apiPath': '/test-path',
            'httpMethod': 'POST'
        }
        
        response = format_bedrock_response(combined_results, original_event)
        
        assert response['messageVersion'] == '1.0'
        assert response['response']['actionGroup'] == 'test_group'
        assert response['response']['httpStatusCode'] == 200
        
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['success'] is True
        assert body['medication_name'] == 'Advil'
        assert body['confidence'] == 0.85
        assert body['drug_info_available'] is True
        assert 'drug_info' in body
    
    def test_format_bedrock_response_error(self):
        """Test formatting Bedrock response with error"""
        # Simulate an error in formatting
        combined_results = None  # This will cause an error
        
        original_event = {
            'actionGroup': 'test_group',
            'apiPath': '/test-path',
            'httpMethod': 'POST'
        }
        
        response = format_bedrock_response(combined_results, original_event)
        
        assert response['response']['httpStatusCode'] == 500
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['success'] is False
        assert 'error' in body


class TestErrorResponse:
    """Test cases for error response creation"""
    
    def test_create_error_response_processing_error(self):
        """Test creating processing error response"""
        original_event = {
            'actionGroup': 'test_group',
            'apiPath': '/test-path',
            'httpMethod': 'POST'
        }
        
        response = create_error_response("Test error", original_event, "processing_error")
        
        assert response['response']['httpStatusCode'] == 400
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['success'] is False
        assert body['error'] == "Test error"
        assert body['error_type'] == "processing_error"
        assert 'timestamp' in body
    
    def test_create_error_response_vision_error(self):
        """Test creating vision error response"""
        original_event = {}
        
        response = create_error_response("Vision failed", original_event, "vision_error")
        
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['error_type'] == "vision_error"
        assert "Unable to analyze" in body['user_response']


# Integration test fixtures
@pytest.fixture
def sample_vision_results():
    """Sample vision results for testing"""
    return {
        'medication_name': 'Advil',
        'confidence': 0.85,
        'dosage': '200mg',
        'image_quality': 'good',
        'alternative_names': ['Ibuprofen']
    }


@pytest.fixture
def sample_drug_info_success():
    """Sample successful drug info for testing"""
    return {
        'success': True,
        'drug_info': {
            'brand_name': 'Advil',
            'generic_name': 'Ibuprofen',
            'purpose': 'Pain reliever/fever reducer',
            'warnings': 'Do not exceed recommended dose',
            'indications_and_usage': 'For temporary relief of minor aches'
        }
    }


@pytest.fixture
def sample_drug_info_error():
    """Sample error drug info for testing"""
    return {
        'success': False,
        'error': 'Drug not found in database',
        'suggestion': 'Try using generic name',
        'user_message': 'Could not find detailed information for this medication'
    }


class TestIntegrationScenarios:
    """Integration test scenarios"""
    
    def test_end_to_end_successful_flow(self, sample_vision_results, sample_drug_info_success):
        """Test complete end-to-end successful flow"""
        original_event = {
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
        
        # Combine results
        combined = combine_results(sample_vision_results, sample_drug_info_success, original_event)
        
        # Format for Bedrock
        bedrock_response = format_bedrock_response(combined, original_event)
        
        # Verify complete response
        assert bedrock_response['response']['httpStatusCode'] == 200
        body = json.loads(bedrock_response['response']['responseBody']['application/json']['body'])
        
        assert body['success'] is True
        assert body['medication_name'] == 'Advil'
        assert body['confidence'] == 0.85
        assert body['drug_info_available'] is True
        assert 'Advil' in body['user_response']
        assert 'high confidence' in body['user_response']
    
    def test_end_to_end_error_flow(self, sample_vision_results, sample_drug_info_error):
        """Test complete end-to-end error handling flow"""
        original_event = {
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/analyze-medication',
            'httpMethod': 'POST'
        }
        
        # Combine results with error
        combined = combine_results(sample_vision_results, sample_drug_info_error, original_event)
        
        # Format for Bedrock
        bedrock_response = format_bedrock_response(combined, original_event)
        
        # Verify error handling
        assert bedrock_response['response']['httpStatusCode'] == 200
        body = json.loads(bedrock_response['response']['responseBody']['application/json']['body'])
        
        assert body['success'] is True  # Vision succeeded
        assert body['medication_name'] == 'Advil'
        assert body['drug_info_available'] is False
        assert "couldn't retrieve detailed drug information" in body['user_response']


if __name__ == '__main__':
    pytest.main([__file__])