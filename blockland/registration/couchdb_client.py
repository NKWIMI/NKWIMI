# registration/couchdb_client.py
from couchdb import Server, http
from django.conf import settings
from datetime import datetime, date
from decimal import Decimal

def _coerce(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value

def _deep_coerce(obj):
    if isinstance(obj, dict):
        return {k: _deep_coerce(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_coerce(v) for v in obj]
    return _coerce(obj)

def get_server():
    server = Server(settings.COUCHDB["URL"])
    # set basic auth without embedding creds in URL
    server.resource.credentials = (
        settings.COUCHDB["USERNAME"],
        settings.COUCHDB["PASSWORD"],
    )
    return server

def get_or_create_db(key: str):
    """key is a logical name: 'parcels', 'properties', etc. -> returns a couchdb.Database"""
    server = get_server()
    name = settings.COUCHDB["DBS"][key]
    if name not in server:
        server.create(name)
    return server[name]

def upsert(db, doc_id: str, data: dict):
    """Create or update a document safely (handles _rev)."""
    data = _deep_coerce(data)
    data["_id"] = doc_id
    existing = db.get(doc_id)
    if existing and "_rev" in existing:
        data["_rev"] = existing["_rev"]
    return db.save(data)

def delete_doc(db, doc_id: str):
    existing = db.get(doc_id)
    if existing:
        db.delete(existing)
