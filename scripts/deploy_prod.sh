#!/usr/bin/env bash
set -e

echo "=================================================="
echo "CERMS - Starting Automated Production Deployment"
echo "=================================================="

export HOME=/root
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH

mkdir -p /opt/cerms
cd /opt/cerms

if [ ! -f .env ]; then
  cp .env.example .env
fi

# Authenticate with Amazon ECR
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "804372444724")
export ECR_URL=${AWS_ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com
export ECR_IMAGE=${ECR_URL}/cerms-web-repo:latest

echo "[*] Logging into Amazon ECR..."
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin ${ECR_URL} || true

echo "[*] Pulling updated production container images..."
docker compose pull web celery || true

echo "[*] Starting Database and Cache Services..."
docker compose up -d mariadb redis

echo "[*] Waiting for MariaDB readiness..."
for i in $(seq 1 30); do
  if docker exec cerms_mariadb mariadb-admin ping --silent 2>/dev/null; then
    echo "MariaDB is ready"
    break
  fi
  sleep 2
done

echo "[*] Initializing Database & User Permissions..."
docker exec cerms_mariadb mariadb -u root -e "CREATE DATABASE IF NOT EXISTS cerms_db; CREATE USER IF NOT EXISTS 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; ALTER USER 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; GRANT ALL PRIVILEGES ON cerms_db.* TO 'cerms_user'@'%'; FLUSH PRIVILEGES;" || true

echo "[*] Starting Web Application, Celery Worker, and Nginx..."
docker compose up -d --remove-orphans web celery nginx
docker compose restart nginx || true
sleep 5

echo "[*] Running Django Database Migrations..."
docker exec cerms_web python manage.py migrate --noinput

echo "[*] Running Seed Initial Data..."
docker exec cerms_web python manage.py seed_initial_data || true

echo "[*] Collecting Static Assets..."
docker exec cerms_web python manage.py collectstatic --noinput

echo "[*] Executing Infrastructure Healthcheck..."
chmod +x ./scripts/healthcheck_harness.sh || true
./scripts/healthcheck_harness.sh || true

echo "[*] Executing Static Route Smoke Tests..."
docker cp scan_urls.py cerms_web:/app/scan_urls.py || true
docker exec cerms_web python scan_urls.py || true
docker cp cerms_web:/app/smoke_test_summary.json ./smoke_test_summary.json || true

echo "=== SMOKE TEST SUMMARY ==="
cat ./smoke_test_summary.json || echo '{"total_tested": 0, "crashes": 0}'

echo "=================================================="
echo "CERMS - Production Deployment Completed Successfully!"
echo "=================================================="
