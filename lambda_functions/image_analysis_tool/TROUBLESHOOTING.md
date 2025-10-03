# Troubleshooting Guide for Image Analysis Tool

This guide helps diagnose and resolve common issues with the Image Analysis Tool Lambda function.

## Table of Contents

1. [Common Error Messages](#common-error-messages)
2. [Image-Related Issues](#image-related-issues)
3. [Performance Issues](#performance-issues)
4. [Integration Issues](#integration-issues)
5. [Deployment Issues](#deployment-issues)
6. [Monitoring and Debugging](#monitoring-and-debugging)
7. [FAQ](#faq)

## Common Error Messages

### "No image data provided. Please upload an image of the medication."

**Cause:** The request doesn't contain valid image data in the expected format.

**Solutions:**
1. Ensure the `image_data` parameter contains base64-encoded image data
2. Check that the request format matches one of the supported formats
3. Verify the image was properly encoded before sending

**Example Fix:**
```python
# Incorrect - missing base64 encoding
payload = {"image_data": "path/to/image.jpg"}

# Correct - properly encoded
import base64
with open("path/to/image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')
payload = {"image_data": image_data}
```

### "Image format not supported. Please use JPEG, PNG, or WebP."

**Cause:** The uploaded image is in an unsupported format.

**Solutions:**
1. Convert image to JPEG, PNG, or WebP format
2. Check file extension matches actual format
3. Ensure image isn't corrupted

**Supported Formats:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- WebP (.webp)

**Conversion Example:**
```python
from PIL import Image

# Convert any image to JPEG
img = Image.open("image.bmp")
img = img.convert("RGB")
img.save("image.jpg", "JPEG")
```

### "Image size exceeds maximum limit of 10MB."

**Cause:** The image file is too large.

**Solutions:**
1. Compress the image before uploading
2. Resize the image to smaller dimensions
3. Use JPEG format with lower quality settings

**Compression Example:**
```python
from PIL import Image

def compress_image(input_path, output_path, max_size_mb=10):
    img = Image.open(input_path)
    
    # Calculate target size
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Start with quality 95 and reduce if needed
    quality = 95
    while quality > 10:
        img.save(output_path, "JPEG", quality=quality, optimize=True)
        
        if os.path.getsize(output_path) <= max_size_bytes:
            break
        quality -= 10
    
    return output_path
```

### "No medication clearly visible in the image."

**Cause:** The vision model cannot identify medication in the image.

**Solutions:**
1. Ensure medication is clearly visible and in focus
2. Improve lighting conditions
3. Remove obstructions or clutter from the image
4. Take photo from a better angle
5. Use a plain, contrasting background

**Best Practices for Medication Photos:**
- Fill the frame with the medication
- Use good, even lighting (avoid shadows)
- Ensure text/labels are readable
- Keep camera steady to avoid blur
- Use plain background (white paper works well)

### "Vision model timeout. Please try again."

**Cause:** The vision model API call timed out.

**Solutions:**
1. Retry the request (often resolves temporary issues)
2. Use a smaller image file
3. Check network connectivity
4. Try again during off-peak hours

**Retry Logic Example:**
```python
import time

def analyze_with_retry(image_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = analyze_medication_image(image_path)
            if result['success'] or result['error_type'] != 'timeout_error':
                return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
        
        # Exponential backoff
        time.sleep(2 ** attempt)
    
    return {'success': False, 'error': 'Max retries exceeded'}
```

### "Drug information lookup failed."

**Cause:** The DrugInfoTool integration encountered an error.

**Solutions:**
1. Check if the medication name was correctly identified
2. Verify DrugInfoTool is deployed and accessible
3. Check IAM permissions for Lambda-to-Lambda calls
4. Review DrugInfoTool logs for specific errors

**Debug Steps:**
1. Check CloudWatch logs for both functions
2. Verify the medication name being passed to DrugInfoTool
3. Test DrugInfoTool independently with the same medication name

## Image-Related Issues

### Blurry or Low-Quality Images

**Symptoms:**
- Low confidence scores (< 0.7)
- Incorrect medication identification
- "Image quality too poor" errors

**Solutions:**
1. **Camera Settings:**
   - Use autofocus or manual focus
   - Ensure adequate lighting
   - Hold camera steady or use tripod
   - Clean camera lens

2. **Image Composition:**
   - Get closer to the medication
   - Fill frame with medication
   - Use macro mode if available
   - Avoid extreme angles

3. **Post-Processing:**
   ```python
   from PIL import Image, ImageEnhance
   
   def enhance_image(image_path):
       img = Image.open(image_path)
       
       # Enhance sharpness
       enhancer = ImageEnhance.Sharpness(img)
       img = enhancer.enhance(1.5)
       
       # Enhance contrast
       enhancer = ImageEnhance.Contrast(img)
       img = enhancer.enhance(1.2)
       
       return img
   ```

### Multiple Medications in Image

**Symptoms:**
- Inconsistent results
- Wrong medication identified
- Low confidence scores

**Solutions:**
1. **Single Medication Photos:**
   - Photograph one medication at a time
   - Remove other medications from frame
   - Focus on the primary medication

2. **Custom Prompts:**
   ```python
   prompt = "Identify the largest/most prominent medication in this image"
   result = analyze_medication_image(image_path, prompt)
   ```

### Poor Lighting Conditions

**Symptoms:**
- Dark or shadowy images
- Unreadable text on medication
- Low confidence scores

**Solutions:**
1. **Natural Light:** Use daylight near a window
2. **Artificial Light:** Use bright, even lighting
3. **Avoid Flash:** Can create harsh shadows and glare
4. **Light Positioning:** Light source should be behind or beside camera

### Reflective Surfaces and Glare

**Symptoms:**
- Bright spots obscuring text
- Unreadable labels
- Vision model errors

**Solutions:**
1. **Angle Adjustment:** Change camera angle to avoid reflections
2. **Lighting Position:** Move light source to reduce glare
3. **Matte Background:** Use non-reflective surface
4. **Polarizing Filter:** If using professional camera

## Performance Issues

### Slow Response Times

**Symptoms:**
- Processing takes > 10 seconds
- Timeout errors
- Poor user experience

**Diagnostic Steps:**
1. **Check CloudWatch Metrics:**
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value=image-analysis-tool \
     --start-time 2024-01-01T00:00:00Z \
     --end-time 2024-01-02T00:00:00Z \
     --period 300 \
     --statistics Average,Maximum
   ```

2. **Review Function Logs:**
   ```bash
   aws logs tail /aws/lambda/image-analysis-tool --follow
   ```

**Optimization Solutions:**
1. **Image Size:** Reduce image size before processing
2. **Memory Allocation:** Increase Lambda memory (up to 1024MB)
3. **Timeout Settings:** Increase timeout (up to 300 seconds)
4. **Cold Start:** Implement warming strategies

### Memory Issues

**Symptoms:**
- "Runtime exited with error: signal: killed" errors
- Out of memory errors in logs
- Function timeouts with large images

**Solutions:**
1. **Increase Memory:**
   ```bash
   aws lambda update-function-configuration \
     --function-name image-analysis-tool \
     --memory-size 1024
   ```

2. **Image Optimization:**
   ```python
   def optimize_for_memory(image_path, max_dimension=1024):
       img = Image.open(image_path)
       
       # Resize if too large
       if max(img.size) > max_dimension:
           ratio = max_dimension / max(img.size)
           new_size = tuple(int(dim * ratio) for dim in img.size)
           img = img.resize(new_size, Image.Resampling.LANCZOS)
       
       return img
   ```

### High Error Rates

**Symptoms:**
- > 5% error rate in CloudWatch metrics
- Frequent timeout or system errors
- Inconsistent results

**Investigation Steps:**
1. **Error Analysis:**
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/image-analysis-tool \
     --filter-pattern "ERROR" \
     --start-time 1640995200000
   ```

2. **Performance Monitoring:**
   - Check Bedrock API limits and quotas
   - Monitor DrugInfoTool performance
   - Review network connectivity

## Integration Issues

### DrugInfoTool Integration Failures

**Symptoms:**
- Medication identified but no drug information
- "Drug information lookup failed" errors
- Partial responses

**Diagnostic Steps:**
1. **Check IAM Permissions:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": "lambda:InvokeFunction",
         "Resource": "arn:aws:lambda:*:*:function:drug-info-tool"
       }
     ]
   }
   ```

2. **Test DrugInfoTool Independently:**
   ```bash
   aws lambda invoke \
     --function-name drug-info-tool \
     --payload '{"drug_name": "Advil"}' \
     response.json
   ```

3. **Check Function Versions:**
   - Ensure both functions are using compatible versions
   - Verify function names and ARNs are correct

### Bedrock API Issues

**Symptoms:**
- "Access denied" errors
- "Model not found" errors
- Vision analysis failures

**Solutions:**
1. **Check Bedrock Permissions:**
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

2. **Verify Model Access:**
   ```bash
   aws bedrock list-foundation-models \
     --region us-east-1
   ```

3. **Check Model ID:**
   - Ensure model ID in config matches available models
   - Verify model supports multimodal input

## Deployment Issues

### Function Deployment Failures

**Common Issues:**
1. **Package Size Too Large:**
   ```bash
   # Check package size
   ls -lh deployment-package.zip
   
   # If > 50MB, optimize:
   # - Remove unnecessary files
   # - Use Lambda layers for large dependencies
   # - Compress images and assets
   ```

2. **Missing Dependencies:**
   ```bash
   # Ensure all requirements are installed
   pip install -r requirements.txt -t .
   
   # Check for missing imports
   python -c "import app; print('All imports successful')"
   ```

3. **Permission Issues:**
   ```bash
   # Check IAM role exists and has correct policies
   aws iam get-role --role-name lambda-image-analysis-role
   aws iam list-attached-role-policies --role-name lambda-image-analysis-role
   ```

### Environment Configuration Issues

**Symptoms:**
- Function works locally but fails in AWS
- Configuration-related errors
- Environment variable issues

**Solutions:**
1. **Verify Environment Variables:**
   ```bash
   aws lambda get-function-configuration \
     --function-name image-analysis-tool \
     --query 'Environment.Variables'
   ```

2. **Check Configuration Files:**
   ```python
   # Ensure config files are included in deployment
   import os
   print(os.listdir('.'))  # Should include env_configs/
   ```

3. **Test Configuration Loading:**
   ```python
   from config import config
   print(f"Environment: {config.ENVIRONMENT}")
   print(f"Model ID: {config.BEDROCK_MODEL_ID}")
   ```

## Monitoring and Debugging

### CloudWatch Logs Analysis

**Key Log Patterns to Monitor:**
```bash
# Error patterns
aws logs filter-log-events \
  --log-group-name /aws/lambda/image-analysis-tool \
  --filter-pattern "ERROR"

# Performance patterns
aws logs filter-log-events \
  --log-group-name /aws/lambda/image-analysis-tool \
  --filter-pattern "processing_time"

# Vision model issues
aws logs filter-log-events \
  --log-group-name /aws/lambda/image-analysis-tool \
  --filter-pattern "vision_analysis"
```

### Custom Metrics Dashboard

**Key Metrics to Monitor:**
- Request success rate
- Average processing time
- Vision model confidence scores
- Error rates by type
- Memory utilization

**CloudWatch Dashboard Example:**
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Duration", "FunctionName", "image-analysis-tool"],
          ["AWS/Lambda", "Errors", "FunctionName", "image-analysis-tool"],
          ["AWS/Lambda", "Invocations", "FunctionName", "image-analysis-tool"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Performance"
      }
    }
  ]
}
```

### Debug Mode

**Enable Debug Logging:**
```python
# Set LOG_LEVEL to DEBUG in environment config
import logging
logging.getLogger().setLevel(logging.DEBUG)

# Add debug statements in code
logger.debug(f"Image size: {len(image_data)} bytes")
logger.debug(f"Vision response: {vision_response}")
```

**Local Testing:**
```python
# Test function locally with debug output
import json
from app import lambda_handler

event = {
    "image_data": "base64_encoded_test_image",
    "prompt": "Test prompt"
}

context = type('Context', (), {
    'aws_request_id': 'test-request-id',
    'function_name': 'test-function'
})()

result = lambda_handler(event, context)
print(json.dumps(result, indent=2))
```

## FAQ

### Q: Why is my medication not being identified correctly?

**A:** Common causes include:
- Poor image quality (blurry, dark, or low resolution)
- Multiple medications in the same image
- Unusual medication packaging or generic brands
- Damaged or partially visible labels

**Solutions:**
- Take a clear, well-lit photo of a single medication
- Ensure labels and text are clearly visible
- Try different angles or lighting conditions
- Use the generic name if brand name isn't recognized

### Q: How can I improve identification accuracy?

**A:** Best practices:
1. **Image Quality:** Use high-resolution, well-lit photos
2. **Single Focus:** Photograph one medication at a time
3. **Clear Labels:** Ensure text and labels are readable
4. **Stable Camera:** Avoid camera shake and blur
5. **Good Background:** Use plain, contrasting backgrounds

### Q: What should I do if the function times out frequently?

**A:** Optimization steps:
1. **Reduce Image Size:** Compress images before processing
2. **Increase Memory:** Allocate more memory to the Lambda function
3. **Increase Timeout:** Extend the function timeout setting
4. **Check Dependencies:** Ensure all external services are responsive

### Q: How do I handle cases where drug information is not available?

**A:** Implementation strategies:
```python
def handle_missing_drug_info(result):
    if not result['drug_information']['available']:
        # Provide alternative information sources
        medication_name = result['medication_identification']['medication_name']
        
        return {
            'message': f'Medication identified as {medication_name}',
            'suggestions': [
                'Consult your healthcare provider for detailed information',
                'Check the medication packaging for instructions',
                'Visit the manufacturer\'s website for more details'
            ]
        }
```

### Q: Can I process multiple images in a single request?

**A:** Currently, the function processes one image per request. For multiple images:
1. **Sequential Processing:** Call the function multiple times
2. **Batch Processing:** Use AWS Step Functions for orchestration
3. **Async Processing:** Implement queue-based processing with SQS

### Q: How do I monitor function performance in production?

**A:** Monitoring setup:
1. **CloudWatch Alarms:** Set up alerts for errors and performance
2. **Custom Metrics:** Track business-specific metrics
3. **Log Analysis:** Use CloudWatch Insights for log analysis
4. **Dashboard:** Create operational dashboards
5. **Health Checks:** Implement regular function health checks

### Q: What are the security considerations for image processing?

**A:** Security measures:
1. **No Storage:** Images are processed in memory only
2. **Encryption:** All data transmission is encrypted
3. **Access Control:** Use IAM for function access
4. **Logging:** No sensitive data in logs
5. **Compliance:** Maintain HIPAA compliance for healthcare data

For additional support or issues not covered in this guide, please contact the development team with:
- Function logs from CloudWatch
- Request payload (without sensitive data)
- Error messages and timestamps
- Steps to reproduce the issue