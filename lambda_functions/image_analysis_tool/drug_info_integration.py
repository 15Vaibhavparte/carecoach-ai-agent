"""
DrugInfoTool Integration Module

This module provides functions to integrate with the existing DrugInfoTool lambda handler
to retrieve comprehensive drug information after medication identification from images.
"""

import json
import logging
import sys
import os
from typing import Dict, Any, Optional, Union

# Add the parent directory to the path to import drug_info_tool
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from drug_info_tool.app import lambda_handler as drug_info_handler, build_response

logger = logging.getLogger(__name__)


class DrugInfoIntegrationError(Exception):
    """Custom exception for drug info integration errors"""
    pass


def format_drug_info_event(drug_name: str, original_event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format an event for DrugInfoTool compatibility.
    
    Args:
        drug_name: The medication name to look up
        original_event: Original event context for maintaining consistency
        
    Returns:
        Formatted event dictionary for DrugInfoTool
    """
    if not drug_name or not isinstance(drug_name, str):
        raise DrugInfoIntegrationError("Drug name must be a non-empty string")
    
    # Clean and validate drug name
    drug_name = drug_name.strip()
    if len(drug_name) < 2:
        raise DrugInfoIntegrationError("Drug name must be at least 2 characters long")
    
    # Create event in the format that DrugInfoTool expects
    # Based on the DrugInfoTool code, it supports multiple formats
    event = {
        'input': {
            'RequestBody': {
                'content': {
                    'application/json': {
                        'properties': [
                            {
                                'name': 'drug_name',
                                'value': drug_name
                            }
                        ]
                    }
                }
            }
        },
        # Also include fallback formats
        'parameters': [
            {
                'name': 'drug_name',
                'value': drug_name
            }
        ],
        'requestBody': {
            'drug_name': drug_name
        },
        'drug_name': drug_name
    }
    
    # Preserve original event context if provided
    if original_event:
        event.update({
            'actionGroup': original_event.get('actionGroup', 'image_analysis_tool'),
            'apiPath': original_event.get('apiPath', '/drug-info'),
            'httpMethod': original_event.get('httpMethod', 'POST')
        })
    else:
        event.update({
            'actionGroup': 'image_analysis_tool',
            'apiPath': '/drug-info',
            'httpMethod': 'POST'
        })
    
    logger.debug(f"Formatted event for drug '{drug_name}': {json.dumps(event, indent=2)}")
    return event


def call_drug_info_tool(drug_name: str, original_event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Call the existing DrugInfoTool lambda handler to get drug information.
    
    Args:
        drug_name: The medication name to look up
        original_event: Original event context for maintaining consistency
        
    Returns:
        Drug information response from DrugInfoTool
        
    Raises:
        DrugInfoIntegrationError: If the call fails or returns invalid data
    """
    try:
        # Format the event for DrugInfoTool
        event = format_drug_info_event(drug_name, original_event)
        
        # Create a mock context object (DrugInfoTool doesn't use it extensively)
        class MockContext:
            def __init__(self):
                self.function_name = 'image_analysis_tool'
                self.function_version = '$LATEST'
                self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:image_analysis_tool'
                self.memory_limit_in_mb = 128
                self.remaining_time_in_millis = lambda: 30000
        
        context = MockContext()
        
        logger.info(f"Calling DrugInfoTool for drug: {drug_name}")
        
        # Call the DrugInfoTool handler
        response = drug_info_handler(event, context)
        
        logger.debug(f"DrugInfoTool response: {json.dumps(response, indent=2)}")
        
        # Validate response structure
        if not isinstance(response, dict):
            raise DrugInfoIntegrationError("Invalid response format from DrugInfoTool")
        
        return response
        
    except Exception as e:
        logger.error(f"Error calling DrugInfoTool for drug '{drug_name}': {str(e)}")
        raise DrugInfoIntegrationError(f"Failed to retrieve drug information: {str(e)}")


def parse_drug_info_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the response from DrugInfoTool and extract relevant information.
    
    Args:
        response: Raw response from DrugInfoTool
        
    Returns:
        Parsed drug information dictionary
        
    Raises:
        DrugInfoIntegrationError: If response parsing fails
    """
    try:
        # Extract the response body from the Bedrock Agent format
        response_body = response.get('response', {}).get('responseBody', {})
        json_body = response_body.get('application/json', {})
        body_str = json_body.get('body', '{}')
        
        # Parse the JSON body
        if isinstance(body_str, str):
            drug_data = json.loads(body_str)
        else:
            drug_data = body_str
        
        logger.debug(f"Parsed drug data: {json.dumps(drug_data, indent=2)}")
        
        # Check for errors in the response
        if 'error' in drug_data:
            error_msg = drug_data['error']
            logger.warning(f"DrugInfoTool returned error: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'suggestion': drug_data.get('suggestion', ''),
                'drug_info': None
            }
        
        # Extract drug information
        drug_info = {
            'success': True,
            'error': None,
            'drug_info': {
                'brand_name': drug_data.get('brand_name', 'N/A'),
                'generic_name': drug_data.get('generic_name', 'N/A'),
                'purpose': drug_data.get('purpose', 'Not available'),
                'warnings': drug_data.get('warnings', 'Not available'),
                'indications_and_usage': drug_data.get('indications_and_usage', 'Not available')
            }
        }
        
        # Handle special case where response contains warnings directly
        if 'warnings' in drug_data and 'response' in drug_data:
            drug_info['drug_info']['warnings'] = drug_data['warnings']
        
        return drug_info
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        raise DrugInfoIntegrationError(f"Invalid JSON in DrugInfoTool response: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing DrugInfoTool response: {str(e)}")
        raise DrugInfoIntegrationError(f"Failed to parse drug information: {str(e)}")


def get_drug_information(drug_name: str, original_event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    High-level function to get drug information for a medication name.
    
    This function handles the complete flow of calling DrugInfoTool and parsing the response.
    
    Args:
        drug_name: The medication name to look up
        original_event: Original event context for maintaining consistency
        
    Returns:
        Dictionary containing drug information or error details
    """
    try:
        # Input validation
        if not drug_name or not isinstance(drug_name, str):
            return {
                'success': False,
                'error': 'Invalid drug name provided',
                'drug_info': None
            }
        
        # Clean drug name
        drug_name = drug_name.strip()
        if len(drug_name) < 2:
            return {
                'success': False,
                'error': 'Drug name must be at least 2 characters long',
                'drug_info': None
            }
        
        logger.info(f"Getting drug information for: {drug_name}")
        
        # Call DrugInfoTool
        response = call_drug_info_tool(drug_name, original_event)
        
        # Parse response
        parsed_info = parse_drug_info_response(response)
        
        logger.info(f"Successfully retrieved drug information for: {drug_name}")
        return parsed_info
        
    except DrugInfoIntegrationError as e:
        logger.error(f"DrugInfoIntegration error for '{drug_name}': {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'drug_info': None
        }
    except Exception as e:
        logger.error(f"Unexpected error getting drug info for '{drug_name}': {str(e)}")
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'drug_info': None
        }


