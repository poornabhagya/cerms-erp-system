# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# EC2 Compute Provisioning Module (Production & Staging Nodes)
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

variable "production_subnet_id" { type = string }
variable "staging_subnet_id" { type = string }
variable "security_group_id" { type = string }
variable "instance_profile_name" { type = string }

# 1. Fetch latest Ubuntu 22.04 LTS (AMD64 / Free Tier Eligible)
data "aws_ami" "ubuntu_amd64" {
  most_recent = true
  owners      = ["099720109477"] # Canonical official AWS account

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# 2. Production EC2 Node (10.10.1.0/24 Subnet in ap-south-1a)
resource "aws_instance" "production" {
  ami                    = data.aws_ami.ubuntu_amd64.id
  instance_type          = "t3.micro"
  subnet_id              = var.production_subnet_id
  vpc_security_group_ids = [var.security_group_id]
  iam_instance_profile   = var.instance_profile_name
  user_data              = file("${path.module}/../../templates/user_data.sh.tpl")

  root_block_device {
    volume_type = "gp3"
    volume_size = 15
  }

  tags = {
    Name        = "cerms-production-node"
    Environment = "Production"
    Project     = "CERMS"
  }
}

# 3. Static Elastic IP (EIP) for Production Node
resource "aws_eip" "production_eip" {
  instance = aws_instance.production.id
  domain   = "vpc"

  tags = {
    Name        = "cerms-production-eip"
    Environment = "Production"
    Project     = "CERMS"
  }
}

# 4. Staging EC2 Node (10.10.2.0/24 Subnet in ap-south-1b)
resource "aws_instance" "staging" {
  ami                    = data.aws_ami.ubuntu_amd64.id
  instance_type          = "t3.micro"
  subnet_id              = var.staging_subnet_id
  vpc_security_group_ids = [var.security_group_id]
  iam_instance_profile   = var.instance_profile_name
  user_data              = file("${path.module}/../../templates/user_data.sh.tpl")

  root_block_device {
    volume_type = "gp3"
    volume_size = 15
  }

  tags = {
    Name        = "cerms-staging-node"
    Environment = "Staging"
    Project     = "CERMS"
  }
}

# Module Outputs
output "production_eip" {
  description = "Public Elastic IP assigned to Production EC2 Node"
  value       = aws_eip.production_eip.public_ip
}

output "production_instance_id" {
  description = "Instance ID of Production EC2 Node"
  value       = aws_instance.production.id
}

output "staging_instance_id" {
  description = "Instance ID of Staging EC2 Node"
  value       = aws_instance.staging.id
}
