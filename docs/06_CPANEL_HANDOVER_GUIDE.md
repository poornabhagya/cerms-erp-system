# 06_CPANEL_HANDOVER_GUIDE

## 1. Overview

The CERMS platform is designed to transition seamlessly from an AWS enterprise environment to a standard cPanel shared or VPS hosting environment without deleting any code. This transition is controlled entirely via environment variables.

## 2. Mandatory `.env` Modifications

Upon deploying the codebase to cPanel, the following `.env` variables must be updated:

- `DJANGO_SETTINGS_MODULE=cerms_project.settings.cpanel`: Switches the application to use local storage and synchronous processing settings.
- `USE_CELERY=False`: Disables the Celery worker dependency. All asynchronous notifications and background tasks will automatically execute synchronously in the main thread.
- `USE_S3=False`: Bypasses AWS S3 integration. Uploaded documents and equipment photos will be saved directly to the local cPanel disk (e.g., `/home/user/public_html/media/`).
- `DB_HOST=127.0.0.1` (or `localhost`): Points the database connection to the local cPanel MySQL/MariaDB server instead of the Docker network.

## 3. Replacing Celery Beat with cPanel Cron Jobs

Since the Celery daemon will not be running on cPanel, automated scheduled tasks (e.g., daily profitability calculations, overdue rental alerts) must be executed using cPanel's native Cron Jobs functionality.

- **Implementation:** Convert automated tasks into Django Custom Management Commands (e.g., `management/commands/run_daily_tasks.py`).
- **cPanel Cron Job Configuration:** Add the execution command in the cPanel "Cron Jobs" interface at the required intervals (e.g., midnight):
  ```bash
  /usr/local/bin/python /home/yourusername/public_html/manage.py run_daily_tasks > /dev/null 2>&1
  ```
