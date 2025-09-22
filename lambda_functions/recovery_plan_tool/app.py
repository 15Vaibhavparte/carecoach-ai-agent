import json
import boto3
import os

# Initialize the S3 client
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    This function is called by the Bedrock Agent.
    It retrieves a specific day's recovery plan from a JSON file in S3.
    """
    # Get the S3 bucket name from an environment variable for security
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        return {
            "statusCode": 500,
            "body": json.dumps("Error: S3_BUCKET_NAME environment variable is not set.")
        }
    
    # Extract parameters passed from the Bedrock Agent
    properties = event.get('input', {}).get('RequestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
    
    day = None
    surgery_type = None  # We'll use this later to fetch different files
    
    for prop in properties:
        if prop.get('name') == 'day':
            day = int(prop.get('value'))
    
    if day is None:
        return {
            "response": "I'm sorry, you need to specify which day you want the plan for."
        }
    
    # The key (filename) in the S3 bucket
    file_key = 'knee_arthroscopy_protocol.json'
    
    try:
        # Get the JSON file from S3
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        content = response['Body'].read().decode('utf-8')
        protocol = json.loads(content)
        
        # Find the plan for the requested day
        day_plan = "No plan found for that day."
        for item in protocol.get('timeline', []):
            if item.get('day') == day:
                day_plan = item.get('tasks')
                break
        
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
        
    except Exception as e:
        # Handle errors gracefully
        return {
            "response": f"An error occurred: {str(e)}"
        }