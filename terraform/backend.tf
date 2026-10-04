# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Terraform S3 Remote State Backend (Shared Central Master State Bucket)
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

terraform {
  backend "s3" {
    bucket       = "canmee-enterprise-terraform-state"
    key          = "tenants/cerms/prod/terraform.tfstate"
    region       = "ap-south-1"
    use_lockfile = true
  }
}
