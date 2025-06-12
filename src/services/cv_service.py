"""
CV (Curriculum Vitae) service for processing and managing resumes/CVs.

This module provides:
1. Functions for parsing CVs with LLM
2. CV processing logic (single and multiple)
"""

from typing import Dict, List, Optional
import asyncio
import uuid

from src.llm.parser import parse_document
from src.schemas.schemas import CVOutput
from src.vector_db.cv_repository import add_cv_to_db
from src.utils.logging import get_logger

logger = get_logger(__name__)

async def parse_cv_with_llm(
    cv_base64_content: Optional[str] = None, 
    cv_raw_text_content: Optional[str] = None, 
    content_type: str = "application/pdf"
) -> Dict:
    """
    Parses a CV using an LLM for structured data.
    Accepts either base64 encoded content or raw text content.
    
    Args:
        cv_base64_content: Base64 encoded content of the CV file
        cv_raw_text_content: Raw text content of the CV
        content_type: MIME type of the content
        
    Returns:
        Dictionary containing structured CV data
    """
    logger.info("Starting CV parsing with LLM.")
    
    try:
        # Get structured data from LLM
        structured_data = await parse_document(
            prompt_file="src/prompts/json_output_cv_prompt.md", 
            output_schema_class=CVOutput,
            base64_content=cv_base64_content,
            raw_text_content=cv_raw_text_content,
            content_type=content_type
        )
        
        logger.info("CV parsing with LLM completed successfully.")
        
        # Return the structured data in a dictionary with the key 'structured_data'
        # to match the format expected by the routes.py API handling
        return {
            "structured_data": structured_data
        }
    except Exception as e:
        logger.error(f"Error during CV parsing with LLM: {e}")
        return {"error": f"Failed to parse CV: {str(e)}"}

async def process_cv(
    cv_base64_content: Optional[str] = None,
    cv_raw_text_content: Optional[str] = None,
    cv_metadata: Optional[Dict] = None,
    associated_jd_id: Optional[str] = None,
    content_type: str = "application/pdf"
) -> Dict:
    """
    Process a CV: parse with LLM and store in vector database.
    
    Args:
        cv_base64_content: Base64 encoded content of the CV file
        cv_raw_text_content: Raw text content of the CV
        cv_metadata: Additional metadata for the CV
        associated_jd_id: ID of the associated job description
        content_type: MIME type of the content
        
    Returns:
        Dictionary containing processed CV data including vector DB ID
    """
    if cv_metadata is None:
        cv_metadata = {}
        
    if not associated_jd_id:
        return {"error": "Associated JD ID is required to process a CV."}
        
    try:
        # First parse the CV with LLM
        structured_data = await parse_cv_with_llm(
            cv_base64_content=cv_base64_content,
            cv_raw_text_content=cv_raw_text_content,
            content_type=content_type
        )
        
        # Generate a unique ID for the CV if not provided
        cv_id = cv_metadata.get("original_doc_id", str(uuid.uuid4()))
        
        # Prepare metadata for vector DB
        cv_metadata_with_links = {
            **cv_metadata,
            "original_doc_id": cv_id,
            "associated_jd_id": associated_jd_id,
            "structured_data": structured_data,
            "original_filename": cv_metadata.get("original_filename", f"CV_{cv_id}")
        }
        
        # Add to vector database
        stored_cv_id = await add_cv_to_db(
            cv_metadata_with_links=cv_metadata_with_links,
            cv_base64_content=cv_base64_content,
            cv_raw_text_content=cv_raw_text_content,
            content_type=content_type
        )
        
        if not stored_cv_id:
            return {"error": "Failed to add CV to vector database."}
            
        return {
            "cv_id": stored_cv_id,
            "structured_data": structured_data,
            "message": "CV processed and added to vector database successfully."
        }
        
    except Exception as e:
        logger.error(f"Error processing CV: {e}")
        return {"error": f"Failed to process CV: {str(e)}"}

async def process_multiple_cvs(
    cv_base64_contents: List[str],
    associated_jd_id: str,
    cv_metadata_list: Optional[List[Dict]] = None,
    content_type: str = "application/pdf"
) -> List[Dict]:
    """
    Process multiple CVs concurrently.
    
    Args:
        cv_base64_contents: List of base64 encoded CV contents
        associated_jd_id: ID of the associated job description
        cv_metadata_list: List of metadata dictionaries for each CV
        content_type: MIME type of the content
        
    Returns:
        List of dictionaries containing processed CV data
    """
    if not cv_base64_contents:
        return []
        
    if cv_metadata_list is None:
        cv_metadata_list = [{} for _ in cv_base64_contents]
        
    # Ensure cv_metadata_list matches the length of cv_base64_contents
    if len(cv_metadata_list) != len(cv_base64_contents):
        cv_metadata_list.extend([{} for _ in range(len(cv_base64_contents) - len(cv_metadata_list))])
        
    tasks = []
    for i, cv_content in enumerate(cv_base64_contents):
        tasks.append(
            process_cv(
                cv_base64_content=cv_content,
                cv_metadata=cv_metadata_list[i],
                associated_jd_id=associated_jd_id,
                content_type=content_type
            )
        )
        
    results = await asyncio.gather(*tasks)
    return list(results)

async def process_cv_from_s3(
    s3_uri: str,
    associated_jd_id: str
) -> Dict:
    """
    Process a CV from S3: fetch from S3, parse with LLM and store in vector database.
    
    Args:
        s3_uri: S3 URI of the CV file (format: s3://bucket-name/folder/file.pdf)
        associated_jd_id: ID of the associated job description
        
    Returns:
        Dictionary containing processed CV data including vector DB ID
    """
    if not associated_jd_id:
        return {"error": "Associated JD ID is required to process a CV."}
        
    try:
        # Import S3 handler here to avoid circular imports
        from src.utils.s3_handler import s3_handler
        
        # Get file from S3
        s3_file_data = await s3_handler.get_file_from_s3(s3_uri)
        
        if s3_file_data.get("error"):
            logger.error(f"S3 file processing error for CV {s3_file_data.get('filename')}: {s3_file_data.get('error')}")
            return {"error": s3_file_data.get("error")}

        filename = s3_file_data["filename"]
        raw_text = s3_file_data["raw_text_content"]
        base64_encoded = s3_file_data["base64_content"]
        actual_content_type = s3_file_data["content_type"]
        
        # Prepare metadata for vector DB
        cv_metadata = {
            "original_filename": filename,
            "source_s3_uri": s3_uri,
            "source_bucket": s3_file_data["bucket"],
            "source_key": s3_file_data["key"],
            "file_size_mb": s3_file_data["file_size_mb"]
        }
        
        # Use existing process_cv function
        result = await process_cv(
            cv_base64_content=base64_encoded,
            cv_raw_text_content=raw_text,
            cv_metadata=cv_metadata,
            associated_jd_id=associated_jd_id,
            content_type=actual_content_type
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing CV from S3 {s3_uri}: {e}")
        return {"error": f"Failed to process CV from S3: {str(e)}"} 