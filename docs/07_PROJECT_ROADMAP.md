# 07_PROJECT_ROADMAP

## Phase 0: Cloud Infrastructure & DevOps Plane (AWS)

- **Boilerplate & Dockerization:** Initialize Django 5+ project, configure multi-stage `Dockerfile`, and setup `docker-compose.yml` (Django, Nginx, MariaDB, Redis, Celery) using an isolated bridge network (`172.28.0.0/16`).
- **Infrastructure as Code (Terraform):** Provision AWS Multi-Tenant Dedicated VPC (Staging & Prod subnets), EC2 Graviton2 instances, Amazon ECR, CloudFront CDN, and Central S3 DR Bucket with Glacier lifecycle policies.
- **Zero-Trust CI/CD (GitHub Actions):** Configure OIDC passwordless authentication. Implement `staging.yml` (push to main) and `deploy.yml` (release tags) for immutable container promotion and SSM Bastionless deployments.
- **Automated Testing & DR:** Setup `scan_urls.py` for post-deploy smoke tests, healthcheck harnesses, and configure nightly GPG AES-256 encrypted database backups streaming to S3.

## Phase 1: Core System Modules

- **Setup:** Custom User Models, Authentication, and Role-Based Access Control (RBAC).
- **Fleet & Customer Management:** Equipment Master, Categories, Customers, and Projects/Sites management.
- **Rental Lifecycle:** Availability Calendar, Rental Quotations, Contract/Agreement generation, Equipment Dispatch workflows, and Return processing.
- **Financials:** Automated Rental Billing and Payments/Security Deposits tracking.

## Phase 2: Operations Management

- **Asset Tracking:** Equipment Usage (Hour Meter) tracking and Operator Management.
- **Maintenance:** Preventive schedules, Breakdown/Damage Incident management, and Spare Parts/Inventory control.
- **Logistics:** Fuel Management logs and Transport/Delivery scheduling.

## Phase 3: Advanced Features, Automation & Supervisor UAT

- **Analytics:** Profitability/ROI calculation, Equipment Utilization tracking, and Smart Dashboard KPIs.
- **Automation & UI:** Email/SMS Notifications, Mobile-responsive Field Operations UI, Audit Trail, and Customer Portal.
- **Supervisor UAT:** Comprehensive User Acceptance Testing (UAT) conducted by the supervisor on the live AWS Production and Staging cloud environments.

## Phase 4: cPanel Handover & Final Delivery

- **Environment Configuration:** Toggle `.env` variables (`USE_CELERY=False`, `USE_S3=False`) to safely disable AWS-specific background workers and cloud object storage.
- **Task Scheduling:** Convert Celery Beat background tasks to standard Django Management Commands executable via cPanel Cron Jobs.
- **Final Deployment:** Migrate the compiled monolithic codebase, media assets, and database to the client's final cPanel VPS/Dedicated hosting environment.
