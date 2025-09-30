#!/usr/bin/env python3
"""
Deployment script for the Image Analysis Lambda function.
This script handles packaging, deployment, and configuration management.
"""

import os
import sys
import json
import zipfile
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

class LambdaDeployer:
    """Handles Lambda function deployment operations"""
    
    def __init__(self, function_dir: str, environment: str = 'production'):
        self.function_dir = Path(function_dir)
        self.environment = environment
        self.function_name = 'image-analysis-tool'
        self.package_name = 'deployment-package.zip'
        
    def load_config(self) -> Dict[str, Any]:
        """Load base configuration and environment-specific overrides"""
        # Load base configuration
        base_config_path = self.function_dir / 'lambda_config.json'
        with open(base_config_path, 'r') as f:
            config = json.load(f)
        
        # Load environment-specific overrides
        env_config_path = self.function_dir / 'env_configs' / f'{self.environment}.json'
        if env_config_path.exists():
            with open(env_config_path, 'r') as f:
                env_config = json.load(f)
                # Merge environment-specific settings
                config.update(env_config)
        
        return config
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        print("Installing dependencies...")
        requirements_path = self.function_dir / 'requirements.txt'
        
        if not requirements_path.exists():
            print("No requirements.txt found")
            return True
        
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                '-r', str(requirements_path),
                '-t', str(self.function_dir)
            ], check=True, capture_output=True, text=True)
            print("Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dependencies: {e}")
            return False
    
    def create_package(self) -> bool:
        """Create deployment package"""
        print("Creating deployment package...")
        
        package_path = self.function_dir / self.package_name
        
        # Files to exclude from package
        exclude_patterns = [
            '__pycache__',
            '*.pyc',
            '.pytest_cache',
            'test_*.py',
            '*.zip',
            'deploy.py',
            'lambda_config.json',
            'env_configs',
            'iam_policy.json',
            'trust_policy.json',
            'README.md'
        ]
        
        try:
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self.function_dir.rglob('*'):
                    if file_path.is_file():
                        # Check if file should be excluded
                        relative_path = file_path.relative_to(self.function_dir)
                        should_exclude = any(
                            pattern in str(relative_path) for pattern in exclude_patterns
                        )
                        
                        if not should_exclude:
                            zipf.write(file_path, relative_path)
            
            print(f"Package created: {package_path}")
            return True
        except Exception as e:
            print(f"Failed to create package: {e}")
            return False
    
    def validate_package(self) -> bool:
        """Validate the deployment package"""
        print("Validating deployment package...")
        
        package_path = self.function_dir / self.package_name
        if not package_path.exists():
            print("Package not found")
            return False
        
        # Check package size (Lambda limit is 50MB for direct upload)
        package_size = package_path.stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB
        
        if package_size > max_size:
            print(f"Package size ({package_size / (1024*1024):.1f}MB) exceeds limit")
            return False
        
        # Check required files are present
        required_files = ['app.py']
        
        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                package_files = zipf.namelist()
                
                for required_file in required_files:
                    if required_file not in package_files:
                        print(f"Required file missing: {required_file}")
                        return False
            
            print("Package validation successful")
            return True
        except Exception as e:
            print(f"Package validation failed: {e}")
            return False    

    def deploy_function(self, aws_profile: Optional[str] = None) -> bool:
        """Deploy the Lambda function"""
        print(f"Deploying Lambda function for {self.environment} environment...")
        
        config = self.load_config()
        package_path = self.function_dir / self.package_name
        
        # Build AWS CLI command
        cmd = ['aws', 'lambda']
        
        if aws_profile:
            cmd.extend(['--profile', aws_profile])
        
        # Check if function exists
        try:
            check_cmd = cmd + ['get-function', '--function-name', self.function_name]
            subprocess.run(check_cmd, check=True, capture_output=True)
            # Function exists, update it
            update_cmd = cmd + [
                'update-function-code',
                '--function-name', self.function_name,
                '--zip-file', f'fileb://{package_path}'
            ]
            subprocess.run(update_cmd, check=True)
            
            # Update configuration
            config_cmd = cmd + [
                'update-function-configuration',
                '--function-name', self.function_name,
                '--timeout', str(config.get('Timeout', 300)),
                '--memory-size', str(config.get('MemorySize', 1024)),
                '--environment', f'Variables={json.dumps(config["Environment"]["Variables"])}'
            ]
            subprocess.run(config_cmd, check=True)
            
        except subprocess.CalledProcessError:
            # Function doesn't exist, create it
            create_cmd = cmd + [
                'create-function',
                '--function-name', self.function_name,
                '--runtime', config.get('Runtime', 'python3.9'),
                '--role', config['Role'],
                '--handler', config.get('Handler', 'app.lambda_handler'),
                '--zip-file', f'fileb://{package_path}',
                '--timeout', str(config.get('Timeout', 300)),
                '--memory-size', str(config.get('MemorySize', 1024)),
                '--environment', f'Variables={json.dumps(config["Environment"]["Variables"])}'
            ]
            subprocess.run(create_cmd, check=True)
        
        print("Deployment completed successfully")
        return True
    
    def run_tests(self) -> bool:
        """Run deployment validation tests"""
        print("Running deployment validation tests...")
        
        try:
            # Run pytest on test files
            test_cmd = [sys.executable, '-m', 'pytest', str(self.function_dir), '-v']
            result = subprocess.run(test_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("All tests passed")
                return True
            else:
                print(f"Tests failed: {result.stdout}")
                return False
        except Exception as e:
            print(f"Test execution failed: {e}")
            return False

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description='Deploy Image Analysis Lambda function')
    parser.add_argument('--environment', '-e', default='production',
                       choices=['development', 'staging', 'production'],
                       help='Deployment environment')
    parser.add_argument('--profile', '-p', help='AWS profile to use')
    parser.add_argument('--skip-tests', action='store_true',
                       help='Skip running tests before deployment')
    parser.add_argument('--package-only', action='store_true',
                       help='Only create package, do not deploy')
    
    args = parser.parse_args()
    
    # Get function directory (current directory)
    function_dir = Path(__file__).parent
    
    deployer = LambdaDeployer(function_dir, args.environment)
    
    try:
        # Install dependencies
        if not deployer.install_dependencies():
            sys.exit(1)
        
        # Run tests unless skipped
        if not args.skip_tests:
            if not deployer.run_tests():
                print("Tests failed. Use --skip-tests to deploy anyway.")
                sys.exit(1)
        
        # Create deployment package
        if not deployer.create_package():
            sys.exit(1)
        
        # Validate package
        if not deployer.validate_package():
            sys.exit(1)
        
        # Deploy function unless package-only mode
        if not args.package_only:
            if not deployer.deploy_function(args.profile):
                sys.exit(1)
        
        print("Deployment process completed successfully!")
        
    except KeyboardInterrupt:
        print("\nDeployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Deployment failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()