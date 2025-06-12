"""
Logging utilities for Smart Recruit.

This module provides:
1. Logging configuration
2. Logger factory function
"""

import os
import logging
import sys
from logging.handlers import RotatingFileHandler

# Set the desired log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Log file path
LOG_FILE = os.path.join(LOG_DIR, "smartrecruit.log")

# Create a simpler formatter
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create file handler with rotation
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Configure the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove existing handlers to prevent duplicate logs
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Add the handlers
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

def get_logger(name):
    """
    Get a logger with the specified name that uses the project's logging configuration.
    
    Args:
        name: Name for the logger (typically module name)
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    return logger

def set_log_level(level):
    """
    Set the log level for all handlers.
    
    Args:
        level: Logging level (e.g., logging.INFO, logging.DEBUG)
    """
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level) 