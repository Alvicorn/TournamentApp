variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "vpc_id" {
  description = "VPC that the Redis EC2 and App Runner VPC connector will live in"
  type        = string
}

variable "subnet_id" {
  description = "Private subnet ID for the Redis EC2"
  type        = string
}

variable "apprunner_security_group_id" {
  description = "Security group attached to the App Runner VPC connector"
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
