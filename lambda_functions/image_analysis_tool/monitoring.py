"""
Monitoring and metrics collection module for the image analysis tool.
This module provides structured logging, performance monitoring, and metrics collection
following the DrugInfoTool pattern.
"""

import json
import time
import logging
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

from config import config

class MetricType(Enum):
    """Types of metrics we collect"""
    COUNTER = "counter"
    TIMER = "timer"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"

class LogLevel(Enum):
    """Log levels for structured logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class PerformanceMetric:
    """Data structure for performance metrics"""
    name: str
    value: float
    unit: str
    timestamp: float
    tags: Dict[str, str] = None
    metric_type: MetricType = MetricType.GAUGE
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        result = asdict(self)
        result['metric_type'] = self.metric_type.value
        return result

@dataclass
class ProcessingStage:
    """Data structure for tracking processing stages"""
    stage_name: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = True
    error_message: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate stage duration"""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return None
    
    def finish(self, success: bool = True, error_message: str = ""):
        """Mark stage as finished"""
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        result = asdict(self)
        result['duration'] = self.duration
        return result

class StructuredLogger:
    """
    Structured logger that provides consistent logging format and privacy compliance.
    Follows the DrugInfoTool debug logging pattern.
    """
    
    def __init__(self, name: str = __name__):
        """Initialize structured logger"""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL))
        
        # Sensitive fields that should be masked in logs
        self.sensitive_fields = {
            'image_data', 'base64', 'user_id', 'session_id', 
            'personal_info', 'patient_data', 'user_info'
        }
    
    def _sanitize_data(self, data: Any) -> Any:
        """Remove or mask sensitive information from log data"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                    if key.lower() == 'image_data':
                        sanitized[key] = f"[IMAGE_DATA:{len(str(value)) if value else 0}_bytes]"
                    elif 'id' in key.lower():
                        sanitized[key] = f"[{key.upper()}_MASKED]"
                    else:
                        sanitized[key] = "[SENSITIVE_DATA_MASKED]"
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str) and len(data) > 1000:
            # Truncate very long strings that might contain sensitive data
            return f"[LONG_STRING_TRUNCATED:{len(data)}_chars]"
        else:
            return data
    
    def _format_log_entry(self, level: LogLevel, message: str, 
                         context: Dict[str, Any] = None, 
                         stage: str = None,
                         request_id: str = None) -> Dict[str, Any]:
        """Format log entry with consistent structure"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level.value,
            'message': message,
            'service': 'image_analysis_tool',
            'version': '1.0.0'
        }
        
        if request_id:
            log_entry['request_id'] = request_id
        
        if stage:
            log_entry['stage'] = stage
        
        if context:
            log_entry['context'] = self._sanitize_data(context)
        
        return log_entry
    
    def debug(self, message: str, context: Dict[str, Any] = None, 
              stage: str = None, request_id: str = None):
        """Log debug message following DrugInfoTool pattern"""
        if config.is_debug_enabled():
            log_entry = self._format_log_entry(LogLevel.DEBUG, message, context, stage, request_id)
            self.logger.debug(f"[DEBUG] {json.dumps(log_entry, indent=2)}")
    
    def info(self, message: str, context: Dict[str, Any] = None, 
             stage: str = None, request_id: str = None):
        """Log info message"""
        log_entry = self._format_log_entry(LogLevel.INFO, message, context, stage, request_id)
        self.logger.info(f"[INFO] {json.dumps(log_entry)}")
    
    def warning(self, message: str, context: Dict[str, Any] = None, 
                stage: str = None, request_id: str = None):
        """Log warning message"""
        log_entry = self._format_log_entry(LogLevel.WARNING, message, context, stage, request_id)
        self.logger.warning(f"[WARNING] {json.dumps(log_entry)}")
    
    def error(self, message: str, context: Dict[str, Any] = None, 
              stage: str = None, request_id: str = None, 
              include_traceback: bool = False):
        """Log error message"""
        log_entry = self._format_log_entry(LogLevel.ERROR, message, context, stage, request_id)
        
        if include_traceback:
            log_entry['traceback'] = traceback.format_exc()
        
        self.logger.error(f"[ERROR] {json.dumps(log_entry, indent=2)}")
    
    def critical(self, message: str, context: Dict[str, Any] = None, 
                 stage: str = None, request_id: str = None, 
                 include_traceback: bool = True):
        """Log critical message"""
        log_entry = self._format_log_entry(LogLevel.CRITICAL, message, context, stage, request_id)
        
        if include_traceback:
            log_entry['traceback'] = traceback.format_exc()
        
        self.logger.critical(f"[CRITICAL] {json.dumps(log_entry, indent=2)}")

