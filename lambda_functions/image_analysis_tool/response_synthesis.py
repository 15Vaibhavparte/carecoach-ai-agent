"""
Response Synthesis Module

This module provides functions to combine vision analysis results with drug information
to create comprehensive, user-friendly responses for medication identification.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ResponseSynthesisError(Exception):
    """Custom exception for response synthesis errors"""
    pass


def validate_vision_results(vision_results: Dict[str, Any]) -> bool:
    """
    Validate vision analysis results structure.
    
    Args:
        vision_results: Results from vision model analysis
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(vision_results, dict):
        return False
    
    required_fields = ['medication_name', 'confidence']
    return all(field in vision_results for field in required_fields)


def validate_drug_info(drug_info: Dict[str, Any]) -> bool:
    """
    Validate drug information structure.
    
    Args:
        drug_info: Drug information from DrugInfoTool
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(drug_info, dict):
        return False
    
    # Check if it's a successful response
    if drug_info.get('success') is False:
        return True  # Error responses are valid too
    
    # For successful responses, check for drug_info structure
    if 'drug_info' in drug_info and isinstance(drug_info['drug_info'], dict):
        return True
    
    return False


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """
    Sanitize and truncate text for safe display.
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return "Not available"
    
    # Remove any potentially harmful characters
    sanitized = text.strip()
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length-3] + "..."
    
    return sanitized if sanitized else "Not available"


def format_confidence_level(confidence: float) -> str:
    """
    Format confidence level into user-friendly text.
    
    Args:
        confidence: Confidence score (0.0 to 1.0)
        
    Returns:
        User-friendly confidence description
    """
    if confidence >= 0.9:
        return "Very High"
    elif confidence >= 0.8:
        return "High"
    elif confidence >= 0.7:
        return "Good"
    elif confidence >= 0.6:
        return "Moderate"
    elif confidence >= 0.5:
        return "Low"
    else:
        return "Very Low"


