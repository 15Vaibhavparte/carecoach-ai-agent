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

## Usage

The Lambda handler accepts base64-encoded images and returns structured medication identification results combined with detailed drug information from the existing DrugInfoTool.