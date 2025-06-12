"""
File handling utilities for Smart Recruit.

This module provides:
1. Functions for processing uploaded files
2. File content extraction and conversion
"""

import base64
import io
from typing import Dict, Optional, Union
import docx
import magic
from fastapi import UploadFile

from src.utils.logging import get_logger

logger = get_logger(__name__)

async def process_uploaded_file_content(file: UploadFile) -> Dict[str, Optional[Union[str, bytes]]]:
    """
    Process an uploaded file and extract its content.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Dictionary containing:
        - raw_text_content: Extracted text content if available
        - base64_content: Base64-encoded content if text extraction not possible
        - content_type: MIME type of the file
        - filename: Original filename
        - error: Error message if processing failed
    """
    contents = await file.read()
    await file.seek(0) 

    mime_type = magic.from_buffer(contents, mime=True)
    logger.info(f"Detected MIME type for {file.filename}: {mime_type}")

    raw_text_content: Optional[str] = None
    base64_content_str: Optional[str] = None

    if mime_type == "application/pdf":
        base64_content_str = base64.b64encode(contents).decode('utf-8')
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or \
         (mime_type == "application/zip" and file.filename and file.filename.lower().endswith('.docx')):
        if mime_type == "application/zip":
            logger.info(f"MIME type detected as 'application/zip' for {file.filename}, but attempting DOCX parse due to .docx extension.")
        try:
            doc = docx.Document(io.BytesIO(contents))
            extracted_text = "\\\\n".join([para.text for para in doc.paragraphs])
            if not extracted_text.strip(): # Check if extracted text is blank
                logger.warning(f"No text content found in DOCX paragraphs for {file.filename}. It might be image-only or text in unsupported elements.")
                return {"error": f"No text content found in DOCX paragraphs for {file.filename}. The document might be image-only or text is in elements not directly parseable as paragraphs.", "filename": file.filename, "raw_text_content": None, "base64_content": None, "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}

            raw_text_content = extracted_text # Assign if not blank
            logger.info(f"Successfully extracted text from DOCX: {file.filename}")
            # Ensure the content_type reflects that we are treating it as docx for text extraction
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" 
        except Exception as e:
            logger.error(f"Error processing DOCX file {file.filename} (even after specific check): {e}", exc_info=True)
            # Fallback to base64 if DOCX parsing fails for a .docx file
            logger.warning(f"Falling back to base64 for {file.filename} after DOCX parsing attempt failed.")
            base64_content_str = base64.b64encode(contents).decode('utf-8')
            mime_type = "application/octet-stream" # Fallback MIME type
            raw_text_content = None # Ensure raw_text is None if fallback happens
    elif mime_type in ["text/plain", "text/markdown"]:
        try:
            raw_text_content = contents.decode('utf-8')
            logger.info(f"Successfully read text from {mime_type} file: {file.filename}")
        except UnicodeDecodeError:
            try:
                raw_text_content = contents.decode('latin-1') # Fallback
                logger.info(f"Successfully read text (latin-1) from {mime_type} file: {file.filename}")
            except UnicodeDecodeError as ude_fallback:
                logger.error(f"Fallback decoding error for {file.filename}: {ude_fallback}", exc_info=True)
                return {"error": f"Could not decode text file {file.filename}. Ensure it is UTF-8 or Latin-1 encoded.", "filename": file.filename, "raw_text_content": None, "base64_content": None, "content_type": mime_type}
    else:
        logger.warning(f"Unsupported or ambiguous file type: {mime_type} for file {file.filename}. Attempting base64 encoding as a fallback.")
        base64_content_str = base64.b64encode(contents).decode('utf-8')
        mime_type = "application/octet-stream" # Generic for LLM if it can handle it as image/pdf
        
    return {
        "raw_text_content": raw_text_content,
        "base64_content": base64_content_str,
        "content_type": mime_type,
        "filename": file.filename,
        "error": None
    }

def encode_file_to_base64(file_path: str) -> str:
    """
    Read a file and encode its contents as base64.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Base64-encoded string of the file contents
        
    Raises:
        FileNotFoundError: If the file does not exist
        IOError: If there is an error reading the file
    """
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
            return base64.b64encode(file_content).decode('utf-8')
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except IOError as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise

def decode_base64_to_bytes(base64_str: str) -> bytes:
    """
    Decode a base64 string to bytes.
    
    Args:
        base64_str: Base64-encoded string
        
    Returns:
        Decoded bytes
        
    Raises:
        ValueError: If the input is not a valid base64 string
    """
    try:
        return base64.b64decode(base64_str)
    except Exception as e:
        logger.error(f"Error decoding base64 string: {str(e)}")
        raise ValueError(f"Invalid base64 string: {str(e)}") 