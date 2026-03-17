# CloudWatch Alarms Configuration

## Overview

This document describes the CloudWatch alarms configured for monitoring the Interest Definition Chatbot. These alarms provide proactive alerting for performance degradation, high error rates, and service dependency issues.

## Alarm Summary

| Alarm | Metric | Threshold | Evaluation | Purpose |
|-------|--------|-----------|------------|---------|
| High Response Time | ChatbotResponseTime (p95) | > 7 seconds | 2 of 3 periods | Detect slow chatbot responses |
| High Error Rate | ChatbotFailure / Total | > 10% | 2 of 3 periods | Detect chatbot reliability issues |
| Description Generation Failure | DescriptionGenerationFailure / Total | > 10% | 2 of 3 periods | Detect description generation problems |
| Bedrock API Error Spike | BedrockAPIError (Sum) | > 50 in 5 min | 1 of 1 period | Detect AWS Bedrock service issues |

## Deployment Options

### Option 1: CloudFormation Template (Recommended)

Use the provided CloudFormation template for infrastructure-as-code deployment:

```bash
# Deploy alarms with email notifications
aws cloudformation deploy \
  --template-file cloudwatch-alarms.yaml \
  --stack-name literature-boot-chatbot-alarms-prod \
  --parameter-overrides \
    Environment=production \
    AlarmEmail=alerts@example.com \
  --region us-west-2

# Deploy alarms with existing SNS topic
aws cloudformation deploy \
  --template-file cloudwatch-alarms.yaml \
  --stack-name literature-boot-chatbot-alarms-prod \
  --parameter-overrides \
    Environment=production \
    AlarmSNSTopicArn=arn:aws:sns:us-west-2:123456789012:my-topic \
  --region us-west-2

# Delete alarms
aws cloudformation delete-stack \
  --stack-name literature-boot-chatbot-alarms-prod \
  --region us-west-2
```

### Option 2: Python Script

Use the Python script for programmatic alarm creation:

```bash
# Install boto3 if not already installed
pip install boto3

# Create alarms with email notifications
python setup_cloudwatch_alarms.py \
  --environment production \
  --email alerts@example.com \
  --region us-west-2

# Create alarms with existing SNS topic
python setup_cloudwatch_alarms.py \
  --environment production \
  --sns-topic-arn arn:aws:sns:us-west-2:123456789012:my-topic \
  --region us-west-2

# Delete alarms
python setup_cloudwatch_alarms.py \
  --environment production \
  --delete \
  --region us-west-2
```

### Option 3: AWS Console

Manually create alarms through the AWS CloudWatch console:

1. Navigate to CloudWatch > Alarms > Create Alarm
2. Select metric from namespace `LiteratureBoot/Chatbot`
3. Configure threshold and evaluation periods as specified below
4. Add SNS topic for notifications
5. Repeat for each alarm

## Alarm Details

### 1. High Response Time Alarm

**Purpose**: Alert when chatbot responses are taking too long, indicating performance degradation.

**Configuration**:
- **Metric**: ChatbotResponseTime
- **Statistic**: p95 (95th percentile)
- **Threshold**: > 7000 milliseconds (7 seconds)
- **Period**: 5 minutes
- **Evaluation**: 2 out of 3 periods
- **Dimensions**:
  - Environment: production/staging/development
  - Service: InterestDefinitionChatbot
  - Operation: ChatbotResponse
  - Status: Success

**Rationale**:
- Target response time is 5 seconds (Requirement 8.1)
- Alarm threshold is 7 seconds to allow some buffer
- p95 statistic catches performance issues affecting most users
- 2 of 3 evaluation periods reduces false positives from transient spikes

**Response Actions**:
1. Check AWS Bedrock API latency in CloudWatch
2. Review chatbot service logs for slow operations
3. Check if Bedrock model is experiencing issues
4. Consider increasing timeout or optimizing prompts

### 2. High Error Rate Alarm

**Purpose**: Alert when chatbot error rate exceeds acceptable threshold, indicating reliability issues.

**Configuration**:
- **Metric Math**: `(ChatbotFailure / (ChatbotSuccess + ChatbotFailure)) * 100`
- **Threshold**: > 10%
- **Period**: 5 minutes
- **Evaluation**: 2 out of 3 periods
- **Dimensions**:
  - Environment: production/staging/development
  - Service: InterestDefinitionChatbot
  - Operation: ChatbotResponse

**Rationale**:
- Target success rate is > 95% (5% error rate)
- Alarm threshold is 10% to focus on significant issues
- Metric math calculates percentage automatically
- 2 of 3 evaluation periods reduces false positives

