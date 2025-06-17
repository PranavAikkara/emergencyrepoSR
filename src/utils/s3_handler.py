import boto3
import base64
import magic
from urllib.parse import urlparse
from typing import Dict, Any, Optional
from src.utils.logging import get_logger
from config import get_s3_config

logger = get_logger(__name__)

class S3Handler:
    """Handler for S3 operations with direct memory processing"""
    
    def __init__(self):
        self.s3_config = get_s3_config()
        try:
            # Use standard AWS credential chain - this automatically handles:
            # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
            # 2. IAM roles (for EC2, Lambda, ECS deployments)
            # 3. AWS SSO profiles (if AWS_PROFILE env var is set)
            # 4. ~/.aws/credentials file
            # 5. EC2 instance metadata
            region = self.s3_config.get("region", "ap-south-1")
            
            self.s3_client = boto3.client('s3', region_name=region)
            logger.info(f"S3 handler initialized in region '{region}' using AWS credential chain")
                
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise ValueError(f"S3 client initialization failed. Please check AWS credentials: {e}")
    
    def parse_s3_uri(self, s3_uri: str) -> Dict[str, str]:
        """Parse S3 URI and extract bucket and key components"""
        try:
            if not s3_uri.startswith('s3://'):
                raise ValueError(f"Invalid S3 URI. Expected format: s3://bucket-name/key. Got: {s3_uri}")
            
            # Remove s3:// prefix and split
            path_part = s3_uri[5:]  # Remove 's3://'
            if '/' not in path_part:
                raise ValueError(f"Invalid S3 URI format. Missing key after bucket name: {s3_uri}")
            
            bucket_name, key = path_part.split('/', 1)
            
            if not bucket_name or not key:
                raise ValueError(f"Invalid S3 URI format. Bucket or key is empty: {s3_uri}")
            
            # Extract filename from key
            filename = key.split('/')[-1] if '/' in key else key
            
            return {
                "bucket": bucket_name,
                "key": key,
                "filename": filename,
                "s3_uri": s3_uri
            }
        except Exception as e:
            logger.error(f"Failed to parse S3 URI '{s3_uri}': {e}")
            raise ValueError(f"Invalid S3 URI format: {e}")
    
    async def get_file_from_s3(self, s3_uri: str) -> Dict[str, Any]:
        """
        Download file from S3 directly into memory and process it
        Returns dict with file content, metadata, and processing info
        """
        try:
            s3_info = self.parse_s3_uri(s3_uri)
            bucket = s3_info["bucket"]
            key = s3_info["key"]
            filename = s3_info["filename"]
            
            logger.info(f"Fetching file from S3: {s3_uri}")
            
            # Check if object exists and get metadata
            try:
                response = self.s3_client.head_object(Bucket=bucket, Key=key)
                file_size_bytes = response['ContentLength']
                file_size_mb = file_size_bytes / (1024 * 1024)
                    
            except self.s3_client.exceptions.NoSuchKey:
                raise ValueError(f"File not found in S3: {s3_uri}")
            except self.s3_client.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'Forbidden' or error_code == '403':
                    raise ValueError(f"Access denied to S3 object: {s3_uri}. Please check AWS credentials and bucket permissions.")
                elif error_code == 'InvalidAccessKeyId':
                    raise ValueError(f"Invalid AWS access key. Please check AWS credentials configuration.")
                elif error_code == 'SignatureDoesNotMatch':
                    raise ValueError(f"AWS signature mismatch. Please check AWS secret access key.")
                else:
                    raise ValueError(f"AWS error accessing S3 object: {e}")
            except Exception as e:
                raise ValueError(f"Error checking S3 object: {e}")
            
            # Download file content to memory
            try:
                response = self.s3_client.get_object(Bucket=bucket, Key=key)
                file_bytes = response['Body'].read()
                
            except Exception as e:
                raise ValueError(f"Error downloading file from S3: {e}")
            
            # Detect MIME type
            mime_type = magic.from_buffer(file_bytes, mime=True)
            logger.info(f"Detected MIME type for {filename}: {mime_type}")
            
            # Process file content using same logic as other handlers
            processed_content = await self._process_s3_file_content(file_bytes, filename, mime_type)
            
            return {
                "filename": filename,
                "s3_uri": s3_uri,
                "bucket": bucket,
                "key": key,
                "file_size_mb": file_size_mb,
                "mime_type": mime_type,
                **processed_content
            }
            
        except Exception as e:
            logger.error(f"Error fetching file from S3 '{s3_uri}': {e}")
            raise
    
    async def _process_s3_file_content(self, file_bytes: bytes, filename: str, mime_type: str) -> Dict[str, Optional[str]]:
        """
        Process S3 file content similar to existing handlers
        Returns dict with raw_text_content, base64_content, content_type, and error
        """
        raw_text_content: Optional[str] = None
        base64_content_str: Optional[str] = None
        
        try:
            if mime_type == "application/pdf":
                base64_content_str = base64.b64encode(file_bytes).decode('utf-8')
                
            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or \
                 (mime_type == "application/zip" and filename.lower().endswith('.docx')):
                
                if mime_type == "application/zip":
                    logger.info(f"MIME type detected as 'application/zip' for {filename}, but attempting DOCX parse due to .docx extension.")
                
                try:
                    import docx
                    import io
                    doc = docx.Document(io.BytesIO(file_bytes))
                    extracted_text = "\\n".join([para.text for para in doc.paragraphs])
                    
                    if not extracted_text.strip():
                        logger.warning(f"No text content found in DOCX paragraphs for {filename}.")
                        return {
                            "error": f"No text content found in DOCX paragraphs for {filename}. The document might be image-only or text is in elements not directly parseable as paragraphs.",
                            "raw_text_content": None,
                            "base64_content": None,
                            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        }
                    
                    raw_text_content = extracted_text
                    logger.info(f"Successfully extracted text from DOCX: {filename}")
                    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    
                except Exception as e:
                    logger.error(f"Error processing DOCX file {filename}: {e}")
                    logger.warning(f"Falling back to base64 for {filename} after DOCX parsing attempt failed.")
                    base64_content_str = base64.b64encode(file_bytes).decode('utf-8')
                    mime_type = "application/octet-stream"
                    raw_text_content = None
                    
            elif mime_type in ["text/plain", "text/markdown"]:
                try:
                    raw_text_content = file_bytes.decode('utf-8')
                    logger.info(f"Successfully read text from {mime_type} file: {filename}")
                except UnicodeDecodeError:
                    try:
                        raw_text_content = file_bytes.decode('latin-1')
                        logger.info(f"Successfully read text (latin-1) from {mime_type} file: {filename}")
                    except UnicodeDecodeError as ude_fallback:
                        logger.error(f"Fallback decoding error for {filename}: {ude_fallback}")
                        return {
                            "error": f"Could not decode text file {filename}. Ensure it is UTF-8 or Latin-1 encoded.",
                            "raw_text_content": None,
                            "base64_content": None,
                            "content_type": mime_type
                        }
            else:
                logger.warning(f"Unsupported or ambiguous file type: {mime_type} for file {filename}. Attempting base64 encoding as a fallback.")
                base64_content_str = base64.b64encode(file_bytes).decode('utf-8')
                mime_type = "application/octet-stream"
            
            return {
                "raw_text_content": raw_text_content,
                "base64_content": base64_content_str,
                "content_type": mime_type,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error processing S3 file content for {filename}: {e}")
            return {
                "error": f"Error processing file content: {str(e)}",
                "raw_text_content": None,
                "base64_content": None,
                "content_type": mime_type
            }

# Global S3 handler instance
s3_handler = S3Handler() 