# 09_PROJECT_STRUCTURE_AND_STANDARDS

## 1. Django App Architecture (Business Modularity)

To maintain a scalable monolithic architecture, the CERMS project is strictly divided into five logical Django applications based on core business areas. This prevents circular dependencies and keeps the codebase maintainable for both AWS and future cPanel environments.

- **`fleet`**: Manages the core assets. (Models: `Equipment`, `Category`, `SparePart`, `TransportRequest`).
- **`rentals`**: Handles the rental lifecycle. (Models: `Customer`, `ProjectSite`, `Quotation`, `RentalContract`, `Dispatch`, `Return`).
- **`finance`**: Manages money and ROI. (Models: `Invoice`, `Payment`, `SecurityDeposit`, `EquipmentProfitability`).
- **`operations`**: Tracks field and maintenance activities. (Models: `HourMeter`, `Operator`, `MaintenanceJob`, `Breakdown`, `FuelLog`).
- **`intelligence`**: Handles system-wide functions. (Models: `AuditLog`, `AlertMessage`, `DashboardMetrics`).

## 2. Standard Directory Layout

The repository must follow this standardized directory structure:

```text
cerms/
├── cerms_project/          # Main Django configuration folder (settings, urls, wsgi, asgi)
│   ├── settings/           # Environment-aware settings
│   │   ├── base.py         # Common settings
│   │   ├── aws.py          # AWS/Docker specific (Celery, S3, Redis)
│   │   └── cpanel.py       # cPanel specific (Cron, Local Storage)
├── fleet/                  # Django App 1
├── rentals/                # Django App 2
├── finance/                # Django App 3
├── operations/             # Django App 4
├── intelligence/           # Django App 5
├── static/                 # Global static assets (CSS, JS, images)
├── media/                  # User-uploaded files (PDFs, photos)
├── templates/              # Global HTML templates
│   ├── base.html           # Main layout structure
│   ├── components/         # Reusable UI components (modals, cards)
│   └── [app_name]/         # App-specific templates
├── docs/                   # Markdown documentation & rules
├── scripts/                # Utility scripts (e.g., db backups, healthchecks)
├── docker-compose.yml      # Local/AWS container orchestration
├── Dockerfile              # Multi-stage container build instructions
├── manage.py
└── requirements.txt
3. Separation of Concerns (Fat Models, Service Layer, Thin Views)
To ensure the business logic does not break when transitioning between Celery (AWS) and Synchronous tasks (cPanel), we must strictly adhere to the following pattern:

Thin Views: Views (views.py) must ONLY handle HTTP requests, permissions, form validation, and returning HTTP responses/JSON. Never place complex business calculations inside a view.

Fat Models: Data-centric logic (e.g., calculating the remaining capacity of a machine, generating an Equipment ID) should reside within the Model methods (models.py).

Service Layer (services.py): Complex workflows involving multiple models (e.g., converting a Quotation to a Contract, processing a Return and updating Billing + Maintenance) MUST be written in a separate services.py file within the respective app.

4. Coding Standards & Naming Conventions
The project must strictly adhere to PEP 8 guidelines to ensure readability and maintainability.

Classes (Models, Forms, Views): Use PascalCase. (e.g., RentalContract, EquipmentCreateView).

Variables, Functions, and Methods: Use snake_case. (e.g., calculate_total_cost(), rental_duration).

Constants: Use UPPER_SNAKE_CASE. (e.g., DEFAULT_TAX_RATE, MAX_RENTAL_DAYS).

Boolean Variables: Prefix with is_, has_, or can_. (e.g., is_available, has_operator).

Docstrings: Every class, model method, and service function MUST have a brief docstring explaining its purpose, parameters, and return types.

Inline Comments: Use comments to explain why a complex piece of logic was written, not what the code does (the code should be self-explanatory).

5. File Import Standards
Imports at the top of any Python file must be grouped logically in this exact order, separated by a blank line:

Python Standard Library imports (e.g., import os, import datetime)

Third-party imports (e.g., import django, import weasyprint, import celery)

Local application imports (e.g., from .models import Equipment, from rentals.services import generate_invoice)
```
