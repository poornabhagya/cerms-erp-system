#!/usr/bin/env python3
# ==============================================================================
# CERMS - Systems Manager (SSM) Deployment Payload Generator
# Generates zero-defect, properly escaped JSON payload for AWS SSM RunShellScript
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

import sys
import os
import json

def generate_ssm_payload():
    instance_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('STAGING_INSTANCE_ID', 'i-0cb762fcdb76a4720')
    image_tag = sys.argv[2] if len(sys.argv) > 2 else 'staging'
    region = os.environ.get('AWS_REGION', 'ap-south-1')
    account_id = "804372444724"
    ecr_registry = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
    ecr_image = f"{ecr_registry}/cerms-web-repo:{image_tag}"

    # Read orchestration and verification assets
    with open('docker-compose.yml', 'r', encoding='utf-8') as f:
        compose_content = f.read()

    with open('nginx.conf', 'r', encoding='utf-8') as f:
        nginx_content = f.read()

    with open('scripts/healthcheck_harness.sh', 'r', encoding='utf-8') as f:
        health_content = f.read()

    with open('scan_urls.py', 'r', encoding='utf-8') as f:
        scan_content = f.read()

    with open('.env.example', 'r', encoding='utf-8') as f:
        env_content = f.read()

    # Construct the remote shell script
    remote_script = f"""#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
export HOME=/root
mkdir -p /opt/cerms/certs /opt/cerms/scripts
cd /opt/cerms

echo "=== [1/8] Deploying System Configuration & Orchestration Files ==="
cat << 'CERMS_EOF_COMPOSE' > /opt/cerms/docker-compose.yml
{compose_content}
CERMS_EOF_COMPOSE

cat << 'CERMS_EOF_NGINX' > /opt/cerms/nginx.conf
{nginx_content}
CERMS_EOF_NGINX

cat << 'CERMS_EOF_HEALTH' > /opt/cerms/scripts/healthcheck_harness.sh
{health_content}
CERMS_EOF_HEALTH

cat << 'CERMS_EOF_SCAN' > /opt/cerms/scan_urls.py
{scan_content}
CERMS_EOF_SCAN

if [ ! -f /opt/cerms/.env ]; then
  cat << 'CERMS_EOF_ENV' > /opt/cerms/.env
{env_content}
CERMS_EOF_ENV
fi

chmod +x /opt/cerms/scripts/healthcheck_harness.sh

echo "=== [2/8] Authenticating Docker with Amazon ECR ==="
export ECR_IMAGE="{ecr_image}"
aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin "{ecr_registry}" || echo "ECR login warning (proceeding with local/cached images)"

echo "=== [3/8] Pulling Latest Container Images ==="
docker compose pull web celery || true

echo "=== [4/8] Starting Core Infrastructure (MariaDB & Redis) ==="
docker compose up -d mariadb redis

echo "=== [5/8] Awaiting Database Engine Readiness ==="
for i in $(seq 1 30); do
  if docker exec cerms_mariadb mariadb-admin ping --silent 2>/dev/null; then
    echo "MariaDB engine is responsive (attempt $i/30)"
    break
  fi
  echo "Waiting for MariaDB daemon... ($i/30)"
  sleep 2
done

# Ensure database and user permissions are initialized
docker exec cerms_mariadb mariadb -u root -e "CREATE DATABASE IF NOT EXISTS cerms_db; CREATE USER IF NOT EXISTS 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; ALTER USER 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; GRANT ALL PRIVILEGES ON cerms_db.* TO 'cerms_user'@'%'; FLUSH PRIVILEGES;" || true

echo "=== [6/8] Launching Application & Web Ingress Containers ==="
docker compose up -d --remove-orphans web celery nginx
docker compose restart nginx || true
sleep 5

echo "=== [7/8] Executing Migrations, Seed Data & Static Asset Collection ==="
docker exec cerms_web python manage.py migrate --noinput
docker exec cerms_web python manage.py seed_initial_data || true
docker exec cerms_web python manage.py collectstatic --noinput

echo "=== [8/8] Executing Runtime Verification & Automated Smoke Tests ==="
/opt/cerms/scripts/healthcheck_harness.sh

docker cp /opt/cerms/scan_urls.py cerms_web:/app/scan_urls.py || true
docker exec cerms_web python scan_urls.py
docker cp cerms_web:/app/smoke_test_summary.json /opt/cerms/smoke_test_summary.json || true

echo "=== SMOKE TEST SUMMARY JSON ==="
cat /opt/cerms/smoke_test_summary.json || echo '{{"total_tested": 0, "crashes": 0}}'
"""

    payload = {
        "DocumentName": "AWS-RunShellScript",
        "InstanceIds": [instance_id],
        "Comment": f"CERMS CI/CD Deploy [{image_tag}] to {instance_id}",
        "Parameters": {
            "commands": [remote_script]
        }
    }

    output_path = "ssm_request.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[+] Successfully generated SSM payload for instance {instance_id} (tag: {image_tag}) -> {output_path}")

if __name__ == "__main__":
    generate_ssm_payload()
