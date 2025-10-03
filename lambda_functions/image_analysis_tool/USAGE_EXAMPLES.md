# Usage Examples for Image Analysis Tool

This document provides comprehensive examples of how to use the Image Analysis Tool Lambda function in various programming languages and scenarios.

## Table of Contents

1. [Python Examples](#python-examples)
2. [JavaScript/Node.js Examples](#javascriptnodejs-examples)
3. [cURL Examples](#curl-examples)
4. [AWS CLI Examples](#aws-cli-examples)
5. [Web Frontend Examples](#web-frontend-examples)
6. [Error Handling Examples](#error-handling-examples)
7. [Testing Examples](#testing-examples)

## Python Examples

### Basic Usage with boto3

```python
import boto3
import base64
import json

def analyze_medication_image(image_path, prompt=None):
    """
    Analyze a medication image using the Image Analysis Tool.
    
    Args:
        image_path (str): Path to the image file
        prompt (str, optional): Custom analysis prompt
    
    Returns:
        dict: Analysis results
    """
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Read and encode image
    with open(image_path, 'rb') as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Prepare payload
    payload = {
        "input": {
            "RequestBody": {
                "content": {
                    "application/json": {
                        "properties": [
                            {
                                "name": "image_data",
                                "value": image_data
                            }
                        ]
                    }
                }
            }
        }
    }
    
    # Add custom prompt if provided
    if prompt:
        payload["input"]["RequestBody"]["content"]["application/json"]["properties"].append({
            "name": "prompt",
            "value": prompt
        })
    
    # Invoke Lambda function
    response = lambda_client.invoke(
        FunctionName='image-analysis-tool',
        Payload=json.dumps(payload)
    )
    
    # Parse response
    response_payload = json.loads(response['Payload'].read())
    
    if 'response' in response_payload:
        body = json.loads(response_payload['response']['responseBody']['application/json']['body'])
        return body
    else:
        return response_payload

# Example usage
if __name__ == "__main__":
    try:
        result = analyze_medication_image('medication_photo.jpg')
        
        if result['success']:
            medication = result['medication_identification']
            print(f"Medication: {medication['medication_name']}")
            print(f"Dosage: {medication['dosage']}")
            print(f"Confidence: {medication['confidence']:.2%}")
            
            if result['drug_information']['available']:
                drug_info = result['drug_information']
                print(f"Purpose: {drug_info['purpose']}")
                print(f"Warnings: {drug_info['warnings'][:100]}...")
        else:
            print(f"Error: {result['error']}")
            if 'suggestions' in result:
                print("Suggestions:")
                for suggestion in result['suggestions']:
                    print(f"  - {suggestion}")
                    
    except Exception as e:
        print(f"Failed to analyze image: {e}")
```

### Advanced Usage with Error Handling and Retry

```python
import boto3
import base64
import json
import time
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError

class MedicationImageAnalyzer:
    """Advanced medication image analyzer with retry logic and error handling."""
    
    def __init__(self, region_name='us-east-1', function_name='image-analysis-tool'):
        self.lambda_client = boto3.client('lambda', region_name=region_name)
        self.function_name = function_name
        self.max_retries = 3
        self.retry_delay = 1.0
    
    def analyze_image(self, image_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze medication image with retry logic.
        
        Args:
            image_path: Path to image file
            prompt: Optional custom prompt
            
        Returns:
            Analysis results dictionary
        """
        # Validate image file
        if not self._validate_image_file(image_path):
            return {
                'success': False,
                'error': 'Invalid image file',
                'error_type': 'validation_error'
            }
        
        # Encode image
        try:
            image_data = self._encode_image(image_path)
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to encode image: {str(e)}',
                'error_type': 'image_processing_error'
            }
        
        # Prepare payload
        payload = self._build_payload(image_data, prompt)
        
        # Invoke with retry logic
        for attempt in range(self.max_retries):
            try:
                result = self._invoke_lambda(payload)
                
                # Check for retryable errors
                if not result['success'] and self._is_retryable_error(result):
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                
                return result
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['TooManyRequestsException', 'ServiceException'] and attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    return {
                        'success': False,
                        'error': f'AWS Error: {error_code}',
                        'error_type': 'system_error'
                    }
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    return {
                        'success': False,
                        'error': f'Unexpected error: {str(e)}',
                        'error_type': 'system_error'
                    }
        
        return {
            'success': False,
            'error': 'Max retries exceeded',
            'error_type': 'timeout_error'
        }
    
    def _validate_image_file(self, image_path: str) -> bool:
        """Validate image file exists and has valid extension."""
        import os
        if not os.path.exists(image_path):
            return False
        
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        _, ext = os.path.splitext(image_path.lower())
        return ext in valid_extensions
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _build_payload(self, image_data: str, prompt: Optional[str]) -> Dict[str, Any]:
        """Build Lambda payload."""
        properties = [{"name": "image_data", "value": image_data}]
        
        if prompt:
            properties.append({"name": "prompt", "value": prompt})
        
        return {
            "input": {
                "RequestBody": {
                    "content": {
                        "application/json": {
                            "properties": properties
                        }
                    }
                }
            }
        }
    
    def _invoke_lambda(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke Lambda function and parse response."""
        response = self.lambda_client.invoke(
            FunctionName=self.function_name,
            Payload=json.dumps(payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if 'response' in response_payload:
            return json.loads(response_payload['response']['responseBody']['application/json']['body'])
        else:
            return response_payload
    
    def _is_retryable_error(self, result: Dict[str, Any]) -> bool:
        """Check if error is retryable."""
        retryable_types = ['timeout_error', 'system_error', 'vision_model_error']
        return result.get('error_type') in retryable_types

# Example usage
analyzer = MedicationImageAnalyzer()
result = analyzer.analyze_image('medication.jpg', 'Identify this medication and its strength')

if result['success']:
    print(f"Identified: {result['medication_identification']['medication_name']}")
else:
    print(f"Analysis failed: {result['error']}")
```

## JavaScript/Node.js Examples

### Basic Usage with AWS SDK v3

```javascript
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";
import { readFileSync } from 'fs';

class MedicationAnalyzer {
    constructor(region = 'us-east-1') {
        this.lambdaClient = new LambdaClient({ region });
        this.functionName = 'image-analysis-tool';
    }

    async analyzeImage(imagePath, prompt = null) {
        try {
            // Read and encode image
            const imageBuffer = readFileSync(imagePath);
            const imageData = imageBuffer.toString('base64');

            // Build payload
            const properties = [
                { name: 'image_data', value: imageData }
            ];

            if (prompt) {
                properties.push({ name: 'prompt', value: prompt });
            }

            const payload = {
                input: {
                    RequestBody: {
                        content: {
                            'application/json': {
                                properties: properties
                            }
                        }
                    }
                }
            };

            // Invoke Lambda
            const command = new InvokeCommand({
                FunctionName: this.functionName,
                Payload: JSON.stringify(payload)
            });

            const response = await this.lambdaClient.send(command);
            const responsePayload = JSON.parse(new TextDecoder().decode(response.Payload));

            if (responsePayload.response) {
                return JSON.parse(responsePayload.response.responseBody['application/json'].body);
            } else {
                return responsePayload;
            }

        } catch (error) {
            return {
                success: false,
                error: `Failed to analyze image: ${error.message}`,
                error_type: 'system_error'
            };
        }
    }

    async analyzeImageWithRetry(imagePath, prompt = null, maxRetries = 3) {
        for (let attempt = 0; attempt < maxRetries; attempt++) {
            const result = await this.analyzeImage(imagePath, prompt);

            if (result.success || !this.isRetryableError(result)) {
                return result;
            }

            if (attempt < maxRetries - 1) {
                await this.delay(1000 * Math.pow(2, attempt)); // Exponential backoff
            }
        }

        return {
            success: false,
            error: 'Max retries exceeded',
            error_type: 'timeout_error'
        };
    }

    isRetryableError(result) {
        const retryableTypes = ['timeout_error', 'system_error', 'vision_model_error'];
        return retryableTypes.includes(result.error_type);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Example usage
async function main() {
    const analyzer = new MedicationAnalyzer();
    
    try {
        const result = await analyzer.analyzeImageWithRetry('medication.jpg');
        
        if (result.success) {
            const medication = result.medication_identification;
            console.log(`Medication: ${medication.medication_name}`);
            console.log(`Dosage: ${medication.dosage}`);
            console.log(`Confidence: ${(medication.confidence * 100).toFixed(1)}%`);
            
            if (result.drug_information.available) {
                console.log(`Purpose: ${result.drug_information.purpose}`);
            }
        } else {
            console.error(`Error: ${result.error}`);
            if (result.suggestions) {
                console.log('Suggestions:');
                result.suggestions.forEach(suggestion => {
                    console.log(`  - ${suggestion}`);
                });
            }
        }
    } catch (error) {
        console.error('Failed to analyze medication:', error);
    }
}

main();
```

### Web Frontend Integration

```javascript
// Frontend JavaScript for web applications
class WebMedicationAnalyzer {
    constructor(apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
    }

    async analyzeImageFile(file, prompt = null) {
        try {
            // Validate file
            if (!this.validateImageFile(file)) {
                throw new Error('Invalid image file. Please use JPEG, PNG, or WebP format.');
            }

            // Convert to base64
            const imageData = await this.fileToBase64(file);

            // Build request
            const requestBody = {
                image_data: imageData
            };

            if (prompt) {
                requestBody.prompt = prompt;
            }

            // Send request
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();

        } catch (error) {
            return {
                success: false,
                error: error.message,
                error_type: 'system_error'
            };
        }
    }

    validateImageFile(file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
        const maxSize = 10 * 1024 * 1024; // 10MB

        return validTypes.includes(file.type) && file.size <= maxSize;
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                // Remove data:image/jpeg;base64, prefix
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = error => reject(error);
        });
    }
}

// HTML usage example
/*
<input type="file" id="imageInput" accept="image/*">
<button onclick="analyzeImage()">Analyze Medication</button>
<div id="results"></div>

<script>
const analyzer = new WebMedicationAnalyzer('/api/analyze-medication');

async function analyzeImage() {
    const fileInput = document.getElementById('imageInput');
    const resultsDiv = document.getElementById('results');
    
    if (!fileInput.files[0]) {
        resultsDiv.innerHTML = '<p style="color: red;">Please select an image file.</p>';
        return;
    }
    
    resultsDiv.innerHTML = '<p>Analyzing image...</p>';
    
    const result = await analyzer.analyzeImageFile(fileInput.files[0]);
    
    if (result.success) {
        const medication = result.medication_identification;
        resultsDiv.innerHTML = `
            <h3>Analysis Results</h3>
            <p><strong>Medication:</strong> ${medication.medication_name}</p>
            <p><strong>Dosage:</strong> ${medication.dosage}</p>
            <p><strong>Confidence:</strong> ${(medication.confidence * 100).toFixed(1)}%</p>
            ${result.drug_information.available ? 
                `<p><strong>Purpose:</strong> ${result.drug_information.purpose}</p>` : 
                '<p>No additional drug information available.</p>'
            }
        `;
    } else {
        resultsDiv.innerHTML = `
            <p style="color: red;">Error: ${result.error}</p>
            ${result.suggestions ? 
                '<ul>' + result.suggestions.map(s => `<li>${s}</li>`).join('') + '</ul>' : 
                ''
            }
        `;
    }
}
</script>
*/
```

## cURL Examples

### Basic Request

```bash
# Encode image to base64 first
IMAGE_DATA=$(base64 -w 0 medication.jpg)

# Make request
curl -X POST \
  https://lambda-url.us-east-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d "{
    \"input\": {
      \"RequestBody\": {
        \"content\": {
          \"application/json\": {
            \"properties\": [
              {
                \"name\": \"image_data\",
                \"value\": \"$IMAGE_DATA\"
              }
            ]
          }
        }
      }
    }
  }"
```

### Request with Custom Prompt

```bash
IMAGE_DATA=$(base64 -w 0 medication.jpg)

curl -X POST \
  https://lambda-url.us-east-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d "{
    \"input\": {
      \"RequestBody\": {
        \"content\": {
          \"application/json\": {
            \"properties\": [
              {
                \"name\": \"image_data\",
                \"value\": \"$IMAGE_DATA\"
              },
              {
                \"name\": \"prompt\",
                \"value\": \"Identify the medication name, strength, and manufacturer from this image\"
              }
            ]
          }
        }
      }
    }
  }" | jq '.'
```

## AWS CLI Examples

### Direct Lambda Invocation

```bash
# Create payload file
cat > payload.json << EOF
{
  "input": {
    "RequestBody": {
      "content": {
        "application/json": {
          "properties": [
            {
              "name": "image_data",
              "value": "$(base64 -w 0 medication.jpg)"
            }
          ]
        }
      }
    }
  }
}
EOF

# Invoke Lambda function
aws lambda invoke \
  --function-name image-analysis-tool \
  --payload file://payload.json \
  response.json

# View response
cat response.json | jq '.'
```

### Batch Processing Script

```bash
#!/bin/bash
# Process multiple images

FUNCTION_NAME="image-analysis-tool"
RESULTS_DIR="results"

mkdir -p "$RESULTS_DIR"

for image in *.jpg *.png *.webp; do
    if [ -f "$image" ]; then
        echo "Processing $image..."
        
        # Create payload
        IMAGE_DATA=$(base64 -w 0 "$image")
        cat > temp_payload.json << EOF
{
  "input": {
    "RequestBody": {
      "content": {
        "application/json": {
          "properties": [
            {
              "name": "image_data",
              "value": "$IMAGE_DATA"
            }
          ]
        }
      }
    }
  }
}
EOF

        # Invoke function
        aws lambda invoke \
          --function-name "$FUNCTION_NAME" \
          --payload file://temp_payload.json \
          "$RESULTS_DIR/${image%.*}_result.json"
        
        # Extract medication name if successful
        if jq -e '.response.responseBody."application/json".body | fromjson | .success' "$RESULTS_DIR/${image%.*}_result.json" > /dev/null; then
            MEDICATION=$(jq -r '.response.responseBody."application/json".body | fromjson | .medication_identification.medication_name' "$RESULTS_DIR/${image%.*}_result.json")
            echo "  ✓ Identified: $MEDICATION"
        else
            ERROR=$(jq -r '.response.responseBody."application/json".body | fromjson | .error' "$RESULTS_DIR/${image%.*}_result.json")
            echo "  ✗ Error: $ERROR"
        fi
        
        rm temp_payload.json
    fi
done

echo "Batch processing complete. Results in $RESULTS_DIR/"
```

## Error Handling Examples

### Comprehensive Error Handling in Python

```python
def handle_analysis_result(result):
    """Handle different types of analysis results and errors."""
    
    if result['success']:
        medication = result['medication_identification']
        confidence = medication['confidence']
        
        if confidence >= 0.9:
            print(f"✓ High confidence identification: {medication['medication_name']}")
        elif confidence >= 0.7:
            print(f"⚠ Medium confidence identification: {medication['medication_name']}")
            print("  Consider retaking the photo for better accuracy")
        else:
            print(f"⚠ Low confidence identification: {medication['medication_name']}")
            print("  Please verify the result manually")
        
        # Handle drug information
        if result['drug_information']['available']:
            print("✓ Drug information retrieved successfully")
        else:
            print("⚠ Drug information not available")
        
        return True
    
    else:
        error_type = result.get('error_type', 'unknown')
        error_message = result.get('error', 'Unknown error')
        suggestions = result.get('suggestions', [])
        
        print(f"✗ Analysis failed ({error_type}): {error_message}")
        
        # Provide specific guidance based on error type
        if error_type == 'validation_error':
            print("  → Check image format and size")
        elif error_type == 'image_processing_error':
            print("  → Try a different image or check image quality")
        elif error_type == 'vision_model_error':
            print("  → Retake photo with better lighting and focus")
        elif error_type == 'timeout_error':
            print("  → Try again later or use a smaller image")
        elif error_type == 'system_error':
            print("  → Contact support if problem persists")
        
        if suggestions:
            print("  Suggestions:")
            for suggestion in suggestions:
                print(f"    • {suggestion}")
        
        return False

# Usage example with error handling
try:
    result = analyze_medication_image('medication.jpg')
    success = handle_analysis_result(result)
    
    if not success:
        # Implement fallback logic
        print("Consider manual medication lookup or consult healthcare provider")
        
except Exception as e:
    print(f"Unexpected error: {e}")
    print("Please try again or contact support")
```

## Testing Examples

### Unit Test Example

```python
import unittest
from unittest.mock import patch, MagicMock
import json

class TestMedicationAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = MedicationImageAnalyzer()
    
    @patch('boto3.client')
    def test_successful_analysis(self, mock_boto_client):
        # Mock Lambda response
        mock_lambda = MagicMock()
        mock_boto_client.return_value = mock_lambda
        
        mock_response = {
            'Payload': MagicMock()
        }
        
        mock_payload_data = {
            'response': {
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'success': True,
                            'medication_identification': {
                                'medication_name': 'Advil',
                                'dosage': '200mg',
                                'confidence': 0.95
                            },
                            'drug_information': {
                                'available': True,
                                'purpose': 'Pain reliever'
                            }
                        })
                    }
                }
            }
        }
        
        mock_response['Payload'].read.return_value = json.dumps(mock_payload_data).encode()
        mock_lambda.invoke.return_value = mock_response
        
        # Test
        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            result = self.analyzer.analyze_image('test_image.jpg')
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertEqual(result['medication_identification']['medication_name'], 'Advil')
        self.assertEqual(result['medication_identification']['confidence'], 0.95)
    
    def test_image_validation(self):
        # Test invalid file extension
        self.assertFalse(self.analyzer._validate_image_file('test.txt'))
        
        # Test valid file extension (assuming file exists)
        with patch('os.path.exists', return_value=True):
            self.assertTrue(self.analyzer._validate_image_file('test.jpg'))

if __name__ == '__main__':
    unittest.main()
```

### Integration Test Example

```python
import pytest
import tempfile
import os
from PIL import Image

class TestImageAnalysisIntegration:
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample test image."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color='white')
            img.save(tmp.name, 'JPEG')
            yield tmp.name
        os.unlink(tmp.name)
    
    def test_end_to_end_analysis(self, sample_image):
        """Test complete analysis workflow."""
        analyzer = MedicationImageAnalyzer()
        
        # This would require actual AWS credentials and deployed function
        # result = analyzer.analyze_image(sample_image)
        # assert 'success' in result
        
        # For testing without AWS, mock the response
        pass
    
    def test_image_encoding(self, sample_image):
        """Test image encoding functionality."""
        analyzer = MedicationImageAnalyzer()
        
        encoded = analyzer._encode_image(sample_image)
        assert isinstance(encoded, str)
        assert len(encoded) > 0
        
        # Verify it's valid base64
        import base64
        try:
            decoded = base64.b64decode(encoded)
            assert len(decoded) > 0
        except Exception:
            pytest.fail("Invalid base64 encoding")
```

These examples provide comprehensive coverage of how to use the Image Analysis Tool in various scenarios, programming languages, and environments. Each example includes proper error handling and follows best practices for production use.