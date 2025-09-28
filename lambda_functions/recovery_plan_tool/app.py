import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize the S3 client
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    This function is called by the Bedrock Agent.
    It retrieves a specific day's recovery plan from a JSON file in S3.
    """
    # Debug logging - Log the incoming event for troubleshooting
    print(f"[DEBUG] Incoming event: {json.dumps(event, indent=2)}")
    print(f"[DEBUG] Context: {context}")
    
    # Get the S3 bucket name from an environment variable for security
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        return build_response(event, {"error": "S3_BUCKET_NAME environment variable is not set."})
    
    # Extract parameters passed from the Bedrock Agent
    properties = event.get('input', {}).get('RequestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
    print(f"[DEBUG] Extracted properties: {json.dumps(properties, indent=2)}")
    
    day = None
    surgery_type = None  # We'll use this later to fetch different files
    
    for prop in properties:
        if prop.get('name') == 'day':
            try:
                day = int(prop.get('value'))
                if day < 1:
                    return build_response(event, {"error": "Day must be a positive number (1 or greater)."})
            except (ValueError, TypeError):
                return build_response(event, {"error": "Day must be a valid number."})
    
    if day is None:
        return build_response(event, {"error": "Please specify which day you want the recovery plan for."})
    
    # The key (filename) in the S3 bucket
    file_key = 'knee_arthroscopy_protocol.json'
    print(f"[DEBUG] Requesting day: {day}")
    print(f"[DEBUG] S3 Bucket: {bucket_name}")
    print(f"[DEBUG] S3 Key: {file_key}")
    
    try:
        # Get the JSON file from S3
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        print(f"[DEBUG] Successfully retrieved S3 object")
        content = response['Body'].read().decode('utf-8')
        protocol = json.loads(content)
        
        # Validate protocol structure
        if 'timeline' not in protocol:
            return build_response(event, {"error": "Invalid protocol file format: missing timeline."})
        
        # Find the plan for the requested day
        day_plan = "No plan found for that day."
        print(f"[DEBUG] Available days in protocol: {[item.get('day') for item in protocol.get('timeline', [])]}")
        
        for item in protocol.get('timeline', []):
            if item.get('day') == day:
                day_plan = item.get('tasks')
                print(f"[DEBUG] Found plan for day {day}: {day_plan}")
                break
        
        if day_plan == "No plan found for that day.":
            print(f"[DEBUG] No plan found for day {day}")
        
        # This is the standard response format for Bedrock Agents
        api_response = {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup'),
                'apiPath': event.get('apiPath'),
                'httpMethod': event.get('httpMethod'),
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({'plan': day_plan})
                    }
                }
            }
        }
        
        return api_response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            return build_response(event, {"error": f"S3 bucket '{bucket_name}' does not exist."})
        elif error_code == 'NoSuchKey':
            return build_response(event, {"error": f"Recovery protocol file '{file_key}' not found in S3."})
        else:
            return build_response(event, {"error": f"S3 error: {str(e)}"})
    except json.JSONDecodeError as e:
        return build_response(event, {"error": f"Invalid JSON in protocol file: {str(e)}"})
    except Exception as e:
        # Handle errors gracefully
        return build_response(event, {"error": f"An unexpected error occurred: {str(e)}"})

def build_response(event, body):
    """Helper function to build the standard Bedrock Agent response."""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup'),
            'apiPath': event.get('apiPath'),
            'httpMethod': event.get('httpMethod'),
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(body)
                }
            }
        }
    }