class PerformanceMonitor:
    """
    Performance monitoring and metrics collection.
    Tracks processing times, success rates, and system performance.
    """
    
    def __init__(self, logger: StructuredLogger = None):
        """Initialize performance monitor"""
        self.logger = logger or StructuredLogger()
        self.metrics: List[PerformanceMetric] = []
        self.stages: List[ProcessingStage] = []
        self.start_time = time.time()
        self.request_id = None
    
    def set_request_id(self, request_id: str):
        """Set request ID for tracking"""
        self.request_id = request_id
    
    def start_stage(self, stage_name: str, metadata: Dict[str, Any] = None) -> ProcessingStage:
        """Start tracking a processing stage"""
        stage = ProcessingStage(
            stage_name=stage_name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self.stages.append(stage)
        
        self.logger.debug(
            f"Started stage: {stage_name}",
            context={'stage_metadata': metadata},
            stage=stage_name,
            request_id=self.request_id
        )
        
        return stage
    
    def finish_stage(self, stage: ProcessingStage, success: bool = True, 
                    error_message: str = "", metadata: Dict[str, Any] = None):
        """Finish tracking a processing stage"""
        stage.finish(success, error_message)
        
        if metadata:
            stage.metadata.update(metadata)
        
        # Record timing metric
        if stage.duration:
            self.record_metric(
                name=f"stage_{stage.stage_name}_duration",
                value=stage.duration,
                unit="seconds",
                metric_type=MetricType.TIMER,
                tags={'stage': stage.stage_name, 'success': str(success)}
            )
        
        log_level = LogLevel.DEBUG if success else LogLevel.WARNING
        message = f"Finished stage: {stage.stage_name} ({'success' if success else 'failed'})"
        
        context = {
            'duration': stage.duration,
            'success': success,
            'stage_metadata': stage.metadata
        }
        
        if error_message:
            context['error'] = error_message
        
        if success:
            self.logger.debug(message, context, stage.stage_name, self.request_id)
        else:
            self.logger.warning(message, context, stage.stage_name, self.request_id)
    
    def record_metric(self, name: str, value: float, unit: str, 
                     metric_type: MetricType = MetricType.GAUGE,
                     tags: Dict[str, str] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            tags=tags or {},
            metric_type=metric_type
        )
        
        # Add request ID to tags if available
        if self.request_id:
            metric.tags['request_id'] = self.request_id
        
        self.metrics.append(metric)
        
        self.logger.debug(
            f"Recorded metric: {name}",
            context={'metric': metric.to_dict()},
            request_id=self.request_id
        )
    
    def record_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Record a counter metric"""
        self.record_metric(name, float(value), "count", MetricType.COUNTER, tags)
    
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record a timer metric"""
        self.record_metric(name, duration, "seconds", MetricType.TIMER, tags)
    
    def record_gauge(self, name: str, value: float, unit: str, tags: Dict[str, str] = None):
        """Record a gauge metric"""
        self.record_metric(name, value, unit, MetricType.GAUGE, tags)
    
    def get_total_processing_time(self) -> float:
        """Get total processing time since monitor creation"""
        return time.time() - self.start_time
    
    def get_stage_summary(self) -> Dict[str, Any]:
        """Get summary of all processing stages"""
        summary = {
            'total_stages': len(self.stages),
            'successful_stages': sum(1 for stage in self.stages if stage.success),
            'failed_stages': sum(1 for stage in self.stages if not stage.success),
            'total_processing_time': self.get_total_processing_time(),
            'stages': [stage.to_dict() for stage in self.stages]
        }
        
        return summary
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all collected metrics"""
        summary = {
            'total_metrics': len(self.metrics),
            'metrics_by_type': {},
            'metrics': [metric.to_dict() for metric in self.metrics]
        }
        
        # Group metrics by type
        for metric in self.metrics:
            metric_type = metric.metric_type.value
            if metric_type not in summary['metrics_by_type']:
                summary['metrics_by_type'][metric_type] = 0
            summary['metrics_by_type'][metric_type] += 1
        
        return summary
    
    def log_final_summary(self):
        """Log final processing summary"""
        stage_summary = self.get_stage_summary()
        metrics_summary = self.get_metrics_summary()
        
        summary = {
            'processing_summary': stage_summary,
            'metrics_summary': metrics_summary,
            'request_id': self.request_id
        }
        
        success_rate = (stage_summary['successful_stages'] / 
                       max(stage_summary['total_stages'], 1)) * 100
        
        message = (f"Processing completed - "
                  f"Total time: {stage_summary['total_processing_time']:.2f}s, "
                  f"Success rate: {success_rate:.1f}%")
        
        if stage_summary['failed_stages'] > 0:
            self.logger.warning(message, context=summary, request_id=self.request_id)
        else:
            self.logger.info(message, context=summary, request_id=self.request_id)

class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, monitor: PerformanceMonitor, stage_name: str, 
                 metadata: Dict[str, Any] = None):
        """Initialize timing context"""
        self.monitor = monitor
        self.stage_name = stage_name
        self.metadata = metadata or {}
        self.stage = None
        self.exception_occurred = False
    
    def __enter__(self) -> ProcessingStage:
        """Start timing"""
        self.stage = self.monitor.start_stage(self.stage_name, self.metadata)
        return self.stage
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish timing"""
        if exc_type is not None:
            self.exception_occurred = True
            error_message = f"{exc_type.__name__}: {str(exc_val)}"
            self.monitor.finish_stage(self.stage, success=False, error_message=error_message)
        else:
            self.monitor.finish_stage(self.stage, success=True)
        
        return False  # Don't suppress exceptions

# Global instances for easy access
structured_logger = StructuredLogger()

def create_performance_monitor(request_id: str = None) -> PerformanceMonitor:
    """Create a new performance monitor instance"""
    monitor = PerformanceMonitor(structured_logger)
    if request_id:
        monitor.set_request_id(request_id)
    return monitor

def log_request_start(event: Dict[str, Any], context: Any, 
                     logger: StructuredLogger = None) -> str:
    """Log request start following DrugInfoTool pattern"""
    if logger is None:
        logger = structured_logger
    
    request_id = getattr(context, 'aws_request_id', 'unknown')
    
    # Sanitize event for logging (remove sensitive data)
    sanitized_event = logger._sanitize_data(event)
    
    context_info = {
        'function_name': getattr(context, 'function_name', 'unknown'),
        'function_version': getattr(context, 'function_version', 'unknown'),
        'memory_limit': getattr(context, 'memory_limit_in_mb', 'unknown'),
        'remaining_time': getattr(context, 'get_remaining_time_in_millis', lambda: 'unknown')()
    }
    
    logger.info(
        "Request started",
        context={
            'event': sanitized_event,
            'lambda_context': context_info
        },
        stage='request_start',
        request_id=request_id
    )
    
    return request_id

def log_request_end(request_id: str, response: Dict[str, Any], 
                   processing_time: float, success: bool = True,
                   logger: StructuredLogger = None):
    """Log request completion"""
    if logger is None:
        logger = structured_logger
    
    # Extract key response info without sensitive data
    response_info = {
        'status_code': response.get('response', {}).get('httpStatusCode', 'unknown'),
        'success': success,
        'processing_time': processing_time
    }
    
    # Parse response body for additional info
    try:
        if 'response' in response and 'responseBody' in response['response']:
            body_str = response['response']['responseBody']['application/json']['body']
            body = json.loads(body_str)
            response_info.update({
                'medication_identified': body.get('medication_name', 'unknown'),
                'confidence': body.get('confidence', 0),
                'drug_info_available': body.get('drug_info_available', False)
            })
    except (json.JSONDecodeError, KeyError):
        pass
    
    message = f"Request completed ({'success' if success else 'failed'}) in {processing_time:.2f}s"
    
    if success:
        logger.info(message, context=response_info, stage='request_end', request_id=request_id)
    else:
        logger.error(message, context=response_info, stage='request_end', request_id=request_id)