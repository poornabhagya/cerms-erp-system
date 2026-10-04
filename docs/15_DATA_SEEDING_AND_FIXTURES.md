# 15_DATA_SEEDING_AND_FIXTURES

## 1. Overview

To facilitate rapid development, QA testing, and staging environment setups, the CERMS platform requires a standardized method for populating the database with initial mandatory data (e.g., User Roles) and realistic dummy data (e.g., fake Customers, Equipment, and Contracts).

## 2. Static Data Seeding (Django Fixtures)

For static, foundational data that is strictly required for the system to function, use Django JSON fixtures.

- **Target Data:** The 8 core User Roles/Groups (Administrator, Management, Rental Officer, Operations Officer, Workshop Manager, Accountant, Storekeeper, Field Officer), default System Settings, and initial Superuser accounts.
- **Storage Location:** Store fixture files in the respective app's fixture directory (e.g., `users/fixtures/core_roles.json`).
- **Execution:** Loaded via the standard Django command:
  `python manage.py loaddata core_roles.json`

## 3. Dynamic Dummy Data (Custom Management Commands)

For generating large volumes of realistic testing data, static JSON fixtures are inefficient and difficult to maintain. Developers must write Custom Django Management Commands utilizing the Python `Faker` library.

- **Command Location:** Create scripts inside `[app_name]/management/commands/` (e.g., `rentals/management/commands/seed_dummy_data.py`).
- **Execution:** Run via `python manage.py seed_dummy_data`.
- **Mandatory Seed Entities:**
  - **Users:** Generate 1-2 test users mapped to each RBAC Role for permission testing.
  - **Fleet:** Generate at least 50 realistic construction equipment entries with varied statuses (Available, Maintenance, Reserved, On Rent).
  - **Rentals & Finance:** Generate a full lifecycle simulation including historical rental contracts, dispatch/return logs, and active/overdue invoices to properly test the Smart Dashboard charts.

## 4. Safety and Production Constraints

- **Production Protection:** Custom management commands that generate destructive or fake data MUST include a strict environment check to prevent accidental execution on the live production database.
- **Implementation Rule:** At the very beginning of the `handle()` method in any seeding script, verify the environment:

  ```python
  from django.conf import settings
  from django.core.management.base import CommandError

  def handle(self, *args, **kwargs):
      if not settings.DEBUG:
          raise CommandError("CRITICAL: Refusing to generate dummy data in a Production environment.")
      # Proceed with data generation...
  ```
