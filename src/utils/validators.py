"""
Validation utilities for Smart Recruit.

This module provides:
1. Input validation functions
2. Data format validation
"""

import re
import uuid
from typing import Dict, Any, List, Optional, Union

from src.utils.logging import get_logger

logger = get_logger(__name__)

def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        uuid_string: String to validate as UUID
        
    Returns:
        True if the string is a valid UUID, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(uuid_string)
        return str(uuid_obj) == uuid_string
    except (ValueError, AttributeError):
        return False

def validate_jd_id(jd_id: str) -> bool:
    """
    Validate a JD ID.
    
    Args:
        jd_id: JD ID to validate
        
    Returns:
        True if the JD ID is valid, False otherwise
    """
    if not jd_id or not isinstance(jd_id, str):
        logger.error(f"Invalid JD ID: {jd_id}. Must be a non-empty string.")
        return False
    
    if not is_valid_uuid(jd_id):
        logger.error(f"Invalid JD ID format: {jd_id}. Must be a valid UUID.")
        return False
    
    return True

def validate_cv_id(cv_id: str) -> bool:
    """
    Validate a CV ID.
    
    Args:
        cv_id: CV ID to validate
        
    Returns:
        True if the CV ID is valid, False otherwise
    """
    if not cv_id or not isinstance(cv_id, str):
        logger.error(f"Invalid CV ID: {cv_id}. Must be a non-empty string.")
        return False
    
    if not is_valid_uuid(cv_id):
        logger.error(f"Invalid CV ID format: {cv_id}. Must be a valid UUID.")
        return False
    
    return True

def validate_file_type(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Validate if a filename has an allowed extension.
    
    Args:
        filename: Name of the file to validate
        allowed_extensions: List of allowed file extensions (e.g., ['pdf', 'docx'])
        
    Returns:
        True if the file has an allowed extension, False otherwise
    """
    if not filename or not isinstance(filename, str):
        logger.error(f"Invalid filename: {filename}. Must be a non-empty string.")
        return False
    
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    if not extension or extension not in allowed_extensions:
        logger.error(f"Invalid file type: {filename}. Allowed extensions: {', '.join(allowed_extensions)}.")
        return False
    
    return True

def validate_email(email: str) -> bool:
    """
    Validate an email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if the email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Simple regex for email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))

def validate_ranking_request(request_data: Dict[str, Any]) -> Optional[str]:
    """
    Validate a ranking request.
    
    Args:
        request_data: Dictionary containing ranking request data
        
    Returns:
        Error message if validation fails, None if validation succeeds
    """
    if not isinstance(request_data, dict):
        return "Request data must be a dictionary."
    
    if 'jd_id' not in request_data:
        return "Missing required field: jd_id."
    
    if not validate_jd_id(request_data['jd_id']):
        return f"Invalid JD ID: {request_data['jd_id']}."
    
    if 'cv_ids' not in request_data or not isinstance(request_data['cv_ids'], list):
        return "Missing or invalid field: cv_ids. Must be a list."
    
    if not request_data['cv_ids']:
        return "CV IDs list cannot be empty."
    
    for cv_id in request_data['cv_ids']:
        if not validate_cv_id(cv_id):
            return f"Invalid CV ID in list: {cv_id}."
    
    return None

def validate_question_generation_request(request_data: Dict[str, Any]) -> Optional[str]:
    """
    Validate a question generation request.
    
    Args:
        request_data: Dictionary containing question generation request data
        
    Returns:
        Error message if validation fails, None if validation succeeds
    """
    if not isinstance(request_data, dict):
        return "Request data must be a dictionary."
    
    if 'jd_id' not in request_data:
        return "Missing required field: jd_id."
    
    if not validate_jd_id(request_data['jd_id']):
        return f"Invalid JD ID: {request_data['jd_id']}."
    
    if 'cv_id' not in request_data:
        return "Missing required field: cv_id."
    
    if not validate_cv_id(request_data['cv_id']):
        return f"Invalid CV ID: {request_data['cv_id']}."
    
    return None 