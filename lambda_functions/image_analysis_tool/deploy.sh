#!/bin/bash

# Deployment script for Image Analysis Lambda function
# Usage: ./deploy.sh [environment] [aws-profile]

set -e

# Configuration
FUNCTION_NAME="image-analysis-tool"
ENVIRONMENT=${1:-production}
AWS_PROFILE=${2:-default}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Deploying Image Analysis Lambda function..."
echo "Environment: $ENVIRONMENT"
echo "AWS Profile: $AWS_PROFILE"
echo "Function Directory: $SCRIPT_DIR"

# Clean up previous builds
echo "Cleaning up previous builds..."
rm -f "$SCRIPT_DIR/deployment-package.zip"
find "$SCRIPT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null || true

# Install dependencies
echo "Installing dependencies..."
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -r "$SCRIPT_DIR/requirements.txt" -t "$SCRIPT_DIR" --upgrade
else
    echo "No requirements.txt found, skipping dependency installation"
fi

# Create deployment package
echo "Creating deployment package..."
cd "$SCRIPT_DIR"
zip -r deployment-package.zip . \
    -x "*.git*" \
    -x "*__pycache__*" \
    -x "*.pyc" \
    -x "*test_*" \
    -x "*.zip" \
    -x "deploy.py" \
    -x "deploy.sh" \
    -x "lambda_config.json" \
    -x "env_configs/*" \
    -x "iam_policy.json" \
    -x "trust_policy.json" \
    -x "README.md" \
    -x ".pytest_cache/*"

# Validate package size
PACKAGE_SIZE=$(stat -f%z deployment-package.zip 2>/dev/null || stat -c%s deployment-package.zip)
MAX_SIZE=$((50 * 1024 * 1024))  # 50MB

if [ "$PACKAGE_SIZE" -gt "$MAX_SIZE" ]; then
    echo "Error: Package size ($((PACKAGE_SIZE / 1024 / 1024))MB) exceeds 50MB limit"
    exit 1
fi

echo "Package size: $((PACKAGE_SIZE / 1024 / 1024))MB"

# Load environment configuration
ENV_CONFIG_FILE="$SCRIPT_DIR/env_configs/$ENVIRONMENT.json"
if [ ! -f "$ENV_CONFIG_FILE" ]; then
    echo "Error: Environment configuration not found: $ENV_CONFIG_FILE"
    exit 1
fi

# Extract configuration values
MEMORY_SIZE=$(jq -r '.MemorySize' "$ENV_CONFIG_FILE")
TIMEOUT=$(jq -r '.Timeout' "$ENV_CONFIG_FILE")
ENV_VARS=$(jq -c '.Environment.Variables' "$ENV_CONFIG_FILE")

echo "Configuration loaded for $ENVIRONMENT environment"
echo "Memory: ${MEMORY_SIZE}MB, Timeout: ${TIMEOUT}s"

# Deploy function
echo "Deploying Lambda function..."

# Check if function exists
if aws lambda get-function --function-name "$FUNCTION_NAME" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
    echo "Function exists, updating..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file fileb://deployment-package.zip \
        --profile "$AWS_PROFILE"
    
    # Update function configuration
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --memory-size "$MEMORY_SIZE" \
        --timeout "$TIMEOUT" \
        --environment "Variables=$ENV_VARS" \
        --profile "$AWS_PROFILE"
else
    echo "Function does not exist, creating..."
    echo "Note: You need to set the correct IAM role ARN in lambda_config.json"
    
    # This would create the function, but requires proper IAM role setup
    # aws lambda create-function \
    #     --function-name "$FUNCTION_NAME" \
    #     --runtime python3.9 \
    #     --role "arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role" \
    #     --handler app.lambda_handler \
    #     --zip-file fileb://deployment-package.zip \
    #     --memory-size "$MEMORY_SIZE" \
    #     --timeout "$TIMEOUT" \
    #     --environment "Variables=$ENV_VARS" \
    #     --profile "$AWS_PROFILE"
fi

echo "Deployment completed successfully!"
echo "Package location: $SCRIPT_DIR/deployment-package.zip"