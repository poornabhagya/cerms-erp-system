# 08_FRONTEND_AND_UI_GUIDELINES

## 1. Core Frontend Philosophy & Technologies

The CERMS frontend strictly relies on server-side rendering combined with lightweight asynchronous interactions.

- **Mandatory Stack:** Django Native Templates, Bootstrap 5.3+, JavaScript, and AJAX[cite: 34].
- **Prohibited Tech:** Under no circumstances should React, Next.js, Vue, or any external Single Page Application (SPA) frameworks be used[cite: 1].

## 2. Django Template Standards

To ensure UI consistency across all 5 business modules, every HTML page must extend a central master layout.

- **Master Layout:** All pages must extend `templates/base.html`.
- **Template Blocks:** Use standard blocks: `{% block title %}`, `{% block content %}`, `{% block extra_css %}`, and `{% block extra_js %}`.
- **Static Assets:** Always use the `{% static %}` tag for loading CSS, JS, and images. Hardcoded paths are strictly prohibited.

## 3. Mobile Responsiveness (Bootstrap 5.3+)

The system must be fully usable on mobile devices and tablets, specifically to support the `Field Officer` role for on-site dispatch, return inspections, and hour-meter entries[cite: 34].

- **Grid System:** Always use Bootstrap's responsive grid classes (`col-12 col-md-6 col-lg-4`).
- **Mobile-First Tables:** Wrap all tables in `<div class="table-responsive">` to prevent horizontal scrolling breaking the layout on mobile devices.
- **Inputs:** Use Bootstrap's `form-control` and `form-select` for all inputs. Use `form-floating` for modern labels.

## 4. AJAX & Asynchronous Form Submissions

To enhance user experience, forms that do not require full page redirects (e.g., updating a status, adding a spare part to a job) must be submitted via AJAX[cite: 34].

- **CSRF Protection:** Every AJAX POST/PUT request MUST include the Django CSRF token in the headers (`X-CSRFToken`).
- **JSON Responses:** Django Views handling AJAX must return `JsonResponse` (e.g., `{"status": "success", "message": "...", "data": {...}}`).
- **UI Feedback:** Always disable the submit button during the AJAX call and show a Bootstrap spinner. Display a toast notification (Bootstrap Toasts or SweetAlert2) upon success or failure.

## 5. DataTables Configuration Standard

All data grids (e.g., Equipment List, Active Contracts, Invoices) must use DataTables[cite: 34]. AI must strictly use this initialization pattern to prevent UI fragmentation:

- **Default Config:** Enable pagination, search, and sorting by default.
- **Styling:** Use the `DataTables Bootstrap 5` integration.
- **Export Options:** Include DataTables export buttons (`Copy`, `CSV`, `Excel`, `PDF`, `Print`) for reports and module lists.
- **AJAX Loading:** For tables exceeding 1000 rows (e.g., `FuelLog`, `AuditLog`), configure DataTables to use `serverSide: true` combined with Django REST Framework or custom JSON views to prevent browser freezing.

## 6. Chart.js Configuration Standard

The Smart Dashboard utilizes Chart.js for KPI visualizations (e.g., revenue, utilization, profitability)[cite: 34].

- **Responsiveness:** Always set `responsive: true` and `maintainAspectRatio: false` in the chart options.
- **Color Palette:** Use Bootstrap 5 standard colors or a predefined consistent palette for datasets (Primary, Success, Warning, Danger) to maintain visual harmony.
- **Tooltips:** Enable tooltips to display exact numerical values (e.g., currency formatted as LKR) when hovering over data points.
