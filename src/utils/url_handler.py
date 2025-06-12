import aiohttp
import base64
import magic
from urllib.parse import urlparse, unquote
from typing import Dict, List, Optional, Any
from src.utils.logging import get_logger

logger = get_logger(__name__)

class URLHandler:
    """Handler for HTTP/HTTPS operations with direct memory processing"""
    
    def __init__(self, max_file_size_mb: int = 50, timeout_seconds: int = 300):
        self.max_file_size_mb = max_file_size_mb
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        logger.info("URL handler initialized successfully")
    
    def parse_url(self, url: str) -> Dict[str, str]:
        """Parse URL and extract components"""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ['http', 'https']:
                raise ValueError(f"Invalid URL scheme. Expected 'http' or 'https', got '{parsed.scheme}'")
            
            # Extract filename from path
            path = unquote(parsed.path)
            filename = path.split('/')[-1] if path else 'unknown_file'
            
            return {
                "scheme": parsed.scheme,
                "netloc": parsed.netloc,
                "path": path,
                "filename": filename,
                "full_url": url
            }
        except Exception as e:
            logger.error(f"Failed to parse URL '{url}': {e}")
            raise ValueError(f"Invalid URL format: {e}")
    
    async def get_file_from_url(self, url: str) -> Dict[str, Any]:
        """
        Download file from HTTP/HTTPS URL directly into memory and process it
        Returns dict with file content, metadata, and processing info
        """
        try:
            url_info = self.parse_url(url)
            filename = url_info["filename"]
            
            logger.info(f"Fetching file from URL: {url}")
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ValueError(f"HTTP {response.status}: Failed to download file from {url}")
                    
                    # Check Content-Length header if available
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        file_size_mb = int(content_length) / (1024 * 1024)
                        if file_size_mb > self.max_file_size_mb:
                            raise ValueError(f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({self.max_file_size_mb} MB)")
                    
                    # Read file content
                    file_bytes = await response.read()
                    
                    # Double-check actual file size
                    actual_size_mb = len(file_bytes) / (1024 * 1024)
                    if actual_size_mb > self.max_file_size_mb:
                        raise ValueError(f"File size ({actual_size_mb:.2f} MB) exceeds maximum allowed size ({self.max_file_size_mb} MB)")
            
            # Detect MIME type
            mime_type = magic.from_buffer(file_bytes, mime=True)
            logger.info(f"Detected MIME type for {filename}: {mime_type}")
            
            # Process file content using same logic as S3Handler
            processed_content = await self._process_url_file_content(file_bytes, filename, mime_type)
            
            return {
                "filename": filename,
                "url": url,
                "file_size_mb": actual_size_mb,
                "mime_type": mime_type,
                **processed_content
            }
            
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching file from URL '{url}': {e}")
            raise ValueError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error fetching file from URL '{url}': {e}")
            raise
    
    async def list_files_in_url_folder(self, folder_list_url: str) -> List[str]:
        """
        Get list of file URLs from a folder listing API endpoint
        Expected response format: {"files": ["file1.pdf", "file2.pdf", ...]}
        """
        try:
            logger.info(f"Listing files from folder API: {folder_list_url}")
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(folder_list_url) as response:
                    if response.status != 200:
                        raise ValueError(f"HTTP {response.status}: Failed to list folder contents from {folder_list_url}")
                    
                    data = await response.json()
                    
                    # Handle different possible response formats
                    if isinstance(data, dict) and "files" in data:
                        file_urls = data["files"]
                    elif isinstance(data, list):
                        file_urls = data
                    else:
                        raise ValueError(f"Unexpected response format from folder listing API: {data}")
                    
                    if not isinstance(file_urls, list):
                        raise ValueError(f"Expected list of file URLs, got: {type(file_urls)}")
                    
                    logger.info(f"Found {len(file_urls)} files in folder")
                    return file_urls
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error listing folder '{folder_list_url}': {e}")
            raise ValueError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error listing folder '{folder_list_url}': {e}")
            raise
    
    async def _process_url_file_content(self, file_bytes: bytes, filename: str, mime_type: str) -> Dict[str, Optional[str]]:
        """
        Process URL file content similar to S3Handler._process_s3_file_content
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
            logger.error(f"Error processing URL file content for {filename}: {e}")
            return {
                "error": f"Error processing file content: {str(e)}",
                "raw_text_content": None,
                "base64_content": None,
                "content_type": mime_type
            }

# Global URL handler instance
url_handler = URLHandler() 