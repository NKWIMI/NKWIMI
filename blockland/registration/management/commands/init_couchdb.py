from django.core.management.base import BaseCommand
from registration.couchdb_client import get_or_create_db
import json

class Command(BaseCommand):
    help = "Create CouchDB databases and design documents"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Initializing CouchDB..."))

        # Ensure DBs exist
        parcels = get_or_create_db("parcels")
        properties = get_or_create_db("properties")
        transfers = get_or_create_db("transfers")
        audit = get_or_create_db("audit")
        blockchain = get_or_create_db("blockchain")
        contacts = get_or_create_db("contacts")

        # Create design docs / views
        self._ensure_design_doc(
            parcels,
            "_design/parcels",
            views={
                "by_land_id": {
                    "map": """function(doc){
                        if(doc.type === 'parcel' && doc.land_id){
                            emit(doc.land_id, doc._id);
                        }
                    }"""
                },
                "by_owner_id": {
                    "map": """function(doc){
                        if(doc.type === 'parcel' && doc.owner_id){
                            emit(doc.owner_id, 1);
                        }
                    }""",
                    "reduce": "_sum"
                }
            }
        )

        self._ensure_design_doc(
            properties,
            "_design/properties",
            views={
                "by_property_id": {
                    "map": """function(doc){
                        if(doc.type === 'property' && doc.property_id){
                            emit(doc.property_id, doc._id);
                        }
                    }"""
                }
            }
        )

        self._ensure_design_doc(
            transfers,
            "_design/transfers",
            views={
                "by_parcel": {
                    "map": """function(doc){
                        if(doc.type === 'transfer' && doc.parcel_id){
                            emit(doc.parcel_id, {status: doc.status, ts: doc.created_at});
                        }
                    }"""
                },
                "by_status": {
                    "map": """function(doc){
                        if(doc.type === 'transfer' && doc.status){
                            emit(doc.status, 1);
                        }
                    }""",
                    "reduce": "_sum"
                }
            }
        )

        self._ensure_design_doc(
            audit,
            "_design/audit",
            views={
                "by_action_ts": {
                    "map": """function(doc){
                        if(doc.type === 'audit' && doc.action && doc.timestamp){
                            emit([doc.action, doc.timestamp], 1);
                        }
                    }""",
                    "reduce": "_sum"
                }
            }
        )

        self.stdout.write(self.style.SUCCESS("CouchDB initialization complete."))

    def _ensure_design_doc(self, db, doc_id, views):
        doc = db.get(doc_id)
        design = {"_id": doc_id, "language": "javascript", "views": views}
        if doc:
            design["_rev"] = doc["_rev"]
        db.save(design)
