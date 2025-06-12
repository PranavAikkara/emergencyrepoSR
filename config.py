import os
from dotenv import load_dotenv
from qdrant_client import AsyncQdrantClient
from sentence_transformers import SentenceTransformer

load_dotenv()

qdrant_api_key = os.getenv("QDRANT_API_KEY")

# S3 Configuration
S3_CONFIG = {
    "default_bucket": "your-smart-recruit-bucket",  # Placeholder - update with actual bucket name
    "region": "ap-south-1",  # Default region - update as needed
    "max_file_size_mb": 50,  # Maximum file size to process from S3
    "aws_profile": "AWSAdministratorAccess-024848453356",  # AWS profile to use for SSO
}

qdrant_client = AsyncQdrantClient(
    url="https://8889bc57-c76e-4707-aca1-dda9416115d6.eu-west-2-0.aws.cloud.qdrant.io",
    api_key=qdrant_api_key,
    timeout=20
)

embedding_model = SentenceTransformer("BAAI/bge-large-en-v1.5")

def get_s3_config() -> dict:
    """Get S3 configuration settings"""
    return S3_CONFIG.copy()