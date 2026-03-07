"""Logging setup and configuration for QueryReactor."""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json
import time
from ..config.loader import config_loader


class QueryReactorFormatter(logging.Formatter):
    """Custom formatter for QueryReactor logs."""
    
    def __init__(self):
        super().__init__()
        self.start_time = time.time()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with QueryReactor-specific information."""
        
        # Add timestamp
        record.timestamp = int(time.time() * 1000)
        record.elapsed_ms = int((time.time() - self.start_time) * 1000)
        
        # Extract module code from logger name if present
        if 'queryreactor.' in record.name:
            module_code = record.name.split('.')[-1].upper()
            record.module_code = f"[{module_code}]"
        else:
            record.module_code = "[SYS]"
        
        # Create structured log message
        log_data = {
            "timestamp": record.timestamp,
            "level": record.levelname,
            "module": record.module_code,
            "message": record.getMessage(),
            "elapsed_ms": record.elapsed_ms
        }
        
        # Add request ID if available in record
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Format based on log level
        if record.levelno >= logging.ERROR:
            if hasattr(record, 'exc_info') and record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
        
        # Return JSON for structured logging or formatted string for console
        if getattr(record, 'structured', False):
            return json.dumps(log_data)
        else:
            return f"{log_data['timestamp']} {log_data['level']:5} {log_data['module']} {log_data['message']}"


def setup_logging(log_level: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """Setup logging configuration for QueryReactor."""
    
    # Get configuration
    if log_level is None:
        log_level = config_loader.get_env("LOG_LEVEL", "INFO")
    
    if log_file is None:
        log_file = config_loader.get_config("logging.file", "logs/queryreactor.log")
    
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "queryreactor": {
                "()": QueryReactorFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "queryreactor",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "queryreactor",
                "filename": log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "queryreactor": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "langgraph": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "pydantic": {
                "level": "WARNING", 
                "handlers": ["console", "file"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file"]
        }
    }
    
    # Apply configuration
    logging.config.dictConfig(logging_config)
    
    # Log startup message
    logger = logging.getLogger("queryreactor.system")
    logger.info(f"QueryReactor logging initialized - Level: {log_level}, File: {log_file}")


class RequestLogger:
    """Logger for tracking request-specific information."""
    
    def __init__(self, request_id: str, logger_name: str = "queryreactor"):
        self.request_id = request_id
        self.logger = logging.getLogger(logger_name)
        self.start_time = time.time()
    
    def log(self, level: int, message: str, **kwargs) -> None:
        """Log message with request context."""
        extra = {
            "request_id": self.request_id,
            "extra_fields": kwargs
        }
        self.logger.log(level, message, extra=extra)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.log(logging.DEBUG, message, **kwargs)
    
    def log_timing(self, operation: str, duration_ms: float, **kwargs) -> None:
        """Log timing information."""
        self.info(f"Timing: {operation} completed in {duration_ms:.2f}ms", 
                 operation=operation, duration_ms=duration_ms, **kwargs)
    
    def log_module_execution(self, module_code: str, operation: str, **kwargs) -> None:
        """Log module execution."""
        self.info(f"{module_code} {operation}", 
                 module=module_code, operation=operation, **kwargs)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since logger creation."""
        return (time.time() - self.start_time) * 1000


def get_request_logger(request_id: str) -> RequestLogger:
    """Get a request-specific logger."""
    return RequestLogger(request_id)