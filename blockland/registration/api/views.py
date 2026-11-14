# registration/api/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from registration.models import User, PropertyParcel

import json

@csrf_exempt
def user_list(request):
    """Basic API view for user listing"""
    if request.method == 'GET':
        users = User.objects.all().values('id', 'username', 'email')
        return JsonResponse({'users': list(users)})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt 
def user_detail(request, user_id):
    """Single user detail view"""
    try:
        user = User.objects.get(pk=user_id)
        if request.method == 'GET':
            return JsonResponse({
                'id': user.id,
                'username': user.username,
                'email': user.email
            })
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

@csrf_exempt
def parcel_list(request):
    """Parcel listing endpoint"""
    if request.method == 'GET':
        parcels = PropertyParcel.objects.all().values()
        return JsonResponse({'parcels': list(parcels)})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def parcel_detail(request, parcel_id):
    """Single parcel detail"""
    try:
        parcel = PropertyParcel.objects.get(pk=parcel_id)
        if request.method == 'GET':
            return JsonResponse({
                'id': parcel.id,
                'address': parcel.address,
                'owner_id': parcel.owner_id
            })
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    except PropertyParcel.DoesNotExist:
        return JsonResponse({'error': 'Parcel not found'}, status=404)