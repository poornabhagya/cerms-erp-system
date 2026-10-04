# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# IAM Bastionless Roles & Scoped Backup Policy Module
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

variable "backup_bucket_arn" {
  description = "Central S3 Disaster Recovery Bucket ARN"
  type        = string
  default     = ""
}

# 1. EC2 Instance Role for SSM and AWS Services
resource "aws_iam_role" "ec2_ssm_role" {
  name = "cerms-ec2-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "cerms-ec2-ssm-role"
    Environment = "Production"
    Project     = "CERMS"
  }
}

# 2. Attach AmazonSSMManagedInstanceCore for SSH-less management
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# 3. Attach AmazonEC2ContainerRegistryReadOnly to pull images from ECR
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# 4. EC2 Instance Profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "cerms-ec2-instance-profile"
  role = aws_iam_role.ec2_ssm_role.name
}

# 5. S3 Central Backup Policy (Strict Tenant-B Prefix-Level Scoping: tenant-b-cerms/*)
resource "aws_iam_policy" "ec2_s3_backup_policy" {
  name        = "cerms-ec2-s3-backup-policy"
  description = "Strict least-privilege policy for CERMS database offsite backups scoped to tenant-b-cerms"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowTenantBPrefixOnly"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.backup_bucket_arn,
          "${var.backup_bucket_arn}/tenant-b-cerms/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_s3_backup_attach" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = aws_iam_policy.ec2_s3_backup_policy.arn
}

output "instance_profile_name" {
  description = "EC2 Instance Profile Name for SSM attachment"
  value       = aws_iam_instance_profile.ec2_profile.name
}
