# registration/forms/parcel_forms.py
from django import forms
from ..models.parcel_models import Parcel
from ..models.user_models import User
from ..models.transfer_models import Transfer
from ..services.file_hash_service import FileHashService
from ..services.blockchain_service import BlockchainService
import logging

logger = logging.getLogger(__name__)

class ParcelRegistrationForm(forms.ModelForm):
    change_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    
    coordinates_input = forms.CharField(
        required=False,
        label="Coordinates",
        help_text="Enter as 'latitude,longitude' (e.g., 40.7128,-74.0060)",
        widget=forms.TextInput(attrs={'placeholder': '40.7128,-74.0060'})
    )

    # Add owner_address field for admin users
    owner_address = forms.CharField(
        required=False,
        max_length=42,
        label="Owner Blockchain Address",
        help_text="Ethereum address of the parcel owner (0x...)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0x...',
            'pattern': '^0x[a-fA-F0-9]{40}$'
        })
    )

    class Meta:
        model = Parcel
        fields = ['land_id', 'owner', 'owner_address', 'size_sqm', 'coordinates_input', 'contract_file']
        widgets = {
            'owner': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'updateOwnerAddress(this.value)'
            }),
            'contract_file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set up owner field based on user permissions
        if self.user and (self.user.is_staff or self.user.is_superuser):
            self.fields['owner'].queryset = User.objects.all()
            self.fields['owner'].empty_label = "Select parcel owner"
            
            # Show owner_address field for admin users
            self.fields['owner_address'].required = True
            self.fields['owner_address'].help_text = "Enter the Ethereum address of the parcel owner"
        else:
            # For regular users, restrict to themselves and hide owner_address
            if self.user and hasattr(self.user, 'id'):
                self.fields['owner'].queryset = User.objects.filter(id=self.user.id)
                self.fields['owner'].initial = self.user
                self.fields['owner'].widget.attrs['readonly'] = True
                self.fields['owner'].widget.attrs['disabled'] = True
            else:
                # If no user is provided, show all users (for admin use)
                self.fields['owner'].queryset = User.objects.all()
            
            # Hide owner_address field for regular users (auto-populated)
            self.fields['owner_address'].widget = forms.HiddenInput()
            self.fields['owner_address'].required = False

        # Set initial owner_address if instance exists
        if self.instance and self.instance.pk:
            self.fields['owner_address'].initial = self.instance.owner_address
        elif self.user and not (self.user.is_staff or self.user.is_superuser):
            # Pre-populate with user's blockchain address for regular users
            self.fields['owner_address'].initial = self.user.blockchain_address

        if self.instance and self.instance.contract_file:
            self.fields['contract_file'].help_text = f'Current file: {self.instance.contract_file.name}'

    def clean_coordinates_input(self):
        coords = self.cleaned_data.get('coordinates_input')
        if not coords:
            return None
            
        try:
            lat_str, lng_str = coords.split(',')
            lat = float(lat_str.strip())
            lng = float(lng_str.strip())
            
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise forms.ValidationError("Invalid coordinate values. Latitude must be between -90 and 90, longitude between -180 and 180.")
                
            self.cleaned_data['parsed_coordinates'] = {"lat": lat, "lng": lng}
            return {"lat": lat, "lng": lng}
        except ValueError:
            raise forms.ValidationError("Enter coordinates as 'latitude,longitude' (e.g., 40.7128,-74.0060).")
        except Exception as e:
            raise forms.ValidationError(f"Invalid coordinate format: {str(e)}")

    def clean_owner_address(self):
        owner_address = self.cleaned_data.get('owner_address', '').strip()
        
        # For admin users, validate the provided address
        if self.user and (self.user.is_staff or self.user.is_superuser):
            if not owner_address:
                raise forms.ValidationError("Owner address is required for admin registrations.")
            
            # Basic Ethereum address validation
            if not owner_address.startswith('0x') or len(owner_address) != 42:
                raise forms.ValidationError("Invalid Ethereum address format. Must start with 0x and be 42 characters long.")
        
        return owner_address

    def clean(self):
        cleaned_data = super().clean()
        owner = cleaned_data.get('owner')
        owner_address = cleaned_data.get('owner_address')
        
        # For admin users, ensure owner_address matches selected owner's blockchain address
        if self.user and (self.user.is_staff or self.user.is_superuser) and owner:
            if owner.blockchain_address and owner_address != owner.blockchain_address:
                self.add_error('owner_address', 
                    f"Owner address must match the selected owner's blockchain address. "
                    f"Expected: {owner.blockchain_address}"
                )
        
        return cleaned_data

    def save(self, commit=True):
        parcel = super().save(commit=False)
        
        # Handle owner_address assignment
        if self.user and (self.user.is_staff or self.user.is_superuser):
            # Admin users can set custom owner_address
            owner_address = self.cleaned_data.get('owner_address')
            if owner_address:
                parcel.owner_address = owner_address
            elif parcel.owner and parcel.owner.blockchain_address:
                parcel.owner_address = parcel.owner.blockchain_address
        else:
            # Regular users - auto-populate from their blockchain address
            parcel.owner = self.user
            if self.user.blockchain_address:
                parcel.owner_address = self.user.blockchain_address
            else:
                # Fallback to blockchain service account
                blockchain_service = BlockchainService()
                parcel.owner_address = blockchain_service.account.address
        
        # Handle coordinates
        parsed_coords = self.cleaned_data.get('parsed_coordinates')
        if parsed_coords:
            parcel.coordinates = parsed_coords
        
        if commit:
            parcel.save()
            
        return parcel

