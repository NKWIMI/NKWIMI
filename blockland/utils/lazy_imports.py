# registration/utils/lazy_imports.py
def get_form_class(form_name):
    """Lazy import forms to avoid circular imports"""
    form_map = {
        'ContactForm': 'registration.forms.contact_form.ContactForm',
        'ParcelTransferForm': 'registration.forms.parcel_forms.ParcelTransferForm',
        'ParcelRegistrationForm': 'registration.forms.parcel_forms.ParcelRegistrationForm',
    }
    
    if form_name in form_map:
        module_path, class_name = form_map[form_name].rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    
    return None