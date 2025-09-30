# Makefile for Image Analysis Lambda function deployment

.PHONY: help install test package deploy clean validate

# Default environment
ENV ?= production
PROFILE ?= default

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt -t . --upgrade

test: ## Run tests
	python -m pytest . -v

validate: ## Validate deployment configuration
	python test_deployment.py

package: clean install ## Create deployment package
	@echo "Creating deployment package..."
	zip -r deployment-package.zip . \
		-x "*.git*" \
		-x "*__pycache__*" \
		-x "*.pyc" \
		-x "*test_*" \
		-x "*.zip" \
		-x "deploy.py" \
		-x "deploy.sh" \
		-x "deploy.ps1" \
		-x "Makefile" \
		-x "lambda_config.json" \
		-x "env_configs/*" \
		-x "iam_policy.json" \
		-x "trust_policy.json" \
		-x "README.md" \
		-x ".pytest_cache/*"
	@echo "Package created: deployment-package.zip"

deploy-dev: ## Deploy to development environment
	$(MAKE) deploy ENV=development

deploy-staging: ## Deploy to staging environment
	$(MAKE) deploy ENV=staging

deploy-prod: ## Deploy to production environment
	$(MAKE) deploy ENV=production

deploy: package validate ## Deploy to specified environment
	@echo "Deploying to $(ENV) environment with profile $(PROFILE)..."
	python deploy.py --environment $(ENV) --profile $(PROFILE)

deploy-code-only: package ## Deploy only code changes (faster)
	@echo "Deploying code changes to $(ENV) environment..."
	aws lambda update-function-code \
		--function-name image-analysis-tool \
		--zip-file fileb://deployment-package.zip \
		--profile $(PROFILE)

clean: ## Clean build artifacts
	rm -f deployment-package.zip
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache

logs: ## View Lambda function logs
	aws logs tail /aws/lambda/image-analysis-tool --follow --profile $(PROFILE)

invoke-test: ## Test invoke the Lambda function
	aws lambda invoke \
		--function-name image-analysis-tool \
		--payload '{"test": true}' \
		--profile $(PROFILE) \
		response.json
	cat response.json
	rm response.json

setup-iam: ## Create IAM role and policies (requires admin permissions)
	@echo "Creating IAM role for Lambda function..."
	aws iam create-role \
		--role-name lambda-image-analysis-role \
		--assume-role-policy-document file://trust_policy.json \
		--profile $(PROFILE)
	
	aws iam put-role-policy \
		--role-name lambda-image-analysis-role \
		--policy-name lambda-image-analysis-policy \
		--policy-document file://iam_policy.json \
		--profile $(PROFILE)
	
	@echo "IAM role created: lambda-image-analysis-role"

status: ## Check Lambda function status
	aws lambda get-function \
		--function-name image-analysis-tool \
		--profile $(PROFILE) \
		--query 'Configuration.{State:State,LastModified:LastModified,Runtime:Runtime,MemorySize:MemorySize,Timeout:Timeout}'

config: ## Show current function configuration
	aws lambda get-function-configuration \
		--function-name image-analysis-tool \
		--profile $(PROFILE)

# Development helpers
dev-install: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-mock

dev-test: ## Run tests in development mode
	python -m pytest . -v --tb=short

dev-watch: ## Watch for changes and run tests
	@echo "Watching for changes... (requires entr: brew install entr)"
	find . -name "*.py" | entr -c python -m pytest . -v