# Deployment Guide for Image Analysis Lambda Function

This guide covers the deployment process for the CareCoach Image Analysis Lambda function.

## Prerequisites

- Python 3.9 or later
- AWS CLI configured with appropriate credentials
- Required permissions for Lambda, Bedrock, and IAM operations
- `jq` command-line tool (for shell scripts)

## Quick Start

### Using Make (Recommended)

```bash
# Deploy to production
make deploy

# Deploy to development
make deploy-dev

# Deploy to staging
make deploy-staging

# Package only (no deployment)
make package
```

### Using Python Script

```bash
# Deploy to production
python deploy.py --environment production

# Deploy to development with specific AWS profile
python deploy.py --environment development --profile dev-profile

# Create package only
python deploy.py --package-only
```

### Using Shell Script (Linux/macOS)

```bash
# Deploy to production
./deploy.sh production default

# Deploy to development
./deploy.sh development dev-profile
```

### Using PowerShell Script (Windows)

```powershell
# Deploy to production
.\deploy.ps1 -Environment production -AwsProfile default

# Deploy to development
.\deploy.ps1 -Environment development -AwsProfile dev-profile

# Package only
.\deploy.ps1 -PackageOnly
```

## Configuration

### Environment Variables

The function uses environment-specific configuration files located in `env_configs/`:

- `development.json` - Development environment settings
- `staging.json` - Staging environment settings  
- `production.json` - Production environment settings

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `production` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `BEDROCK_MODEL_ID` | Vision model ID | `meta.llama3-2-11b-instruct-v1:0` |
| `MAX_IMAGE_SIZE` | Maximum image size in bytes | `10485760` (10MB) |
| `VISION_TIMEOUT` | Vision API timeout in seconds | `30` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Lambda Configuration

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| Memory | 512MB | 768MB | 1024MB |
| Timeout | 180s | 240s | 300s |
| Concurrency | 5 | 8 | 10 |

## IAM Permissions

### Required Permissions

The Lambda function requires the following permissions:

1. **CloudWatch Logs**
   - `logs:CreateLogGroup`
   - `logs:CreateLogStream`
   - `logs:PutLogEvents`

2. **Amazon Bedrock**
   - `bedrock:InvokeModel`
   - `bedrock:InvokeModelWithResponseStream`

3. **Lambda (for DrugInfoTool integration)**
   - `lambda:InvokeFunction`

4. **X-Ray Tracing**
   - `xray:PutTraceSegments`
   - `xray:PutTelemetryRecords`

5. **CloudWatch Metrics**
   - `cloudwatch:PutMetricData`

### Setting up IAM Role

```bash
# Create IAM role and policies
make setup-iam

# Or manually:
aws iam create-role \
    --role-name lambda-image-analysis-role \
    --assume-role-policy-document file://trust_policy.json

aws iam put-role-policy \
    --role-name lambda-image-analysis-role \
    --policy-name lambda-image-analysis-policy \
    --policy-document file://iam_policy.json
```

## Deployment Process

### 1. Pre-deployment Validation

```bash
# Run tests
make test

# Validate configuration
make validate

# Check deployment readiness
python test_deployment.py
```

### 2. Package Creation

The deployment process creates a ZIP package containing:

- Application code (`app.py`, modules)
- Dependencies from `requirements.txt`
- Configuration files

Excluded from package:
- Test files (`test_*.py`)
- Development scripts
- Configuration templates
- Documentation

### 3. Deployment Steps

1. **Clean previous builds**
2. **Install dependencies** to function directory
3. **Run tests** (unless skipped)
4. **Create ZIP package**
5. **Validate package** (size, required files)
6. **Deploy to AWS Lambda**
7. **Update configuration** (memory, timeout, environment variables)

### 4. Post-deployment Verification

```bash
# Check function status
make status

# View configuration
make config

# Test invoke
make invoke-test

# View logs
make logs
```

## Troubleshooting

### Common Issues

1. **Package too large (>50MB)**
   - Remove unnecessary dependencies
   - Use Lambda layers for large libraries
   - Optimize image processing libraries

2. **Permission denied errors**
   - Verify IAM role has required permissions
   - Check AWS CLI credentials and profile

3. **Function timeout**
   - Increase timeout in environment config
   - Optimize image processing code
   - Consider async processing for large images

4. **Bedrock access denied**
   - Ensure Bedrock service is enabled in region
   - Verify model access permissions
   - Check model ID is correct

### Debug Commands

```bash
# View detailed logs
aws logs tail /aws/lambda/image-analysis-tool --follow

# Check function metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Duration \
    --dimensions Name=FunctionName,Value=image-analysis-tool \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Average

# Test with sample payload
aws lambda invoke \
    --function-name image-analysis-tool \
    --payload file://test_payload.json \
    response.json
```

## Environment-Specific Deployment

### Development Environment

- Lower memory allocation (512MB)
- Shorter timeout (180s)
- Debug logging enabled
- Reduced concurrency limits

```bash
make deploy-dev
```

### Staging Environment

- Medium memory allocation (768MB)
- Medium timeout (240s)
- Info-level logging
- Moderate concurrency limits

```bash
make deploy-staging
```

### Production Environment

- High memory allocation (1024MB)
- Extended timeout (300s)
- Info-level logging
- Full concurrency limits
- Enhanced monitoring

```bash
make deploy-prod
```

## Monitoring and Maintenance

### CloudWatch Metrics

The function publishes custom metrics:
- Image processing duration
- Vision model response time
- Success/failure rates
- Confidence score distributions

### Log Analysis

Structured logging includes:
- Request ID for tracing
- Processing timestamps
- Error details and stack traces
- Performance metrics

### Maintenance Tasks

```bash
# Update dependencies
pip install -r requirements.txt --upgrade
make deploy-code-only

# Rotate logs (if needed)
aws logs delete-log-group --log-group-name /aws/lambda/image-analysis-tool

# Update configuration only
aws lambda update-function-configuration \
    --function-name image-analysis-tool \
    --environment Variables='{...}'
```

## Security Considerations

1. **Image Data**: Images are processed in memory only, never stored
2. **Logging**: No sensitive data logged (images, personal info)
3. **Network**: Function runs in AWS managed VPC by default
4. **Encryption**: All data encrypted in transit and at rest
5. **Access Control**: Least privilege IAM permissions

## Support

For deployment issues:
1. Check CloudWatch logs for errors
2. Verify IAM permissions
3. Validate configuration files
4. Run deployment validation tests
5. Contact development team with error details