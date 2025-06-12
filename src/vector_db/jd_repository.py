"""
JD (Job Description) repository for vector database operations.

This module provides:
1. Functions for adding JDs to the vector database
2. JD-specific search and retrieval operations
"""

import uuid
from typing import Dict, Any, Optional, List, Union

from src.vector_db.vectordb_client import (
    JD_COLLECTION_NAME,
    get_embedding,
    get_qdrantchunk_content,
    get_full_document_text_from_db,
    search_similar_chunks
)
from src.llm.chunker import chunk_document_with_llm
from src.utils.logging import get_logger
from qdrant_client.models import PointStruct

from config import qdrant_client

logger = get_logger(__name__)

async def _process_chunks_for_vector_db(
    chunks: Optional[List[Dict[str, Union[str, int]]]],
    target_collection_name: str, 
    doc_metadata: Dict[str, Any]
) -> bool:
    """
    Internal: Embeds enriched text from chunks and upserts to Qdrant.
    Payload stores both original and enriched text.
    
    Args:
        chunks: List of chunk dictionaries with enriched_content
        target_collection_name: Collection name to add chunks to
        doc_metadata: Metadata to attach to each chunk
        
    Returns:
        Boolean indicating success or failure
    """
    if not chunks or not all(isinstance(chunk, dict) and chunk.get("enriched_content") for chunk in chunks):
        logger.warning(f"No valid chunk objects (with enriched_content) provided for processing for collection '{target_collection_name}'. Doc ID: {doc_metadata.get('original_doc_id')}")
        return False
    
    points = []
    original_doc_id = doc_metadata.get("original_doc_id", str(uuid.uuid4()))
    if "original_doc_id" not in doc_metadata:
        doc_metadata["original_doc_id"] = original_doc_id

    for i, chunk_item in enumerate(chunks):
        og_text = chunk_item.get("og_content", "")
        enriched_text = chunk_item.get("enriched_content", "")

        if not enriched_text.strip(): 
            logger.warning(f"Skipping empty enriched_text for chunk {i} for doc ID {original_doc_id} in {target_collection_name}.")
            continue

        chunk_id = str(uuid.uuid4())
        embedding = await get_embedding(enriched_text)
        
        payload = {
            **doc_metadata,
            "chunk_index": i,
            "enriched_text": enriched_text, # Storing enriched_text as "text" for embedding/primary search
            "og_text": og_text,    # Storing original text as "og_text"
            "total_chunks_for_doc": len(chunks),
        }
        # Add weight to payload only for JD chunks
        if target_collection_name == JD_COLLECTION_NAME():
            payload["weight"] = chunk_item.get("weight", 1) # Default to 1 if missing
        
        points.append(PointStruct(id=chunk_id, vector=embedding, payload=payload))

    if not points:
        logger.warning(f"No valid points generated after processing chunks for Doc ID {original_doc_id}. Nothing to upsert.")
        return False
    
    try:
        await qdrant_client.upsert(
            collection_name=target_collection_name,
            points=points
        )
        logger.info(f"Successfully added {len(points)} points for Doc ID {original_doc_id} to '{target_collection_name}'.")
        return True
    except Exception as e:
        logger.error(f"Error upserting points to '{target_collection_name}' for Doc ID {original_doc_id}: {e}")
        return False

async def add_jd_to_db(
    jd_specific_metadata: Optional[Dict[str, Any]] = None,
    jd_base64_content: Optional[str] = None, 
    jd_raw_text_content: Optional[str] = None,
    content_type: str = "application/pdf"  # Default for PDF if base64 is used
) -> Optional[str]:
    """
    Processes a JD using LLM for chunking, adds its content to jd_collection.
    Accepts either base64 encoded content or raw text content.
    
    Args:
        jd_specific_metadata: Dictionary of metadata specific to this JD
        jd_base64_content: Base64 encoded content of the JD file
        jd_raw_text_content: Raw text content of the JD
        content_type: MIME type of the content
        
    Returns:
        original_doc_id or None if processing failed
    """
    if jd_specific_metadata is None:
        jd_specific_metadata = {}
    
    jd_filename = jd_specific_metadata.get("original_filename", "Unknown JD")
    logger.info(f"Processing JD ({jd_filename}) for vector DB using LLM chunking...")

    if not jd_base64_content and not jd_raw_text_content:
        logger.error(f"No content (base64 or raw text) provided for JD: {jd_filename}. Cannot add to vector DB.")
        return None

    logger.info(f"Chunking JD ({jd_filename}) using LLM chunker...")
    jd_chunks = await chunk_document_with_llm(
        base64_content=jd_base64_content,
        raw_text_content=jd_raw_text_content,
        content_type=content_type,
        prompt_file="src/prompts/jd_enrich_prompt.md"
    )
    
    if not jd_chunks:
        logger.error(f"Failed to chunk JD ({jd_filename}) using LLM. Cannot add to vector DB.")
        return None

    original_doc_id = str(uuid.uuid4())
    doc_metadata = {
        **jd_specific_metadata,
        "original_doc_id": original_doc_id,
        "document_type": "jd"
    }
    if "source" not in doc_metadata: # Add a generic source if not provided
        doc_metadata["source"] = "base64_upload_jd_multimodal_chunking"

    success = await _process_chunks_for_vector_db(jd_chunks, JD_COLLECTION_NAME(), doc_metadata)
    if success:
        logger.info(f"JD ({jd_filename}) successfully added to vector DB. Doc ID: {original_doc_id}")
    else:
        logger.error(f"Failed to add JD ({jd_filename}) to vector DB after chunking.")
    return original_doc_id if success else None

async def search_jd_chunks(query_text: str, top_k: int = 5, filter_by_doc_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Search for JD chunks similar to query text, optionally filtered by specific document IDs.
    
    Args:
        query_text: Text to search for
        top_k: Maximum number of results to return
        filter_by_doc_ids: Optional list of document IDs to filter by
        
    Returns:
        List of dictionaries containing search results with scores
    """
    return await search_similar_chunks(query_text, JD_COLLECTION_NAME(), top_k, filter_by_doc_ids)

async def get_jd_chunks(doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all chunk payloads for a given JD document ID.
    
    Args:
        doc_id: Document ID to retrieve chunks for
        
    Returns:
        List of dictionaries containing chunk payloads
    """
    return await get_qdrantchunk_content(doc_id, JD_COLLECTION_NAME())

async def get_full_jd_text(doc_id: str) -> Optional[str]:
    """
    Retrieves and reconstructs the full text of a JD document.
    
    Args:
        doc_id: The original_doc_id of the JD document
        
    Returns:
        The reconstructed full text of the JD document or None if not found
    """
    return await get_full_document_text_from_db(doc_id, JD_COLLECTION_NAME()) 