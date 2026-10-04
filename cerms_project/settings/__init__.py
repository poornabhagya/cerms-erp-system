"""
Construction Equipment Rental Management System (CERMS)
Modular Settings Package Initialization
Reference: docs/09_PROJECT_STRUCTURE_AND_STANDARDS.md, docs/19_SETTINGS_AND_ENV_MANAGEMENT.md
"""

from decouple import config

# Dynamically resolve environment module when 'cerms_project.settings' is targeted
_settings_module = config('DJANGO_SETTINGS_MODULE', default='cerms_project.settings.aws')

if _settings_module.endswith('.cpanel'):
    from .cpanel import *
else:
    from .aws import *
