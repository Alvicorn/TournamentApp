# ── CloudWatch alarms ────────────────────────────────────────────────────────
# See docs/infra/operations.md#monitoring for alarm rationale.

# EC2 system status check (triggers EC2 auto-recovery action)
resource "aws_cloudwatch_metric_alarm" "redis_system_check" {
  alarm_name          = "redis-ec2-system-check"
  alarm_description   = "Redis EC2 system status check failed — triggers auto-recovery"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed_System"
  dimensions          = { InstanceId = aws_instance.redis.id }
  period              = 60
  evaluation_periods  = 2
  statistic           = "Maximum"
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"

  alarm_actions = [
    "arn:aws:automate:${var.aws_region}:ec2:recover",
    var.alarm_sns_topic_arn,
  ]

  ok_actions = [var.alarm_sns_topic_arn]
}

# EC2 instance status check (manual intervention needed)
resource "aws_cloudwatch_metric_alarm" "redis_instance_check" {
  alarm_name          = "redis-ec2-instance-check"
  alarm_description   = "Redis EC2 instance status check failed — manual intervention needed"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed_Instance"
  dimensions          = { InstanceId = aws_instance.redis.id }
  period              = 60
  evaluation_periods  = 2
  statistic           = "Maximum"
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"

  alarm_actions = [var.alarm_sns_topic_arn]
  ok_actions    = [var.alarm_sns_topic_arn]
}

# CPU credit balance (t4g.nano is burstable — running out = degraded perf)
resource "aws_cloudwatch_metric_alarm" "redis_cpu_credits" {
  alarm_name          = "redis-ec2-cpu-credits-low"
  alarm_description   = "Redis EC2 CPU credit balance < 20 — performance may degrade"
  namespace           = "AWS/EC2"
  metric_name         = "CPUCreditBalance"
  dimensions          = { InstanceId = aws_instance.redis.id }
  period              = 300
  evaluation_periods  = 1
  statistic           = "Average"
  threshold           = 20
  comparison_operator = "LessThanThreshold"

  alarm_actions = [var.alarm_sns_topic_arn]
  ok_actions    = [var.alarm_sns_topic_arn]
}

# ALB 5xx rate (backend errors surfaced at the load balancer)
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "alb-5xx-rate"
  alarm_description   = "ALB 5xx error rate > 5% over 5 minutes"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  dimensions          = { LoadBalancer = var.alb_arn_suffix }
  period              = 300
  evaluation_periods  = 1
  statistic           = "Sum"
  threshold           = 50
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [var.alarm_sns_topic_arn]
  ok_actions    = [var.alarm_sns_topic_arn]
}

# ECS unhealthy tasks (ALB target group health check failures)
resource "aws_cloudwatch_metric_alarm" "ecs_unhealthy_tasks" {
  alarm_name          = "ecs-unhealthy-tasks"
  alarm_description   = "ECS Fargate task health check failing — service may be down"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }
  period              = 60
  evaluation_periods  = 2
  statistic           = "Maximum"
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [var.alarm_sns_topic_arn]
  ok_actions    = [var.alarm_sns_topic_arn]
}

# Redis health check failures (custom metric emitted by FastAPI /health/redis)
resource "aws_cloudwatch_metric_alarm" "redis_health_check" {
  alarm_name          = "redis-health-check-failures"
  alarm_description   = "Redis health endpoint failed 3 consecutive times"
  namespace           = "TournamentApp"
  metric_name         = "RedisHealthCheckFailures"
  period              = 60
  evaluation_periods  = 3
  statistic           = "Sum"
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [var.alarm_sns_topic_arn]
  ok_actions    = [var.alarm_sns_topic_arn]
}
