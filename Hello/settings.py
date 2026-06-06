"""
Django settings for VetClinic Desktop (local SQLite, admin-only).
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-CHANGE-ME-on-first-install'
DEBUG = False

TIME_ZONE = 'America/Bogota'
USE_TZ = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'home',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Hello.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'home' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'home.context_processors.user_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'Hello.wsgi.application'

# Allow Electron to redirect writable paths to %APPDATA% on the user's machine
# while keeping defaults working for development and `collectstatic`.
_DB_PATH = os.environ.get('VETCLINIC_DB_PATH') or str(BASE_DIR / 'db.sqlite3')
_DATA_DIR = os.environ.get('VETCLINIC_DATA_DIR') or str(BASE_DIR)

_DATABASE_URL = os.environ.get('VETCLINIC_DATABASE_URL') or os.environ.get('DATABASE_URL')

if _DATABASE_URL:
    from urllib.parse import urlparse, unquote
    _u = urlparse(_DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': (_u.path or '/postgres').lstrip('/') or 'postgres',
            'USER': unquote(_u.username or ''),
            'PASSWORD': unquote(_u.password or ''),
            'HOST': _u.hostname or '',
            'PORT': str(_u.port or 5432),
            'CONN_MAX_AGE': 0,
            'OPTIONS': {'sslmode': 'require'},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': _DB_PATH,
        }
    }

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(_DATA_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(_DATA_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ──────────────────────────────────────────────
# Email — Gmail SMTP (kane.agropet@gmail.com)
# Contraseña de aplicación: Cuenta Google →
#   Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones
# ──────────────────────────────────────────────
EMAIL_BACKEND      = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST         = 'smtp.gmail.com'
EMAIL_PORT         = 587
EMAIL_USE_TLS      = True
EMAIL_USE_SSL      = False
EMAIL_HOST_USER    = 'santiagotabina@gmail.com'
EMAIL_HOST_PASSWORD = 'cfbf lwsl xuje mocl'   # ← 16 caracteres sin espacios
DEFAULT_FROM_EMAIL = 'Kane Agropet <kane.agropet@gmail.com>'

# ──────────────────────────────────────────────
# Datos del negocio (facturas, emails, PDFs)
# ──────────────────────────────────────────────
BUSINESS_NAME              = 'Kane Agropet'
BUSINESS_NIT               = '10883475951'
BUSINESS_PHONE             = '+57 300 975 3389'
BUSINESS_EMAIL             = 'kane.agropet@gmail.com'
BUSINESS_ADDRESS           = 'Dosquebradas'
BUSINESS_CITY              = 'Dosquebradas, Risaralda'
BUSINESS_REGIMEN           = 'Responsable de IVA'
BUSINESS_RESOLUCION_DIAN   = 'Resolución DIAN 18760000000000 - Vigencia 24 meses'
