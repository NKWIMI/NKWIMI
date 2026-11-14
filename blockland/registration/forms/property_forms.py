from django import forms
from django.core.exceptions import ValidationError
from ..models import Property

class PropertyRegistrationForm(forms.ModelForm):
    owner_address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0x...',
            'readonly': True
        }),
        help_text="Blockchain address of the property owner"
    )

    class Meta:
        model = Property
        fields = ['name', 'property_id', 'owner_address', 'size_sqm', 'location', 'property_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Property Name'
            }),
            'property_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'PROP-1234'
            }),
            'size_sqm': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City, District'
            }),
            'property_type': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and hasattr(self.user, 'profile'):
            self.fields['owner_address'].initial = self.user.profile.blockchain_address

    def clean_property_id(self):
        property_id = self.cleaned_data.get('property_id')
        if not property_id:
            raise ValidationError("Property ID is required")
            
        if Property.objects.filter(property_id__iexact=property_id).exists():
            raise ValidationError(f"A property with ID {property_id} already exists")
            
        return property_id.strip()

    def save(self, commit=True):
        property = super().save(commit=False)
        if self.user and hasattr(self.user, 'profile'):
            property.owner = self.user
            property.owner_address = self.user.profile.blockchain_address
            
        if commit:
            property.save()
            property.generate_blockchain_hash()
            
        return property