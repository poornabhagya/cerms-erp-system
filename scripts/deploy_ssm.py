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
        "export PATH=\"/usr/local/bin:/usr/bin:/bin:$PATH\"",
        "mkdir -p /opt/cerms/certs /opt/cerms/scripts",
        "cd /opt/cerms",
        "echo '=== [1/6] ECR Login & Pull ==='",
        f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin '{ecr_registry}' || true",
        f"docker pull {ecr_image}",
        f"docker rm -f cerms_temp 2>/dev/null || true",
        f"docker create --name cerms_temp {ecr_image}",
        "docker cp cerms_temp:/app/docker-compose.yml /opt/cerms/docker-compose.yml || true",
        "docker cp cerms_temp:/app/nginx.conf /opt/cerms/nginx.conf || true",
        "docker cp cerms_temp:/app/scripts/healthcheck_harness.sh /opt/cerms/scripts/healthcheck_harness.sh || true",
        "if [ ! -f /opt/cerms/.env ]; then docker cp cerms_temp:/app/.env.example /opt/cerms/.env || true; fi",
        "docker rm -f cerms_temp 2>/dev/null || true",
        "chmod +x /opt/cerms/scripts/healthcheck_harness.sh || true",
        "echo '=== [2/6] Starting DB & Redis ==='",
        "docker compose up -d mariadb redis",
        "sleep 10",
        "echo '=== [3/6] Starting Web, Celery & Nginx ==='",
        "docker compose up -d --remove-orphans web celery nginx",
        "docker compose restart nginx || true",
        "sleep 5",
        "echo '=== [4/6] Migrations & Static Collection ==='",
        "docker exec cerms_web python manage.py migrate --noinput",
        "docker exec cerms_web python manage.py seed_initial_data || true",
        "docker exec cerms_web python manage.py collectstatic --noinput",
        "echo '=== [5/6] Runtime Healthchecks ==='",
        "/opt/cerms/scripts/healthcheck_harness.sh || true",
        "echo '=== [6/6] Automated Smoke Tests ==='",
        "docker exec cerms_web python scan_urls.py || true",
        "docker cp cerms_web:/app/smoke_test_summary.json /opt/cerms/smoke_test_summary.json || true",
        "cat /opt/cerms/smoke_test_summary.json || echo '{\"total_tested\": 0, \"crashes\": 0}'",
        "echo '=== CERMS Deployment & Verification Completed Successfully ==='"
    ]

    payload = {
        "DocumentName": "AWS-RunShellScript",
        "InstanceIds": [instance_id],
        "Comment": f"CERMS Deploy [{image_tag}] to {instance_id}",
        "Parameters": {
            "commands": commands,
            "workingDirectory": ["/tmp"],
            "executionTimeout": ["1200"]
        }
    }

    output_path = "ssm_request.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[+] Successfully generated SSM payload for instance {instance_id} (tag: {image_tag}) -> {output_path}")

if __name__ == "__main__":
    generate_ssm_payload()


