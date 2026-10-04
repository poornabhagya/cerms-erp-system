# 01_PROJECT_ARD_AND_GOALS

## 1. Project Overview & Goals

**Project Name:** Construction Equipment Rental Management System (CERMS)
**Core Objective:** CERMS is a centralized, smart, and modern web-based enterprise platform designed to manage the complete lifecycle of construction equipment. This includes equipment acquisition, real-time availability, quotations, contracts, dispatch, hour-meter tracking, automated billing, maintenance workflows, fuel consumption, and ROI analytics.

## 2. Architectural Strategy

**Architecture Pattern:** Multi-Tenant Dedicated VPC Architecture (Monolithic)
The system is built as a highly available, scalable, and low-cost monolithic application. It strictly follows a "Silo Pattern" where the network, compute, and application runtimes are isolated within a dedicated AWS VPC, while allowing for seamless transition to traditional cPanel hosting environments for final client delivery.

## 3. Technology Stack

- **Backend & Frontend (Monolithic):** Django 5+ (Python 3.12). The system will strictly use Django's native templating engine for the frontend. (Do not use React, Next.js, or any separate frontend frameworks).
- **UI/UX & Interactions:** Bootstrap 5.3+, custom JavaScript, and AJAX for asynchronous operations without page reloads.
- **Data Presentation:** DataTables for grid views and Chart.js for dashboard analytics.
- **PDF Generation:** WeasyPrint or ReportLab for generating quotations, contracts, and invoices.
- **Database:** MariaDB 10.11 LTS (InnoDB, utf8mb4_unicode_ci for full Unicode support).
- **Cache & Message Broker:** Redis 7.2 Alpine and Celery (for asynchronous background tasks and notifications).
- **Web Server / Proxy:** Gunicorn (WSGI) and Nginx 1.25 Alpine.
- **Containerization:** Docker and Docker Compose (Multi-container setup via an isolated bridge network `172.28.0.0/16`).
- **Infrastructure as Code (IaC):** HashiCorp Terraform 1.5+ (Remote S3 State Configuration).

## 4. Strict Environment Rule (AWS vs. cPanel)

**CRITICAL DIRECTIVE:** The development, staging, and production testing of this system will occur on an Enterprise-Grade AWS Cloud infrastructure (utilizing Docker, Celery, Redis, EC2, ECR, and GitHub Actions CI/CD). However, the **final compiled project will be handed over to the client on a traditional cPanel hosting environment.**

Therefore, the codebase MUST be strictly **"Environment-Aware"**:

- All environment-specific features (e.g., Celery task execution vs. Synchronous execution, S3 storage vs. Local file storage) must be controlled dynamically via `.env` variables (e.g., `USE_CELERY=True/False`, `USE_S3=True/False`).
- The code must be written so that transitioning from AWS to cPanel requires ZERO code deletion—only modifications to the `.env` configuration file and switching from Celery Beat to standard cPanel Cron Jobs for background tasks.

## 5. Core Business Areas

The monolithic Django project should be logically partitioned into five major business modules (Django Apps):

1.  **Fleet Management:** Equipment Master, Categories, Spare Parts, Transport.
2.  **Rental Management:** Customers, Quotations, Contracts, Dispatch/Return.
3.  **Financial Management:** Billing, Payments/Deposits, Equipment Profitability/ROI.
4.  **Asset Operations:** Hour Meter/Usage, Maintenance, Operators, Fuel Logs.
5.  **Intelligence & Automation:** Smart Dashboard, Reports, Alerts, Audit Trail, Customer Portal.
