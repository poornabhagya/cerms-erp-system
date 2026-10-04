"""
Construction Equipment Rental Management System (CERMS)
cPanel Shared / VPS Hosting Environment Settings
Reference: docs/06_CPANEL_HANDOVER_GUIDE.md, docs/10_LOGGING_AND_ERROR_HANDLING.md,
           docs/19_SETTINGS_AND_ENV_MANAGEMENT.md
"""

from .base import *
from pathlib import Path
import os

# ==============================================================================
# cPanel Environment Overrides (Forced Synchronous & Local Storage)
# ==============================================================================
USE_CELERY = False
USE_S3 = False

# Force any Celery task invocations to execute synchronously within the main HTTP thread
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Standard Local Filesystem Storage
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Local In-Memory Cache (No Redis dependency on cPanel shared hosting)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'cerms_cpanel_cache',
    }
}

# ==============================================================================
# Local File-Based Logging Configuration (docs/10_LOGGING_AND_ERROR_HANDLING.md)
# ==============================================================================
# Ensure the local logs directory exists for cPanel File Manager inspection
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'cpanel_standard': {
            'format': '[%(asctime)s] %(levelname)-8s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'django_error.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5 MB per file
            'backupCount': 5,
            'formatter': 'cpanel_standard',
            'encoding': 'utf-8',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Business Modules loggers
        'fleet': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'rentals': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'finance': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'operations': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'intelligence': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
