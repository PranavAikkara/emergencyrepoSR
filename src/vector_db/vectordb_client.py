"""
Vector database client configuration and common operations.

This module provides:
1. Client configuration for Qdrant vector database
2. Collection initialization functions
3. Embedding generation utilities using DeepInfra BGE API
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
import aiohttp

from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

from config import qdrant_client, get_embedding_config
from src.utils.logging import get_logger

logger = get_logger(__name__)

# --- Collection Names ---
def JD_COLLECTION_NAME():
    return "jd_collection"

def CV_COLLECTION_NAME():
    return "cv_collection"

# Get embedding configuration
embedding_config = get_embedding_config()

# Vector parameters for collections
_vector_params = VectorParams(size=embedding_config["dimensions"], distance=Distance.COSINE)

# --- Initialize Collections ---
async def _initialize_collection(collection_name: str, vectors_config: VectorParams):
    """
    Initialize a collection in Qdrant if it doesn't exist.
    Creates payload indexes for efficient filtering.
    
    Args:
        collection_name: Name of the collection to initialize
        vectors_config: Vector parameters for the collection
    """
    try:
        await qdrant_client.get_collection(collection_name=collection_name)
        logger.info(f"Collection '{collection_name}' found. Ensuring payload index for 'original_doc_id' exists.")
        # Optionally, check and create index if it doesn't exist even if collection exists.
        # For simplicity here, we assume if we created it, we made the index.
        # A more robust check would list indexes and create if missing.
        try:
            await qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name="original_doc_id",
                field_schema=PayloadSchemaType.KEYWORD # UUIDs stored as strings are best indexed as keywords
            )
            logger.info(f"Payload index for 'original_doc_id' ensured/created in '{collection_name}'.")
            # If it's the JD collection, also try to create an index for weight
            if collection_name == JD_COLLECTION_NAME():
                await qdrant_client.create_payload_index(
                    collection_name=collection_name,
                    field_name="weight",
                    field_schema=PayloadSchemaType.INTEGER
                )
                logger.info(f"Payload index for 'weight' ensured/created in JD collection '{collection_name}'.")
        except Exception as index_e:
            # This might happen if index already exists with a different config, or other issues.
            logger.warning(f"Note: Could not create/verify payload index for 'original_doc_id' or 'weight' in '{collection_name}' (may already exist or other issue): {type(index_e).__name__} - {index_e}")

    except Exception as e:
        logger.error(f"Collection '{collection_name}' not found or error: {type(e).__name__}. Attempting to create.")
        try:
            await qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=vectors_config
            )
            logger.info(f"Collection '{collection_name}' created successfully.")
            # Create payload index for original_doc_id after collection creation
            try:
                await qdrant_client.create_payload_index(
                    collection_name=collection_name,
                    field_name="original_doc_id",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                logger.info(f"Payload index for 'original_doc_id' created in '{collection_name}'.")
                # If it's the JD collection, also create an index for weight
                if collection_name == JD_COLLECTION_NAME():
                    await qdrant_client.create_payload_index(
                        collection_name=collection_name,
                        field_name="weight",
                        field_schema=PayloadSchemaType.INTEGER
                    )
                    logger.info(f"Payload index for 'weight' created in JD collection '{collection_name}'.")
            except Exception as index_creation_e:
                logger.warning(f"Error creating payload index for 'original_doc_id' or 'weight' in new collection '{collection_name}': {type(index_creation_e).__name__} - {index_creation_e}")
        except Exception as creation_e:
            logger.error(f"Error creating collection '{collection_name}': {type(creation_e).__name__} - {creation_e}. It might already exist now.")

async def initialize_qdrant_collections():
    """
    Initializes all necessary Qdrant collections asynchronously.
    Creates JD and CV collections with appropriate vector parameters.
    """
    logger.info("Attempting to initialize Qdrant collections asynchronously...")
    vector_params = VectorParams(size=embedding_config["dimensions"], distance=Distance.COSINE)
    await _initialize_collection(JD_COLLECTION_NAME(), vector_params)
    await _initialize_collection(CV_COLLECTION_NAME(), vector_params)
    logger.info("Asynchronous Qdrant collection initialization process completed.")

# --- Embedding Generation ---
async def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector for the given text using DeepInfra BGE API.
    
    Args:
        text: Text to generate embedding for
        
    Returns:
        List of floating point values representing the embedding vector
    """
    try:
        text = text.strip()
        if not text:
            logger.warning("Empty text provided for embedding generation")
            return [0.0] * _vector_params.size
        
        # Check if API key is configured
        if not embedding_config["api_key"]:
            raise Exception("EMBEDDING_MODEL_API key not configured")
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {embedding_config['api_key']}"
        }
        
        payload = {
            "inputs": [text]
        }
        
        timeout = aiohttp.ClientTimeout(total=embedding_config["timeout"])
        
        # Make API call
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                embedding_config["api_url"],
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DeepInfra API error {response.status}: {error_text}")
                
                result = await response.json()
                
                if "embeddings" not in result or not result["embeddings"]:
                    raise Exception("Invalid response format from DeepInfra API")
                
                embedding_vector = result["embeddings"][0]
                
                if len(embedding_vector) != embedding_config["dimensions"]:
                    raise Exception(f"Unexpected embedding dimensions: got {len(embedding_vector)}, expected {embedding_config['dimensions']}")
                
                logger.debug(f"Successfully generated embedding for text of length {len(text)}")
                return embedding_vector
        
    except Exception as e:
        logger.error(f"Error generating embedding via DeepInfra API: {e}")
        # Return zero vector as fallback
        return [0.0] * _vector_params.size

