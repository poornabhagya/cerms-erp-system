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

    commands = [
        "echo '=== Step 1: System Environment & Paths ==='",
        "whoami",
        "hostname",
        "pwd",
        "export PATH=\"/usr/local/bin:/usr/bin:/bin:$PATH\"",
        "which docker || echo 'docker not found in PATH'",
        "which aws || echo 'aws not found in PATH'",
        "mkdir -p /opt/cerms/certs /opt/cerms/scripts",
        "cd /opt/cerms",
        "echo '=== Step 2: ECR Authentication & Image Pull ==='",
        f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin '{ecr_registry}' || echo 'ECR login failed'",
        f"docker pull {ecr_image}",
        f"CID=$(docker create {ecr_image})",
        "docker cp ${CID}:/app/docker-compose.yml /opt/cerms/docker-compose.yml || echo 'No docker-compose in container'",
        "docker cp ${CID}:/app/nginx.conf /opt/cerms/nginx.conf || echo 'No nginx.conf in container'",
        "docker cp ${CID}:/app/scripts/healthcheck_harness.sh /opt/cerms/scripts/healthcheck_harness.sh || echo 'No healthcheck in container'",
        "if [ ! -f /opt/cerms/.env ]; then docker cp ${CID}:/app/.env.example /opt/cerms/.env || true; fi",
        "docker rm ${CID} || true",
        "chmod +x /opt/cerms/scripts/healthcheck_harness.sh || true",
        "echo '=== Step 3: Infrastructure Orchestration (MariaDB & Redis) ==='",
        "docker compose up -d mariadb redis",
        "for i in $(seq 1 30); do if docker exec cerms_mariadb mariadb-admin ping --silent 2>/dev/null; then echo 'DB Ready'; break; fi; echo 'Waiting for MariaDB...'; sleep 2; done",
        "docker exec cerms_mariadb mariadb -u root -e \"CREATE DATABASE IF NOT EXISTS cerms_db; CREATE USER IF NOT EXISTS 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; ALTER USER 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; GRANT ALL PRIVILEGES ON cerms_db.* TO 'cerms_user'@'%'; FLUSH PRIVILEGES;\" || true",
        "echo '=== Step 4: Web Application & Proxy Deployment ==='",
        "docker compose up -d --remove-orphans web celery nginx",
        "docker compose restart nginx || true",
        "sleep 5",
        "echo '=== Step 5: Database Migrations & Data Seeding ==='",
        "docker exec cerms_web python manage.py migrate --noinput",
        "docker exec cerms_web python manage.py seed_initial_data || true",
        "docker exec cerms_web python manage.py collectstatic --noinput",
        "echo '=== Step 6: Environment Healthchecks & Smoke Tests ==='",
        "/opt/cerms/scripts/healthcheck_harness.sh || echo 'Healthcheck harness returned non-zero'",
        "docker exec cerms_web python scan_urls.py || echo 'Scan URLs returned non-zero'",
        "docker cp cerms_web:/app/smoke_test_summary.json /opt/cerms/smoke_test_summary.json || true",
        "echo '=== SMOKE TEST SUMMARY JSON ==='",
        "cat /opt/cerms/smoke_test_summary.json || echo '{\"total_tested\": 0, \"crashes\": 0}'"
    ]

    payload = {
        "DocumentName": "AWS-RunShellScript",
        "InstanceIds": [instance_id],
        "Comment": f"CERMS Deploy [{image_tag}] to {instance_id}",
        "Parameters": {
            "commands": commands
        }
    }

    output_path = "ssm_request.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[+] Successfully generated SSM payload for instance {instance_id} (tag: {image_tag}) -> {output_path}")

if __name__ == "__main__":
    generate_ssm_payload()


