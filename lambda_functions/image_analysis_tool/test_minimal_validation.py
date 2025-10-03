#!/usr/bin/env python3
"""Minimal validation test"""

import sys
import os
import time
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("Testing minimal validation...")

def validate_environment():
    """Simple environment validation"""
    try:
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            return {
                'success': False,
                'error': f'Python 3.8+ required, found {python_version.major}.{python_version.minor}'
            }
        
        print("✓ Python version check passed")
        
        # Check if main application modules are available
        try:
            from app import lambda_handler, health_check
            print("✓ app module imported")
        except ImportError as e:
            return {
                'success': False,
                'error': f'Failed to import app module: {str(e)}'
            }
        
        try:
            from models import ImageAnalysisRequest, MedicationIdentification
            print("✓ models module imported")
        except ImportError as e:
            return {
                'success': False,
                'error': f'Failed to import models module: {str(e)}'
            }
        
        try:
            from config import config
            print("✓ config module imported")
        except ImportError as e:
            return {
                'success': False,
                'error': f'Failed to import config module: {str(e)}'
            }
        
        return {'success': True, 'message': 'Environment validation passed'}
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Environment validation error: {str(e)}'
        }

def run_minimal_validation():
    """Run minimal validation"""
    
    print("=" * 60)
    print("MINIMAL END-TO-END VALIDATION")
    print("=" * 60)
    print()
    
    # Step 1: Environment validation
    print("Step 1: Environment Validation")
    print("-" * 30)
    
    env_result = validate_environment()
    if not env_result['success']:
        print(f"❌ Environment validation failed: {env_result['error']}")
        return False
    
    print(f"✓ {env_result['message']}")
    print()
    
    # Step 2: Test health check
    print("Step 2: Health Check Test")
    print("-" * 30)
    
    try:
        from app import health_check
        
        mock_context = type('MockContext', (), {
            'function_name': 'image_analysis_tool',
            'aws_request_id': 'test-request-id'
        })()
        
        health_response = health_check({}, mock_context)
        
        if health_response.get('statusCode') == 200:
            print("✓ Health check endpoint working")
        else:
            print(f"❌ Health check failed with status: {health_response.get('statusCode')}")
            return False
            
    except Exception as e:
        print(f"❌ Health check test failed: {str(e)}")
        return False
    
    print()
    
    # Step 3: Test basic lambda handler with invalid input
    print("Step 3: Basic Lambda Handler Test")
    print("-" * 30)
    
    try:
        from app import lambda_handler
        
        # Test with empty event (should handle gracefully)
        mock_context = type('MockContext', (), {
            'function_name': 'image_analysis_tool',
            'aws_request_id': 'test-request-id',
            'remaining_time_in_millis': lambda: 30000
        })()
        
        response = lambda_handler({}, mock_context)
        
        # Should return error response for empty event
        if 'response' in response and 'responseBody' in response['response']:
            body = json.loads(response['response']['responseBody']['application/json']['body'])
            if not body.get('success', True) and 'error' in body:
                print("✓ Lambda handler correctly handles empty input")
            else:
                print("⚠ Lambda handler should have returned error for empty input")
        else:
            print("❌ Lambda handler returned invalid response format")
            return False
            
    except Exception as e:
        print(f"❌ Lambda handler test failed: {str(e)}")
        return False
    
    print()
    
    # Final summary
    print("=" * 60)
    print("MINIMAL VALIDATION SUMMARY")
    print("=" * 60)
    print()
    print("✅ MINIMAL VALIDATION PASSED!")
    print()
    print("The basic system components are working correctly.")
    print("Ready for more comprehensive testing.")
    print()
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    success = run_minimal_validation()
    sys.exit(0 if success else 1)