# CareCoach AI Agent Development Guide

## Project Overview

CareCoach is an AI agent built on AWS for providing unified surgical recovery support. The agent uses specialized Lambda tools to provide recovery plans, medication information (text/image), and follow-up scheduling.

## Core Architecture

Full-stack serverless application with Bedrock Agent orchestration:

1.  **Frontend:** Single-page React/JS app (Vercel/Netlify hosted)
2.  **API Layer:** Amazon API Gateway as secure backend gateway  
3.  **Orchestrator:** Amazon Bedrock Agent (ID: `GBBAJWBJHO`, Alias: `TSTALIASID`)
4.  **Tools:** Individual AWS Lambda functions in `lambda_functions/` directories
5.  **Data:** S3 knowledge base + external APIs (openFDA) + Bedrock vision models



## Lambda Tools

### `lambda_functions/recovery_plan_tool/`
Retrieves day-specific recovery plans from S3. **Requires `S3_BUCKET_NAME` environment variable.**
- Input: `day` (integer from Bedrock properties)
- Data source: `knee_arthroscopy_protocol.json` in S3
- Pattern: Complex property extraction from `event.input.RequestBody.content`

### `lambda_functions/drug_info_tool/`  
FDA API integration for medication lookup and warnings.
- Input: `drug_name` (string from Bedrock parameters list)
- External API: `https://api.fda.gov/drug/label.json`
- Pattern: Simple parameter iteration with `event.parameters[]`

### `lambda_functions/image_analysis_tool/`
Bedrock vision model for medication identification from images.
- Input: `image_data` (base64), `prompt` (optional)
- Service: `bedrock-agent-runtime.invoke_agent()` with session attributes
- Max image size: 10MB, supports PNG/JPEG/WebP

### `build/package/`
Contains packaged Lambda with bundled dependencies (`boto3`, `requests`) ready for deployment.

## Bedrock Agent Integration Patterns

### Standard Response Format
All Lambda functions must return this exact structure:
```python
def build_response(event, body):
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
```

### Parameter Extraction
**Simple parameters** (drug_info_tool pattern):
```python
parameters = event.get('parameters', [])
for param in parameters:
    if param.get('name') == 'drug_name':
        drug_name = param.get('value')
```

**Complex properties** (recovery_plan_tool pattern):
```python
properties = event.get('input', {}).get('RequestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
for prop in properties:
    if prop.get('name') == 'day':
        day = int(prop.get('value'))
```

## Development Workflow

### Lambda Deployment Process
Critical workflow for packaging and deploying Lambda functions:

1. Navigate to tool directory: `cd lambda_functions/drug_info_tool`
2. Install dependencies locally: `pip install -r requirements.txt -t .`
3. Create zip file containing all directory contents
4. Upload `package.zip` to AWS Lambda console

### Debug Patterns
Include comprehensive logging for troubleshooting:
```python
print(f"[DEBUG] Incoming event: {json.dumps(event, indent=2)}")
print(f"[DEBUG] Extracted properties: {json.dumps(properties, indent=2)}")
```

## External Integrations
- **Bedrock Agent**: ID `GBBAJWBJHO`, Alias `TSTALIASID` (hardcoded in `build/package/app.py`)
- **FDA API**: Drug information lookup via openFDA public endpoint
- **AWS S3**: Protocol storage requiring `S3_BUCKET_NAME` environment variable