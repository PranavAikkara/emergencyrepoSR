"""
JD (Job Description) service for processing and managing job descriptions.

This module provides:
1. Functions for parsing JDs with LLM
2. JD processing logic
"""

from typing import Dict, Optional

from src.llm.parser import parse_document
from src.schemas.schemas import JDOutput
from src.vector_db.jd_repository import add_jd_to_db
from src.utils.logging import get_logger

logger = get_logger(__name__)

async def parse_jd_with_llm(
    jd_base64_content: Optional[str] = None, 
    jd_raw_text_content: Optional[str] = None, 
    content_type: str = "application/pdf"
) -> Dict:
    """
    Parses a Job Description using an LLM for structured data.
    Accepts either base64 encoded content (e.g., for PDFs) or raw text content.
    
    Args:
        jd_base64_content: Base64 encoded content of the JD file
        jd_raw_text_content: Raw text content of the JD
        content_type: MIME type of the content
        
    Returns:
        Dictionary containing parsed JD data or error information
    """
    logger.info("Starting JD parsing with LLM.")
    if not jd_base64_content and not jd_raw_text_content:
        logger.error("Error: JD content not provided (neither base64 nor raw text).")
        return {"error": "JD content not provided."}

    try:
        # Pass the appropriate content to parse_document
        parsed_data_from_llm = await parse_document(
            prompt_file="src/prompts/json_output_jd_prompt.md", 
            output_schema_class=JDOutput,
            base64_content=jd_base64_content, 
            raw_text_content=jd_raw_text_content,
            content_type=content_type
        )
        logger.info("JD parsing with LLM completed successfully.")
        return parsed_data_from_llm
    except Exception as e:
        logger.error(f"Error during JD parsing with LLM: {e}")
        raise

async def process_jd(
    jd_base64_content: Optional[str] = None,
    jd_raw_text_content: Optional[str] = None,
    jd_metadata: Optional[Dict] = None,
    content_type: str = "application/pdf"
) -> Dict:
    """
    Process a job description: parse with LLM and store in vector database.
    
    Args:
        jd_base64_content: Base64 encoded content of the JD file
        jd_raw_text_content: Raw text content of the JD
        jd_metadata: Additional metadata for the JD
        content_type: MIME type of the content
        
    Returns:
        Dictionary containing processed JD data including vector DB ID
    """
    if jd_metadata is None:
        jd_metadata = {}
        
    try:
        # First parse the JD with LLM
        parsed_jd = await parse_jd_with_llm(
            jd_base64_content=jd_base64_content,
            jd_raw_text_content=jd_raw_text_content,
            content_type=content_type
        )
        
        if "error" in parsed_jd:
            return parsed_jd
            
        # Add structured data to metadata
        jd_metadata.update({
            "structured_data": parsed_jd,
            "original_filename": jd_metadata.get("original_filename", "Unknown JD")
        })
        
        # Add to vector database
        jd_id = await add_jd_to_db(
            jd_specific_metadata=jd_metadata,
            jd_base64_content=jd_base64_content,
            jd_raw_text_content=jd_raw_text_content,
            content_type=content_type
        )
        
        if not jd_id:
            return {"error": "Failed to add JD to vector database."}
            
        return {
            "jd_id": jd_id,
            "structured_data": parsed_jd,
            "message": "JD processed and added to vector database successfully."
        }
        
    except Exception as e:
        logger.error(f"Error processing JD: {e}")
        return {"error": f"Failed to process JD: {str(e)}"} 