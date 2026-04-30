output "redis_private_ip" {
  description = "Private IP of the Redis EC2 — use in REDIS_URL for App Runner"
  value       = aws_instance.redis.private_ip
}

output "redis_eip" {
  description = "Elastic IP (public) — not used for App Runner; listed for debugging"
  value       = aws_eip.redis.public_ip
}

output "redis_security_group_id" {
  description = "Redis security group ID — reference in App Runner VPC connector SG egress rule"
  value       = aws_security_group.redis.id
}