**Response Actions**:
1. Check ChatbotFailure metric dimensions for ErrorType breakdown
2. Review application logs for error patterns
3. Check AWS Bedrock service health
4. Verify IAM permissions and network connectivity
5. Check if rate limiting is occurring

### 3. Description Generation Failure Rate Alarm

**Purpose**: Alert when description generation is failing frequently, indicating issues with the final step of the chatbot flow.

**Configuration**:
- **Metric Math**: `(DescriptionGenerationFailure / (DescriptionGenerationSuccess + DescriptionGenerationFailure)) * 100`
- **Threshold**: > 10%
- **Period**: 5 minutes
- **Evaluation**: 2 out of 3 periods
- **Dimensions**:
  - Environment: production/staging/development
  - Service: InterestDefinitionChatbot
  - Operation: DescriptionGeneration

**Rationale**:
- Target success rate is > 95%
- Alarm threshold is 10% to focus on significant issues
- Description generation is critical for feature value
- 2 of 3 evaluation periods reduces false positives

**Response Actions**:
1. Check DescriptionGenerationFailure metric for ErrorType breakdown
2. Review conversation histories that failed to generate descriptions
3. Check if Bedrock API is returning malformed responses
4. Verify prompt engineering for description generation
5. Check for conversation history size limits

### 4. Bedrock API Error Spike Alarm

**Purpose**: Alert when AWS Bedrock API errors spike suddenly, indicating service dependency issues.

**Configuration**:
- **Metric**: BedrockAPIError
- **Statistic**: Sum
- **Threshold**: > 50 errors in 5 minutes
- **Period**: 5 minutes
- **Evaluation**: 1 out of 1 period
- **Dimensions**:
  - Environment: production/staging/development
  - Service: InterestDefinitionChatbot

**Rationale**:
- Target error rate is < 5%
- Spike detection requires immediate alerting (1 of 1 period)
- 50 errors in 5 minutes indicates significant service issue
- Bedrock is critical dependency - failures impact all chatbot operations

**Response Actions**:
1. Check AWS Bedrock service health dashboard
2. Review BedrockAPIError metric for ErrorCode breakdown
3. Check for ThrottlingException (rate limiting)
4. Verify IAM role permissions
5. Check AWS service quotas and limits
6. Consider implementing exponential backoff or circuit breaker

## SNS Topic Configuration

### Email Notifications

When using email notifications:
1. SNS sends a confirmation email to the specified address
2. You must click the confirmation link to activate notifications
3. Unsubscribe link is included in all alarm emails

### Topic Naming

- Development: `literature-boot-chatbot-alarms-development`
- Staging: `literature-boot-chatbot-alarms-staging`
- Production: `literature-boot-chatbot-alarms-production`

### Integration Options

SNS topics can integrate with:
- Email
- SMS
- AWS Lambda functions
- Amazon SQS queues
- PagerDuty (via HTTPS endpoint)
- Slack (via AWS Chatbot)
- Microsoft Teams (via AWS Chatbot)

## IAM Permissions Required

### For Alarm Creation

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:DeleteAlarms"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:CreateTopic",
        "sns:Subscribe",
        "sns:GetTopicAttributes"
      ],
      "Resource": "arn:aws:sns:*:*:literature-boot-chatbot-alarms-*"
    }
  ]
}
```

### For Metric Emission (Application)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "LiteratureBoot/Chatbot"
        }
      }
    }
  ]
}
```

## Testing Alarms

### Manual Testing

Trigger alarms manually to verify configuration:

```python
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')

# Emit high response time to trigger alarm
for i in range(10):
    cloudwatch.put_metric_data(
        Namespace='LiteratureBoot/Chatbot',
        MetricData=[
            {
                'MetricName': 'ChatbotResponseTime',
                'Value': 8000.0,  # 8 seconds - above threshold
                'Unit': 'Milliseconds',
                'Timestamp': datetime.utcnow(),
                'Dimensions': [
                    {'Name': 'Environment', 'Value': 'development'},
                    {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'},
                    {'Name': 'Operation', 'Value': 'ChatbotResponse'},
                    {'Name': 'Status', 'Value': 'Success'}
                ]
            }
        ]
    )

# Emit high error rate to trigger alarm
for i in range(20):
    cloudwatch.put_metric_data(
        Namespace='LiteratureBoot/Chatbot',
        MetricData=[
            {
                'MetricName': 'ChatbotFailure',
                'Value': 1,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow(),
                'Dimensions': [
                    {'Name': 'Environment', 'Value': 'development'},
                    {'Name': 'Service', 'Value': 'InterestDefinitionChatbot'},
                    {'Name': 'Operation', 'Value': 'ChatbotResponse'}
                ]
            }
        ]
    )
```

### Alarm State Verification

