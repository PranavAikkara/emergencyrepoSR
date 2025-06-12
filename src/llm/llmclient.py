"""
LLM client configuration and management
"""
import os
from typing import Dict, Optional, Any
from dotenv import load_dotenv
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Model configurations
MODEL_CONFIGS = {
    "gemini_flash_multimodal": {
        "model_name": "gemini/gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
        "temperature": 0.0,  # Set to 0 for consistent CV ranking
    },
    "gemini_2_5_flash_preview": {
        "model_name": "gemini/gemini-2.5-flash-preview-05-20",
        "api_key_env": "GEMINI_API_KEY",
        "temperature": 0.0,  # Set to 0 for consistent CV ranking
    },   
    "openai_gpt_4o": {
        "model_name": "openai/gpt-4o",
        "api_key_env": "OPENAI_API_KEY", 
        "temperature": 0.0,  # Changed from 0.7 to 0 for consistent CV ranking
    },
    # Add other model configurations here
}

def get_litellm_params(model_alias: str = "gemini_flash_multimodal") -> Dict[str, Any]:
    """
    Get LiteLLM parameters for the specified model.
    
    Args:
        model_alias: Alias of the model configuration to use
        
    Returns:
        Dictionary of parameters for LiteLLM
        
    Raises:
        ValueError: If the model alias is not found in the configuration
    """
    config = MODEL_CONFIGS.get(model_alias)
    if not config:
        error_msg = f"Configuration for model alias '{model_alias}' not found."
        logger.error(error_msg)
        raise ValueError(error_msg)

    params = {
        "model": config["model_name"],
        "api_key": os.getenv(config["api_key_env"]),
    }
    
    # Add any other common or model-specific parameters from the config
    if "temperature" in config:
        params["temperature"] = config["temperature"]
    if "max_tokens" in config:
        params["max_tokens"] = config["max_tokens"]
    # ... and so on for other LiteLLM parameters
    
    logger.info(f"Using LLM model: {config['model_name']}")
    return params

def get_api_key_for_model(model_alias: str) -> Optional[str]:
    """
    Get the API key for a specific model.
    
    Args:
        model_alias: Alias of the model configuration
        
    Returns:
        API key or None if not found
    """
    config = MODEL_CONFIGS.get(model_alias)
    if config and config.get("api_key_env"):
        return os.getenv(config["api_key_env"])
    return None 