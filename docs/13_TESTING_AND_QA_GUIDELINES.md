# 13_TESTING_AND_QA_GUIDELINES

## 1. Overview

In an enterprise ERP system like CERMS, undetected bugs can lead to financial losses, incorrect billing, or equipment mismanagement. To prevent logic regressions, AI agents and developers must write comprehensive automated tests before a feature is considered complete.

## 2. Django Unit Testing Standards

- **Test Location:** Every Django app must contain a `tests/` directory to separate test concerns (e.g., `rentals/tests/test_models.py`, `rentals/tests/test_services.py`, `rentals/tests/test_apis.py`). Do not use a single `tests.py` file for an entire app.
- **Test Isolation:** Each test must be completely independent. Use the `setUp()` method or libraries like `factory_boy` to generate mock data (Dummy Users, Equipment, Customers) for each test class.
- **No Hardcoded IDs:** Never assume an ID (like `customer_id=1`) exists in the test database. Always dynamically query or use the object instance created in the `setUp()` function.

## 3. Mandatory Test Coverage Areas

When a new module or feature is created, the following layers MUST be explicitly covered by unit tests:

### A. Business Logic & Services (`services.py`)

- Test complex financial calculations (e.g., Rental invoice totals, including overtime, transport, and fuel costs).
- Test state transitions (e.g., Ensure an Equipment's status automatically changes to `On Rent` when a Dispatch is created, and `Available` or `Maintenance` upon Return).

### B. Model Constraints & Logic (`models.py`)

- Test custom validation in `clean()` methods (e.g., Ensure `return_hour_meter` cannot be mathematically less than the `dispatch_hour_meter`).
- Test database integrity protections, such as ensuring `on_delete=models.PROTECT` successfully prevents the deletion of a Customer with active Contracts.

### C. Role-Based Access Control (RBAC) & Views

- Ensure an `Administrator` or `Rental Officer` receives a `200 OK` response for quotation endpoints.
- Ensure a `Storekeeper` attempting to delete a financial invoice receives a `403 Forbidden` response.
- Verify that unauthenticated requests receive a `302 Redirect` to the login page (for web views) or a `401 Unauthorized` (for APIs).

### D. API Responses (`serializers.py` & API Views)

- Validate that API endpoints return the strict JSON envelope structure defined in `12_API_AND_REST_STANDARDS.md`.
- Test missing or malformed parameters to ensure proper `400 Bad Request` validation errors are returned instead of `500 Internal Server Error` crashes.

## 4. QA & Pre-Deployment Checklist

Before any code is committed or pushed to trigger the GitHub Actions CI/CD pipeline, the following criteria must be met locally:

1.  Run `python manage.py test` (Must report 0 failures or errors).
2.  Verify no sensitive data (passwords, keys) is hardcoded in the new files.
3.  Ensure the feature works seamlessly regardless of whether `USE_CELERY` or `USE_S3` is set to True or False in the `.env` file.
