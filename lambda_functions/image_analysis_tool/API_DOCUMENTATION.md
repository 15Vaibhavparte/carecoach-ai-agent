# Image Analysis Tool API Documentation

## Overview

The Image Analysis Tool is a Lambda function that provides medication identification from images using computer vision and integrates with the existing DrugInfoTool to provide comprehensive medication information.

## API Endpoint

**Function Name:** `image-analysis-tool`  
**Runtime:** Python 3.9  
**Handler:** `app.lambda_handler`  
**Timeout:** 300 seconds  
**Memory:** 1024 MB  

## Request Format

The Lambda function accepts requests in multiple formats to maintain compatibility with different invocation patterns.

### Format 1: Bedrock Agent Format (Recommended)

```json
{
  "input": {
    "RequestBody": {
      "content": {
        "application/json": {
          "properties": [
            {
              "name": "image_data",
              "value": "base64_encoded_image_string"
            },
            {
              "name": "prompt",
              "value": "Identify the medication name and dosage in this image"
            }
          ]
        }
      }
    }
  }
}
```

### Format 2: Direct Parameters Format

```json
{
  "image_data": "base64_encoded_image_string",
  "prompt": "Identify the medication name and dosage in this image"
}
```

### Format 3: Body Format

```json
{
  "body": "{\"image_data\": \"base64_encoded_image_string\", \"prompt\": \"Identify the medication name and dosage in this image\"}"
}
```

## Request Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `image_data` | string | Yes | Base64 encoded image data | - |
| `prompt` | string | No | Custom analysis prompt | "Identify the medication name and dosage in this image" |

### Image Requirements

- **Supported Formats:** JPEG, PNG, WebP
- **Maximum Size:** 10 MB
- **Encoding:** Base64
- **Quality:** Clear, well-lit images work best

## Response Format

### Success Response

```json
{
  "response": {
    "responseBody": {
      "application/json": {
        "body": "{\"success\": true, \"medication_identification\": {...}, \"drug_information\": {...}, \"processing_time\": 2.45, \"request_id\": \"req_123\"}"
      }
    }
  }
}
```

### Response Body Structure

```json
{
  "success": true,
  "medication_identification": {
    "medication_name": "Advil",
    "dosage": "200mg",
    "confidence": 0.95,
    "alternative_names": ["Ibuprofen"],
    "image_quality": "good"
  },
  "drug_information": {
    "available": true,
    "brand_name": "Advil",
    "generic_name": "Ibuprofen",
    "purpose": "Pain reliever/fever reducer",
    "warnings": "Do not exceed recommended dosage...",
    "indications_and_usage": "For temporary relief of minor aches and pains...",
    "dosage_and_administration": "Adults: Take 1-2 tablets every 4-6 hours...",
    "contraindications": "Do not use if allergic to ibuprofen...",
    "adverse_reactions": "May cause stomach upset, dizziness..."
  },
  "processing_time": 2.45,
  "request_id": "req_123456789",
  "performance_metrics": {
    "total_processing_time": 2.45,
    "stage_count": 6,
    "successful_stages": 6
  }
}
```

### Error Response

```json
{
  "response": {
    "responseBody": {
      "application/json": {
        "body": "{\"success\": false, \"error\": \"Invalid image format\", \"error_type\": \"validation_error\", \"suggestions\": [\"Please upload a JPEG, PNG, or WebP image\"]}"
      }
    }
  }
}
```

## Data Models

### MedicationIdentification

| Field | Type | Description |
|-------|------|-------------|
| `medication_name` | string | Identified medication name |
| `dosage` | string | Identified dosage (e.g., "200mg") |
| `confidence` | float | Confidence score (0.0 to 1.0) |
| `alternative_names` | array | Alternative medication names |
| `image_quality` | string | Image quality assessment ("good", "fair", "poor") |

### DrugInformation

| Field | Type | Description |
|-------|------|-------------|
| `available` | boolean | Whether drug information was found |
| `brand_name` | string | Brand name of the medication |
| `generic_name` | string | Generic name of the medication |
| `purpose` | string | Primary purpose of the medication |
| `warnings` | string | Important warnings and precautions |
| `indications_and_usage` | string | Approved uses and indications |
| `dosage_and_administration` | string | Dosage instructions |
| `contraindications` | string | When not to use the medication |
| `adverse_reactions` | string | Possible side effects |

