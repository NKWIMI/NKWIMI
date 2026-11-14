# registration/apps.py
from django.apps import AppConfig

class RegistrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'registration'

    def ready(self):
        # Import and connect signals
        import registration.signals
# # registration/apps.py
# from django.apps import AppConfig

# class RegistrationConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'registration'
    
#     def ready(self):
#         import registration.signals  # This imports your signals
# registration/apps.py
