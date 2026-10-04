# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Terraform AWS Provider Configuration (HashiCorp AWS ~> 5.0 / ap-south-1)
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Primary Regional AWS Provider (Mumbai - ap-south-1)
provider "aws" {
  region = "ap-south-1"

  default_tags {
    tags = {
      Project     = "CERMS"
      ManagedBy   = "Terraform"
      Platform    = "Construction Equipment Rental Management System"
      Environment = "Production"
    }
  }
}
