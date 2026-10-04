# 18_LOCALIZATION_AND_FORMATTING

## 1. Overview

Since the CERMS platform is designed specifically for operations within Sri Lanka, proper localization and formatting are critical to prevent discrepancies in timestamps, financial calculations, and multilingual text rendering.

## 2. Timezone Configuration

To ensure all equipment dispatch logs, return times, and maintenance schedules are recorded in the correct local time rather than default UTC:

- The Django configuration (inside `settings/base.py`) MUST have the timezone explicitly set to Sri Lanka:
  ```python
  TIME_ZONE = 'Asia/Colombo'
  USE_TZ = True
  ```
- **Coding Standard:** Never use Python's standard `datetime.now()`. Always use Django's timezone-aware utilities for timestamps:
  ```python
  from django.utils import timezone
  current_time = timezone.now()
  ```

## 3. Currency and Financial Formatting

Financial data (Invoices, Quotations, Payments, Rental Rates) must be formatted uniformly across all UI views (DataTables, Dashboards) and generated PDFs.

- **Currency Symbol:** All monetary values must be displayed with the prefix **"LKR"**.
- **Decimal Formatting:** Monetary values must strictly be displayed with thousands separators and 2 decimal places (e.g., `LKR 12,500.00`).
- **Database Storage:** To prevent floating-point calculation errors, all financial fields in the models MUST use `DecimalField`:
  ```python
  amount = models.DecimalField(max_digits=12, decimal_places=2)
  ```

## 4. Character Encoding (Sinhala & Tamil Support)

Users may input customer names, site addresses, or maintenance notes in Sinhala or Tamil. To support proper multilingual text storage:

- The MariaDB database and all tables are configured at the DevOps level to use the `utf8mb4` character set with `utf8mb4_unicode_ci` collation.
- The Django ORM must simply rely on this configuration. Standard `utf8` is strictly prohibited as it does not fully support all Unicode characters required for complex scripts.
