"""
CV (Curriculum Vitae) repository for vector database operations.

This module provides:
1. Functions for adding CVs to the vector database
2. CV-specific search and retrieval operations
"""

from typing import Dict, Any, Optional, List, Union

from src.vector_db.vectordb_client import (
    CV_COLLECTION_NAME,
    get_qdrantchunk_content,
    get_full_document_text_from_db,
    search_similar_chunks
)
from src.vector_db.jd_repository import _process_chunks_for_vector_db
from src.llm.chunker import chunk_document_with_llm
from src.utils.logging import get_logger

logger = get_logger(__name__)

async def add_cv_to_db(
    cv_metadata_with_links: Dict[str, Any],
    cv_base64_content: Optional[str] = None,
    cv_raw_text_content: Optional[str] = None,
    content_type: str = "application/pdf" # Default for PDF if base64 is used
) -> Optional[str]:
    """
    Processes CV using LLM for chunking, then adds to cv_collection.
    cv_metadata_with_links MUST include 'original_doc_id' (for the CV) and 'associated_jd_id'.
    Accepts either base64 encoded content or raw text content.
    
    Args:
        cv_metadata_with_links: Dictionary containing metadata and links to related documents
        cv_base64_content: Base64 encoded content of the CV file
        cv_raw_text_content: Raw text content of the CV
        content_type: MIME type of the content
        
    Returns:
        original_doc_id (of the CV) or None if processing failed
    """
    if not cv_metadata_with_links.get("original_doc_id"):
        logger.error("Error: 'original_doc_id' for the CV must be provided in cv_metadata_with_links.")
        return None 
    if not cv_metadata_with_links.get("associated_jd_id"):
        logger.error("Error: 'associated_jd_id' must be provided in cv_metadata_with_links.")
        return None
        
    cv_id = cv_metadata_with_links['original_doc_id']
    logger.info(f"Processing CV (ID: {cv_id}) for vector DB using LLM chunking...")
    
    # Chunk the CV using the general LLM chunker
    cv_chunks = await chunk_document_with_llm(
        base64_content=cv_base64_content,
        raw_text_content=cv_raw_text_content,
        content_type=content_type,
        prompt_file="src/prompts/cv_enrich_prompt.md"
    ) 

    if not cv_chunks:
        logger.error(f"Failed to chunk CV (ID: {cv_id}) using LLM. Cannot add to vector DB.")
        return None
    
    # Add document type for clarity in DB
    cv_metadata_with_links["document_type"] = "cv"

    # Use the refactored function to process the already chunked CV text
    success = await _process_chunks_for_vector_db(cv_chunks, CV_COLLECTION_NAME(), cv_metadata_with_links)
    if success:
        logger.info(f"CV (ID: {cv_id}) successfully added to vector DB.")
    else:
        logger.error(f"Failed to add CV (ID: {cv_id}) to vector DB after chunking.")
    return cv_id if success else None

async def search_cv_chunks(query_text: str, top_k: int = 5, filter_by_doc_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Search for CV chunks similar to query text, optionally filtered by specific document IDs.
    
    Args:
        query_text: Text to search for
        top_k: Maximum number of results to return
        filter_by_doc_ids: Optional list of document IDs to filter by
        
    Returns:
        List of dictionaries containing search results with scores
    """
    return await search_similar_chunks(query_text, CV_COLLECTION_NAME(), top_k, filter_by_doc_ids)

async def get_cv_chunks(doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all chunk payloads for a given CV document ID.
    
    Args:
        doc_id: Document ID to retrieve chunks for
        
    Returns:
        List of dictionaries containing chunk payloads
    """
    return await get_qdrantchunk_content(doc_id, CV_COLLECTION_NAME())

async def get_full_cv_text(doc_id: str) -> Optional[str]:
    """
    Retrieves and reconstructs the full text of a CV document.
    
    Args:
        doc_id: The original_doc_id of the CV document
        
    Returns:
        The reconstructed full text of the CV document or None if not found
    """
    return await get_full_document_text_from_db(doc_id, CV_COLLECTION_NAME())

async def get_cvs_for_jd(jd_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves metadata for all CVs associated with a specific JD.
    
    Args:
        jd_id: The JD document ID to find associated CVs for
        
    Returns:
        List of CV metadata dictionaries
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from config import qdrant_client
    
    if not jd_id:
        logger.error("Error: No JD ID provided to get_cvs_for_jd.")
        return []

    try:
        # Get unique CV IDs associated with this JD
        cv_ids = set()
        next_page_offset = None
        limit_per_scroll = 100
        
        while True:
            scroll_response, next_page_offset = await qdrant_client.scroll(
                collection_name=CV_COLLECTION_NAME(),
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="associated_jd_id",
                            match=MatchValue(value=jd_id)
                        )
                    ]
                ),
                limit=limit_per_scroll,
                offset=next_page_offset,
                with_payload=True,
                with_vectors=False
            )
            
            if scroll_response:
                for hit in scroll_response:
                    if hit.payload and "original_doc_id" in hit.payload:
                        cv_ids.add(hit.payload["original_doc_id"])
            
            if next_page_offset is None:
                break
                
        # For each CV ID, get the first chunk to extract metadata
        cv_metadata_list = []
        for cv_id in cv_ids:
            chunks = await get_cv_chunks(cv_id)
            if chunks:
                # Extract metadata from the first chunk
                metadata = {k: v for k, v in chunks[0].items() 
                           if k not in ["chunk_index", "enriched_text", "og_text", "total_chunks_for_doc"]}
                cv_metadata_list.append(metadata)
                
        return cv_metadata_list
        
    except Exception as e:
        logger.error(f"Error retrieving CVs for JD ID '{jd_id}': {type(e).__name__} - {e}")
        return [] 