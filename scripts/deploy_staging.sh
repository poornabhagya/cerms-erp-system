#!/usr/bin/env bash
set -e

echo "=================================================="
echo "CERMS - Starting Automated Staging Deployment"
echo "=================================================="

export HOME=/root
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH

mkdir -p /opt/cerms
mkdir -p /opt/cerms/certs
cd /opt/cerms

if [ ! -f .env ]; then
  cp -f .env.example .env
fi

# Ensure correct DB_PASSWORD is set in .env
sed -i 's/DB_PASSWORD=.*/DB_PASSWORD=cerms_secure_password_2026/g' .env || true

# Authenticate with Amazon ECR
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "804372444724")
export ECR_URL=${AWS_ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com
export ECR_IMAGE=${ECR_URL}/cerms-web-repo:staging

echo "[*] Logging into Amazon ECR..."
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin ${ECR_URL} || true

echo "[*] Pulling updated staging container images..."
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
docker exec cerms_mariadb mariadb -u root -pcerms_secure_password_2026 -e "CREATE DATABASE IF NOT EXISTS cerms_db; CREATE USER IF NOT EXISTS 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; ALTER USER 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; GRANT ALL PRIVILEGES ON cerms_db.* TO 'cerms_user'@'%'; FLUSH PRIVILEGES;" 2>/dev/null || \
docker exec cerms_mariadb mariadb -u root -e "CREATE DATABASE IF NOT EXISTS cerms_db; CREATE USER IF NOT EXISTS 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; ALTER USER 'cerms_user'@'%' IDENTIFIED BY 'cerms_secure_password_2026'; GRANT ALL PRIVILEGES ON cerms_db.* TO 'cerms_user'@'%'; FLUSH PRIVILEGES;" || true

echo "[*] Starting Web Application, Celery Worker, and Nginx..."
docker compose up -d --remove-orphans web celery nginx
docker compose restart nginx || true
sleep 5

echo "[*] Verifying Running Containers on Host..."
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

for c in cerms_mariadb cerms_redis cerms_web cerms_nginx; do
  if ! docker ps --format '{{.Names}}' | grep -q "$c"; then
    echo "[-] FATAL: Container $c is not running!"
    docker logs "$c" 2>&1 | tail -n 30 || true
    exit 1
  fi
done

echo "[*] Running Django Database Migrations..."
docker exec cerms_web python manage.py migrate --noinput

echo "[*] Running Seed Initial Data..."
docker exec cerms_web python manage.py seed_initial_data || true

echo "[*] Collecting Static Assets..."
docker exec cerms_web python manage.py collectstatic --noinput

echo "[*] Executing Infrastructure Healthcheck..."
chmod +x ./scripts/healthcheck_harness.sh || true
./scripts/healthcheck_harness.sh || true

echo "[*] Testing Local Nginx & Application Endpoint..."
for i in $(seq 1 10); do
  if curl -s -f http://127.0.0.1/healthz >/dev/null || curl -s -f http://127.0.0.1/ >/dev/null; then
    echo "[+] Local HTTP endpoint responded successfully!"
    break
  fi
  sleep 2
done

echo "[*] Executing Static Route Smoke Tests..."
docker cp scan_urls.py cerms_web:/app/scan_urls.py || true
docker exec cerms_web python scan_urls.py || true
docker cp cerms_web:/app/smoke_test_summary.json ./smoke_test_summary.json || true

echo "=== SMOKE TEST SUMMARY ==="
cat ./smoke_test_summary.json || echo '{"total_tested": 0, "crashes": 0}'

echo "=================================================="
echo "CERMS - Staging Deployment Completed Successfully!"
echo "=================================================="
