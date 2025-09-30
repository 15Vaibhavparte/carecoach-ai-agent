"""
Tests for monitoring and logging functionality.
"""

import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from monitoring import (
    StructuredLogger,
    PerformanceMonitor,
    TimingContext,
    PerformanceMetric,
    ProcessingStage,
    MetricType,
    LogLevel,
    create_performance_monitor,
    log_request_start,
    log_request_end
)

class TestStructuredLogger:
    """Test structured logging functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.logger = StructuredLogger("test_logger")
    
    def test_sanitize_sensitive_data(self):
        """Test that sensitive data is properly sanitized"""
        sensitive_data = {
            'image_data': 'base64encodedimagedata',
            'user_id': 'user123',
            'session_id': 'session456',
            'normal_field': 'normal_value',
            'nested': {
                'image_data': 'more_image_data',
                'safe_field': 'safe_value'
            }
        }
        
        sanitized = self.logger._sanitize_data(sensitive_data)
        
        assert '[IMAGE_DATA:' in sanitized['image_data']
        assert '[USER_ID_MASKED]' == sanitized['user_id']
        assert '[SESSION_ID_MASKED]' == sanitized['session_id']
        assert sanitized['normal_field'] == 'normal_value'
        assert '[IMAGE_DATA:' in sanitized['nested']['image_data']
        assert sanitized['nested']['safe_field'] == 'safe_value'
    
    def test_sanitize_long_strings(self):
        """Test that very long strings are truncated"""
        long_string = 'x' * 2000
        sanitized = self.logger._sanitize_data(long_string)
        
        assert '[LONG_STRING_TRUNCATED:2000_chars]' == sanitized
    
    def test_format_log_entry(self):
        """Test log entry formatting"""
        context = {'test_field': 'test_value'}
        log_entry = self.logger._format_log_entry(
            LogLevel.INFO, 
            "Test message", 
            context, 
            "test_stage", 
            "req123"
        )
        
        assert log_entry['level'] == 'INFO'
        assert log_entry['message'] == 'Test message'
        assert log_entry['service'] == 'image_analysis_tool'
        assert log_entry['request_id'] == 'req123'
        assert log_entry['stage'] == 'test_stage'
        assert log_entry['context'] == context
        assert 'timestamp' in log_entry
    
    @patch('monitoring.logging.getLogger')
    def test_debug_logging_when_enabled(self, mock_get_logger):
        """Test debug logging when debug mode is enabled"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        with patch('monitoring.config.is_debug_enabled', return_value=True):
            logger = StructuredLogger()
            logger.debug("Debug message", {'key': 'value'}, "test_stage", "req123")
            
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0][0]
            assert '[DEBUG]' in call_args
            assert 'Debug message' in call_args
    
    @patch('monitoring.logging.getLogger')
    def test_debug_logging_when_disabled(self, mock_get_logger):
        """Test debug logging when debug mode is disabled"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        with patch('monitoring.config.is_debug_enabled', return_value=False):
            logger = StructuredLogger()
            logger.debug("Debug message")
            
            mock_logger.debug.assert_not_called()
    
    @patch('monitoring.logging.getLogger')
    def test_error_logging_with_traceback(self, mock_get_logger):
        """Test error logging with traceback"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        logger = StructuredLogger()
        logger.error("Error message", include_traceback=True)
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert '[ERROR]' in call_args
        assert 'Error message' in call_args

