#!/usr/bin/env python3
"""
Deployment validation tests for the Image Analysis Lambda function.
These tests verify that the deployment package and configuration are correct.
"""

import os
import json
import zipfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestDeploymentValidation(unittest.TestCase):
    """Test deployment configuration and package validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.function_dir = Path(__file__).parent
        self.package_path = self.function_dir / 'deployment-package.zip'
        
    def test_requirements_file_exists(self):
        """Test that requirements.txt exists and has necessary dependencies"""
        requirements_path = self.function_dir / 'requirements.txt'
        self.assertTrue(requirements_path.exists(), "requirements.txt not found")
        
        with open(requirements_path, 'r') as f:
            requirements = f.read()
        
        required_packages = ['boto3', 'requests', 'Pillow', 'numpy']
        for package in required_packages:
            self.assertIn(package, requirements, f"Required package {package} not found in requirements.txt")
    
    def test_lambda_config_exists(self):
        """Test that Lambda configuration file exists and is valid"""
        config_path = self.function_dir / 'lambda_config.json'
        self.assertTrue(config_path.exists(), "lambda_config.json not found")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        required_keys = ['FunctionName', 'Runtime', 'Handler', 'Timeout', 'MemorySize']
        for key in required_keys:
            self.assertIn(key, config, f"Required configuration key {key} not found")
        
        # Validate specific values
        self.assertEqual(config['Handler'], 'app.lambda_handler')
        self.assertGreaterEqual(config['Timeout'], 60)
        self.assertGreaterEqual(config['MemorySize'], 512)
    
    def test_environment_configs_exist(self):
        """Test that environment-specific configurations exist"""
        env_configs_dir = self.function_dir / 'env_configs'
        self.assertTrue(env_configs_dir.exists(), "env_configs directory not found")
        
        environments = ['development', 'staging', 'production']
        for env in environments:
            config_path = env_configs_dir / f'{env}.json'
            self.assertTrue(config_path.exists(), f"Configuration for {env} environment not found")
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate environment variables
            self.assertIn('Environment', config)
            self.assertIn('Variables', config['Environment'])
            
            env_vars = config['Environment']['Variables']
            required_env_vars = ['ENVIRONMENT', 'AWS_REGION', 'BEDROCK_MODEL_ID']
            for var in required_env_vars:
                self.assertIn(var, env_vars, f"Required environment variable {var} not found in {env} config")
    
    def test_iam_policy_exists(self):
        """Test that IAM policy file exists and has required permissions"""
        policy_path = self.function_dir / 'iam_policy.json'
        self.assertTrue(policy_path.exists(), "iam_policy.json not found")
        
        with open(policy_path, 'r') as f:
            policy = json.load(f)
        
        self.assertIn('Statement', policy)
        statements = policy['Statement']
        
        # Check for required permissions
        required_actions = [
            'logs:CreateLogGroup',
            'bedrock:InvokeModel',
            'lambda:InvokeFunction'
        ]
        
        all_actions = []
        for statement in statements:
            if 'Action' in statement:
                if isinstance(statement['Action'], list):
                    all_actions.extend(statement['Action'])
                else:
                    all_actions.append(statement['Action'])
        
        for action in required_actions:
            self.assertIn(action, all_actions, f"Required IAM action {action} not found in policy")
    
    def test_main_handler_exists(self):
        """Test that the main Lambda handler file exists"""
        handler_path = self.function_dir / 'app.py'
        self.assertTrue(handler_path.exists(), "app.py (main handler) not found")
        
        # Check that lambda_handler function exists
        with open(handler_path, 'r') as f:
            content = f.read()
        
        self.assertIn('def lambda_handler', content, "lambda_handler function not found in app.py")
    
    def test_deployment_package_validation(self):
        """Test deployment package if it exists"""
        if not self.package_path.exists():
            self.skipTest("Deployment package not found, run deployment first")
        
        # Check package size
        package_size = self.package_path.stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB
        self.assertLessEqual(package_size, max_size, 
                           f"Package size ({package_size / (1024*1024):.1f}MB) exceeds 50MB limit")
        
        # Check required files are in package
        with zipfile.ZipFile(self.package_path, 'r') as zipf:
            package_files = zipf.namelist()
            
            required_files = ['app.py', 'config.py']
            for required_file in required_files:
                self.assertIn(required_file, package_files, 
                            f"Required file {required_file} not found in package")
            
            # Check that test files are excluded
            test_files = [f for f in package_files if f.startswith('test_')]
            self.assertEqual(len(test_files), 0, "Test files should be excluded from package")
    
    def test_configuration_consistency(self):
        """Test that configurations are consistent across environments"""
        env_configs_dir = self.function_dir / 'env_configs'
        environments = ['development', 'staging', 'production']
        
        configs = {}
        for env in environments:
            config_path = env_configs_dir / f'{env}.json'
            with open(config_path, 'r') as f:
                configs[env] = json.load(f)
        
        # Check that all environments have the same structure
        base_keys = set(configs['production'].keys())
        for env in environments:
            env_keys = set(configs[env].keys())
            self.assertEqual(base_keys, env_keys, 
                           f"Configuration structure mismatch in {env} environment")
        
        # Check that environment-specific values are set correctly
        for env in environments:
            env_vars = configs[env]['Environment']['Variables']
            self.assertEqual(env_vars['ENVIRONMENT'], env, 
                           f"ENVIRONMENT variable mismatch in {env} config")

class TestDeploymentScripts(unittest.TestCase):
    """Test deployment scripts functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.function_dir = Path(__file__).parent
    
    def test_deploy_script_exists(self):
        """Test that deployment scripts exist"""
        scripts = ['deploy.py', 'deploy.sh', 'deploy.ps1']
        for script in scripts:
            script_path = self.function_dir / script
            self.assertTrue(script_path.exists(), f"Deployment script {script} not found")
    
    def test_deploy_python_script_imports(self):
        """Test that Python deployment script can be imported"""
        try:
            import sys
            sys.path.insert(0, str(self.function_dir))
            from deploy import LambdaDeployer
            
            # Test that deployer can be instantiated
            deployer = LambdaDeployer(str(self.function_dir))
            self.assertIsNotNone(deployer)
            
        except ImportError as e:
            self.fail(f"Failed to import deployment script: {e}")

if __name__ == '__main__':
    unittest.main()