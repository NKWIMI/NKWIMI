# registration/services/file_hash_service.py
import logging
import hashlib
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

class FileHashService:
    """
    Service for handling file hashing and storage.
    Provides fallback when IPFS is not available.
    """
    
    def __init__(self):
        self.setup_ipfs()
    
    def setup_ipfs(self):
        """Setup IPFS connection if available, otherwise use fallback"""
        self.ipfs_available = False
        self.ipfs_client = None
        
        # Check if IPFS is enabled in settings
        if getattr(settings, 'IPFS_ENABLED', False):
            try:
                # Try to import IPFS client
                from .ipfs_service import IPFSService
                self.ipfs_client = IPFSService()
                self.ipfs_available = True
                logger.info("✅ IPFS service initialized")
            except ImportError as e:
                logger.warning(f"⚠ IPFS service not available: {e}")
            except Exception as e:
                logger.warning(f"⚠ IPFS setup failed: {e}")
        else:
            logger.info("ℹ️ IPFS disabled via settings, using local file storage")
    
    def add_file(self, file_obj, filename=None):
        """
        Add a file to storage and return a hash identifier.
        Uses IPFS if available, otherwise falls back to local storage with hash.
        """
        try:
            # Read file content
            file_content = file_obj.read()
            
            if self.ipfs_available and self.ipfs_client:
                # Use IPFS if available
                try:
                    ipfs_hash = self.ipfs_client.add_file(file_content, filename)
                    logger.info(f"✅ File uploaded to IPFS: {ipfs_hash}")
                    return ipfs_hash
                except Exception as e:
                    logger.warning(f"IPFS upload failed, falling back to local storage: {e}")
            
            # Fallback: Use local storage with hash-based filename
            return self._store_file_locally(file_content, file_obj.name, filename)
            
        except Exception as e:
            logger.error(f"❌ File storage failed: {e}")
            raise
    
    def _store_file_locally(self, file_content, original_filename, custom_filename=None):
        """Store file locally and return a hash identifier"""
        try:
            # Generate hash for the file content
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Determine filename
            if custom_filename:
                filename = custom_filename
            else:
                # Use original filename with hash prefix
                name, ext = os.path.splitext(original_filename)
                filename = f"{file_hash[:16]}_{name}{ext}"
            
            # Store file using Django's storage system
            file_path = f"contracts/{filename}"
            saved_path = default_storage.save(file_path, ContentFile(file_content))
            
            logger.info(f"✅ File stored locally: {saved_path} (Hash: {file_hash})")
            
            # Return the hash as identifier (you could also return the file path)
            return file_hash
            
        except Exception as e:
            logger.error(f"❌ Local file storage failed: {e}")
            raise
    
    def get_file_url(self, file_hash):
        """Get file URL from hash identifier"""
        try:
            if self.ipfs_available and self.ipfs_client:
                # Try IPFS first
                try:
                    return self.ipfs_client.get_file_url(file_hash)
                except Exception as e:
                    logger.warning(f"IPFS retrieval failed: {e}")
            
            # Fallback: Try to find local file by hash
            # This is a simplified implementation - you might want to store
            # the mapping between hash and file path in your database
            return self._get_local_file_url(file_hash)
            
        except Exception as e:
            logger.error(f"❌ File retrieval failed: {e}")
            return None
    
    def _get_local_file_url(self, file_hash):
        """Get URL for locally stored file (simplified implementation)"""
        # In a real implementation, you'd look up the file path from your database
        # For now, return a placeholder or the media URL pattern
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        return f"{media_url}contracts/{file_hash}"
    
    def calculate_file_hash(self, file_content):
        """Calculate SHA256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    def validate_file_hash(self, file_content, expected_hash):
        """Validate that file content matches expected hash"""
        actual_hash = self.calculate_file_hash(file_content)
        return actual_hash == expected_hash

# Simple IPFS service stub for when IPFS is not available
class IPFSService:
    """Stub IPFS service for when IPFS is not configured"""
    
    def __init__(self):
        logger.warning("⚠ Using stub IPFS service - no actual IPFS functionality")
    
    def add_file(self, file_content, filename=None):
        """Stub method that raises error"""
        raise ImportError("IPFS service not configured")
    
    def get_file_url(self, file_hash):
        """Stub method that raises error"""
        raise ImportError("IPFS service not configured")

# Alternative: Create a simple version that doesn't try to import IPFS at all
class SimpleFileHashService:
    """
    Simplified file hash service that only uses local storage.
    Use this if you don't need IPFS functionality.
    """
    
    def __init__(self):
        logger.info("✅ SimpleFileHashService initialized (local storage only)")
    
    def add_file(self, file_obj, filename=None):
        """Store file locally and return hash"""
        try:
            # Read file content
            file_content = file_obj.read()
            
            # Generate hash
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Determine filename
            original_filename = file_obj.name
            if filename:
                storage_filename = filename
            else:
                name, ext = os.path.splitext(original_filename)
                storage_filename = f"{file_hash[:16]}_{name}{ext}"
            
            # Store file
            file_path = f"contracts/{storage_filename}"
            saved_path = default_storage.save(file_path, ContentFile(file_content))
            
            logger.info(f"✅ File stored: {saved_path} (Hash: {file_hash})")
            return file_hash
            
        except Exception as e:
            logger.error(f"❌ File storage failed: {e}")
            raise
    
    def get_file_url(self, file_hash):
        """Get file URL (simplified - returns media URL pattern)"""
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        return f"{media_url}contracts/{file_hash}"

# Use the simple service by default to avoid IPFS dependencies
FileHashService = SimpleFileHashService