# registration/views/api_views.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from ..models.parcel_models import Parcel

@require_GET
def parcels_by_owner_api(request, owner_id):
    """API endpoint to get parcels by owner ID"""
    try:
        parcels = Parcel.objects.filter(owner_id=owner_id).values('id', 'land_id', 'size_sqm')
        return JsonResponse({
            'success': True,
            'parcels': list(parcels)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)