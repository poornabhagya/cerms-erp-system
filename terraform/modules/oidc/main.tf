# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# AWS IAM OpenID Connect (OIDC) Identity Provider & GitHub Actions Role
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

variable "github_repo" {
  description = "GitHub repository (e.g., username/repo)"
  type        = string
  default     = "*cerms*"
}

# 1. Reference Shared Account-Level AWS IAM OpenID Connect Provider for GitHub Actions
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# 2. OIDC Assume Role Trust Policy Document (Scoped to CERMS Repositories)
data "aws_iam_policy_document" "github_oidc_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:*cerms*:*",
        "repo:*hardware*renting*:*",
        "repo:*rentingSys*:*"
      ]
    }
  }
}

# 3. Dedicated IAM Role assumed by GitHub Actions Runner for CERMS
resource "aws_iam_role" "github_actions" {
  name               = "cerms-github-actions-deploy-role"
  assume_role_policy = data.aws_iam_policy_document.github_oidc_assume.json

  tags = {
    Name        = "cerms-github-actions-deploy-role"
    Environment = "CI/CD"
    Project     = "CERMS"
  }
}

# 4. Permissions to push/retag images in ECR
resource "aws_iam_role_policy_attachment" "github_ecr_poweruser" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
}

# 5. Permissions for GitHub Actions to trigger SSM deployments
resource "aws_iam_policy" "github_ssm_deploy" {
  name        = "cerms-github-ssm-deploy-policy"
  description = "Permissions for GitHub Actions to trigger SSM deployments on CERMS nodes"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "ssm:ListCommandInvocations",
          "ssm:DescribeInstanceInformation"
        ]
        Resource = "*"
      }
    ]
  })
}

# 6. Attach SSM Policy to Role
resource "aws_iam_role_policy_attachment" "github_ssm_attach" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_ssm_deploy.arn
}

# 7. Outputs
output "github_actions_role_arn" {
  description = "Role ARN to be assumed by GitHub Actions via OIDC"
  value       = aws_iam_role.github_actions.arn
}
