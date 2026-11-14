from django import forms
from django.core.exceptions import ValidationError
from ..models import PropertyDocument
from ..services.file_hash_service import FileHashService
from django.conf import settings

class DocumentUploadForm(forms.Form):
    document = forms.FileField(
        required=True,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx,.txt'
        }),
        help_text="Upload the document (max 10MB)"
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe the document...'
        }),
        required=False,
        help_text="Optional description of the document"
    )

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document.size > 10 * 1024 * 1024:  # 10MB limit
            raise ValidationError("Document size must be less than 10MB")
        return document

class PropertyDocumentForm(forms.ModelForm):
    class Meta:
        model = PropertyDocument
        fields = ['document_type', 'file', 'description']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Document description...'
            }),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file.size > 10 * 1024 * 1024:  # 10MB limit
            raise ValidationError("File size must be less than 10MB")
        return file

    def save(self, commit=True):
        document = super().save(commit=False)
        if commit:
            document.save()
            # Process file upload to IPFS if needed
            if hasattr(settings, 'IPFS_API_KEY') and settings.IPFS_API_KEY:
                file_service = FileHashService(use_ipfs=True)
                ipfs_hash = file_service.add_file(document.file)
                if ipfs_hash:
                    document.ipfs_hash = ipfs_hash
                    document.save()
        return document