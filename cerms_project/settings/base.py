"""
Construction Equipment Rental Management System (CERMS)
Base Settings (Universal project configuration)
Reference: docs/01_PROJECT_ARD_AND_GOALS.md, docs/09_PROJECT_STRUCTURE_AND_STANDARDS.md,
           docs/18_LOCALIZATION_AND_FORMATTING.md, docs/19_SETTINGS_AND_ENV_MANAGEMENT.md
"""

from pathlib import Path
import os
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project: BASE_DIR points to the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security and Debug Settings
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-cerms-default-key-replace-in-production'
)

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = list(config(
    'ALLOWED_HOSTS',
    default='*',
    cast=Csv()
))
if '*' not in ALLOWED_HOSTS and 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')


# Application Definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
]

# Core and Business Modules
LOCAL_APPS = [
    'core.apps.CoreConfig',
    'users.apps.UsersConfig',
    'fleet.apps.FleetConfig',
    'rentals.apps.RentalsConfig',
    'finance.apps.FinanceConfig',
    'operations.apps.OperationsConfig',
    'intelligence.apps.IntelligenceConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Custom User Model (docs/02_DATABASE_SCHEMA.md & docs/03_ROLES_AND_PERMISSIONS.md)
AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cerms_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'cerms_project.wsgi.application'
ASGI_APPLICATION = 'cerms_project.asgi.application'

# Database Configuration (MariaDB 10.11 LTS with InnoDB & utf8mb4)
DB_HOST = config('DB_HOST', default='127.0.0.1')
DB_NAME = config('DB_NAME', default='cerms_db')
DB_USER = config('DB_USER', default='cerms_user')
DB_PASSWORD = config('DB_PASSWORD', default='')
DB_PORT = config('DB_PORT', default='3306')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': (
                "SET sql_mode='STRICT_TRANS_TABLES', "
                "default_storage_engine=INNODB, "
                "collation_connection='utf8mb4_unicode_ci'"
            ),
        },
    }
}

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Localization & Formatting (Sri Lanka Standards - docs/18_LOCALIZATION_AND_FORMATTING.md)
LANGUAGE_CODE = 'en-us'
TIME_ZONE = config('TIME_ZONE', default='Asia/Colombo')
USE_I18N = True
USE_TZ = True

# Static Files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'collected_static'

# Media Files (User Uploads, PDF Contracts, Photos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default Primary Key Field Type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Feature Toggles (docs/01_PROJECT_ARD_AND_GOALS.md & docs/19_SETTINGS_AND_ENV_MANAGEMENT.md)
USE_CELERY = config('USE_CELERY', default=True, cast=bool)
USE_S3 = config('USE_S3', default=True, cast=bool)

# Crispy Forms Configuration (Bootstrap 5.3)
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Django REST Framework Configuration (docs/12_API_AND_REST_STANDARDS.md)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%SZ',
}

# SimpleJWT Authentication Configuration (docs/11_SECURITY_AND_AUTHENTICATION.md)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Security & CORS Configuration
CORS_ALLOW_ALL_ORIGINS = DEBUG
X_FRAME_OPTIONS = 'DENY'

# Authentication URLs
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'users:profile'
LOGOUT_REDIRECT_URL = 'users:login'
