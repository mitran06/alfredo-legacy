"""Logging utility with support for LOG prefix and structured logging."""

import logging
import sys
from datetime import datetime
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    """Log levels for the application."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors and prefixes to log messages."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
        'BOLD': '\033[1m',        # Bold
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors and LOG prefix."""
        # Add LOG prefix for backend events
        log_prefix = f"{self.COLORS['BOLD']}[LOG]{self.COLORS['RESET']}"
        
        # Color based on log level
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        
        # Format timestamp if needed
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Build the formatted message
        if record.levelname == 'INFO':
            # INFO messages are clean without level prefix
            formatted_msg = f"{log_prefix} {record.getMessage()}"
        else:
            # Other levels show the level name
            formatted_msg = f"{log_prefix} {level_color}[{record.levelname}]{self.COLORS['RESET']} {record.getMessage()}"
        
        return formatted_msg


class AppLogger:
    """Application logger with LOG prefix support."""
    
    _instance: Optional['AppLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        """Singleton pattern to ensure single logger instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logger if not already initialized."""
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self, level: str = "INFO"):
        """Set up the logger with custom formatter."""
        self._logger = logging.getLogger("pingmate")
        self._logger.setLevel(getattr(logging, level))
        
        # Remove existing handlers
        self._logger.handlers.clear()
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level))
        
        # Set custom formatter
        formatter = ColoredFormatter()
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        self._logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        self._logger.propagate = False
    
    def set_level(self, level: str):
        """Set the logging level."""
        if self._logger:
            self._logger.setLevel(getattr(logging, level.upper()))
            for handler in self._logger.handlers:
                handler.setLevel(getattr(logging, level.upper()))
    
    def log(self, message: str, level: LogLevel = LogLevel.INFO):
        """Log a message with the specified level."""
        if self._logger:
            log_func = getattr(self._logger, level.value.lower())
            log_func(message)
    
    def debug(self, message: str):
        """Log a debug message."""
        self.log(message, LogLevel.DEBUG)
    
    def info(self, message: str):
        """Log an info message."""
        self.log(message, LogLevel.INFO)
    
    def warning(self, message: str):
        """Log a warning message."""
        self.log(message, LogLevel.WARNING)
    
    def error(self, message: str):
        """Log an error message."""
        self.log(message, LogLevel.ERROR)
    
    def critical(self, message: str):
        """Log a critical message."""
        self.log(message, LogLevel.CRITICAL)


# Global logger instance
logger = AppLogger()


def setup_logging(level: str = "INFO"):
    """Set up logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger.set_level(level)
    logger.info("Logger initialized")


# Convenience functions
def log_info(message: str):
    """Log an info message."""
    logger.info(message)


def log_debug(message: str):
    """Log a debug message."""
    logger.debug(message)


def log_warning(message: str):
    """Log a warning message."""
    logger.warning(message)


def log_error(message: str):
    """Log an error message."""
    logger.error(message)


def log_critical(message: str):
    """Log a critical message."""
    logger.critical(message)
