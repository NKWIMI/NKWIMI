# registration/couchdb_utils.py
import couchdb
from django.conf import settings

def get_couchdb_connection():
    """Get CouchDB database connection"""
    try:
        couchdb_url = getattr(settings, 'COUCHDB_URL', 'http://localhost:5984')
        db_name = getattr(settings, 'COUCHDB_DB_NAME', 'blockland')
        username = getattr(settings, 'COUCHDB_USERNAME', 'admin')
        password = getattr(settings, 'COUCHDB_PASSWORD', 'password')
        
        server = couchdb.Server(couchdb_url)
        if username and password:
            server.resource.credentials = (username, password)
        
        if db_name in server:
            return server[db_name]
        else:
            return server.create(db_name)
    except Exception as e:
        print(f"CouchDB connection error: {e}")
        return None