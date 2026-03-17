# CloudWatch Alarms Setup Guide

Quick reference for deploying CloudWatch alarms for the Interest Definition Chatbot.

## Prerequisites

- AWS CLI configured with appropriate credentials
- IAM permissions for CloudWatch and SNS
- Email address for alarm notifications (optional)

## Quick Start

### 1. Choose Your Deployment Method

**CloudFormation (Recommended)** - Infrastructure as code, easy rollback
**Python Script** - Programmatic, flexible, good for automation
**AWS CDK** - TypeScript/Python, integrates with existing CDK apps

### 2. Deploy Alarms

#### CloudFormation

```bash
# Production with email notifications
aws cloudformation deploy \
  --template-file cloudwatch-alarms.yaml \
  --stack-name literature-boot-chatbot-alarms-prod \
  --parameter-overrides \
    Environment=production \
    AlarmEmail=your-email@example.com \
  --region us-west-2

# Staging environment
aws cloudformation deploy \
  --template-file cloudwatch-alarms.yaml \
  --stack-name literature-boot-chatbot-alarms-staging \
  --parameter-overrides \
    Environment=staging \
    AlarmEmail=team@example.com \
  --region us-west-2
```

#### Python Script

```bash
# Install dependencies
pip install boto3

# Production
python setup_cloudwatch_alarms.py \
  --environment production \
  --email your-email@example.com \
  --region us-west-2

# Staging
python setup_cloudwatch_alarms.py \
  --environment staging \
  --email team@example.com \
  --region us-west-2
```

### 3. Confirm Email Subscription

1. Check your email inbox for "AWS Notification - Subscription Confirmation"
2. Click the "Confirm subscription" link
3. You'll receive alarm notifications once confirmed

### 4. Verify Alarms

```bash
# List all alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix LiteratureBoot-Chatbot- \
  --region us-west-2

# Check specific alarm
aws cloudwatch describe-alarms \
  --alarm-names LiteratureBoot-Chatbot-HighResponseTime-production \
  --region us-west-2
```

## Alarm Summary

| Alarm | Triggers When | Action Required |
|-------|---------------|-----------------|
| **High Response Time** | p95 > 7 seconds | Check Bedrock API latency, optimize prompts |
| **High Error Rate** | Error rate > 10% | Review logs, check Bedrock health |
| **Description Failure Rate** | Failure rate > 10% | Check conversation histories, verify prompts |
| **Bedrock API Error Spike** | > 50 errors in 5 min | Check Bedrock service health, verify IAM |

## Updating Alarms

### CloudFormation

```bash
# Update stack with new parameters
aws cloudformation deploy \
  --template-file cloudwatch-alarms.yaml \
  --stack-name literature-boot-chatbot-alarms-prod \
  --parameter-overrides Environment=production \
  --region us-west-2
```

### Python Script

```bash
# Delete old alarms
python setup_cloudwatch_alarms.py \
  --environment production \
  --delete \
  --region us-west-2

# Create new alarms
python setup_cloudwatch_alarms.py \
  --environment production \
  --email your-email@example.com \
  --region us-west-2
```

## Deleting Alarms

### CloudFormation

```bash
aws cloudformation delete-stack \
  --stack-name literature-boot-chatbot-alarms-prod \
  --region us-west-2
```

### Python Script

```bash
python setup_cloudwatch_alarms.py \
  --environment production \
  --delete \
  --region us-west-2
```

## Testing Alarms

### Manual Test (Development Only)

```python
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')

# Trigger high response time alarm
for i in range(10):
    cloudwatch.put_metric_data(
        Namespace='LiteratureBoot/Chatbot',
        MetricData=[{
            'MetricName': 'ChatbotResponseTime',
            'Value': 8000.0,  # Above 7000ms threshold
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow(),
            'Dimensions': [
                {'Name': 'Environment', 'Value': 'development'},
                {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'},
                {'Name': 'Operation', 'Value': 'ChatbotResponse'},
                {'Name': 'Status', 'Value': 'Success'}
            ]
        }]
    )
```

Wait 5-10 minutes for alarm to evaluate and trigger.

## Troubleshooting

### Alarms Not Created

1. Check AWS CLI credentials: `aws sts get-caller-identity`
2. Verify IAM permissions for CloudWatch and SNS
3. Check CloudFormation stack events for errors

### Email Notifications Not Received

1. Check spam/junk folder
2. Verify email subscription is confirmed
3. Check SNS topic subscriptions:
   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn <your-topic-arn> \
     --region us-west-2
   ```

### Alarms Not Triggering

1. Verify metrics are being emitted:
   ```bash
   aws cloudwatch list-metrics \
     --namespace LiteratureBoot/Chatbot \
     --region us-west-2
   ```

2. Check metric data:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace LiteratureBoot/Chatbot \
     --metric-name ChatbotResponseTime \
     --dimensions Name=Environment,Value=production \
     --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average \
     --region us-west-2
   ```

3. Review alarm configuration and thresholds

## Cost Estimate

- 4 CloudWatch alarms: ~$1.00/month
- SNS email notifications: Free (first 1,000 emails/month)
- Total: ~$1.00/month

## Next Steps

1. Deploy alarms to development environment first
2. Test alarm triggering with simulated metrics
3. Deploy to staging and production
4. Set up PagerDuty or Slack integration (optional)
5. Create runbooks for alarm response procedures

## Related Documentation

- [CLOUDWATCH_ALARMS.md](./CLOUDWATCH_ALARMS.md) - Complete alarm documentation
- [METRICS.md](./METRICS.md) - CloudWatch metrics documentation
- [AWS CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