class TestPerformanceMetric:
    """Test performance metric data structure"""
    
    def test_metric_creation(self):
        """Test metric creation with defaults"""
        metric = PerformanceMetric(
            name="test_metric",
            value=1.5,
            unit="seconds"
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 1.5
        assert metric.unit == "seconds"
        assert metric.metric_type == MetricType.GAUGE
        assert isinstance(metric.tags, dict)
        assert metric.timestamp > 0
    
    def test_metric_to_dict(self):
        """Test metric conversion to dictionary"""
        metric = PerformanceMetric(
            name="test_metric",
            value=2.0,
            unit="count",
            metric_type=MetricType.COUNTER,
            tags={'key': 'value'}
        )
        
        result = metric.to_dict()
        
        assert result['name'] == "test_metric"
        assert result['value'] == 2.0
        assert result['unit'] == "count"
        assert result['metric_type'] == "counter"
        assert result['tags'] == {'key': 'value'}

class TestProcessingStage:
    """Test processing stage tracking"""
    
    def test_stage_creation(self):
        """Test stage creation"""
        start_time = time.time()
        stage = ProcessingStage("test_stage", start_time)
        
        assert stage.stage_name == "test_stage"
        assert stage.start_time == start_time
        assert stage.end_time is None
        assert stage.success is True
        assert stage.duration is None
    
    def test_stage_finish(self):
        """Test stage completion"""
        start_time = time.time()
        stage = ProcessingStage("test_stage", start_time)
        
        time.sleep(0.01)  # Small delay
        stage.finish(success=True)
        
        assert stage.end_time is not None
        assert stage.success is True
        assert stage.duration > 0
    
    def test_stage_finish_with_error(self):
        """Test stage completion with error"""
        stage = ProcessingStage("test_stage", time.time())
        stage.finish(success=False, error_message="Test error")
        
        assert stage.success is False
        assert stage.error_message == "Test error"

class TestPerformanceMonitor:
    """Test performance monitoring functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.monitor = PerformanceMonitor()
        self.monitor.set_request_id("test_request_123")
    
    def test_monitor_initialization(self):
        """Test monitor initialization"""
        assert isinstance(self.monitor.metrics, list)
        assert isinstance(self.monitor.stages, list)
        assert self.monitor.request_id == "test_request_123"
        assert self.monitor.start_time > 0
    
    def test_start_stage(self):
        """Test starting a processing stage"""
        metadata = {'key': 'value'}
        stage = self.monitor.start_stage("test_stage", metadata)
        
        assert stage.stage_name == "test_stage"
        assert stage.metadata == metadata
        assert len(self.monitor.stages) == 1
        assert self.monitor.stages[0] == stage
    
    def test_finish_stage(self):
        """Test finishing a processing stage"""
        stage = self.monitor.start_stage("test_stage")
        time.sleep(0.01)  # Small delay
        
        self.monitor.finish_stage(stage, success=True)
        
        assert stage.success is True
        assert stage.duration > 0
        
        # Check that timing metric was recorded
        timing_metrics = [m for m in self.monitor.metrics if m.name == "stage_test_stage_duration"]
        assert len(timing_metrics) == 1
        assert timing_metrics[0].metric_type == MetricType.TIMER
    
    def test_record_metrics(self):
        """Test recording various types of metrics"""
        # Test gauge metric
        self.monitor.record_gauge("test_gauge", 1.5, "units")
        
        # Test counter metric
        self.monitor.record_counter("test_counter", 5)
        
        # Test timer metric
        self.monitor.record_timer("test_timer", 2.5)
        
        assert len(self.monitor.metrics) == 3
        
        gauge_metric = next(m for m in self.monitor.metrics if m.name == "test_gauge")
        assert gauge_metric.value == 1.5
        assert gauge_metric.metric_type == MetricType.GAUGE
        
        counter_metric = next(m for m in self.monitor.metrics if m.name == "test_counter")
        assert counter_metric.value == 5.0
        assert counter_metric.metric_type == MetricType.COUNTER
        
        timer_metric = next(m for m in self.monitor.metrics if m.name == "test_timer")
        assert timer_metric.value == 2.5
        assert timer_metric.metric_type == MetricType.TIMER
    
    def test_get_stage_summary(self):
        """Test stage summary generation"""
        # Add some stages
        stage1 = self.monitor.start_stage("stage1")
        self.monitor.finish_stage(stage1, success=True)
        
        stage2 = self.monitor.start_stage("stage2")
        self.monitor.finish_stage(stage2, success=False, error_message="Test error")
        
        summary = self.monitor.get_stage_summary()
        
        assert summary['total_stages'] == 2
        assert summary['successful_stages'] == 1
        assert summary['failed_stages'] == 1
        assert summary['total_processing_time'] > 0
        assert len(summary['stages']) == 2
    
    def test_get_metrics_summary(self):
        """Test metrics summary generation"""
        self.monitor.record_gauge("gauge1", 1.0, "units")
        self.monitor.record_counter("counter1", 1)
        self.monitor.record_counter("counter2", 2)
        
        summary = self.monitor.get_metrics_summary()
        
        assert summary['total_metrics'] == 3
        assert summary['metrics_by_type']['gauge'] == 1
        assert summary['metrics_by_type']['counter'] == 2
        assert len(summary['metrics']) == 3

class TestTimingContext:
    """Test timing context manager"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.monitor = PerformanceMonitor()
    
    def test_successful_timing_context(self):
        """Test timing context for successful operation"""
        with TimingContext(self.monitor, "test_operation") as stage:
            assert stage.stage_name == "test_operation"
            time.sleep(0.01)  # Small delay
        
        assert len(self.monitor.stages) == 1
        assert self.monitor.stages[0].success is True
        assert self.monitor.stages[0].duration > 0
    
    def test_timing_context_with_exception(self):
        """Test timing context when exception occurs"""
        with pytest.raises(ValueError):
            with TimingContext(self.monitor, "test_operation"):
                raise ValueError("Test error")
        
        assert len(self.monitor.stages) == 1
        assert self.monitor.stages[0].success is False
        assert "ValueError: Test error" in self.monitor.stages[0].error_message

class TestRequestLogging:
    """Test request start/end logging functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_context = Mock()
        self.mock_context.aws_request_id = 'test-request-123'
        self.mock_context.function_name = 'image_analysis_tool'
        self.mock_context.function_version = '$LATEST'
        self.mock_context.memory_limit_in_mb = 128
        self.mock_context.get_remaining_time_in_millis = lambda: 30000
    
    @patch('monitoring.structured_logger')
    def test_log_request_start(self, mock_logger):
        """Test request start logging"""
        event = {'test_field': 'test_value'}
        
        request_id = log_request_start(event, self.mock_context, mock_logger)
        
        assert request_id == 'test-request-123'
        mock_logger.info.assert_called_once()
        
        # Check call arguments
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "Request started"
        assert call_args[1]['stage'] == 'request_start'
        assert call_args[1]['request_id'] == 'test-request-123'
    
    @patch('monitoring.structured_logger')
    def test_log_request_end_success(self, mock_logger):
        """Test successful request end logging"""
        response = {
            'response': {
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'medication_name': 'Advil',
                            'confidence': 0.9,
                            'drug_info_available': True
                        })
                    }
                }
            }
        }
        
        log_request_end('test-request-123', response, 2.5, True, mock_logger)
        
        mock_logger.info.assert_called_once()
        
        # Check call arguments
        call_args = mock_logger.info.call_args
        assert "Request completed (success)" in call_args[0][0]
        assert call_args[1]['stage'] == 'request_end'
        assert call_args[1]['request_id'] == 'test-request-123'
    
    @patch('monitoring.structured_logger')
    def test_log_request_end_failure(self, mock_logger):
        """Test failed request end logging"""
        response = {
            'response': {
                'httpStatusCode': 400,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'success': False,
                            'error': 'Test error'
                        })
                    }
                }
            }
        }
        
        log_request_end('test-request-123', response, 1.0, False, mock_logger)
        
        mock_logger.error.assert_called_once()
        
        # Check call arguments
        call_args = mock_logger.error.call_args
        assert "Request completed (failed)" in call_args[0][0]
        assert call_args[1]['stage'] == 'request_end'
        assert call_args[1]['request_id'] == 'test-request-123'

class TestMonitoringIntegration:
    """Test monitoring integration with main application"""
    
    def test_create_performance_monitor(self):
        """Test performance monitor creation"""
        monitor = create_performance_monitor("test-request-456")
        
        assert isinstance(monitor, PerformanceMonitor)
        assert monitor.request_id == "test-request-456"
    
    def test_create_performance_monitor_without_request_id(self):
        """Test performance monitor creation without request ID"""
        monitor = create_performance_monitor()
        
        assert isinstance(monitor, PerformanceMonitor)
        assert monitor.request_id is None

if __name__ == '__main__':
    pytest.main([__file__, '-v'])