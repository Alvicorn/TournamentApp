variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "vpc_id" {
  description = "VPC that the Redis EC2 and Fargate tasks share"
  type        = string
}

variable "subnet_id" {
  description = "Private subnet ID for the Redis EC2"
  type        = string
}

variable "fargate_task_security_group_id" {
  description = "Security group auto-created by ECS Express Mode for Fargate tasks"
  type        = string
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix provisioned by ECS Express Mode (portion after 'loadbalancer/', e.g. 'app/tourney-api/abc123')"
  type        = string
}

variable "target_group_arn_suffix" {
  description = "Target group ARN suffix provisioned by ECS Express Mode (portion after 'targetgroup/', e.g. 'targetgroup/tourney-api/abc123')"
  type        = string
}

variable "redis_password" {
  description = "Redis requirepass value — keep in AWS Secrets Manager or SSM"
  type        = string
  sensitive   = true
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarm notifications"
  type        = string
}
