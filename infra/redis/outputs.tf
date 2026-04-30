output "redis_private_ip" {
  description = "Private IP of the Redis EC2 — use in REDIS_URL for the Fargate task definition"
  value       = aws_instance.redis.private_ip
}

output "redis_eip" {
  description = "Elastic IP (public) — not used for intra-VPC traffic; listed for debugging"
  value       = aws_eip.redis.public_ip
}

output "redis_security_group_id" {
  description = "Redis security group ID — reference when configuring Fargate task SG egress rules"
  value       = aws_security_group.redis.id
}
