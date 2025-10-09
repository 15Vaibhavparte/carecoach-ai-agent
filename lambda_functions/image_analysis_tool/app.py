# lambda_functions/image_analysis_tool/app.py
import json
import boto3
import base64

# Initialize the Bedrock Runtime client
bedrock_runtime = boto3.client('bedrock-runtime')
MODEL_ID = 'meta.llama3-2-11b-instruct-v1:0' # The model ID for Llama 3.2 11B Vision

def lambda_handler(event, context):
    # Extract the base64_image parameter
    parameters = event.get('parameters', [])
    base64_image = None
    for param in parameters:
        if param.get('name') == 'base64_image':
            base64_image = param.get('value')
            break

    if not base64_image:
        return build_response(event, {"error": "No image data was provided."})

    # Construct the payload for the Llama 3.2 Vision model
    prompt = "This is an image of a medication pill or box. Extract any text visible in the image. Respond only with the extracted text."

    request_body = {
        "prompt": prompt,
        "images": [base64_image]
    }

    try:
        # Invoke the model directly
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())
        extracted_text = response_body.get('generation')

        return build_response(event, {"extracted_text": extracted_text})

    except Exception as e:
        return build_response(event, {"error": f"Failed to invoke vision model: {str(e)}"})

def build_response(event, body):
    # Standard response format for Bedrock Agents
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup'),
            'apiPath': event.get('apiPath'),
            'httpMethod': event.get('httpMethod'),
            'httpStatusCode': 200,
            'responseBody': {'application/json': {'body': json.dumps(body)}}
        }
    }