# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Amazon Elastic Container Registry (ECR) Module
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

# 1. Private Container Registry (ECR) for CERMS
resource "aws_ecr_repository" "cerms_repo" {
  name                 = "cerms-web-repo"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "cerms-web-repo"
    Environment = "Production"
    Project     = "CERMS"
  }
}

# 2. Lifecycle Policy (Purge untagged images in 1 day, keep last 3 tagged images)
resource "aws_ecr_lifecycle_policy" "cerms_repo_policy" {
  repository = aws_ecr_repository.cerms_repo.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Retain only the last 3 tagged images to control storage costs"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# 3. Outputs
output "repository_url" {
  description = "ECR Repository URL for container image push/pull"
  value       = aws_ecr_repository.cerms_repo.repository_url
}
