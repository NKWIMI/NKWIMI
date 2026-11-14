# In ipfs_helper.py
import requests
import os

IPFS_API = "http://localhost:5001/api/v0/add"
IPFS_GATEWAY = "http://localhost:8080/ipfs/"

def upload_to_ipfs(file_or_path):
    """
    Uploads a file to the local IPFS node and returns the public gateway URL.
    
    Args:
        file_or_path: A file path (str) or a file-like object (e.g., InMemoryUploadedFile).
    
    Returns:
        str: IPFS gateway URL to access the uploaded file.
    
    Raises:
        FileNotFoundError: If the file does not exist (for file path).
        Exception: If the IPFS upload fails.
    """
    try:
        # Handle file-like object (e.g., InMemoryUploadedFile)
        if hasattr(file_or_path, 'read'):
            files = {'file': file_or_path}
            response = requests.post(IPFS_API, files=files)
        # Handle file path
        elif os.path.isfile(file_or_path):
            with open(file_or_path, "rb") as file:
                files = {'file': file}
                response = requests.post(IPFS_API, files=files)
        else:
            raise FileNotFoundError(f"Invalid file or path: {file_or_path}")

        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        ipfs_hash = response.json().get("Hash")

        if not ipfs_hash:
            raise Exception("No IPFS hash returned in response.")

        return f"{IPFS_GATEWAY}{ipfs_hash}"

    except requests.exceptions.RequestException as e:
        raise Exception(f"Request to IPFS API failed: {e}")