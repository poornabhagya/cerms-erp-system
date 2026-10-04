#!/usr/bin/env python
"""
Construction Equipment Rental Management System (CERMS)
Django's command-line utility for administrative tasks.
Reference: docs/09_PROJECT_STRUCTURE_AND_STANDARDS.md, docs/19_SETTINGS_AND_ENV_MANAGEMENT.md
"""

import os
import sys
from decouple import config


def main():
    """Run administrative tasks."""
    # Dynamically resolve environment settings module from .env
    settings_module = config('DJANGO_SETTINGS_MODULE', default='cerms_project.settings.aws')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
