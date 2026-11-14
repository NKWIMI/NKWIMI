from django import forms
from ..models.user_models import User

class UserForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password", 
        widget=forms.PasswordInput,
        help_text="Must be at least 8 characters long",
        required=False  # Make optional for updates
    )
    password2 = forms.CharField(
        label="Confirm Password", 
        widget=forms.PasswordInput,
        help_text="Enter the same password as above for verification",
        required=False  # Make optional for updates
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 
                 'address_text', 'identity_document', 'is_active', 'is_staff', 'is_superuser']
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords don't match")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = True
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

# Add this UserUpdateForm class with custom initialization
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'address_text', 'identity_document']
        # Exclude password fields since this is for updating profile, not changing password
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add placeholders and custom attributes
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Enter your username',
            'class': 'form-control'
        })
        
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Enter your email address',
            'class': 'form-control',
            'type': 'email'
        })
        
        self.fields['phone_number'].widget.attrs.update({
            'placeholder': 'Enter your phone number',
            'class': 'form-control',
            'type': 'tel'
        })
        
        self.fields['address_text'].widget.attrs.update({
            'placeholder': 'Enter your complete address',
            'class': 'form-control',
            'rows': 3
        })
        self.fields['address_text'].widget = forms.Textarea()  # Make address a textarea
        
        self.fields['identity_document'].widget.attrs.update({
            'class': 'form-control-file',
            'accept': '.pdf,.jpg,.jpeg,.png'  # Accept common document formats
        })
        
        # Make email field required
        self.fields['email'].required = True
        
        # Add help text
        self.fields['identity_document'].help_text = 'Upload a PDF, JPG, or PNG file (max 5MB)'
        self.fields['phone_number'].help_text = 'Format: +1234567890'