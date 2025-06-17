import os
from dotenv import load_dotenv
from qdrant_client import AsyncQdrantClient

load_dotenv()

qdrant_api_key = os.getenv("QDRANT_API_KEY")

# Debug: Check if API key is loaded (don't log the actual key for security)
print(f"Qdrant API Key loaded: {'Yes' if qdrant_api_key else 'No'}")

# S3 Configuration - Uses environment variables for deployment flexibility
S3_CONFIG = {
    "default_bucket": os.getenv("S3_BUCKET", "your-smart-recruit-bucket"),  # Set via environment variable
    "region": os.getenv("AWS_REGION", "ap-south-1"),  # Default region - can be overridden
}

# DeepInfra BGE Embedding API Configuration
EMBEDDING_CONFIG = {
    "api_key": os.getenv("EMBEDDING_MODEL_API"),
    "api_url": "https://api.deepinfra.com/v1/inference/BAAI/bge-large-en-v1.5",
    "timeout": 30,
    "dimensions": 1024  # BGE Large model dimensions
}

# Debug: Check if embedding API key is loaded
embedding_api_key = EMBEDDING_CONFIG["api_key"]
print(f"Embedding API Key loaded: {'Yes' if embedding_api_key else 'No'}")

qdrant_client = AsyncQdrantClient(
    url="https://8889bc57-c76e-4707-aca1-dda9416115d6.eu-west-2-0.aws.cloud.qdrant.io",
    api_key=qdrant_api_key,
    timeout=20
)

def get_s3_config() -> dict:
    """Get S3 configuration settings"""
    return S3_CONFIG.copy()

def get_embedding_config() -> dict:
    """Get embedding API configuration settings"""
    return EMBEDDING_CONFIG.copy()