Check alarm states:

```bash
# List all chatbot alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix LiteratureBoot-Chatbot- \
  --region us-west-2

# Check specific alarm state
aws cloudwatch describe-alarms \
  --alarm-names LiteratureBoot-Chatbot-HighResponseTime-production \
  --region us-west-2
```

## Monitoring Best Practices

### 1. Alarm Tuning

After deployment, monitor alarm behavior:
- Track false positive rate (alarms that don't indicate real issues)
- Adjust thresholds if alarms are too sensitive or not sensitive enough
- Review evaluation periods if alarms trigger too quickly or slowly

### 2. Alarm Actions

Configure appropriate actions for each environment:
- **Development**: Log to SNS, no paging
- **Staging**: Email notifications to team
- **Production**: Page on-call engineer, email team, create incident ticket

### 3. Alarm Documentation

Document runbooks for each alarm:
- What the alarm indicates
- How to investigate the issue
- Common causes and solutions
- Escalation procedures

### 4. Regular Review

Review alarm effectiveness quarterly:
- Are alarms catching real issues?
- Are thresholds still appropriate?
- Are there new metrics that should be alarmed?
- Are there alarms that never trigger (too conservative)?

## Cost Optimization

### Alarm Costs

CloudWatch alarm pricing (as of 2024):
- Standard alarms: $0.10 per alarm per month
- Alarms with metric math: $0.30 per alarm per month
- This configuration: 4 alarms = $1.00/month (1 standard + 3 metric math)

### Reducing Costs

If cost is a concern:
- Use composite alarms to combine multiple conditions
- Increase evaluation periods to reduce alarm state changes
- Use anomaly detection alarms instead of static thresholds
- Share SNS topics across multiple services

## Troubleshooting

### Alarm Not Triggering

1. **Check metric data**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace LiteratureBoot/Chatbot \
     --metric-name ChatbotResponseTime \
     --dimensions Name=Environment,Value=production \
     --start-time 2024-01-01T00:00:00Z \
     --end-time 2024-01-01T23:59:59Z \
     --period 300 \
     --statistics Average \
     --region us-west-2
   ```

2. **Verify alarm configuration**:
   - Check dimensions match metric dimensions exactly
   - Verify threshold and comparison operator
   - Check evaluation periods and datapoints to alarm

3. **Check alarm state**:
   ```bash
   aws cloudwatch describe-alarm-history \
     --alarm-name LiteratureBoot-Chatbot-HighResponseTime-production \
     --region us-west-2
   ```

### Alarm Triggering Too Often

1. **Review metric data** to understand actual values
2. **Adjust threshold** if current value is too sensitive
3. **Increase evaluation periods** to require sustained issues
4. **Check for data anomalies** that might be skewing statistics

### SNS Notifications Not Received

1. **Check email subscription** is confirmed (check spam folder)
2. **Verify SNS topic** has active subscriptions:
   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn arn:aws:sns:us-west-2:123456789012:literature-boot-chatbot-alarms-production \
     --region us-west-2
   ```
3. **Check SNS delivery logs** in CloudWatch Logs

## Integration with Incident Management

### PagerDuty Integration

1. Create PagerDuty integration in AWS:
   ```bash
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-west-2:123456789012:literature-boot-chatbot-alarms-production \
     --protocol https \
     --notification-endpoint https://events.pagerduty.com/integration/YOUR_KEY/enqueue \
     --region us-west-2
   ```

2. Configure PagerDuty service with AWS CloudWatch integration
3. Map alarm severity to PagerDuty urgency levels

### Slack Integration

1. Set up AWS Chatbot in AWS Console
2. Connect to Slack workspace
3. Configure SNS topic to send to Slack channel
4. Customize notification format

## Maintenance

### Regular Tasks

- **Weekly**: Review alarm states and false positive rate
- **Monthly**: Analyze alarm effectiveness and adjust thresholds
- **Quarterly**: Review alarm coverage and add new alarms as needed
- **Annually**: Audit alarm costs and optimize configuration

### Alarm Updates

When updating alarms:
1. Test changes in development environment first
2. Deploy to staging and verify behavior
3. Deploy to production during low-traffic period
4. Monitor for 24 hours after changes

## Related Documentation

- [METRICS.md](./METRICS.md) - CloudWatch metrics documentation
- [METRICS_SUMMARY.md](./METRICS_SUMMARY.md) - Metrics implementation summary
- [AWS CloudWatch Alarms Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)

## Support

For issues with alarms:
1. Check CloudWatch Logs for metric emission errors
2. Verify IAM permissions for CloudWatch and SNS
3. Review alarm history in CloudWatch console
4. Contact AWS Support for Bedrock API issues
