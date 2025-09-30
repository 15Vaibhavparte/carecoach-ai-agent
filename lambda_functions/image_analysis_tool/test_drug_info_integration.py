"""
Unit tests for DrugInfoTool integration module
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from drug_info_integration import (
    format_drug_info_event,
    call_drug_info_tool,
    parse_drug_info_response,
    get_drug_information,
    handle_drug_info_errors,
    DrugInfoIntegrationError
)


class TestFormatDrugInfoEvent:
    """Test cases for format_drug_info_event function"""
    
    def test_format_basic_event(self):
        """Test basic event formatting with drug name"""
        drug_name = "Advil"
        event = format_drug_info_event(drug_name)
        
        # Check main structure
        assert 'input' in event
        assert 'RequestBody' in event['input']
        assert 'content' in event['input']['RequestBody']
        assert 'application/json' in event['input']['RequestBody']['content']
        assert 'properties' in event['input']['RequestBody']['content']['application/json']
        
        # Check properties array
        properties = event['input']['RequestBody']['content']['application/json']['properties']
        assert len(properties) == 1
        assert properties[0]['name'] == 'drug_name'
        assert properties[0]['value'] == 'Advil'
        
        # Check fallback formats
        assert event['parameters'][0]['name'] == 'drug_name'
        assert event['parameters'][0]['value'] == 'Advil'
        assert event['requestBody']['drug_name'] == 'Advil'
        assert event['drug_name'] == 'Advil'
    
    def test_format_event_with_original_context(self):
        """Test event formatting with original event context"""
        drug_name = "Tylenol"
        original_event = {
            'actionGroup': 'test_group',
            'apiPath': '/test-path',
            'httpMethod': 'GET'
        }
        
        event = format_drug_info_event(drug_name, original_event)
        
        assert event['actionGroup'] == 'test_group'
        assert event['apiPath'] == '/test-path'
        assert event['httpMethod'] == 'GET'
    
    def test_format_event_strips_whitespace(self):
        """Test that drug name whitespace is stripped"""
        drug_name = "  Advil  "
        event = format_drug_info_event(drug_name)
        
        properties = event['input']['RequestBody']['content']['application/json']['properties']
        assert properties[0]['value'] == 'Advil'
    
    def test_format_event_invalid_drug_name(self):
        """Test error handling for invalid drug names"""
        with pytest.raises(DrugInfoIntegrationError):
            format_drug_info_event("")
        
        with pytest.raises(DrugInfoIntegrationError):
            format_drug_info_event(None)
        
        with pytest.raises(DrugInfoIntegrationError):
            format_drug_info_event("A")  # Too short


class TestCallDrugInfoTool:
    """Test cases for call_drug_info_tool function"""
    
    @patch('drug_info_integration.drug_info_handler')
    def test_successful_call(self, mock_handler):
        """Test successful call to DrugInfoTool"""
        # Mock successful response
        mock_response = {
            'response': {
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'brand_name': 'Advil',
                            'generic_name': 'Ibuprofen',
                            'purpose': 'Pain reliever'
                        })
                    }
                }
            }
        }
        mock_handler.return_value = mock_response
        
        result = call_drug_info_tool("Advil")
        
        assert result == mock_response
        mock_handler.assert_called_once()
    
    @patch('drug_info_integration.drug_info_handler')
    def test_call_with_exception(self, mock_handler):
        """Test handling of exceptions from DrugInfoTool"""
        mock_handler.side_effect = Exception("API Error")
        
        with pytest.raises(DrugInfoIntegrationError) as exc_info:
            call_drug_info_tool("Advil")
        
        assert "Failed to retrieve drug information" in str(exc_info.value)


class TestParseDrugInfoResponse:
    """Test cases for parse_drug_info_response function"""
    
    def test_parse_successful_response(self):
        """Test parsing successful drug info response"""
        response = {
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
        
        result = parse_drug_info_response(response)
        
        assert result['success'] is True
        assert result['error'] is None
        assert result['drug_info']['brand_name'] == 'Advil'
        assert result['drug_info']['generic_name'] == 'Ibuprofen'
        assert result['drug_info']['purpose'] == 'Pain reliever/fever reducer'
        assert result['drug_info']['warnings'] == 'Do not exceed recommended dose'
    
    def test_parse_error_response(self):
        """Test parsing error response from DrugInfoTool"""
        response = {
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
        
        result = parse_drug_info_response(response)
        
        assert result['success'] is False
        assert result['error'] == 'No information found for drug'
        assert result['suggestion'] == 'Try using generic name'
        assert result['drug_info'] is None
    
    def test_parse_warnings_response(self):
        """Test parsing response with warnings format"""
        response = {
            'response': {
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'response': 'Here are the warnings for Advil:',
                            'warnings': 'Do not exceed recommended dose'
                        })
                    }
                }
            }
        }
        
        result = parse_drug_info_response(response)
        
        assert result['success'] is True
        assert result['drug_info']['warnings'] == 'Do not exceed recommended dose'
    
    def test_parse_invalid_json(self):
        """Test handling of invalid JSON response"""
        response = {
            'response': {
                'responseBody': {
                    'application/json': {
                        'body': 'invalid json{'
                    }
                }
            }
        }
        
        with pytest.raises(DrugInfoIntegrationError) as exc_info:
            parse_drug_info_response(response)
        
        assert "Invalid JSON" in str(exc_info.value)


class TestGetDrugInformation:
    """Test cases for get_drug_information function"""
    
    @patch('drug_info_integration.call_drug_info_tool')
    @patch('drug_info_integration.parse_drug_info_response')
    def test_successful_drug_lookup(self, mock_parse, mock_call):
        """Test successful drug information lookup"""
        # Mock successful call and parse
        mock_call.return_value = {'mock': 'response'}
        mock_parse.return_value = {
            'success': True,
            'error': None,
            'drug_info': {
                'brand_name': 'Advil',
                'generic_name': 'Ibuprofen'
            }
        }
        
        result = get_drug_information("Advil")
        
        assert result['success'] is True
        assert result['drug_info']['brand_name'] == 'Advil'
        mock_call.assert_called_once_with("Advil", None)
        mock_parse.assert_called_once_with({'mock': 'response'})
    
    def test_invalid_drug_name(self):
        """Test handling of invalid drug names"""
        result = get_drug_information("")
        assert result['success'] is False
        assert 'Invalid drug name' in result['error']
        
        result = get_drug_information(None)
        assert result['success'] is False
        assert 'Invalid drug name' in result['error']
        
        result = get_drug_information("A")
        assert result['success'] is False
        assert 'at least 2 characters' in result['error']
    
    @patch('drug_info_integration.call_drug_info_tool')
    def test_drug_lookup_exception(self, mock_call):
        """Test handling of exceptions during drug lookup"""
        mock_call.side_effect = DrugInfoIntegrationError("API Error")
        
        result = get_drug_information("Advil")
        
        assert result['success'] is False
        assert result['error'] == "API Error"
        assert result['drug_info'] is None


class TestHandleDrugInfoErrors:
    """Test cases for handle_drug_info_errors function"""
    
    def test_handle_not_found_error(self):
        """Test handling of 'not found' errors"""
        error_response = {'error': 'No information found for drug'}
        result = handle_drug_info_errors(error_response, "TestDrug")
        
        assert result['success'] is False
        assert "No information found for 'TestDrug'" in result['error']
        assert "generic name" in result['suggestion']
        assert "couldn't find detailed information" in result['user_message']
    
    def test_handle_api_error(self):
        """Test handling of API request errors"""
        error_response = {'error': 'API request failed: timeout'}
        result = handle_drug_info_errors(error_response, "TestDrug")
        
        assert result['success'] is False
        assert 'temporarily unavailable' in result['error']
        assert 'try again' in result['suggestion']
        assert 'temporarily unavailable' in result['user_message']
    
    def test_handle_generic_error(self):
        """Test handling of generic errors"""
        error_response = {'error': 'Unknown database error'}
        result = handle_drug_info_errors(error_response, "TestDrug")
        
        assert result['success'] is False
        assert result['error'] == 'Unknown database error'
        assert 'contact support' in result['suggestion']
        assert 'Unknown database error' in result['user_message']


# Integration test fixtures
@pytest.fixture
def sample_drug_response():
    """Sample successful drug response for testing"""
    return {
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


@pytest.fixture
def sample_error_response():
    """Sample error response for testing"""
    return {
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


class TestIntegrationScenarios:
    """Integration test scenarios"""
    
    @patch('drug_info_integration.drug_info_handler')
    def test_end_to_end_successful_lookup(self, mock_handler, sample_drug_response):
        """Test complete end-to-end successful drug lookup"""
        mock_handler.return_value = sample_drug_response
        
        result = get_drug_information("Advil")
        
        assert result['success'] is True
        assert result['drug_info']['brand_name'] == 'Advil'
        assert result['drug_info']['generic_name'] == 'Ibuprofen'
        assert result['drug_info']['purpose'] == 'Pain reliever/fever reducer'
    
    @patch('drug_info_integration.drug_info_handler')
    def test_end_to_end_error_lookup(self, mock_handler, sample_error_response):
        """Test complete end-to-end error handling"""
        mock_handler.return_value = sample_error_response
        
        result = get_drug_information("UnknownDrug")
        
        assert result['success'] is False
        assert result['error'] == 'No information found for drug'
        assert result['suggestion'] == 'Try using generic name'


if __name__ == '__main__':
    pytest.main([__file__])