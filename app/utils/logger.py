"""
Structured logging configuration for PromptEnchanter
"""
import sys
import structlog
import logging
from typing import Any, Dict
from app.config.settings import get_settings

settings = get_settings()


def setup_logging():
    """Configure structured logging"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__):
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class RequestLogger:
    """Logger for API requests with context"""
    
    def __init__(self, request_id: str, endpoint: str):
        self.logger = get_logger("api.request")
        self.request_id = request_id
        self.endpoint = endpoint
    
    def info(self, message: str, **kwargs):
        self.logger.info(
            message,
            request_id=self.request_id,
            endpoint=self.endpoint,
            **kwargs
        )
    
    def error(self, message: str, **kwargs):
        self.logger.error(
            message,
            request_id=self.request_id,
            endpoint=self.endpoint,
            **kwargs
        )
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(
            message,
            request_id=self.request_id,
            endpoint=self.endpoint,
            **kwargs
        )
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(
            message,
            request_id=self.request_id,
            endpoint=self.endpoint,
            **kwargs
        )