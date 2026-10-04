# 19_SETTINGS_AND_ENV_MANAGEMENT

## 1. The Dual-Environment Strategy

The CERMS project must operate flawlessly in an Enterprise-Grade AWS Cloud infrastructure during staging and production, and subsequently transition to a traditional cPanel hosting environment for the client[cite: 1]. Managing both environments within a single `settings.py` file causes code clutter and logic tangling. To enforce the "Environment-Aware" directive, the system utilizes a modular settings architecture controlled by a master `.env` file[cite: 1].

## 2. Settings Directory Structure

The default Django `settings.py` file must be permanently removed. It is replaced by a `settings/` directory within the main project configuration folder (`cerms_project`).

```text
cerms_project/
├── settings/
│   ├── __init__.py
│   ├── base.py         # Common settings for all environments
│   ├── aws.py          # AWS/Docker specific settings
│   └── cpanel.py       # cPanel specific settings
Module Responsibilities:base.py: Contains universal project configurations. This includes INSTALLED_APPS (fleet, rentals, finance, operations, intelligence), MIDDLEWARE, TEMPLATES, authentication rules, timezone (Asia/Colombo), and core database routing.   aws.py: Imports all configurations from base.py. Adds configurations specific to the cloud deployment[cite: 4]. Maps CELERY_BROKER_URL and CELERY_RESULT_BACKEND to the Redis container. Overrides default storage (DEFAULT_FILE_STORAGE, STATICFILES_STORAGE) to route to AWS S3.   cpanel.py: Imports all configurations from base.py. Forces background tasks to execute synchronously and maps storage paths strictly to the local /public_html/ or internal local storage directories.   3. Mandatory Environment Variables (.env)The application determines which settings module to load and which features to activate entirely via the .env file.Required Keys Template:Ini, TOML# Core Configuration
DJANGO_SETTINGS_MODULE=cerms_project.settings.aws  # Change to cerms_project.settings.cpanel for Shared Hosting
SECRET_KEY=<secure_random_string>
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,.domain.com

# Database Configuration (MariaDB 10.11 LTS)
DB_NAME=cerms_db
DB_USER=cerms_user
DB_PASSWORD=<secure_password>
DB_HOST=mariadb  # Use '127.0.0.1' or 'localhost' for cPanel
DB_PORT=3306

# Feature Toggles (Strictly enforced)
USE_CELERY=True  # Set to False in cPanel to execute tasks synchronously
USE_S3=True      # Set to False in cPanel to use local filesystem storage

# AWS S3 Storage Credentials (Required if USE_S3=True)
AWS_ACCESS_KEY_ID=<aws_access_key>
AWS_SECRET_ACCESS_KEY=<aws_secret_key>
AWS_STORAGE_BUCKET_NAME=<bucket_name>
AWS_S3_REGION_NAME=ap-south-1

# Redis Configuration (Required if USE_CELERY=True)
REDIS_URL=redis://redis:6379/0
```
