#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# CERMS - Hardware Renting System: Production Offsite Disaster Recovery Daemon
# Encrypted Non-Blocking Atomic Dump -> S3 Multi-Tenant Cold Storage
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md (Phase 7)
# ==============================================================================

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
YEAR=$(date +"%Y")
MONTH=$(date +"%m")

BACKUP_DIR="/tmp/cerms_backups"
S3_BUCKET="${BACKUP_S3_BUCKET:-canmee-central-enterprise-backups-4cbcc7c3}"
S3_PREFIX="tenant-b-cerms/db/${YEAR}/${MONTH}"

# GPG Symmetric Passphrase for AES-256 in-stream encryption
GPG_PASSPHRASE="${BACKUP_GPG_KEY:-CERMSEnterpriseSecretKey2026!}"
DB_ROOT_PASSWORD="${DB_PASSWORD:-cerms_secure_password_2026}"

mkdir -p "${BACKUP_DIR}"
DUMP_FILE="${BACKUP_DIR}/cerms_db_${TIMESTAMP}.sql.gz.gpg"

echo "=============================================================================="
echo "[$(date)] Starting CERMS Disaster Recovery atomic database backup..."
echo "Target S3 Vault: s3://${S3_BUCKET}/${S3_PREFIX}/"
echo "=============================================================================="

# 1. Non-blocking consistent dump via MariaDB container
# 2. In-stream Gzip compression
# 3. In-stream AES-256 Symmetric GPG Encryption
# Uses -e MARIADB_PWD to safely avoid password warnings and 80-byte blank dumps
docker exec -e MARIADB_PWD="${DB_ROOT_PASSWORD}" cerms_mariadb mariadb-dump \
  -u root \
  --single-transaction \
  --quick \
  --all-databases \
  2>/dev/null | gzip -c | gpg --symmetric --batch --yes --passphrase "${GPG_PASSPHRASE}" --cipher-algo AES256 -o "${DUMP_FILE}"

# Verify backup file was generated and is not empty
if [ ! -s "${DUMP_FILE}" ]; then
  echo "[-] ERROR: Dump file ${DUMP_FILE} is missing or empty! Backup aborted."
  exit 1
fi

FILE_SIZE=$(du -h "${DUMP_FILE}" | cut -f1)
echo "[$(date)] Database dumped and GPG AES-256 encrypted successfully: ${DUMP_FILE} (${FILE_SIZE})"

# 4. Push to Scoped S3 Prefix using EC2 IAM Role credentials (tenant-b-cerms)
aws s3 cp "${DUMP_FILE}" "s3://${S3_BUCKET}/${S3_PREFIX}/cerms_db_${TIMESTAMP}.sql.gz.gpg" --region ap-south-1

echo "[$(date)] Offsite backup uploaded to s3://${S3_BUCKET}/${S3_PREFIX}/cerms_db_${TIMESTAMP}.sql.gz.gpg"

# 5. Local temporary file cleanup
rm -f "${DUMP_FILE}"
echo "[$(date)] Local temporary files cleaned up. Disaster Recovery backup finished successfully."