# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# CloudWatch Monitoring & Incident Alerting Module
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

variable "alert_email" {
  description = "DevOps alert notification email address"
  type        = string
}

variable "production_instance_id" {
  description = "Production EC2 instance ID to monitor"
  type        = string
}

# 1. SNS Incident Alerting Topic
resource "aws_sns_topic" "devops_alerts" {
  name = "cerms-devops-alerts"

  tags = {
    Name        = "cerms-devops-alerts"
    Environment = "Production"
    Project     = "CERMS"
  }
}

# 2. Email Subscription
resource "aws_sns_topic_subscription" "email_alert" {
  topic_arn = aws_sns_topic.devops_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# 3. CloudWatch Alarm: High CPU Utilization (>= 85% for 10 mins)
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "cerms-production-high-cpu-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Triggered when Production EC2 CPU exceeds 85% for 10 consecutive minutes"
  alarm_actions       = [aws_sns_topic.devops_alerts.arn]

  dimensions = {
    InstanceId = var.production_instance_id
  }
}

# 4. CloudWatch Alarm: EC2 Status Check Failed
resource "aws_cloudwatch_metric_alarm" "instance_status_check" {
  alarm_name          = "cerms-production-instance-status-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "Triggered when Production EC2 instance or system status check fails"
  alarm_actions       = [aws_sns_topic.devops_alerts.arn]

  dimensions = {
    InstanceId = var.production_instance_id
  }
}

# Module Outputs
output "sns_topic_arn" {
  description = "ARN of the CERMS DevOps alerts SNS topic"
  value       = aws_sns_topic.devops_alerts.arn
}
