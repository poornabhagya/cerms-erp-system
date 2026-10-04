# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Dedicated Tenant VPC & Subnets Module
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

# 1. Primary Dedicated Tenant VPC (10.10.0.0/16)
resource "aws_vpc" "main" {
  cidr_block           = "10.10.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "cerms-dedicated-vpc"
    Environment = "Production"
    Project     = "CERMS"
  }
}

# 2. Production Subnet (10.10.1.0/24 in ap-south-1a)
resource "aws_subnet" "production" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.10.1.0/24"
  availability_zone       = "ap-south-1a"
  map_public_ip_on_launch = true

  tags = {
    Name        = "cerms-production-subnet"
    Environment = "Production"
    Project     = "CERMS"
  }
}

# 3. Staging Subnet (10.10.2.0/24 in ap-south-1b)
resource "aws_subnet" "staging" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.10.2.0/24"
  availability_zone       = "ap-south-1b"
  map_public_ip_on_launch = true

  tags = {
    Name        = "cerms-staging-subnet"
    Environment = "Staging"
    Project     = "CERMS"
  }
}

# 4. Internet Gateway (IGW)
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "cerms-igw"
    Environment = "Production"
    Project     = "CERMS"
  }
}

# 5. Public Route Table (0.0.0.0/0 -> IGW)
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name        = "cerms-public-route-table"
    Environment = "Production"
    Project     = "CERMS"
  }
}

# 6. Route Table Associations
resource "aws_route_table_association" "prod_assoc" {
  subnet_id      = aws_subnet.production.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "staging_assoc" {
  subnet_id      = aws_subnet.staging.id
  route_table_id = aws_route_table.public.id
}

# --- Module Outputs ---
output "vpc_id" {
  description = "The ID of the CERMS Dedicated VPC"
  value       = aws_vpc.main.id
}

output "production_subnet_id" {
  description = "The ID of the Production Subnet (10.10.1.0/24)"
  value       = aws_subnet.production.id
}

output "staging_subnet_id" {
  description = "The ID of the Staging Subnet (10.10.2.0/24)"
  value       = aws_subnet.staging.id
}
