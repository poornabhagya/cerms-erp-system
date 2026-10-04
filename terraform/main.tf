# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Root Terraform Orchestration Manifest
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

# 1. Dedicated Multi-Tenant VPC & Subnets (10.10.0.0/16)
module "vpc" {
  source = "./modules/vpc"
}

# 2. Zero-Trust Security Groups
module "security_groups" {
  source = "./modules/security_groups"
  vpc_id = module.vpc.vpc_id
}

# 3. IAM Roles & Scoped Backup Policies
module "iam" {
  source            = "./modules/iam"
  backup_bucket_arn = module.storage.bucket_arn
}

# 4. GitHub Actions Passwordless OIDC Authentication
module "oidc" {
  source = "./modules/oidc"
}

# 5. EC2 Compute Provisioning (Production & Staging Nodes)
module "compute" {
  source                = "./modules/compute"
  production_subnet_id  = module.vpc.production_subnet_id
  staging_subnet_id     = module.vpc.staging_subnet_id
  security_group_id     = module.security_groups.security_group_id
  instance_profile_name = module.iam.instance_profile_name
}

# 6. Amazon Elastic Container Registry (ECR)
module "ecr" {
  source = "./modules/ecr"
}

# 7. Centralized Multi-Tenant S3 Storage & Glacier Lifecycle
module "storage" {
  source = "./modules/storage"
}

# 8. CloudWatch Monitoring & Incident Alerting
module "monitoring" {
  source                 = "./modules/monitoring"
  production_instance_id = module.compute.production_instance_id
  alert_email            = "poornabhagy@gmail.com"
}

# --- Root Outputs ---
output "vpc_id" {
  description = "Dedicated VPC ID (10.10.0.0/16)"
  value       = module.vpc.vpc_id
}

output "production_subnet_id" {
  description = "Production Subnet ID (10.10.1.0/24 in ap-south-1a)"
  value       = module.vpc.production_subnet_id
}

output "staging_subnet_id" {
  description = "Staging Subnet ID (10.10.2.0/24 in ap-south-1b)"
  value       = module.vpc.staging_subnet_id
}

output "production_eip" {
  description = "Elastic IP of Production EC2 Node"
  value       = module.compute.production_eip
}

output "ecr_repository_url" {
  description = "ECR Repository URL for CERMS container images"
  value       = module.ecr.repository_url
}

output "github_actions_role_arn" {
  description = "OIDC Role ARN for GitHub Actions deployments"
  value       = module.oidc.github_actions_role_arn
}

output "central_backup_bucket_name" {
  description = "Central Disaster Recovery S3 Bucket Name"
  value       = module.storage.bucket_name
}
