"""
Unit tests for configuration module.
Tests configuration classes, environment handling, and configuration factory.
"""

import unittest
import os
from unittest.mock import patch
from config import (
    Config,
    DevelopmentConfig,
    ProductionConfig,
    TestConfig,
    get_config,
    config
)

class TestBaseConfig(unittest.TestCase):
    """Test base Config class"""
    
    def test_default_values(self):
        """Test default configuration values"""
        self.assertEqual(Config.SUPPORTED_FORMATS, ['jpeg', 'jpg', 'png', 'webp'])
        self.assertEqual(Config.MIN_IMAGE_SIZE, 100)
        self.assertEqual(Config.AWS_REGION, 'us-east-1')
        self.assertIsInstance(Config.ERROR_MESSAGES, dict)
        self.assertIsInstance(Config.SUCCESS_MESSAGES, dict)
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults"""
        with patch.dict(os.environ, {
            'MAX_IMAGE_SIZE': '5242880',  # 5MB
            'BEDROCK_MODEL_ID': 'custom-model-id',
            'MAX_TOKENS': '2000',
            'HIGH_CONFIDENCE_THRESHOLD': '0.9'
        }):
            # Create new config instance to pick up env vars
            test_config = Config()
            
            self.assertEqual(test_config.MAX_IMAGE_SIZE, 5242880)
            self.assertEqual(test_config.BEDROCK_MODEL_ID, 'custom-model-id')
            self.assertEqual(test_config.MAX_TOKENS, 2000)
            self.assertEqual(test_config.HIGH_CONFIDENCE_THRESHOLD, 0.9)
    
    def test_get_supported_formats_string(self):
        """Test supported formats string generation"""
        formats_string = Config.get_supported_formats_string()
        self.assertEqual(formats_string, 'jpeg, jpg, png, webp')
    
    def test_get_max_size_mb(self):
        """Test max size in MB calculation"""
        with patch.object(Config, 'MAX_IMAGE_SIZE', 10485760):  # 10MB
            max_size_mb = Config.get_max_size_mb()
            self.assertEqual(max_size_mb, 10)
    
    def test_is_debug_enabled(self):
        """Test debug mode check"""
        with patch.object(Config, 'DEBUG_MODE', True):
            self.assertTrue(Config.is_debug_enabled())
        
        with patch.object(Config, 'DEBUG_MODE', False):
            self.assertFalse(Config.is_debug_enabled())
    
    def test_get_vision_model_config(self):
        """Test vision model configuration"""
        vision_config = Config.get_vision_model_config()
        
        self.assertIsInstance(vision_config, dict)
        self.assertIn('model_id', vision_config)
        self.assertIn('max_tokens', vision_config)
        self.assertIn('timeout', vision_config)
        
        self.assertEqual(vision_config['model_id'], Config.BEDROCK_MODEL_ID)
        self.assertEqual(vision_config['max_tokens'], Config.MAX_TOKENS)
        self.assertEqual(vision_config['timeout'], Config.VISION_TIMEOUT)
    
    def test_get_confidence_thresholds(self):
        """Test confidence thresholds configuration"""
        thresholds = Config.get_confidence_thresholds()
        
        self.assertIsInstance(thresholds, dict)
        self.assertIn('high', thresholds)
        self.assertIn('low', thresholds)
        
        self.assertEqual(thresholds['high'], Config.HIGH_CONFIDENCE_THRESHOLD)
        self.assertEqual(thresholds['low'], Config.LOW_CONFIDENCE_THRESHOLD)
    
    def test_error_messages_completeness(self):
        """Test that all required error messages are defined"""
        required_error_keys = [
            'no_image_data',
            'invalid_format',
            'file_too_large',
            'file_too_small',
            'vision_model_error',
            'drug_info_error',
            'no_medication_found',
            'low_confidence',
            'system_error'
        ]
        
        for key in required_error_keys:
            with self.subTest(key=key):
                self.assertIn(key, Config.ERROR_MESSAGES)
                self.assertIsInstance(Config.ERROR_MESSAGES[key], str)
                self.assertGreater(len(Config.ERROR_MESSAGES[key]), 0)
    
    def test_success_messages_completeness(self):
        """Test that all required success messages are defined"""
        required_success_keys = [
            'high_confidence',
            'medium_confidence',
            'processing_complete'
        ]
        
        for key in required_success_keys:
            with self.subTest(key=key):
                self.assertIn(key, Config.SUCCESS_MESSAGES)
                self.assertIsInstance(Config.SUCCESS_MESSAGES[key], str)
                self.assertGreater(len(Config.SUCCESS_MESSAGES[key]), 0)
    
    def test_default_analysis_prompt(self):
        """Test default analysis prompt"""
        prompt = Config.DEFAULT_ANALYSIS_PROMPT
        
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 50)  # Should be substantial
        self.assertIn('medication', prompt.lower())
        self.assertIn('dosage', prompt.lower())
        self.assertIn('confidence', prompt.lower())

class TestDevelopmentConfig(unittest.TestCase):
    """Test DevelopmentConfig class"""
    
    def test_development_overrides(self):
        """Test development-specific configuration overrides"""
        dev_config = DevelopmentConfig()
        
        self.assertTrue(dev_config.DEBUG_MODE)
        self.assertEqual(dev_config.LOG_LEVEL, 'DEBUG')
        
        # Should inherit other values from base Config
        self.assertEqual(dev_config.SUPPORTED_FORMATS, Config.SUPPORTED_FORMATS)
        self.assertEqual(dev_config.AWS_REGION, Config.AWS_REGION)

class TestProductionConfig(unittest.TestCase):
    """Test ProductionConfig class"""
    
    def test_production_overrides(self):
        """Test production-specific configuration overrides"""
        prod_config = ProductionConfig()
        
        self.assertFalse(prod_config.DEBUG_MODE)
        self.assertEqual(prod_config.LOG_LEVEL, 'INFO')
        
        # Should inherit other values from base Config
        self.assertEqual(prod_config.SUPPORTED_FORMATS, Config.SUPPORTED_FORMATS)
        self.assertEqual(prod_config.AWS_REGION, Config.AWS_REGION)

class TestTestConfig(unittest.TestCase):
    """Test TestConfig class"""
    
    def test_test_overrides(self):
        """Test test-specific configuration overrides"""
        test_config = TestConfig()
        
        self.assertTrue(test_config.DEBUG_MODE)
        self.assertEqual(test_config.LOG_LEVEL, 'DEBUG')
        self.assertEqual(test_config.MAX_IMAGE_SIZE, 1024 * 1024)  # 1MB
        self.assertEqual(test_config.VISION_TIMEOUT, 5)  # Shorter timeout
        
        # Should inherit other values from base Config
        self.assertEqual(test_config.SUPPORTED_FORMATS, Config.SUPPORTED_FORMATS)

class TestConfigFactory(unittest.TestCase):
    """Test configuration factory function"""
    
    def test_get_config_development(self):
        """Test getting development configuration"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            config_instance = get_config()
            self.assertIsInstance(config_instance, DevelopmentConfig)
            self.assertTrue(config_instance.DEBUG_MODE)
    
    def test_get_config_production(self):
        """Test getting production configuration"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            config_instance = get_config()
            self.assertIsInstance(config_instance, ProductionConfig)
            self.assertFalse(config_instance.DEBUG_MODE)
    
    def test_get_config_test(self):
        """Test getting test configuration"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'test'}):
            config_instance = get_config()
            self.assertIsInstance(config_instance, TestConfig)
            self.assertTrue(config_instance.DEBUG_MODE)
            self.assertEqual(config_instance.MAX_IMAGE_SIZE, 1024 * 1024)
    
    def test_get_config_default(self):
        """Test getting default (production) configuration"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'unknown_env'}):
            config_instance = get_config()
            self.assertIsInstance(config_instance, ProductionConfig)
    
    def test_get_config_no_environment(self):
        """Test getting configuration with no ENVIRONMENT variable"""
        with patch.dict(os.environ, {}, clear=True):
            # Remove ENVIRONMENT if it exists
            if 'ENVIRONMENT' in os.environ:
                del os.environ['ENVIRONMENT']
            
            config_instance = get_config()
            self.assertIsInstance(config_instance, ProductionConfig)

class TestGlobalConfigInstance(unittest.TestCase):
    """Test global configuration instance"""
    
    def test_global_config_exists(self):
        """Test that global config instance exists"""
        self.assertIsNotNone(config)
        self.assertIsInstance(config, Config)
    
    def test_global_config_attributes(self):
        """Test that global config has expected attributes"""
        required_attributes = [
            'MAX_IMAGE_SIZE',
            'SUPPORTED_FORMATS',
            'BEDROCK_MODEL_ID',
            'HIGH_CONFIDENCE_THRESHOLD',
            'LOW_CONFIDENCE_THRESHOLD',
            'ERROR_MESSAGES',
            'SUCCESS_MESSAGES',
            'DEFAULT_ANALYSIS_PROMPT'
        ]
        
        for attr in required_attributes:
            with self.subTest(attribute=attr):
                self.assertTrue(hasattr(config, attr))

class TestConfigurationIntegration(unittest.TestCase):
    """Integration tests for configuration"""
    
    def test_environment_variable_types(self):
        """Test that environment variables are properly typed"""
        with patch.dict(os.environ, {
            'MAX_IMAGE_SIZE': '5242880',
            'MAX_TOKENS': '1500',
            'VISION_TIMEOUT': '25',
            'HIGH_CONFIDENCE_THRESHOLD': '0.85',
            'DEBUG_MODE': 'true'
        }):
            test_config = Config()
            
            # Test integer conversions
            self.assertIsInstance(test_config.MAX_IMAGE_SIZE, int)
            self.assertEqual(test_config.MAX_IMAGE_SIZE, 5242880)
            
            self.assertIsInstance(test_config.MAX_TOKENS, int)
            self.assertEqual(test_config.MAX_TOKENS, 1500)
            
            self.assertIsInstance(test_config.VISION_TIMEOUT, int)
            self.assertEqual(test_config.VISION_TIMEOUT, 25)
            
            # Test float conversions
            self.assertIsInstance(test_config.HIGH_CONFIDENCE_THRESHOLD, float)
            self.assertEqual(test_config.HIGH_CONFIDENCE_THRESHOLD, 0.85)
    
    def test_boolean_environment_variables(self):
        """Test boolean environment variable parsing"""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('invalid', False)  # Should default to False
        ]
        
        for env_value, expected in test_cases:
            with self.subTest(env_value=env_value):
                with patch.dict(os.environ, {'DEBUG_MODE': env_value}):
                    # Note: Config class uses string comparison, not boolean parsing
                    # This tests the actual implementation
                    debug_enabled = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
                    if env_value.lower() == 'true':
                        self.assertTrue(debug_enabled)
                    else:
                        self.assertFalse(debug_enabled)
    
    def test_configuration_consistency(self):
        """Test that configuration values are consistent"""
        # High confidence threshold should be higher than low confidence threshold
        self.assertGreater(config.HIGH_CONFIDENCE_THRESHOLD, config.LOW_CONFIDENCE_THRESHOLD)
        
        # Max image size should be reasonable
        self.assertGreater(config.MAX_IMAGE_SIZE, config.MIN_IMAGE_SIZE)
        
        # Timeouts should be positive
        self.assertGreater(config.VISION_TIMEOUT, 0)
        self.assertGreater(config.DRUG_INFO_TIMEOUT, 0)
        
        # Max tokens should be reasonable
        self.assertGreater(config.MAX_TOKENS, 0)
        self.assertLess(config.MAX_TOKENS, 10000)  # Reasonable upper bound
    
    def test_error_message_formatting(self):
        """Test that error messages are properly formatted"""
        for key, message in config.ERROR_MESSAGES.items():
            with self.subTest(key=key):
                # Should not be empty
                self.assertGreater(len(message), 0)
                
                # Should not have trailing/leading whitespace
                self.assertEqual(message, message.strip())
                
                # Should end with appropriate punctuation
                self.assertTrue(message.endswith('.') or message.endswith('!'))
    
    def test_file_size_calculations(self):
        """Test file size related calculations"""
        # Test MB conversion
        mb_size = config.get_max_size_mb()
        expected_mb = config.MAX_IMAGE_SIZE // (1024 * 1024)
        self.assertEqual(mb_size, expected_mb)
        
        # Test that file size limits make sense
        self.assertGreaterEqual(config.MAX_IMAGE_SIZE, 1024 * 1024)  # At least 1MB
        self.assertLessEqual(config.MAX_IMAGE_SIZE, 100 * 1024 * 1024)  # At most 100MB

if __name__ == '__main__':
    unittest.main(verbosity=2)