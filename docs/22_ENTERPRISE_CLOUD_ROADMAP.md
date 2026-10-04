# 22_ENTERPRISE_CLOUD_ROADMAP

# CERMS: Enterprise Cloud Engineering & CI/CD Roadmap

**Target Stack:** Terraform (IaC) | GitHub Actions (OIDC) | Amazon ECR | Dedicated VPC (10.10.0.0/16) | AWS SSM | EC2 Graviton2 | Docker Compose (Nginx, Django, Celery, Redis, MariaDB) | Central S3/Glacier Cold Storage

---

## Phase 1: Containerization & Docker Orchestration

_Objective: Eliminate environment drift and decouple heavy I/O operations from the main WSGI threads using a robust multi-container architecture._

- **Multi-Stage Dockerfile (`Dockerfile`):**
  - _Stage 1 (Builder):_ Isolate C/C++ compilers (`build-essential`, `default-libmysqlclient-dev`) to compile Python wheels.
  - _Stage 2 (Runtime):_ Use `python:3.12-slim-bookworm`. Create an unprivileged user (`cerms_user:1000`).
  - _Safeguard:_ Inject CPU threading limits (`OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`) to prevent sub-libraries from causing CPU thrashing on multi-tenant cloud cores.
- **Docker Compose Stack (`docker-compose.yml`):**
  - Establish isolated bridge network `cerms_net` (`172.28.0.0/16`).
  - Configure 5 core services: `cerms_nginx`, `cerms_web` (Gunicorn), `cerms_celery`, `cerms_redis`, `cerms_mariadb`.
- **Reverse Proxy & Edge Config (`nginx.conf`):**
  - Enforce OWASP Security Headers (`nosniff`, `DENY`, HSTS).
  - Configure 30-day cache for `/static/` and 7-day cache for `/media/`.
  - Set `X-Forwarded-Proto https` to ensure Django correctly parses SSL terminated at CloudFront.

> **🛠 Engineering Safeguard (Learned from Previous Deployments):**
>
> - **MariaDB OOM Crash Loop:** Strict memory caps on micro-instances cause default MariaDB to crash (Needed 1073741824 bytes). Must explicitly set `--innodb-buffer-pool-size=256M` and `--innodb-log-file-size=64M`.
> - **Empty Password Initialization:** MariaDB 10.11 will fail to initialize without `MARIADB_ALLOW_EMPTY_ROOT_PASSWORD: "yes"` in the compose environment variables.

---

## Phase 2: Infrastructure as Code (Terraform)

_Objective: Provision an isolated, zero-trust AWS environment using modular Terraform HCL, eliminating ClickOps._

- **Remote State Management (`backend.tf` & `provider.tf`):**
  - S3 backend bucket: `cerms-enterprise-terraform-state` with state key `prod/terraform.tfstate`.
  - DynamoDB state-locking table: `cerms-terraform-lock` to prevent concurrent execution collisions.
  - Locked HashiCorp AWS provider version `~> 5.0` in region `ap-south-1`.
- **Dedicated Tenant VPC (`modules/vpc`):**
  - Provision `10.10.0.0/16` (`cerms-dedicated-vpc`) for tenant isolation.
  - Deploy Production Subnet (`10.10.1.0/24`) in availability zone `ap-south-1a` (`cerms-production-subnet`).
  - Deploy Staging Subnet (`10.10.2.0/24`) in availability zone `ap-south-1b` (`cerms-staging-subnet`).
  - _Zero-Cost Routing:_ Use an Internet Gateway (`cerms-igw`) directly instead of expensive NAT Gateways.
- **Zero-Trust Security Groups (`modules/security_groups`):**
  - Open Port 80 and 443 to `0.0.0.0/0` (Edge ingress via CloudFront).
  - Strictly BLOCK Port 22 (SSH), 3306 (MariaDB), and 6379 (Redis) from external ingress.
- **Bastionless IAM Roles (`modules/iam`):**
  - Attach `AmazonSSMManagedInstanceCore` to the EC2 Instance Profile (`cerms-ec2-ssm-role`), allowing secure Systems Manager (SSM) shell access without static SSH keys.
- **Compute Provisioning (`modules/compute`):**
  - Provision EC2 instances (target: `t4g.medium` Graviton2 / `t3.micro`) with 15GB `gp3` root volumes.
  - Inject `user_data.sh.tpl` (Cloud-Init) to automatically allocate 4GB Swap space (`/swapfile`), tune kernel memory (`vm.swappiness=10`), and install Docker/AWS CLI v2 on boot.

---

## Phase 3: Amazon ECR & Passwordless CI/CD Pipeline

_Objective: Establish a secure, automated delivery pipeline utilizing GitHub Actions and OIDC, eliminating static AWS IAM keys._

- **OIDC Trust Identity (`modules/oidc`):**
  - Configure `token.actions.githubusercontent.com` to assume the `cerms-github-actions-deploy-role` scoped specifically to the CERMS GitHub repository.
- **Container Registry (`modules/ecr`):**
  - Provision private ECR repository (`cerms-web-repo`).
  - Implement lifecycle policies to auto-delete untagged images after 1 day and retain only the last 3 tagged images to optimize AWS Free Tier/Storage costs.
- **Staging Pipeline (`.github/workflows/staging.yml`):**
  - Trigger on pushes to `main`.
  - _Test Track:_ Run `pytest` & `manage.py check` against an ephemeral MariaDB/MySQL service container.
  - _Build Track:_ Use Docker Buildx to push `:staging` tag to ECR.
  - _Deploy Track:_ Trigger AWS SSM `AWS-RunShellScript` to pull images, run migrations, `collectstatic`, and restart containers on the Staging EC2 node (`10.10.2.0/24`).

