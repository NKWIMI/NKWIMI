from django.contrib import admin
from .models.user_models import User

# Import the actual models from parcel_models
try:
    from .models.parcel_models import Parcel, ParcelMetadata
    HAS_PARCEL_MODELS = True
except ImportError:
    HAS_PARCEL_MODELS = False
    Parcel = None
    ParcelMetadata = None

# Unregister if already registered
try:
    admin.site.unregister(User)
except:
    pass

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'blockchain_address', 'is_verified', 'is_identity_verified']
    list_filter = ['is_verified', 'is_identity_verified']
    search_fields = ['username', 'email', 'blockchain_address']
    readonly_fields = ['blockchain_address', 'encrypted_private_key']

# Only register parcel models if they exist
if HAS_PARCEL_MODELS and Parcel:
    @admin.register(Parcel)
    class ParcelAdmin(admin.ModelAdmin):
        list_display = ['land_id', 'owner', 'owner_address', 'size_sqm', 'is_frozen']
        list_filter = ['is_frozen', 'created_at']
        search_fields = ['land_id', 'owner__username', 'owner_address']

if HAS_PARCEL_MODELS and ParcelMetadata:
    @admin.register(ParcelMetadata)
    class ParcelMetadataAdmin(admin.ModelAdmin):
        list_display = ['parcel', 'uploader', 'created_at', 'is_status_change']
        list_filter = ['is_status_change', 'created_at']
        search_fields = ['parcel__land_id', 'ipfs_hash']
