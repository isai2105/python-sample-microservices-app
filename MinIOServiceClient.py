import aiohttp
import asyncio
from aiohttp import FormData
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MinIOServiceClient:
    def __init__(self):
        self.base_url = 'localhost:5010'
        self.last_run_bucket_config = {
            'name': "bucket-1"
        }

    async def upload_file(self, file_path: str, bucket_name: str, file_name: str, max_retries: int = 3) -> dict:
        """
        Uploads a file to MinIO with robust error handling and retry logic
        
        Args:
            file_path: Local path to the file
            bucket_name: Target bucket name
            file_name: Destination file name
            max_retries: Maximum retry attempts for transient failures
            
        Returns:
            Upload response JSON
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            PermissionError: If file access is denied
            aiohttp.ClientError: For HTTP-related failures after retries
            Exception: For unexpected errors
        """
        last_exception = None
        file_handle = None
        
        for attempt in range(1, max_retries + 1):
            try:
                # Validate file exists before attempting upload
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Source file not found: {file_path}")
                    
                if not os.access(file_path, os.R_OK):
                    raise PermissionError(f"Read permission denied for: {file_path}")
                
                logger.info(f"Upload attempt {attempt}/{max_retries} for {file_path}")
                
                data = FormData()
                file_handle = open(file_path, 'rb')
                data.add_field(
                    'file',
                    file_handle,
                    filename=file_name,
                    content_type='application/octet-stream'
                )
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"http://{self.base_url}/buckets/{bucket_name}/objects/{file_name}",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff with max 10s
                    logger.warning(f"Transient error (retrying in {wait_time}s): {str(e)}")
                    await asyncio.sleep(wait_time)
                    
            except (FileNotFoundError, PermissionError) as e:
                logger.error(f"File error: {str(e)}")
                raise  # Immediately fail for these errors
                
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                raise
                
            finally:
                if file_handle is not None and not file_handle.closed:
                    file_handle.close()
                    file_handle = None
                    
        # If we get here, all retries failed
        logger.error(f"Failed after {max_retries} attempts")
        raise last_exception or Exception("Upload failed after retries")


    async def upload_last_run_file(self, file_path: str, new_file_name: str) -> dict:
        """
        Simplified wrapper that uses the bucket config and delegates to upload_file
        """
        logger.info(f"Starting upload of last run file: {file_path}")
        try:
            return await self.upload_file(
                file_path,
                self.last_run_bucket_config['name'],
                new_file_name
            )
        except Exception as e:
            logger.error(f"Failed to upload last run file: {str(e)}")
            raise