---

## Phase 4: Automated Quality Assurance & Smoke Testing

_Objective: Guarantee application stability and RBAC integrity programmatically after every deployment._

- **Route Scanning Harness (`scan_urls.py`):**
  - Create a local harness that crawls the Django URL resolver, identifying all static routes.
  - Execute `Client().get(url)` against every route inside the deployed container.
  - Assert 0 HTTP 500 crashes and validate RBAC redirects (HTTP 301/302/403).
- **Pipeline Gatekeeping & Artifacts:**
  - Script must export a detailed `smoke_test_summary.json`.
  - If crashes > 0, exit with `sys.exit(1)` to halt the GitHub Actions pipeline.
- **Automated Alerts & Telemetry:**
  - Dispatch notifications via Amazon SNS to the DevOps team containing execution status, commit SHA, and failed route tracebacks upon completion of the Staging pipeline.

> **🛠 Engineering Safeguard (Learned from Previous Deployments):**
>
> - **SSM Output Parsing:** Do not rely on brittle shell text parsing for CI/CD metrics. Extract JSON directly using a Python regex script (`re.search`) from the SSM execution output to prevent "1 CRASH DETECTED" false alarms.
> - **Workflow Noise:** Add `paths-ignore` for `terraform/**` and `**.md` in workflow triggers to prevent unnecessary CI/CD runs when updating infrastructure or documentation.

---

## Phase 5: Production Promotion & Immutability

_Objective: Safely deploy to production using semantic versioning without recompiling code._

- **Immutable Retagging Pipeline (`.github/workflows/deploy.yml`):**
  - Triggered exclusively by GitHub Release Tags (`v*.*.*`).
  - Skip the `docker build` step entirely. Use AWS CLI `ecr batch-get-image` to fetch the verified `:staging` image manifest and retag it as `vX.X.X` and `latest`.
- **In-Situ Production Audit:**
  - Pass `scan_urls.py` into the SSM payload via Base64 encoding.
  - Execute the smoke test directly on the live production database post-migration.
- **Dynamic Markdown Annotations:**
  - Inject `$GITHUB_STEP_SUMMARY` with a real-time markdown table showing Total Tested, 200 OKs, and Crashes.
  - Use `::error title=...` syntax to visually highlight crashed routes directly in the GitHub Actions UI.

---

## Phase 6: Edge Acceleration & Custom DNS

_Objective: Offload static traffic and terminate SSL at the global edge to reduce EC2 load._

- **ACM Provisioning:** Generate DNS-validated AWS Certificate Manager (ACM) certificates strictly in the `us-east-1` region (required for CloudFront).
- **CloudFront Edge Distribution (`modules/cloudfront`):**
  - Configure EC2 Public DNS (FQDN, not raw IP) as the custom origin.
  - Establish `Default Cache Behavior` (min_ttl=0) to forward `Host`, `Authorization`, and cookies to Django for dynamic traffic.
  - Establish `/static/*` behavior with 30-day immutable cache and Gzip/Brotli compression.
  - Establish `/media/*` behavior with 7-day cache.

---

## Phase 7: Multi-Tenant Disaster Recovery (Offsite S3)

_Objective: Ensure data survivability through automated, encrypted, non-blocking backups to a centralized vault._

- **Central S3 Bucket Configuration (`modules/storage`):**
  - Ensure Server-Side Encryption (AES-256) and strict Public Access Blocks.
  - Implement an S3 Lifecycle Rule targeting the tenant-specific prefix `tenant-b-cerms/db/`: Transition to **Glacier Flexible Retrieval** after 30 days; expire permanently after 365 days.
- **Strict IAM Scoping (`modules/iam`):**
  - Grant the EC2 instance role explicit `s3:PutObject` permissions restricted _only_ to `arn:aws:s3:::cerms-central-enterprise-backups/tenant-b-cerms/*` to prevent cross-tenant data leaks.
- **Encrypted Backup Daemon (`scripts/nightly_db_backup.sh`):**
  - Execute nightly via EC2 cron (`0 2 * * *`).
  - Pipeline: `mariadb-dump --single-transaction` -> `gzip` -> `gpg --symmetric --cipher-algo AES256` -> `aws s3 cp`.

> **🛠 Engineering Safeguard (Learned from Previous Deployments):**
>
> - **S3 Download Permissions:** Ensure the SSM role also has `s3:GetObject` if staging servers need to pull database dumps for QA replication.
> - **PowerShell BOM Errors:** If triggering SSM via Windows PowerShell, UTF-8 Byte Order Marks (BOM) can corrupt the JSON payload (`Expected: '=', received: 'ï'`). Use `[System.Text.UTF8Encoding]::new($false)` to send clean JSON.
> - **DB Dump Blank Files:** Do not hardcode passwords in the backup script. Use `docker exec -e MARIADB_PWD="$MYSQL_ROOT_PASSWORD"` to dynamically inject credentials, avoiding Access Denied 80-byte blank dumps.

---

## Phase 8: Telemetry, Observability & Health Probes

_Objective: Proactive monitoring of the production environment to detect anomalies before user impact._

- **CloudWatch Metrics & Alarms (`modules/monitoring`):**
  - Configure `High CPU Alarm` (> 85% for 5 mins) and `StatusCheckFailed` alarms.
  - Link alarms to an SNS Topic (`cerms-devops-alerts`) to dispatch immediate incident emails to the DevOps team.
- **Headless Verification Harness (`scripts/healthcheck_harness.sh`):**
  - A bash harness to continuously verify `docker ps` states, Redis `PONG` responsiveness, MariaDB `utf8mb4` charset configurations, and Nginx HTTP 200/302 statuses.
