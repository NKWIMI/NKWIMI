# settings.py
import os
from pathlib import Path
import couchdb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
# Tesseract OCR path for Windows (adjust if needed)
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'registration',  # your registration app
    'django_extensions',
    'widget_tweaks',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_bootstrap5', 
    'channels',
    'ai',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'blockland.urls' 

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'registration.wsgi.application'

# Database - Keep SQLite for Django's internal operations
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CouchDB Configuration with authentication
COUCHDB_USER = 'admin'
COUCHDB_PASSWORD = os.getenv('COUCHDB_PASSWORD', '')
COUCHDB_CONFIG = {
    'SERVER': 'http://localhost:5984/',
    'USERNAME': os.getenv('COUCHDB_USERNAME', 'admin'),
    'PASSWORD': os.getenv('COUCHDB_PASSWORD'),
    'DATABASE': 'land_registration',
}

# Initialize CouchDB connection with proper authentication
try:
    # Create authenticated server connection
    couch_server_url = f"http://{COUCHDB_CONFIG['USERNAME']}:{COUCHDB_CONFIG['PASSWORD']}@localhost:5984/"
    couch_server = couchdb.Server(couch_server_url)
    
    # Test connection
    couch_server.version()
    
    # Try to access the database, create if it doesn't exist
    try:
        COUCHDB_DB = couch_server[COUCHDB_CONFIG['DATABASE']]
        print(f"✅ Connected to existing CouchDB database: {COUCHDB_CONFIG['DATABASE']}")
    except couchdb.ResourceNotFound:
        COUCHDB_DB = couch_server.create(COUCHDB_CONFIG['DATABASE'])
        print(f"✅ Created new CouchDB database: {COUCHDB_CONFIG['DATABASE']}")
        
    print(f"✅ Successfully connected to CouchDB with authentication")
    
except couchdb.Unauthorized:
    print(f"❌ CouchDB authentication failed. Please check username and password.")
    COUCHDB_DB = None
except couchdb.ServerError as e:
    print(f"❌ CouchDB server error: {e}")
    COUCHDB_DB = None
except Exception as e:
    print(f"⚠️ Warning: Could not connect to CouchDB: {e}")
    COUCHDB_DB = None

# COUCHDB_DB is now available globally
# settings.py
BLOCKCHAIN_CONFIG = {
    'GANACHE_URL': os.getenv('GANACHE_URL', 'http://127.0.0.1:7545'),
    'CONTRACT_ADDRESS':'0xC3059366a629cFFdAC75C1185186704190ff5608',
    'ETHEREUM_PRIVATE_KEY': os.getenv('ETHEREUM_PRIVATE_KEY'),
    'CONTRACT_ABI_PATH': os.getenv('CONTRACT_ABI_PATH', 'D:/THEO/blockland/blockchain/artifacts/contracts/LandRegistry.sol/LandRegistry.json'),
}

# AI Configuration
AI_CONFIG = {
    'DOCUMENT_VERIFICATION_ENABLED': True,
    'FRAUD_DETECTION_ENABLED': True,
    'MIN_CONFIDENCE_THRESHOLD': 0.7,
    'RISK_THRESHOLD': 50,
    'MODEL_PATH': os.path.join(BASE_DIR, 'ml_models'),
}


# IPFS Configuration
IPFS_CONFIG = {
    'API_URL': os.getenv('IPFS_API_URL', 'https://api.pinata.cloud'),
    'API_KEY': os.getenv('IPFS_API_KEY'),
    'API_SECRET': os.getenv('IPFS_API_SECRET'),
    'REQUIRE_IPFS': os.getenv('REQUIRE_IPFS', 'True').lower() == 'true',
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'registration.User'

# registration/settings.py
#ROOT_URLCONF = 'registration.urls'
WSGI_APPLICATION = 'registration.wsgi.application'
# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# IPFS Configuration (optional - for file storage)
IPFS_API_KEY = os.environ.get('IPFS_API_KEY', '')
IPFS_API_SECRET = os.environ.get('IPFS_API_SECRET', '')
# settings.py
# Email settings
# For development only - emails will print to console
# settings.py
# Email settings for development (emails print to console)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    # Add your production email settings here when needed

# Default email settings
DEFAULT_FROM_EMAIL = 'noreply@blockland.com'
CONTACT_EMAIL = 'admin@blockland.com'

# Or use ADMINS as fallback
ADMINS = [
    ('Admin Name', 'admin@yourdomain.com'),
]
# Crispy Forms Configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Configure ASGI application
ASGI_APPLICATION = 'blockland.asgi.application'

# Channel layers configuration (using Redis)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