# --- Common Search Functions ---
async def search_similar_chunks(
    query_text: str, 
    collection_to_search: str, 
    top_k: int = 5, 
    filter_by_doc_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Search for chunks similar to query text, optionally filtered by specific document IDs.
    
    Args:
        query_text: Text to search for
        collection_to_search: Collection name to search in
        top_k: Maximum number of results to return
        filter_by_doc_ids: Optional list of document IDs to filter by
        
    Returns:
        List of dictionaries containing search results with scores
    """
    from qdrant_client.models import Filter, FieldCondition, MatchAny
    
    if not query_text.strip():
        return []
        
    query_embedding = await get_embedding(query_text)
    if not any(query_embedding):
        logger.warning("Warning: Query embedding is zero vector for search_similar_chunks.")

    search_filter = None
    if filter_by_doc_ids:
        if isinstance(filter_by_doc_ids, list) and filter_by_doc_ids:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="original_doc_id", 
                        match=MatchAny(any=filter_by_doc_ids)
                    )
                ]
            )
            logger.info(f"Searching in '{collection_to_search}' filtered by original_doc_ids: {filter_by_doc_ids}")
        elif not isinstance(filter_by_doc_ids, list):
             logger.warning(f"Warning: filter_by_doc_ids expected a list, got {type(filter_by_doc_ids)}. Ignoring doc ID filter.")
    else:
        logger.info(f"Searching in '{collection_to_search}' without doc_id filter.")

    try:
        search_result = await qdrant_client.search(
            collection_name=collection_to_search,
            query_vector=query_embedding,
            query_filter=search_filter, 
            limit=top_k,
            with_payload=True
        )
        results_with_score = []
        for hit in search_result:
            payload_copy = hit.payload.copy() if hit.payload else {}
            payload_copy['_score'] = hit.score
            results_with_score.append(payload_copy)
        return results_with_score
        
    except Exception as e:
        logger.error(f"Error searching collection '{collection_to_search}': {type(e).__name__} - {e}")
        return []

async def get_qdrantchunk_content(doc_id: str, collection_name: str) -> List[Dict[str, Any]]:
    """
    Retrieves all chunk payloads for a given original_doc_id from the specified collection.
    
    Args:
        doc_id: Document ID to retrieve chunks for
        collection_name: Collection name to retrieve from
        
    Returns:
        List of dictionaries containing chunk payloads
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    if not doc_id:
        logger.error("Error: No document ID provided to get_qdrantchunk_content.")
        return []
    if not collection_name:
        logger.error("Error: No collection name provided to get_qdrantchunk_content.")
        return []

    logger.info(f"Attempting to retrieve all chunks for doc_id: '{doc_id}' from collection: '{collection_name}'")
    
    retrieved_chunks = []
    next_page_offset = None  # Initialize offset for scrolling
    limit_per_scroll = 100 # How many points to fetch per scroll request

    try:
        while True:
            scroll_response, next_page_offset = await qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="original_doc_id",
                            match=MatchValue(value=doc_id)
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
                    retrieved_chunks.append(hit.payload)
            
            if next_page_offset is None:
                break # No more pages to scroll

        if not retrieved_chunks:
            logger.warning(f"No chunks found for doc_id: '{doc_id}' in collection: '{collection_name}'.")
        else:
            logger.info(f"Successfully retrieved {len(retrieved_chunks)} chunks for doc_id: '{doc_id}' from '{collection_name}'.")
        return retrieved_chunks
        
    except Exception as e:
        logger.error(f"Error scrolling collection '{collection_name}' for doc_id '{doc_id}': {type(e).__name__} - {e}")
        return []

async def get_full_document_text_from_db(doc_id: str, collection_name: str) -> Optional[str]:
    """
    Retrieves and reconstructs the full text of a document from its chunks
    stored in the Qdrant database.

    Args:
        doc_id: The original_doc_id of the document.
        collection_name: The Qdrant collection where the document's chunks are stored.

    Returns:
        The reconstructed full text of the document as a single string,
        or None if chunks are not found or an error occurs.
    """
    if not doc_id or not collection_name:
        logger.error("Error: doc_id and collection_name must be provided to get_full_document_text_from_db.")
        return None

    chunks = await get_qdrantchunk_content(doc_id, collection_name)
    if not chunks:
        logger.error(f"No chunks found for doc_id '{doc_id}' in collection '{collection_name}'. Cannot reconstruct text.")
        return None

    # Sort chunks by their original index to reconstruct the document correctly
    sorted_chunks = []
    try:
        # Filter out chunks that might be missing 'chunk_index' or have non-integer types for safety
        valid_chunks_for_sorting = [c for c in chunks if isinstance(c.get("chunk_index"), int)]
        if len(valid_chunks_for_sorting) != len(chunks):
            logger.warning(f"Warning: Some chunks for doc_id '{doc_id}' are missing 'chunk_index' or have an invalid type. They will be excluded from sorting/reconstruction.")
        
        sorted_chunks = sorted(valid_chunks_for_sorting, key=lambda c: c["chunk_index"])
        
    except TypeError as e:
        logger.warning(f"Error sorting chunks for doc_id '{doc_id}': {e}. Attempting to use unsorted chunks.")
        sorted_chunks = chunks

    # Reconstruct using "og_text" for original document content
    full_text_parts = [chunk.get("og_text", "") for chunk in sorted_chunks if isinstance(chunk.get("og_text"), str) and chunk.get("og_text","").strip()]
    
    if not full_text_parts:
        logger.warning(f"No valid original text (og_text) found in chunks for doc_id '{doc_id}' after sorting and filtering.")
        return None
        
    return "\n\n".join(full_text_parts) 