class ParcelTransferForm(forms.ModelForm):
    contract_file = forms.FileField(
        required=False,
        label="Contract Document",
        help_text="Upload the transfer contract document (PDF, DOC, DOCX, TXT, JPG, PNG)",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png'
        })
    )

    class Meta:
        model = Transfer
        fields = ['parcel', 'recipient', 'terms', 'contract_hash']
        widgets = {
            'parcel': forms.Select(attrs={'class': 'form-select'}),
            'recipient': forms.Select(attrs={'class': 'form-select'}),
            'terms': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'contract_hash': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        # Remove is_admin from kwargs before calling super()
        self.is_admin = kwargs.pop('is_admin', False)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Debug: Check what parcels the user actually owns
            all_parcels = Parcel.objects.all()
            user_parcels = []
            
            # Try different ways to find user's parcels
            # Method 1: Check if Parcel has 'owner' field
            if hasattr(Parcel, 'owner'):
                user_parcels = Parcel.objects.filter(owner=self.user)
                logger.debug(f"Using 'owner' field: Found {user_parcels.count()} parcels for user {self.user.username}")
            
            # Method 2: Check if Parcel has 'user' field  
            elif hasattr(Parcel, 'user'):
                user_parcels = Parcel.objects.filter(user=self.user)
                logger.debug(f"Using 'user' field: Found {user_parcels.count()} parcels for user {self.user.username}")
            
            # Method 3: Check by blockchain address
            elif hasattr(Parcel, 'owner_address') and self.user.blockchain_address:
                user_parcels = Parcel.objects.filter(owner_address__iexact=self.user.blockchain_address)
                logger.debug(f"Using 'owner_address' field: Found {user_parcels.count()} parcels for address {self.user.blockchain_address}")
            
            # Method 4: Check all parcels and filter by owner in Python
            else:
                # Fallback: manually check each parcel
                for parcel in all_parcels:
                    # Check if parcel has owner reference
                    if hasattr(parcel, 'owner') and parcel.owner == self.user:
                        user_parcels.append(parcel)
                    elif hasattr(parcel, 'user') and parcel.user == self.user:
                        user_parcels.append(parcel)
                    elif hasattr(parcel, 'owner_address') and parcel.owner_address and self.user.blockchain_address:
                        if parcel.owner_address.lower() == self.user.blockchain_address.lower():
                            user_parcels.append(parcel)
                
                logger.debug(f"Manual filtering: Found {len(user_parcels)} parcels for user {self.user.username}")
            
            # For admin users, show all parcels
            if self.is_admin:
                self.fields['parcel'].queryset = Parcel.objects.all()
                logger.debug(f"Admin mode: Showing all {Parcel.objects.count()} parcels")
            else:
                # For regular users, only show their parcels
                if user_parcels and hasattr(user_parcels, 'count'):
                    # If it's a queryset
                    self.fields['parcel'].queryset = user_parcels
                else:
                    # If it's a list, convert to queryset
                    parcel_ids = [p.id for p in user_parcels]
                    self.fields['parcel'].queryset = Parcel.objects.filter(id__in=parcel_ids)
                
                logger.debug(f"User mode: Showing {self.fields['parcel'].queryset.count()} parcels")
            
            # Filter recipients to exclude the current user
            self.fields['recipient'].queryset = User.objects.exclude(id=self.user.id)
            self.fields['recipient'].label = "Recipient User"
            self.fields['recipient'].help_text = "Select the user to transfer the parcel to"

            # Debug information
            user_parcels_count = self.fields['parcel'].queryset.count()
            logger.debug(f"DEBUG: User {self.user.username} has {user_parcels_count} parcels")
            logger.debug(f"DEBUG: Parcel queryset: {list(self.fields['parcel'].queryset.values_list('land_id', flat=True))}")
            
            # If no parcels found, show helpful message
            if user_parcels_count == 0 and not self.is_admin:
                self.fields['parcel'].empty_label = "No parcels found - you don't own any parcels"
                self.fields['parcel'].help_text = "You need to own parcels to initiate transfers"
            else:
                self.fields['parcel'].empty_label = "Select a parcel to transfer"

    def clean(self):
        cleaned_data = super().clean()
        parcel = cleaned_data.get('parcel')
        recipient = cleaned_data.get('recipient')
        
        if parcel and recipient:
            # Check ownership using multiple methods
            is_owner = False
            
            # Method 1: Check owner field
            if hasattr(parcel, 'owner') and parcel.owner == self.user:
                is_owner = True
            # Method 2: Check user field
            elif hasattr(parcel, 'user') and parcel.user == self.user:
                is_owner = True
            # Method 3: Check blockchain address
            elif hasattr(parcel, 'owner_address') and self.user.blockchain_address:
                if parcel.owner_address.lower() == self.user.blockchain_address.lower():
                    is_owner = True
            
            if parcel.owner == recipient:
                raise forms.ValidationError("Cannot transfer parcel to the current owner")
                
            # Additional validation for non-admin users
            if not self.is_admin and not is_owner:
                raise forms.ValidationError("You can only transfer parcels that you own")
                
        return cleaned_data

    def save(self, commit=True):
        transfer = super().save(commit=False)
        transfer.sender = self.user
        
        if 'contract_file' in self.files:
            file_service = FileHashService()
            contract_file = self.files['contract_file']
            ipfs_hash = file_service.add_file(contract_file)
            transfer.contract_hash = ipfs_hash
        
        if commit:
            transfer.save()
            
        return transfer