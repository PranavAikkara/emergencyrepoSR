"""
LLM document parsing functionality
"""
import json
from typing import Dict, Union, Type, Optional
import litellm
from src.schemas.schemas import JDOutput, CVOutput
from src.utils.logging import get_logger
from src.llm.llmclient import get_litellm_params
from src.llm.utils import load_prompt
import traceback

logger = get_logger(__name__)

async def parse_document(prompt_file: str, 
                        output_schema_class: Type[Union[JDOutput, CVOutput]], 
                        base64_content: Optional[str] = None, 
                        raw_text_content: Optional[str] = None, 
                        content_type: str = "application/pdf") -> Dict:
    """
    Parse a document using an LLM with a specific prompt and output schema.
    
    Args:
        prompt_file: Path to the prompt template file
        output_schema_class: Pydantic model class for validating and structuring the output
        base64_content: Base64-encoded content of the document (for PDFs, images)
        raw_text_content: Plain text content of the document
        content_type: MIME type of the document
        
    Returns:
        Dict containing the parsed document data or error information
    """
    logger.info(f"Starting LLM parsing for document with prompt: {prompt_file}")
    
    if not base64_content and not raw_text_content:
        logger.error("Error: Either base64_content or raw_text_content must be provided to parse_document.")
        return {"error": "No content provided to LLM."}
    if base64_content and raw_text_content:
        logger.warning("Warning: Both base64_content and raw_text_content provided to parse_document. Prioritizing raw_text_content.")
        base64_content = None # Prioritize raw text if both are somehow passed

    text_prompt = load_prompt(prompt_file)
    
    user_content_list = [{"type": "text", "text": text_prompt}]

    if raw_text_content:
        logger.info("Processing document with raw_text_content.")
        user_content_list.append({"type": "text", "text": raw_text_content})
    elif base64_content:
        logger.info(f"Processing document with base64_content, content_type: {content_type}.")
        user_content_list.append({
            "type": "image_url", 
            "image_url": {"url": f"data:{content_type};base64,{base64_content}"}
        })
        
    messages = [{"role": "user", "content": user_content_list}]
    
    params = get_litellm_params()
    
    try:
        # Log the parameters being used (except for the content which could be large)
        param_log = {k: v for k, v in params.items() if k != 'api_key'}
        logger.info(f"Calling LLM with params: {param_log}")
        
        response = await litellm.acompletion(
            **params,
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        # Check if response is None or empty
        if not response or not response.choices:
            logger.error("Empty response received from LLM")
            return {"error": "Empty response from LLM", "raw_response": "No content"}
            
        content = response.choices[0].message.content
        
        # Check if content is None or empty
        if not content:
            logger.error("Empty content received from LLM")
            return {"error": "Empty content from LLM", "raw_response": "No content"}
        
        # Log first part of the response for debugging
        truncated_content = content[:min(1000, len(content))]
        logger.info(f"Raw LLM response received: {truncated_content}...")
        
        # Handle various JSON formatting issues
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
            logger.info("Extracted JSON from markdown code block")
        elif content.startswith("```") and "```" in content[3:]:
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:].strip()
            logger.info("Extracted content from generic code block")
        
        # Check if the content is empty after cleaning
        if not content.strip():
            logger.error("LLM returned empty JSON content after cleanup")
            return {"error": "LLM returned empty content", "raw_response": response.choices[0].message.content}
            
        try:
            parsed_output = json.loads(content)
            logger.info("Successfully parsed JSON response")
            
            # Check if the parsed output is empty or missing key fields
            if not parsed_output:
                logger.error("Parsed JSON is empty")
                return {"error": "Parsed JSON is empty", "raw_response": content}
            
            # Validate against schema
            try:
                validated_data = output_schema_class(**parsed_output).dict()
                
                # Check if the validated data is meaningful (e.g., has candidate name or skills)
                if output_schema_class == CVOutput:
                    if not validated_data.get('candidate_name') and not validated_data.get('skills'):
                        logger.warning("Parsed CV data appears to be missing essential fields")
                
                logger.info("LLM parsing completed successfully with valid schema")
                return validated_data
            except Exception as schema_error:
                logger.error(f"Schema validation failed: {str(schema_error)}")
                logger.error(f"Schema validation traceback: {traceback.format_exc()}")
                return {"error": f"Schema validation failed: {str(schema_error)}", "raw_response": content}
                
        except json.JSONDecodeError as json_error:
            # Try a more lenient approach - find anything that looks like JSON
            logger.warning(f"Initial JSON parsing failed: {str(json_error)}. Attempting more lenient parsing.")
            try:
                # Look for content between curly braces
                if '{' in content and '}' in content:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    json_content = content[json_start:json_end]
                    parsed_output = json.loads(json_content)
                    logger.info("Successfully parsed JSON with lenient method")
                    validated_data = output_schema_class(**parsed_output).dict()
                    logger.info("LLM parsing completed successfully with lenient parsing")
                    return validated_data
            except Exception as lenient_error:
                logger.error(f"Lenient JSON parsing also failed: {str(lenient_error)}")
                
            # If we reach here, both parsing attempts failed
            logger.error(f"Failed to parse LLM response as JSON. Original error: {str(json_error)}")
            return {"error": f"Failed to parse LLM response as JSON: {str(json_error)}", 
                    "raw_response": content}

    except Exception as e:
        logger.error(f"LLM API call failed: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raw_content_info = locals().get('content', "No content available")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            raw_content_info = e.response.text
        return {"error": f"LLM API call failed: {str(e)}", "raw_response": raw_content_info} 