def create_identification_summary(vision_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of the medication identification results.
    
    Args:
        vision_results: Results from vision analysis
        
    Returns:
        Formatted identification summary
    """
    try:
        medication_name = sanitize_text(vision_results.get('medication_name', 'Unknown'))
        confidence = vision_results.get('confidence', 0.0)
        dosage = sanitize_text(vision_results.get('dosage', 'Not specified'))
        
        summary = {
            'identified_medication': medication_name,
            'dosage': dosage,
            'confidence_score': confidence,
            'confidence_level': format_confidence_level(confidence),
            'image_quality': vision_results.get('image_quality', 'Unknown')
        }
        
        # Add alternative names if available
        if 'alternative_names' in vision_results:
            alt_names = vision_results['alternative_names']
            if isinstance(alt_names, list) and alt_names:
                summary['alternative_names'] = [sanitize_text(name, 100) for name in alt_names[:3]]
        
        return summary
        
    except Exception as e:
        logger.error(f"Error creating identification summary: {str(e)}")
        return {
            'identified_medication': 'Error processing identification',
            'confidence_score': 0.0,
            'confidence_level': 'Unknown',
            'error': str(e)
        }


def format_drug_information(drug_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format drug information for user-friendly display.
    
    Args:
        drug_info: Drug information from DrugInfoTool
        
    Returns:
        Formatted drug information
    """
    try:
        if not drug_info.get('success', False):
            return {
                'available': False,
                'error': drug_info.get('error', 'Drug information not available'),
                'suggestion': drug_info.get('suggestion', ''),
                'user_message': drug_info.get('user_message', '')
            }
        
        drug_data = drug_info.get('drug_info', {})
        
        formatted_info = {
            'available': True,
            'brand_name': sanitize_text(drug_data.get('brand_name', 'N/A')),
            'generic_name': sanitize_text(drug_data.get('generic_name', 'N/A')),
            'purpose': sanitize_text(drug_data.get('purpose', 'Not available')),
            'warnings': sanitize_text(drug_data.get('warnings', 'Not available'), 2000),
            'indications_and_usage': sanitize_text(drug_data.get('indications_and_usage', 'Not available'), 2000)
        }
        
        return formatted_info
        
    except Exception as e:
        logger.error(f"Error formatting drug information: {str(e)}")
        return {
            'available': False,
            'error': f'Error processing drug information: {str(e)}'
        }


def create_user_friendly_response(identification: Dict[str, Any], drug_info: Dict[str, Any]) -> str:
    """
    Create a user-friendly text response combining identification and drug info.
    
    Args:
        identification: Formatted identification summary
        drug_info: Formatted drug information
        
    Returns:
        User-friendly response text
    """
    try:
        response_parts = []
        
        # Identification section
        medication = identification.get('identified_medication', 'Unknown medication')
        confidence = identification.get('confidence_level', 'Unknown')
        dosage = identification.get('dosage', '')
        
        if confidence in ['Very Low', 'Low']:
            response_parts.append(f"I detected what appears to be {medication}, but I'm not very confident in this identification (confidence: {confidence}).")
            response_parts.append("You may want to retake the photo with better lighting or a clearer view of the medication.")
        else:
            dosage_text = f" ({dosage})" if dosage and dosage != 'Not specified' else ""
            response_parts.append(f"I identified this medication as {medication}{dosage_text} with {confidence.lower()} confidence.")
        
        # Drug information section
        if drug_info.get('available', False):
            brand_name = drug_info.get('brand_name', 'N/A')
            generic_name = drug_info.get('generic_name', 'N/A')
            purpose = drug_info.get('purpose', 'Not available')
            
            if brand_name != 'N/A' and generic_name != 'N/A' and brand_name != generic_name:
                response_parts.append(f"This is {brand_name} (generic name: {generic_name}).")
            elif brand_name != 'N/A':
                response_parts.append(f"This medication is known as {brand_name}.")
            elif generic_name != 'N/A':
                response_parts.append(f"This medication is {generic_name}.")
            
            if purpose and purpose != 'Not available':
                response_parts.append(f"Purpose: {purpose}")
            
            warnings = drug_info.get('warnings', '')
            if warnings and warnings != 'Not available':
                response_parts.append(f"⚠️ Important Warnings: {warnings}")
        else:
            error_msg = drug_info.get('user_message', drug_info.get('error', 'Drug information not available'))
            response_parts.append(f"However, I couldn't retrieve detailed drug information: {error_msg}")
        
        return " ".join(response_parts)
        
    except Exception as e:
        logger.error(f"Error creating user-friendly response: {str(e)}")
        return f"I identified a medication but encountered an error creating the response: {str(e)}"


def combine_results(vision_results: Dict[str, Any], drug_info: Dict[str, Any], 
                   original_event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Combine vision analysis results with drug information into a comprehensive response.
    
    Args:
        vision_results: Results from vision model analysis
        drug_info: Drug information from DrugInfoTool
        original_event: Original event for context
        
    Returns:
        Combined response dictionary
        
    Raises:
        ResponseSynthesisError: If synthesis fails
    """
    try:
        # Validate inputs
        if not validate_vision_results(vision_results):
            raise ResponseSynthesisError("Invalid vision results structure")
        
        if not validate_drug_info(drug_info):
            raise ResponseSynthesisError("Invalid drug information structure")
        
        # Create identification summary
        identification_summary = create_identification_summary(vision_results)
        
        # Format drug information
        formatted_drug_info = format_drug_information(drug_info)
        
        # Create user-friendly response
        user_response = create_user_friendly_response(identification_summary, formatted_drug_info)
        
        # Build comprehensive response
        combined_response = {
            'success': True,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'identification': identification_summary,
            'drug_information': formatted_drug_info,
            'user_response': user_response,
            'processing_metadata': {
                'vision_confidence': vision_results.get('confidence', 0.0),
                'drug_info_available': formatted_drug_info.get('available', False),
                'image_quality': vision_results.get('image_quality', 'Unknown')
            }
        }
        
        # Add any warnings or suggestions
        warnings = []
        
        if identification_summary.get('confidence_score', 0.0) < 0.7:
            warnings.append("Low confidence identification - consider retaking the photo")
        
        if not formatted_drug_info.get('available', False):
            warnings.append("Drug information not available - manual verification recommended")
        
        if warnings:
            combined_response['warnings'] = warnings
        
        logger.info(f"Successfully combined results for medication: {identification_summary.get('identified_medication')}")
        return combined_response
        
    except Exception as e:
        logger.error(f"Error combining results: {str(e)}")
        raise ResponseSynthesisError(f"Failed to combine results: {str(e)}")


def format_bedrock_response(combined_results: Dict[str, Any], original_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the combined results into a Bedrock Agent compatible response.
    
    Args:
        combined_results: Combined vision and drug information results
        original_event: Original event for response formatting
        
    Returns:
        Bedrock Agent compatible response
    """
    try:
        # Extract key information for the response body
        response_body = {
            'success': combined_results.get('success', False),
            'medication_name': combined_results.get('identification', {}).get('identified_medication', 'Unknown'),
            'confidence': combined_results.get('identification', {}).get('confidence_score', 0.0),
            'confidence_level': combined_results.get('identification', {}).get('confidence_level', 'Unknown'),
            'user_response': combined_results.get('user_response', ''),
            'drug_info_available': combined_results.get('drug_information', {}).get('available', False)
        }
        
        # Add drug information if available
        if combined_results.get('drug_information', {}).get('available', False):
            drug_info = combined_results['drug_information']
            response_body['drug_info'] = {
                'brand_name': drug_info.get('brand_name', 'N/A'),
                'generic_name': drug_info.get('generic_name', 'N/A'),
                'purpose': drug_info.get('purpose', 'Not available'),
                'warnings': drug_info.get('warnings', 'Not available'),
                'indications_and_usage': drug_info.get('indications_and_usage', 'Not available')
            }
        
        # Add warnings if present
        if 'warnings' in combined_results:
            response_body['warnings'] = combined_results['warnings']
        
        # Format as Bedrock Agent response
        bedrock_response = {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': original_event.get('actionGroup', 'image_analysis_tool'),
                'apiPath': original_event.get('apiPath', '/analyze-medication'),
                'httpMethod': original_event.get('httpMethod', 'POST'),
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(response_body)
                    }
                }
            }
        }
        
        return bedrock_response
        
    except Exception as e:
        logger.error(f"Error formatting Bedrock response: {str(e)}")
        # Return error response
        error_body = {
            'success': False,
            'error': f'Response formatting error: {str(e)}',
            'user_response': 'An error occurred while processing the medication identification results.'
        }
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': original_event.get('actionGroup', 'image_analysis_tool'),
                'apiPath': original_event.get('apiPath', '/analyze-medication'),
                'httpMethod': original_event.get('httpMethod', 'POST'),
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(error_body)
                    }
                }
            }
        }


def create_error_response(error_message: str, original_event: Dict[str, Any], 
                         error_type: str = 'processing_error') -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error_message: Error message to include
        original_event: Original event for response formatting
        error_type: Type of error for categorization
        
    Returns:
        Formatted error response
    """
    error_responses = {
        'processing_error': 'An error occurred while processing your medication image.',
        'vision_error': 'Unable to analyze the medication image clearly.',
        'drug_info_error': 'Medication identified but detailed information is unavailable.',
        'validation_error': 'Invalid input provided for medication analysis.'
    }
    
    user_message = error_responses.get(error_type, 'An unexpected error occurred.')
    
    error_body = {
        'success': False,
        'error': error_message,
        'error_type': error_type,
        'user_response': user_message,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': original_event.get('actionGroup', 'image_analysis_tool'),
            'apiPath': original_event.get('apiPath', '/analyze-medication'),
            'httpMethod': original_event.get('httpMethod', 'POST'),
            'httpStatusCode': 400,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(error_body)
                }
            }
        }
    }