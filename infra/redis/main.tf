terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Security group ──────────────────────────────────────────────────────────

resource "aws_security_group" "redis" {
  name        = "redis-sg"
  description = "Redis EC2: allow 6379 from App Runner VPC connector only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from App Runner"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.apprunner_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "redis-sg" }
}

# ── EC2 instance (ARM t4g.nano) ─────────────────────────────────────────────

data "aws_ami" "amazon_linux_arm" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }
}

resource "aws_iam_role" "redis_ec2" {
  name = "redis-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.redis_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "redis_ec2" {
  name = "redis-ec2-profile"
  role = aws_iam_role.redis_ec2.name
}

resource "aws_instance" "redis" {
  ami                    = data.aws_ami.amazon_linux_arm.id
  instance_type          = "t4g.nano"
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.redis.id]
  iam_instance_profile   = aws_iam_instance_profile.redis_ec2.name

  # EC2 auto-recovery: CloudWatch alarm (see cloudwatch.tf) triggers this action.
  maintenance_options {
    auto_recovery = "default"
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    redis_password = var.redis_password
  })

  tags = { Name = "redis-host" }
}

# Elastic IP so App Runner's REDIS_URL doesn't change if instance is replaced
resource "aws_eip" "redis" {
  instance = aws_instance.redis.id
  domain   = "vpc"
  tags     = { Name = "redis-eip" }
}
