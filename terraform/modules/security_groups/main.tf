# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Zero-Trust Security Groups Module
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

variable "vpc_id" {
  description = "VPC ID from the vpc module"
  type        = string
}

resource "aws_security_group" "production" {
  name        = "cerms-production-sg"
  description = "Allow HTTP and HTTPS inbound traffic from edge, strictly block SSH, databases, and redis"
  vpc_id      = var.vpc_id

  # 1. Port 80 (HTTP)
  ingress {
    description = "HTTP Edge Ingress (CloudFront Origin / HTTP Redirect)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # 2. Port 443 (HTTPS)
  ingress {
    description = "HTTPS Edge Ingress (CloudFront / SSL Origin)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # NOTE: Ports 22 (SSH), 3306 (MariaDB), and 6379 (Redis) are completely BLOCKED from external ingress.
  # Administrative shell access is exclusively managed via AWS SSM Session Manager.

  # 3. Egress: Outbound internet access for S3 backup sync, OS patches, and SMS/Email APIs
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "cerms-production-sg"
    Environment = "Production"
    Project     = "CERMS"
  }
}

output "security_group_id" {
  description = "Security Group ID for CERMS instances"
  value       = aws_security_group.production.id
}
