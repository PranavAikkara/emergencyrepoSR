"""
Utility functions for LLM operations
"""
import os
from src.utils.logging import get_logger

logger = get_logger(__name__)

def load_prompt(file_path: str) -> str:
    """
    Load a prompt template from a file.
    
    Args:
        file_path: Path to the prompt template file
        
    Returns:
        String containing the prompt template
        
    Raises:
        FileNotFoundError: If the file does not exist
        IOError: If there is an error reading the file
    """
    logger.info(f"Attempting to load prompt from: {file_path}")
    
    # Try the path as provided
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding="utf-8") as f:
                prompt_content = f.read()
                logger.debug(f"Loaded prompt from {file_path}")
                return prompt_content
        except IOError as e:
            logger.error(f"Error reading prompt file {file_path}: {str(e)}")
            raise
    
    # If the path doesn't include 'src/' prefix, try adding it
    if not file_path.startswith("src/"):
        alt_path = os.path.join("src", file_path)
        logger.info(f"Original path not found, trying with src/ prefix: {alt_path}")
        if os.path.exists(alt_path):
            try:
                with open(alt_path, 'r', encoding="utf-8") as f:
                    prompt_content = f.read()
                    logger.debug(f"Loaded prompt from alternative path {alt_path}")
                    return prompt_content
            except IOError as e:
                logger.error(f"Error reading prompt file {alt_path}: {str(e)}")
                raise
    
    # If all attempts fail, raise FileNotFoundError
    logger.error(f"Prompt file not found: {file_path}")
    raise FileNotFoundError(f"Prompt file not found: {file_path}") 