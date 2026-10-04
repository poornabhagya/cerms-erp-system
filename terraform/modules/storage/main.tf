# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Centralized Multi-Tenant S3 Disaster Recovery & Lifecycle Governance
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

variable "central_backup_bucket_name" {
  description = "Central Master Multi-Tenant S3 Disaster Recovery Bucket Name"
  type        = string
  default     = "canmee-central-enterprise-backups-4cbcc7c3"
}

# 1. Reference Existing Central Multi-Tenant Disaster Recovery S3 Vault
data "aws_s3_bucket" "central_backups" {
  bucket = var.central_backup_bucket_name
}

# Module Outputs for IAM & App Scoping
output "bucket_name" {
  description = "Central Master Backups S3 Bucket Name"
  value       = data.aws_s3_bucket.central_backups.id
}

output "bucket_arn" {
  description = "Central Master Backups S3 Bucket ARN"
  value       = data.aws_s3_bucket.central_backups.arn
}
