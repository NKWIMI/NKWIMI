# registration/forms/contact_form.py
from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.core.mail import send_mail
from django.conf import settings

class ContactForm(forms.Form):
    """
    A comprehensive contact form with:
    - Basic field validation
    - Bootstrap-compatible rendering
    - Custom clean methods
    - Honeypot spam protection
    - Email sending functionality (console output in development)
    """
    name = forms.CharField(
        label='Your Name',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John Doe'
        }),
        error_messages={
            'required': 'Please enter your name',
            'max_length': 'Name is too long (max 100 characters)'
        }
    )
    
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        }),
        error_messages={
            'required': 'Please enter your email',
            'invalid': 'Please enter a valid email address'
        }
    )
    
    phone = forms.CharField(
        label='Phone Number (Optional)',
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1 (123) 456-7890'
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?[\d\s\-\(\)]{7,20}$',
                message='Enter a valid phone number'
            )
        ]
    )
    
    subject = forms.CharField(
        label='Subject',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Regarding...'
        })
    )
    
    message = forms.CharField(
        label='Your Message',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Type your message here...'
        }),
        error_messages={
            'required': 'Please enter your message'
        }
    )
    
    # Honeypot field for spam protection
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'd-none',
            'tabindex': '-1'
        }),
        label=mark_safe('<span style="display:none">Leave this empty</span>')
    )

    def clean_website(self):
        """Honeypot validation"""
        website = self.cleaned_data.get('website')
        if website:  # If filled, it's probably spam
            raise ValidationError("Spam detected")
        return website

    def clean(self):
        """Additional form-wide validation"""
        cleaned_data = super().clean()
        message = cleaned_data.get('message')

        # Check for banned words in message
        banned_words = ['http://', 'https://', 'www.', 'spam', '[url=', '[link=']
        if message and any(word in message.lower() for word in banned_words):
            raise ValidationError("Your message contains suspicious content")

        return cleaned_data

    def send_email(self):
        """Send the contact form email (prints to console in development)"""
        name = self.cleaned_data['name']
        email = self.cleaned_data['email']
        phone = self.cleaned_data['phone'] or 'Not provided'
        subject = self.cleaned_data['subject']
        message = self.cleaned_data['message']
        
        # Build the email content
        email_subject = f"Contact Form: {subject}"
        email_body = f"""
        New contact form submission from Blockland:
        
        Name: {name}
        Email: {email}
        Phone: {phone}
        Subject: {subject}
        
        Message:
        {message}
        
        ---
        This email was sent from the Blockland contact form.
        """
        
        # Send the email (will print to console in development)
        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@blockland.com'),
            recipient_list=[getattr(settings, 'CONTACT_EMAIL', 'admin@blockland.com')],
            fail_silently=False,
        )