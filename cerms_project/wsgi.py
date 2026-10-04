"""
Construction Equipment Rental Management System (CERMS)
WSGI Config for cerms_project
Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/19_SETTINGS_AND_ENV_MANAGEMENT.md
"""

import os
from decouple import config
from django.core.wsgi import get_wsgi_application

# Dynamically set settings module from .env (defaults to AWS cloud configuration)
settings_module = config('DJANGO_SETTINGS_MODULE', default='cerms_project.settings.aws')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()
