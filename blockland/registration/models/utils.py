# registration/models/utils.py
import couchdb
from django.conf import settings
from django.core.exceptions import ValidationError  # Add this
from django.core.validators import FileExtensionValidator
from cryptography.fernet import Fernet
from web3 import Web3
import re
import logging

logger = logging.getLogger(__name__)

# registration/models/utils.py
def get_couchdb_connection():
    try:
        from couchdb import Server
        import os
        from django.conf import settings
        
        # Check if CouchDB settings are configured
        if not hasattr(settings, 'COUCHDB_USER') or not hasattr(settings, 'COUCHDB_PASSWORD'):
            return None
            
        server = Server(f"http://{settings.COUCHDB_USER}:{settings.COUCHDB_PASSWORD}@localhost:5984/")
        db = server['land_registration']
        return db
    except Exception as e:
        print(f"CouchDB connection error: {e}")  # This is what you're seeing
        return None
def validate_ethereum_address(value: str):
    """Validate that the value is a properly formatted Ethereum address"""
    if not isinstance(value, str):
        raise ValidationError("Ethereum address must be a string.")
    if not re.fullmatch(r"^0x[a-fA-F0-9]{40}$", value or ""):
        raise ValidationError(f"{value} is not a valid Ethereum address")
    return value

def get_encryption_key():
    """Get encryption key from settings or generate a new one"""
    key = getattr(settings, 'ENCRYPTION_KEY', None)
    if not key:
        key = Fernet.generate_key().decode()
        setattr(settings, 'ENCRYPTION_KEY', key)
    return key

def validate_file_size(value):
    """Custom file size validator (5MB limit)"""
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError('File too large. Size should not exceed 5MB.')

def generate_file_hash(file_field):
    """Generate cryptographic hash of file content"""
    file_field.seek(0)
    return Web3.keccak(file_field.read()).hex()