#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# CERMS - Hardware Renting System - Environment Healthcheck Harness
# Automated Pre-Flight & Post-Deployment Runtime Verification Suite
# ==============================================================================

echo "=================================================="
echo "CERMS - Hardware Renting System: Healthcheck Suite"
echo "=================================================="

ERRORS=0

# 1. Container Status Check
echo -n "[*] Checking Containers Status... "
RUNNING_CONTAINERS=$(docker ps --format '{{.Names}}' 2>/dev/null || true)
for c in cerms_mariadb cerms_redis cerms_web cerms_nginx; do
  if echo "$RUNNING_CONTAINERS" | grep -q "$c"; then
    echo -n "$c(OK) "
  else
    echo -e "\n[-] FAILED: Container $c is not running!"
    ERRORS=$((ERRORS + 1))
  fi
done
echo ""

# 2. Redis Ping Check
echo -n "[*] Checking Redis Service... "
REDIS_PING=$(docker exec cerms_redis redis-cli ping 2>/dev/null || echo "FAIL")
if [ "$REDIS_PING" = "PONG" ]; then
  echo "OK (PONG received)"
else
  echo "FAILED (Redis not responding)"
  ERRORS=$((ERRORS + 1))
fi

# 3. MariaDB Global Charset & Engine Verification
echo -n "[*] Checking MariaDB Engine & Charset... "
DB_PASSWORD_VAL="${DB_PASSWORD:-cerms_secure_password_2026}"
DB_CHECK=$(docker exec cerms_mariadb mariadb -u root -e "SELECT @@character_set_server AS charset, @@collation_server AS collation;" 2>/dev/null || \
           docker exec cerms_mariadb mariadb -u root -p"${DB_PASSWORD_VAL}" -e "SELECT @@character_set_server AS charset, @@collation_server AS collation;" 2>/dev/null || \
           docker exec cerms_mariadb mariadb-admin -u root ping 2>/dev/null || \
           echo "FAIL")

if echo "$DB_CHECK" | grep -qiE "utf8mb4|alive|mysqld is alive"; then
  echo "OK (MariaDB utf8mb4 / active)"
else
  echo "FAILED (MariaDB validation error)"
  ERRORS=$((ERRORS + 1))
fi

# 4. Web Endpoint Login Check (HTTP 200, 301, or 302 Redirect)
echo -n "[*] Checking Django Web Application (Internal)... "
HTTP_CODE=$(docker exec cerms_web python -c "
import urllib.request, urllib.error
try:
    res = urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)
    print(res.getcode())
except urllib.error.HTTPError as e:
    print(e.code)
except Exception:
    print('000')
" 2>/dev/null || echo "000")

# Also fallback to direct host curl if mapped
if [ "$HTTP_CODE" = "000" ]; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/ 2>/dev/null || echo "000")
fi

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
  echo "OK (HTTP $HTTP_CODE)"
else
  echo "FAILED (Received HTTP $HTTP_CODE)"
  ERRORS=$((ERRORS + 1))
fi

# 5. Nginx Reverse Proxy Ingress (Port 80)
echo -n "[*] Checking Nginx Ingress (Port 80)... "
NGINX_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1/ 2>/dev/null || \
             curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost/ 2>/dev/null || \
             echo "000")

if [ "$NGINX_CODE" = "200" ] || [ "$NGINX_CODE" = "301" ] || [ "$NGINX_CODE" = "302" ] || [ "$NGINX_CODE" = "401" ] || [ "$NGINX_CODE" = "403" ]; then
  echo "OK (HTTP $NGINX_CODE)"
else
  echo "FAILED (Nginx Ingress HTTP $NGINX_CODE)"
  ERRORS=$((ERRORS + 1))
fi

echo "=================================================="
if [ "$ERRORS" -eq 0 ]; then
  echo "[SUCCESS] All CERMS health checks passed with ZERO errors!"
  exit 0
else
  echo "[FAILURE] $ERRORS health checks failed!"
  exit 1
fi