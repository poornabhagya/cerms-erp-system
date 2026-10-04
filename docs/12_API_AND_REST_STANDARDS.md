# 12_API_AND_REST_STANDARDS

## 1. Overview

The CERMS platform will expose APIs via Django REST Framework (DRF) to support Mobile & Field Operations, the Customer Portal, and future external integrations[cite: 1, 33]. To ensure smooth frontend and mobile integration without app crashes, all API endpoints must strictly adhere to standard RESTful conventions.

## 2. Universal JSON Response Structure

To prevent mobile app parsing errors, all API responses MUST be wrapped in a consistent JSON envelope. Developers and AI agents must override DRF's default response behavior using a custom renderer and custom exception handler.

**Success Response Format:**

```json
{
    "status": "success",
    "message": "Equipment dispatched successfully.",
    "data": {
        "transaction_id": "TXN-1002",
        "dispatch_date": "2026-10-03T16:47:00Z"
    }
}
Error Response Format:

JSON
{
    "status": "error",
    "error_code": "VALIDATION_FAILED",
    "message": "Invalid hour meter reading.",
    "details": {
        "return_hour_meter": ["Closing meter cannot be less than dispatch meter."]
    }
}
3. Strict HTTP Status Code Usage
APIs must return the semantically correct HTTP status code. Returning 200 OK for an error combined with a {"status": "error"} payload is strictly prohibited.

200 OK: Successful GET, PUT, or PATCH requests.

201 Created: Successful POST requests (e.g., submitting a new Breakdown request).

204 No Content: Successful DELETE requests.

400 Bad Request: Validation errors, malformed JSON, or missing required parameters.

401 Unauthorized: Missing or invalid session/token.

403 Forbidden: User is authenticated but lacks RBAC permissions (e.g., a Field Officer trying to delete an invoice).

404 Not Found: The requested resource does not exist.

500 Internal Server Error: Unhandled backend exceptions (must be caught and logged via the logging module).

4. Pagination, Filtering, and Sorting Rules
To ensure optimal performance on mobile networks and prevent server memory exhaustion:

Pagination: Endpoints returning lists (e.g., /api/equipment/, /api/invoices/) MUST NEVER return unpaginated data. Implement DRF's PageNumberPagination (e.g., ?page=1&page_size=20).

Filtering: Use django-filter for query parameters. Mobile apps should be able to filter datasets easily (e.g., /api/equipment/?status=Available&category=Excavator).

Sorting: Allow ordering via URL parameters (e.g., /api/invoices/?ordering=-due_date).
```