## Error Handling

### Error Types

| Error Type | Description | HTTP Status |
|------------|-------------|-------------|
| `validation_error` | Invalid input parameters | 400 |
| `image_processing_error` | Image format or processing issues | 400 |
| `vision_model_error` | Vision model API failures | 500 |
| `drug_info_error` | Drug information lookup failures | 500 |
| `timeout_error` | Processing timeout | 504 |
| `system_error` | Unexpected system errors | 500 |

### Common Error Messages

```json
{
  "success": false,
  "error": "No image data provided. Please upload an image of the medication.",
  "error_type": "validation_error",
  "suggestions": [
    "Ensure image_data parameter contains base64 encoded image",
    "Check that the image is properly encoded"
  ]
}
```

```json
{
  "success": false,
  "error": "Image format not supported. Please use JPEG, PNG, or WebP.",
  "error_type": "validation_error",
  "suggestions": [
    "Convert image to JPEG, PNG, or WebP format",
    "Ensure image is not corrupted"
  ]
}
```

```json
{
  "success": false,
  "error": "No medication clearly visible in the image.",
  "error_type": "vision_model_error",
  "suggestions": [
    "Ensure medication is clearly visible and well-lit",
    "Try taking a closer photo of the medication",
    "Remove any obstructions from the image"
  ]
}
```

## Performance Characteristics

### Typical Response Times

| Operation | Average Time | 95th Percentile |
|-----------|--------------|-----------------|
| Image validation | 50ms | 100ms |
| Vision analysis | 1.5s | 3.0s |
| Drug info lookup | 800ms | 1.5s |
| Total processing | 2.4s | 4.5s |

### Resource Usage

- **Memory:** 512MB - 1024MB depending on image size
- **CPU:** Moderate usage during image processing
- **Network:** Outbound calls to Bedrock and DrugInfoTool

## Rate Limits

- **Concurrent executions:** 10 (configurable)
- **Request rate:** No explicit limit (governed by Lambda concurrency)
- **Image size limit:** 10 MB per request

## Security Considerations

- Images are processed in memory only and never stored
- No sensitive data is logged
- All API calls use encrypted connections
- IAM-based access control for function invocation

## Monitoring and Logging

### CloudWatch Metrics

The function publishes the following custom metrics:

- `image_processing_duration` - Time spent processing images
- `vision_model_response_time` - Vision API response time
- `confidence_score_distribution` - Distribution of confidence scores
- `success_rate` - Percentage of successful requests
- `error_rate_by_type` - Error rates by error type

### Log Structure

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "request_id": "req_123456789",
  "stage": "vision_analysis",
  "message": "Analyzing image with vision model",
  "metadata": {
    "image_size_bytes": 2048576,
    "confidence_score": 0.95,
    "processing_time_ms": 1500
  }
}
```

## Integration with DrugInfoTool

The Image Analysis Tool automatically integrates with the existing DrugInfoTool when a medication is successfully identified with sufficient confidence.

### Integration Flow

1. Image analysis identifies medication name
2. If confidence > 0.7, automatically call DrugInfoTool
3. Combine vision results with drug information
4. Return unified response

### DrugInfoTool Parameters

```json
{
  "drug_name": "extracted_medication_name",
  "include_warnings": true,
  "include_dosage": true
}
```

## Best Practices

### Image Quality Guidelines

1. **Lighting:** Ensure good, even lighting
2. **Focus:** Image should be sharp and in focus
3. **Angle:** Take photo straight-on, avoid extreme angles
4. **Background:** Use plain, contrasting background
5. **Size:** Fill frame with medication, avoid too much empty space

### Error Handling

1. Always check the `success` field in responses
2. Implement retry logic for `timeout_error` and `system_error`
3. Provide user-friendly error messages based on `error_type`
4. Use `suggestions` array to guide users on fixing issues

### Performance Optimization

1. Compress images before base64 encoding when possible
2. Use appropriate image formats (JPEG for photos, PNG for text)
3. Implement client-side caching for repeated requests
4. Consider async processing for non-critical use cases

## SDK Examples

See the [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) file for detailed code examples in various programming languages.