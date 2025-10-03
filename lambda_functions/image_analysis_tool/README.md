# Image Analysis Tool

This Lambda function provides medication identification from images using computer vision and integrates with the existing DrugInfoTool to provide comprehensive medication information.

## Structure

- `app.py` - Main Lambda handler following Bedrock Agent pattern
- `models.py` - Data models and interfaces for type safety and structure
- `config.py` - Configuration management and environment settings
- `requirements.txt` - Python dependencies
- `__init__.py` - Package initialization and exports

## Key Components

### ImageAnalysisHandler
Core handler class that orchestrates the image analysis workflow:
- Image validation and preprocessing
- Vision model integration (AWS Bedrock Claude 3 Sonnet)
- Medication information extraction
- DrugInfoTool integration

### Data Models
- `ImageAnalysisRequest` - Input request structure
- `MedicationIdentification` - Vision analysis results
- `CombinedResponse` - Complete response with drug information
- `VisionModelResponse` - Vision model API response
- `DrugInfoResult` - Drug information retrieval results

### Configuration
Centralized configuration management supporting:
- Environment-specific settings (dev/test/prod)
- Image processing limits and formats
- Vision model parameters
- Error and success messages

## Integration Pattern

Follows the same Bedrock Agent pattern as DrugInfoTool:
- Multiple input format support
- Standardized response structure
- Comprehensive error handling
- Debug logging for troubleshooting

## Dependencies

- `boto3` - AWS SDK for Bedrock integration
- `requests` - HTTP client for API calls
- `Pillow` - Image processing capabilities

## Documentation

### Quick Start
- **[API Documentation](API_DOCUMENTATION.md)** - Complete API reference and request/response formats
- **[Usage Examples](USAGE_EXAMPLES.md)** - Code examples in Python, JavaScript, cURL, and more
- **[Deployment Guide](DEPLOYMENT.md)** - Step-by-step deployment instructions

### Configuration and Troubleshooting
- **[Configuration Guide](CONFIGURATION.md)** - Environment settings and performance tuning
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions

### Testing and Validation
- **[End-to-End Validation Report](END_TO_END_VALIDATION_REPORT.md)** - Comprehensive testing results

## Quick Usage

The Lambda handler accepts base64-encoded images and returns structured medication identification results combined with detailed drug information from the existing DrugInfoTool.

### Basic Example

```python
import boto3
import base64
import json

# Encode image
with open('medication.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# Prepare request
payload = {
    "input": {
        "RequestBody": {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "image_data", "value": image_data}
                    ]
                }
            }
        }
    }
}

# Invoke function
lambda_client = boto3.client('lambda')
response = lambda_client.invoke(
    FunctionName='image-analysis-tool',
    Payload=json.dumps(payload)
)

# Parse results
result = json.loads(response['Payload'].read())
if result['success']:
    medication = result['medication_identification']
    print(f"Identified: {medication['medication_name']} ({medication['dosage']})")
```

For complete examples and advanced usage, see the [Usage Examples](USAGE_EXAMPLES.md) documentation.