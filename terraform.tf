# Terraform Configuration for edu-scraper on AWS EC2
# This file automatically creates all necessary AWS resources

terraform {
  required_version = ">= 1.0"
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

# Variables
variable "aws_region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  default     = "t3.small"
  # Options: t3.micro (smallest/cheapest), t3.small (recommended), t3.medium (best performance)
}

variable "instance_name" {
  description = "Name of the EC2 instance"
  default     = "edu-scraper"
}

variable "your_ip" {
  description = "Your IP address for SSH access (get from https://whatismyipaddress.com)"
  type        = string
}

# Get latest Ubuntu 22.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security Group
resource "aws_security_group" "edu_scraper" {
  name        = "edu-scraper-sg"
  description = "Security group for edu-scraper"

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${var.your_ip}/32"]
  }

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound (allow all)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "edu-scraper-sg"
  }
}

# Key Pair
resource "aws_key_pair" "edu_scraper" {
  key_name   = "edu-scraper-key"
  public_key = file("~/.ssh/id_rsa.pub")  # Use your existing SSH public key

  lifecycle {
    ignore_changes = [public_key]
  }

  tags = {
    Name = "edu-scraper-key"
  }
}

# EC2 Instance
resource "aws_instance" "edu_scraper" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name              = aws_key_pair.edu_scraper.key_name
  vpc_security_group_ids = [aws_security_group.edu_scraper.id]
  
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    delete_on_termination = true
    encrypted             = true
  }

  # Deploy script
  user_data = base64encode(templatefile("${path.module}/deploy.sh", {}))

  monitoring          = true
  iam_instance_profile = aws_iam_instance_profile.edu_scraper.name

  tags = {
    Name = var.instance_name
  }

  depends_on = [aws_security_group.edu_scraper]
}

# IAM Role for EC2 (CloudWatch logs, etc.)
resource "aws_iam_role" "edu_scraper" {
  name = "edu-scraper-role"

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
}

resource "aws_iam_role_policy_attachment" "ssm_access" {
  role       = aws_iam_role.edu_scraper.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "edu_scraper" {
  name = "edu-scraper-profile"
  role = aws_iam_role.edu_scraper.name
}

# Elastic IP (optional - useful for static IP)
resource "aws_eip" "edu_scraper" {
  instance = aws_instance.edu_scraper.id
  domain   = "vpc"

  tags = {
    Name = "edu-scraper-eip"
  }

  depends_on = [aws_instance.edu_scraper]
}

# CloudWatch Alarm for high CPU
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "edu-scraper-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"

  dimensions = {
    InstanceId = aws_instance.edu_scraper.id
  }

  alarm_description = "Alert when CPU exceeds 80%"
  alarm_actions     = []  # Add SNS topic if needed
}

# Outputs
output "instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.edu_scraper.id
}

output "public_ip" {
  description = "Public IP address of the instance"
  value       = aws_eip.edu_scraper.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to instance"
  value       = "ssh -i YOUR_KEY ubuntu@${aws_eip.edu_scraper.public_ip}"
}

output "app_url" {
  description = "URL to access the application"
  value       = "http://${aws_eip.edu_scraper.public_ip}"
}
