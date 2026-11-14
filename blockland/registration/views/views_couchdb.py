from django.http import JsonResponse
from registration.couchdb_client import get_or_create_db

def couchdb_health(request):
    try:
        db = get_or_create_db("parcels")
        info = {"db_name": db.name, "doc_count": db.info().get("doc_count", 0)}
        return JsonResponse({"ok": True, "parcels": info})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

def parcels_by_owner(request, owner_id: int):
    db = get_or_create_db("parcels")
    view = db.view("parcels/by_owner_id", key=int(owner_id), reduce=False, include_docs=True)
    docs = [row.doc for row in view]
    return JsonResponse({"count": len(docs), "results": docs})
