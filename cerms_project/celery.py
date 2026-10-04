"""
Construction Equipment Rental Management System (CERMS)
Celery Application Configuration
Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/20_NOTIFICATIONS_AND_INTEGRATIONS.md
"""

import os
from celery import Celery
from decouple import config

# Set default settings module
settings_module = config('DJANGO_SETTINGS_MODULE', default='cerms_project.settings.aws')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

app = Celery('cerms_project')

# Load task configuration from Django settings, prefixed with 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover task modules across all installed Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
