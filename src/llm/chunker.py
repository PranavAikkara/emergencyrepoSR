"""
LLM document chunking functionality
"""
import json
from typing import List, Dict, Union, Optional
import litellm
import unicodedata
from src.utils.logging import get_logger
from src.llm.llmclient import get_litellm_params
from src.llm.utils import load_prompt

logger = get_logger(__name__)

async def chunk_document_with_llm(prompt_file: str, 
                                base64_content: Optional[str] = None, 
                                raw_text_content: Optional[str] = None, 
                                content_type: str = "application/pdf") -> Optional[List[Dict[str, Union[str, int, None]]]]:
    """
    Chunk a document into semantically meaningful parts using an LLM.
    
    Args:
        prompt_file: Path to the prompt template file
        base64_content: Base64-encoded content of the document (for PDFs, images)
        raw_text_content: Plain text content of the document
        content_type: MIME type of the document
        
    Returns:
        List of chunk dictionaries or None if chunking fails
    """
    logger.info(f"Starting LLM chunking for document with prompt: {prompt_file}")

    if not base64_content and not raw_text_content:
        logger.error("Error: Either base64_content or raw_text_content must be provided to chunk_document_with_llm.")
        return None
    if base64_content and raw_text_content:
        logger.warning("Warning: Both base64_content and raw_text_content provided to chunk_document_with_llm. Prioritizing raw_text_content.")
        base64_content = None # Prioritize raw text

    chunking_prompt_text = load_prompt(prompt_file)
    
    user_content_list = [{"type": "text", "text": chunking_prompt_text}]

    if raw_text_content:
        logger.info("Processing document for chunking with raw_text_content.")
        user_content_list.append({"type": "text", "text": raw_text_content})
    elif base64_content:
        logger.info(f"Processing document for chunking with base64_content, content_type: {content_type}.")
        user_content_list.append({
            "type": "image_url",
            "image_url": {"url": f"data:{content_type};base64,{base64_content}"}
        })

    messages = [{"role": "user", "content": user_content_list}]

    params = get_litellm_params()
    # Ensure the model being used is multimodal if base64_content is used,
    # or a good text model if raw_text_content is used.
    # Current get_litellm_params() should provide a model capable of handling both.

    try:
        logger.info(f"Calling LLM for chunking. Model: {params.get('model')}")
        response = await litellm.acompletion(
            **params,
            messages=messages,
            response_format={"type": "json_object"}
        )
        response_content = response.choices[0].message.content
        logger.info(f"Multimodal chunking raw LLM response for prompt {prompt_file}: {response_content}")

        if response_content.startswith("```json"):
            response_content = response_content.split("```json")[1].split("```")[0].strip()
        elif response_content.startswith("```") and response_content.endswith("```"):
            response_content = response_content.strip("`\n ")
        
        # Sanitize the response_content to remove problematic control characters
        # This removes characters from all Unicode 'Control' categories (Cc, Cf, Cs, Co, Cn)
        response_content = "".join(ch for ch in response_content if unicodedata.category(ch)[0] != "C")
        
        logger.info(f"Multimodal chunking raw LLM response (sanitized): {response_content[:500]}...")

        parsed_json = json.loads(response_content)
        logger.info(f"Multimodal chunking parsed JSON for prompt {prompt_file}: {parsed_json}")

        if not parsed_json:
            logger.warning("Warning: Multimodal LLM returned empty JSON for chunking.")
            return None

        # As per new llm_chunking_prompt.md, keys are like 'chunk-1', 'chunk-2'
        # and each maps to an object {"og_content": "...", "enriched_content": "..."}
        sorted_chunk_keys = sorted(parsed_json.keys(), key=lambda x: int(x.split('-')[-1]))
        
        processed_chunks = []
        for key in sorted_chunk_keys:
            chunk_object = parsed_json.get(key)
            chunk_data_to_add = {}

            if (isinstance(chunk_object, dict) and
                isinstance(chunk_object.get("og_content"), str) and
                isinstance(chunk_object.get("enriched_content"), str)):
                
                chunk_data_to_add["og_content"] = chunk_object["og_content"]
                chunk_data_to_add["enriched_content"] = chunk_object["enriched_content"]
                
                # Process weight only if present and valid (intended for JDs)
                if "weight" in chunk_object:
                    weight_val = chunk_object.get("weight")
                    if isinstance(weight_val, int) and 1 <= weight_val <= 3:
                        chunk_data_to_add["weight"] = weight_val
                    else:
                        logger.warning(f"Chunk '{key}' has invalid or out-of-range weight: {weight_val}. Weight will be ignored.")
                        # Do not add a default weight here if it's invalid from LLM for a JD
                        # Let the vector_ops layer handle default if needed for storage for JDs.
                
                processed_chunks.append(chunk_data_to_add)
            else:
                logger.warning(f"Skipping chunk '{key}' due to missing 'og_content' or 'enriched_content'. Found: {chunk_object}")
        
        if not processed_chunks:
            logger.warning(f"Warning: Multimodal LLM JSON ok, but no valid chunk objects found. Response: {response_content[:200]}...")
            return None
        
        logger.info(f"Multimodal chunking successful. Number of chunk objects: {len(processed_chunks)}")
        return processed_chunks

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding LLM JSON response for multimodal chunking: {e}")
        logger.error(f"Raw response: {response_content[:500]}...")
        return None
    except Exception as e:
        logger.error(f"Error during multimodal LLM chunking: {type(e).__name__} - {e}")
        raw_content_info = locals().get('response_content', "No content available during multimodal chunking error")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            raw_content_info = e.response.text
        logger.error(f"Raw response snapshot: {str(raw_content_info)[:500]}...")
        return None 