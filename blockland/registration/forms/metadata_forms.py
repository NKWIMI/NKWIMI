from django import forms
from django.core.exceptions import ValidationError
from ..models import MetadataVersion, Property

class MetadataVersionForm(forms.ModelForm):
    """Form for adding new metadata versions to properties"""
    class Meta:
        model = MetadataVersion
        fields = ['property', 'ipfs_hash', 'version']
        widgets = {
            'property': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '{"key": "value"}',
                'help_text': 'Enter metadata as JSON'
            }),
            'ipfs_hash': forms.TextInput(attrs={
                'placeholder': 'Qm...',
                'help_text': 'IPFS Content Identifier (CID)'
            }),
            'version': forms.NumberInput(attrs={
                'min': 1,
                'help_text': 'Version number (integer)'
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter properties owned by the user
        if user:
            self.fields['property'].queryset = Property.objects.filter(owner=user)

    def clean_version(self):
        """Validate version number is positive"""
        version = self.cleaned_data.get('version')
        if version < 1:
            raise forms.ValidationError("Version must be a positive integer")
        return version

    def clean_ipfs_hash(self):
        """Basic validation for IPFS hash format"""
        ipfs_hash = self.cleaned_data.get('ipfs_hash')
        if not ipfs_hash.startswith('Qm') or len(ipfs_hash) != 46:
            raise forms.ValidationError("Invalid IPFS CID format")
        return ipfs_hash