def handle_drug_info_errors(error_response: Dict[str, Any], drug_name: str) -> Dict[str, Any]:
    """
    Handle and format errors from drug information lookup.
    
    Args:
        error_response: Error response from drug info lookup
        drug_name: Original drug name that was searched
        
    Returns:
        Formatted error response with user-friendly messages
    """
    error_msg = error_response.get('error', 'Unknown error occurred')
    
    # Provide user-friendly error messages and suggestions
    if 'not found' in error_msg.lower() or 'no information found' in error_msg.lower():
        return {
            'success': False,
            'error': f"No information found for '{drug_name}'",
            'suggestion': "Try using the generic name or check the spelling",
            'user_message': f"I couldn't find detailed information for '{drug_name}' in the FDA database. This might be because it's spelled differently or it's not in the database.",
            'drug_info': None
        }
    elif 'api request failed' in error_msg.lower():
        return {
            'success': False,
            'error': 'Drug information service temporarily unavailable',
            'suggestion': 'Please try again in a few moments',
            'user_message': 'The drug information service is temporarily unavailable. Please try again later.',
            'drug_info': None
        }
    else:
        return {
            'success': False,
            'error': error_msg,
            'suggestion': 'Please try again or contact support if the issue persists',
            'user_message': f'There was an issue retrieving drug information: {error_msg}',
            'drug_info': None
        }