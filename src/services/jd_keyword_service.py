"""
JD Keywords service for generating searchable keywords from job descriptions.

This module provides:
1. Functions for extracting keywords from JD content using LLM
2. JD keyword processing logic
"""

from typing import Dict, Optional

from src.llm.parser import parse_document
from src.schemas.schemas import JDKeywordsOutput
from src.vector_db.vectordb_client import get_full_document_text_from_db, JD_COLLECTION_NAME
from src.utils.logging import get_logger

logger = get_logger(__name__)

async def generate_jd_keywords_from_text(jd_text: str) -> Dict:
    """
    Generate keywords from JD text using LLM.
    
    Args:
        jd_text: Raw text content of the JD
        
    Returns:
        Dictionary containing keywords or error information
    """
    logger.info("Starting JD keyword generation with LLM.")
    
    if not jd_text or not jd_text.strip():
        logger.error("Error: JD text content is empty or not provided.")
        return {"error": "JD text content is empty or not provided."}

    try:
        # Use parse_document to generate keywords
        parsed_keywords_from_llm = await parse_document(
            prompt_file="src/prompts/jd_keywords_prompt.md", 
            output_schema_class=JDKeywordsOutput,
            raw_text_content=jd_text,
            content_type="text/plain"
        )
        
        logger.info("JD keyword generation with LLM completed successfully.")
        return parsed_keywords_from_llm
        
    except Exception as e:
        logger.error(f"Error during JD keyword generation with LLM: {e}")
        raise

async def generate_jd_keywords_by_id(jd_id: str) -> Dict:
    """
    Generate keywords for a JD by fetching its content from the database using JD ID.
    
    Args:
        jd_id: The ID of the JD in the vector database
        
    Returns:
        Dictionary containing keywords or error information
    """
    logger.info(f"Starting JD keyword generation for JD ID: {jd_id}")
    
    if not jd_id or not jd_id.strip():
        logger.error("Error: JD ID is empty or not provided.")
        return {"error": "JD ID is empty or not provided."}

    try:
        # Fetch the full JD text from the database
        logger.info(f"Fetching JD content from database for ID: {jd_id}")
        jd_text = await get_full_document_text_from_db(jd_id, JD_COLLECTION_NAME())
        
        if not jd_text:
            logger.error(f"Could not retrieve JD text for ID: {jd_id}")
            return {"error": f"JD not found for ID: {jd_id}"}
        
        logger.info(f"Successfully retrieved JD text for ID: {jd_id}. Text length: {len(jd_text)} characters")
        
        # Generate keywords from the retrieved text
        keywords_result = await generate_jd_keywords_from_text(jd_text)
        
        if "error" in keywords_result:
            logger.error(f"Keyword generation failed for JD ID {jd_id}: {keywords_result['error']}")
            return keywords_result
        
        logger.info(f"Successfully generated keywords for JD ID: {jd_id}")
        return keywords_result
        
    except Exception as e:
        logger.error(f"Error generating keywords for JD ID {jd_id}: {e}")
        return {"error": f"Failed to generate keywords for JD ID {jd_id}: {str(e)}"} 