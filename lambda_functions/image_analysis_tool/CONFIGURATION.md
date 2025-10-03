# Configuration Guide for Image Analysis Tool

This document provides comprehensive information about configuring the Image Analysis Tool Lambda function for different environments and use cases.

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Environment Configuration](#environment-configuration)
3. [Lambda Function Settings](#lambda-function-settings)
4. [Vision Model Configuration](#vision-model-configuration)
5. [Integration Settings](#integration-settings)
6. [Performance Tuning](#performance-tuning)
7. [Security Configuration](#security-configuration)
8. [Monitoring Configuration](#monitoring-configuration)

## Configuration Overview

The Image Analysis Tool uses a hierarchical configuration system that supports:
- Environment-specific settings (development, staging, production)
- Runtime configuration through environment variables
- Default values with override capabilities
- Validation and error handling for invalid configurations

### Configuration Sources (in order of precedence)

1. **Environment Variables** - Runtime overrides
2. **Environment Config Files** - Environment-specific settings
3. **Default Values** - Fallback configuration in code

## Environment Configuration

### Configuration Files Location

Configuration files are stored in the `env_configs/` directory:
```
env_configs/
├── development.json
├── staging.json
└── production.json
```

### Configuration Schema

```json
{
  "ENVIRONMENT": "string",
  "AWS_REGION": "string",
  "BEDROCK_MODEL_ID": "string",
  "MAX_IMAGE_SIZE": "integer (bytes)",
  "VISION_TIMEOUT": "integer (seconds)",
  "LOG_LEVEL": "string (DEBUG|INFO|WARNING|ERROR)",
  "LOW_CONFIDENCE_THRESHOLD": "float (0.0-1.0)",
  "HIGH_CONFIDENCE_THRESHOLD": "float (0.0-1.0)",
  "DRUG_INFO_FUNCTION_NAME": "string",
  "DEFAULT_ANALYSIS_PROMPT": "string",
  "SUPPORTED_IMAGE_FORMATS": "array of strings",
  "ENABLE_PERFORMANCE_MONITORING": "boolean",
  "ENABLE_DEBUG_LOGGING": "boolean",
  "RETRY_ATTEMPTS": "integer",
  "RETRY_DELAY": "float (seconds)"
}
```

### Development Configuration

**File:** `env_configs/development.json`

```json
{
  "ENVIRONMENT": "development",
  "AWS_REGION": "us-east-1",
  "BEDROCK_MODEL_ID": "meta.llama3-2-11b-instruct-v1:0",
  "MAX_IMAGE_SIZE": 5242880,
  "VISION_TIMEOUT": 20,
  "LOG_LEVEL": "DEBUG",
  "LOW_CONFIDENCE_THRESHOLD": 0.6,
  "HIGH_CONFIDENCE_THRESHOLD": 0.8,
  "DRUG_INFO_FUNCTION_NAME": "drug-info-tool-dev",
  "DEFAULT_ANALYSIS_PROMPT": "Identify the medication name and dosage in this image",
  "SUPPORTED_IMAGE_FORMATS": ["jpeg", "jpg", "png", "webp"],
  "ENABLE_PERFORMANCE_MONITORING": true,
  "ENABLE_DEBUG_LOGGING": true,
  "RETRY_ATTEMPTS": 2,
  "RETRY_DELAY": 1.0
}
```

**Characteristics:**
- Smaller image size limit (5MB) for faster testing
- Lower confidence thresholds for more permissive identification
- Debug logging enabled for troubleshooting
- Shorter timeouts for quicker feedback
- Fewer retry attempts to speed up development

### Staging Configuration

**File:** `env_configs/staging.json`

```json
{
  "ENVIRONMENT": "staging",
  "AWS_REGION": "us-east-1",
  "BEDROCK_MODEL_ID": "meta.llama3-2-11b-instruct-v1:0",
  "MAX_IMAGE_SIZE": 8388608,
  "VISION_TIMEOUT": 25,
  "LOG_LEVEL": "INFO",
  "LOW_CONFIDENCE_THRESHOLD": 0.65,
  "HIGH_CONFIDENCE_THRESHOLD": 0.82,
  "DRUG_INFO_FUNCTION_NAME": "drug-info-tool-staging",
  "DEFAULT_ANALYSIS_PROMPT": "Identify the medication name and dosage in this image",
  "SUPPORTED_IMAGE_FORMATS": ["jpeg", "jpg", "png", "webp"],
  "ENABLE_PERFORMANCE_MONITORING": true,
  "ENABLE_DEBUG_LOGGING": false,
  "RETRY_ATTEMPTS": 3,
  "RETRY_DELAY": 1.5
}
```

**Characteristics:**
- Medium image size limit (8MB)
- Balanced confidence thresholds
- Info-level logging for operational visibility
- Production-like timeouts and retry behavior

### Production Configuration

**File:** `env_configs/production.json`

```json
{
  "ENVIRONMENT": "production",
  "AWS_REGION": "us-east-1",
  "BEDROCK_MODEL_ID": "meta.llama3-2-11b-instruct-v1:0",
  "MAX_IMAGE_SIZE": 10485760,
  "VISION_TIMEOUT": 30,
  "LOG_LEVEL": "INFO",
  "LOW_CONFIDENCE_THRESHOLD": 0.7,
  "HIGH_CONFIDENCE_THRESHOLD": 0.85,
  "DRUG_INFO_FUNCTION_NAME": "drug-info-tool",
  "DEFAULT_ANALYSIS_PROMPT": "Identify the medication name and dosage in this image",
  "SUPPORTED_IMAGE_FORMATS": ["jpeg", "jpg", "png", "webp"],
  "ENABLE_PERFORMANCE_MONITORING": true,
  "ENABLE_DEBUG_LOGGING": false,
  "RETRY_ATTEMPTS": 3,
  "RETRY_DELAY": 2.0
}
```

**Characteristics:**
- Maximum image size limit (10MB)
- Higher confidence thresholds for accuracy
- Optimized timeouts and retry behavior
- Performance monitoring enabled

## Lambda Function Settings

### Memory Configuration

| Environment | Memory (MB) | Rationale |
|-------------|-------------|-----------|
| Development | 512 | Sufficient for testing with smaller images |
| Staging | 768 | Balanced performance for integration testing |
| Production | 1024 | Optimal performance for production workloads |

**Configuration Command:**
```bash
aws lambda update-function-configuration \
    --function-name image-analysis-tool \
    --memory-size 1024
```

### Timeout Configuration

| Environment | Timeout (seconds) | Rationale |
|-------------|-------------------|-----------|
| Development | 180 | Quick feedback for development |
| Staging | 240 | Realistic testing timeouts |
| Production | 300 | Maximum time for complex processing |

**Configuration Command:**
```bash
aws lambda update-function-configuration \
    --function-name image-analysis-tool \
    --timeout 300
```

### Concurrency Configuration

```bash
# Reserved concurrency (production)
aws lambda put-reserved-concurrency-configuration \
    --function-name image-analysis-tool \
    --reserved-concurrent-executions 10

# Provisioned concurrency (if needed)
aws lambda put-provisioned-concurrency-config \
    --function-name image-analysis-tool \
    --qualifier $LATEST \
    --provisioned-concurrency-executions 2
```

### Environment Variables

**Runtime Environment Variables:**
```bash
aws lambda update-function-configuration \
    --function-name image-analysis-tool \
    --environment Variables='{
        "ENVIRONMENT":"production",
        "AWS_REGION":"us-east-1",
        "LOG_LEVEL":"INFO",
        "MAX_IMAGE_SIZE":"10485760"
    }'
```

**Environment Variable Precedence:**
1. Lambda environment variables (highest priority)
2. Configuration file values
3. Default values in code (lowest priority)

## Vision Model Configuration

### Supported Models

| Model ID | Capabilities | Use Case |
|----------|--------------|----------|
| `meta.llama3-2-11b-instruct-v1:0` | Multimodal, fast | General medication identification |
| `anthropic.claude-3-sonnet-20240229-v1:0` | High accuracy | Complex medication analysis |
| `anthropic.claude-3-haiku-20240307-v1:0` | Fast, cost-effective | High-volume processing |

### Model Selection Criteria

**Development/Testing:**
- Use faster, cost-effective models
- Prioritize quick feedback over accuracy

**Production:**
- Balance accuracy and performance
- Consider cost implications for high volume

### Vision Model Parameters

```json
{
  "model_parameters": {
    "max_tokens": 1000,
    "temperature": 0.1,
    "top_p": 0.9,
    "stop_sequences": ["</analysis>"]
  }
}
```

### Custom Prompts

**Default Prompt:**
```
Identify the medication name and dosage in this image
```

**Enhanced Prompt for Complex Cases:**
```
Analyze this medication image and extract:
1. Medication name (brand and/or generic)
2. Dosage strength (mg, ml, etc.)
3. Manufacturer if visible
4. Any special markings or identifiers

If multiple medications are visible, focus on the most prominent one.
If the image is unclear, indicate the confidence level.
```

**Prompt Configuration:**
```python
# In config file
"DEFAULT_ANALYSIS_PROMPT": "Your custom prompt here"

# Runtime override
payload = {
    "image_data": "base64_image",
    "prompt": "Custom prompt for this request"
}
```

## Integration Settings

### DrugInfoTool Integration

**Function Name Configuration:**
```json
{
  "DRUG_INFO_FUNCTION_NAME": "drug-info-tool",
  "DRUG_INFO_TIMEOUT": 30,
  "DRUG_INFO_RETRY_ATTEMPTS": 2
}
```

**Cross-Function IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:*:*:function:drug-info-tool",
        "arn:aws:lambda:*:*:function:drug-info-tool-*"
      ]
    }
  ]
}
```

### Bedrock Integration

**Required Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

**Model Access Configuration:**
```bash
# Enable model access in Bedrock console or via CLI
aws bedrock put-model-invocation-logging-configuration \
    --logging-config cloudWatchConfig='{
        "logGroupName":"/aws/bedrock/modelinvocations",
        "roleArn":"arn:aws:iam::123456789012:role/BedrockLoggingRole"
    }'
```

## Performance Tuning

### Image Processing Optimization

**Image Size Limits by Environment:**
```json
{
  "development": 5242880,    // 5MB
  "staging": 8388608,        // 8MB  
  "production": 10485760     // 10MB
}
```

**Image Quality Settings:**
```json
{
  "image_optimization": {
    "max_dimension": 2048,
    "jpeg_quality": 85,
    "png_compression": 6,
    "webp_quality": 80
  }
}
```

### Timeout Configuration

**Component-Specific Timeouts:**
```json
{
  "timeouts": {
    "vision_model": 30,
    "drug_info_lookup": 15,
    "image_processing": 10,
    "total_request": 300
  }
}
```

### Retry Configuration

**Retry Strategy:**
```json
{
  "retry_config": {
    "max_attempts": 3,
    "initial_delay": 1.0,
    "max_delay": 10.0,
    "exponential_base": 2.0,
    "jitter": true
  }
}
```

### Memory Optimization

**Memory Usage Guidelines:**
- **512MB:** Basic image processing, small images
- **768MB:** Medium images, complex processing
- **1024MB:** Large images, optimal performance
- **1536MB+:** Very large images, maximum performance

## Security Configuration

### IAM Role Configuration

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Execution Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:drug-info-tool*"
    }
  ]
}
```

### VPC Configuration (Optional)

**For Enhanced Security:**
```bash
aws lambda update-function-configuration \
    --function-name image-analysis-tool \
    --vpc-config SubnetIds=subnet-12345,subnet-67890,SecurityGroupIds=sg-abcdef
```

**VPC Considerations:**
- Requires NAT Gateway for internet access
- Increases cold start time
- Necessary for private resource access

### Encryption Configuration

**Environment Variable Encryption:**
```bash
aws lambda update-function-configuration \
    --function-name image-analysis-tool \
    --kms-key-arn arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
```

## Monitoring Configuration

### CloudWatch Metrics

**Custom Metrics Configuration:**
```json
{
  "custom_metrics": {
    "namespace": "CareCoach/ImageAnalysis",
    "metrics": [
      "ProcessingDuration",
      "VisionModelLatency", 
      "ConfidenceScore",
      "ImageSize",
      "SuccessRate"
    ]
  }
}
```

### Log Configuration

**Log Retention:**
```bash
aws logs put-retention-policy \
    --log-group-name /aws/lambda/image-analysis-tool \
    --retention-in-days 30
```

**Structured Logging Format:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "request_id": "req_123456789",
  "stage": "vision_analysis",
  "message": "Processing image",
  "metadata": {
    "image_size": 2048576,
    "confidence": 0.95,
    "processing_time": 1.5
  }
}
```

### Alarms Configuration

**Error Rate Alarm:**
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "ImageAnalysis-ErrorRate" \
    --alarm-description "High error rate in image analysis" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value=image-analysis-tool \
    --evaluation-periods 2
```

**Duration Alarm:**
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "ImageAnalysis-Duration" \
    --alarm-description "High processing duration" \
    --metric-name Duration \
    --namespace AWS/Lambda \
    --statistic Average \
    --period 300 \
    --threshold 10000 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value=image-analysis-tool \
    --evaluation-periods 2
```

## Configuration Validation

### Validation Script

```python
#!/usr/bin/env python3
"""Configuration validation script for Image Analysis Tool."""

import json
import os
from typing import Dict, Any, List

def validate_config(config_path: str) -> List[str]:
    """Validate configuration file and return list of errors."""
    errors = []
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        return [f"Failed to load config: {e}"]
    
    # Required fields
    required_fields = [
        'ENVIRONMENT', 'AWS_REGION', 'BEDROCK_MODEL_ID',
        'MAX_IMAGE_SIZE', 'VISION_TIMEOUT', 'LOG_LEVEL'
    ]
    
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # Validate specific fields
    if 'MAX_IMAGE_SIZE' in config:
        if not isinstance(config['MAX_IMAGE_SIZE'], int) or config['MAX_IMAGE_SIZE'] <= 0:
            errors.append("MAX_IMAGE_SIZE must be positive integer")
    
    if 'LOG_LEVEL' in config:
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        if config['LOG_LEVEL'] not in valid_levels:
            errors.append(f"LOG_LEVEL must be one of: {valid_levels}")
    
    if 'LOW_CONFIDENCE_THRESHOLD' in config:
        threshold = config['LOW_CONFIDENCE_THRESHOLD']
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            errors.append("LOW_CONFIDENCE_THRESHOLD must be float between 0 and 1")
    
    return errors

# Validate all environment configs
for env in ['development', 'staging', 'production']:
    config_path = f'env_configs/{env}.json'
    if os.path.exists(config_path):
        errors = validate_config(config_path)
        if errors:
            print(f"Errors in {env} config:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"✓ {env} config is valid")
    else:
        print(f"⚠ {env} config not found")
```

### Configuration Testing

```python
def test_configuration():
    """Test configuration loading and validation."""
    from config import config
    
    # Test required attributes exist
    assert hasattr(config, 'ENVIRONMENT')
    assert hasattr(config, 'BEDROCK_MODEL_ID')
    assert hasattr(config, 'MAX_IMAGE_SIZE')
    
    # Test value ranges
    assert 0 < config.MAX_IMAGE_SIZE <= 50 * 1024 * 1024  # Max 50MB
    assert 0 <= config.LOW_CONFIDENCE_THRESHOLD <= 1
    assert config.LOW_CONFIDENCE_THRESHOLD < config.HIGH_CONFIDENCE_THRESHOLD
    
    print("✓ Configuration validation passed")

if __name__ == "__main__":
    test_configuration()
```

This configuration guide provides comprehensive information for setting up and tuning the Image Analysis Tool for different environments and use cases. Adjust the settings based on your specific requirements and constraints.