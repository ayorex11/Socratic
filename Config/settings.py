"""
Django settings for Config project.
"""

from pathlib import Path
import os
from datetime import timedelta

from dotenv import load_dotenv 
load_dotenv()
env_path = Path('.')/'.env'
load_dotenv(dotenv_path=env_path)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '.ngrok-free.dev','.ngrok.io',]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_yasg',
    'rest_framework.authtoken',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'corsheaders',
    'Account',
    'Socratic',
    'Pricing',
    'logs',
    'payment',
    'Quiz',
    'storages',
    'rest_framework_simplejwt.token_blacklist',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'Config','templates', 'template'],
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

WSGI_APPLICATION = 'Config.wsgi.application'



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '6543'),
        'OPTIONS': {
            'sslmode': 'require',
        },
        'CONN_MAX_AGE': 0,
    }
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

# Cloudflare R2 Configuration - Everything goes to R2
AWS_ACCESS_KEY_ID = os.getenv('ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('BUCKET_NAME')
AWS_S3_REGION_NAME = "auto"
AWS_S3_ENDPOINT_URL = f"https://{os.getenv('ACCOUNT_ID')}.r2.cloudflarestorage.com"
AWS_S3_SIGNATURE_VERSION = 's3v4'

# Make files publicly accessible
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# Set custom domain if available
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")
if R2_PUBLIC_URL:
    AWS_S3_CUSTOM_DOMAIN = R2_PUBLIC_URL
else:
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.r2.cloudflarestorage.com"

# Storage configuration with folder arrangements
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "location": "media",  # All media files go to 'media/' folder in R2
            "file_overwrite": False,
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage", 
        "OPTIONS": {
            "location": "static",  # All static files go to 'static/' folder in R2
        },
    },
}

# URLs for static and media files
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_HOST_USER')

# Allauth
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[Socratic] '
SITE_ID = 1
SITE_NAME = 'Socratic'

# Custom user model
AUTH_USER_MODEL = 'Account.User'

# URLs
FRONTEND_URL = 'http://localhost:5173'
DJANGO_SITE_URL = 'http://localhost:8000'
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_SIGNUP_FIELDS = ['email*']
BASE_URL = 'localhost:5173'

# REST Auth
REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_RETURN_EXPIRATION': True,
    'JWT_AUTH_COOKIE': 'my-app-auth',
    'JWT_AUTH_HTTPONLY': False,
    'JWT_AUTH_REFRESH_COOKIE': 'my-refresh-token',
    'USER_DETAILS_SERIALIZER': 'Account.serializers.UserDetailsSerializer',
    'REGISTER_SERIALIZER': 'Account.serializers.RegisterSerializer',
}

REST_AUTH_TOKEN_MODEL = None

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'dj_rest_auth.jwt_auth.JWTCookieAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle', 
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '30/hour',
        'user_burst': '5/minute',  
        'user_sustained': '15/hour',
        'dj_rest_auth': '1000/day',  
        'login': '10/minute',
        'registration': '5/hour',
    }
}

# CORS
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:3001',
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# Security
IS_DEVELOPMENT = os.getenv('ENVIRONMENT') == 'development' or DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not IS_DEVELOPMENT  
SESSION_COOKIE_SECURE = not IS_DEVELOPMENT
CSRF_COOKIE_SECURE = not IS_DEVELOPMENT
SECURE_HSTS_SECONDS = 31536000 if not IS_DEVELOPMENT else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not IS_DEVELOPMENT
SECURE_HSTS_PRELOAD = not IS_DEVELOPMENT
SECURE_BROWSER_XSS_FILTER = not IS_DEVELOPMENT
SECURE_CONTENT_TYPE_NOSNIFF = not IS_DEVELOPMENT
X_FRAME_OPTIONS = 'DENY'

# JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=24),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# Custom adapters
ACCOUNT_ADAPTER = 'Config.adapters.CustomAccountAdapter'

# Gemini
GEMINI_CONFIG = {
    'temperature': 0.7,
    'top_p': 0.8,
    'top_k': 40,
    'max_output_tokens': 2048,
}

# Swagger
SWAGGER_SETTINGS = {
    'PERSIST_AUTH': True,  
    'USE_SESSION_AUTH': False, 
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Enter your JWT token with `Bearer ` prefix, e.g. Bearer <token>',
        }
    },
}

# Celery
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0' 
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC' 
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}