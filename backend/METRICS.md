# CloudWatch Metrics Documentation

## Overview

The Interest Definition Chatbot emits custom metrics to AWS CloudWatch for monitoring performance, reliability, and user engagement. Metrics are emitted asynchronously to avoid blocking request processing.

## Namespace

All metrics are published under the namespace: `LiteratureBoot/Chatbot`

## Common Dimensions

All metrics include these dimensions for filtering and aggregation:

- **Environment**: The deployment environment (development, staging, production)
- **Service**: Always set to "InterestDefinitionChatbot"
- **Operation**: The specific operation being measured (ChatbotResponse, DescriptionGeneration, ConversationCompletion)

## Metrics

### 1. ChatbotResponseTime

**Description**: Duration of chatbot response generation in milliseconds

**Unit**: Milliseconds

**Target**: < 5000ms (5 seconds)

**Dimensions**:
- Environment
- Service
- Operation: "ChatbotResponse"
- Status: "Success" or "Failure"

**Use Cases**:
- Monitor chatbot performance
- Identify slow responses
- Set alarms for p95 > 7000ms

### 2. ChatbotSuccess

**Description**: Count of successful chatbot responses

**Unit**: Count

**Target Success Rate**: > 95%

**Dimensions**:
- Environment
- Service
- Operation: "ChatbotResponse"

**Use Cases**:
- Calculate success rate (ChatbotSuccess / (ChatbotSuccess + ChatbotFailure))
- Monitor overall chatbot reliability
- Track user experience quality

### 3. ChatbotFailure

**Description**: Count of failed chatbot responses

**Unit**: Count

**Dimensions**:
- Environment
- Service
- Operation: "ChatbotResponse"
- ErrorType: "timeout", "bedrock_api_error", "unexpected_error"

**Use Cases**:
- Calculate failure rate
- Identify error patterns
- Set alarms for failure rate > 10%

### 4. ChatbotTimeout

**Description**: Count of chatbot responses that exceeded 5-second timeout

**Unit**: Count

**Dimensions**:
- Environment
- Service
- Operation: "ChatbotResponse"

**Use Cases**:
- Monitor timeout frequency
- Identify performance degradation
- Correlate with Bedrock API latency

### 5. DescriptionGenerationSuccess

**Description**: Count of successful comprehensive description generations

**Unit**: Count

**Target Success Rate**: > 95%

**Dimensions**:
- Environment
- Service
- Operation: "DescriptionGeneration"

**Use Cases**:
- Calculate description generation success rate
- Monitor feature reliability
- Track user journey completion

### 6. DescriptionGenerationFailure

**Description**: Count of failed description generations

**Unit**: Count

**Dimensions**:
- Environment
- Service
- Operation: "DescriptionGeneration"
- ErrorType: "bedrock_api_error", "unexpected_error", "empty_output"

**Use Cases**:
- Calculate failure rate
- Identify generation issues
- Set alarms for failure rate > 10%

### 7. ConversationCompletion

**Description**: Count of conversations successfully completed (description saved)

**Unit**: Count

**Dimensions**:
- Environment
- Service
- Operation: "ConversationCompletion"

**Use Cases**:
- Track user engagement
- Calculate conversation completion rate
- Measure feature adoption

### 8. BedrockAPIError

**Description**: Count of AWS Bedrock API errors

**Unit**: Count

**Target Error Rate**: < 5%

**Dimensions**:
- Environment
- Service
- Operation: "ChatbotResponse" or "DescriptionGeneration"
- ErrorCode: AWS error code (e.g., "ThrottlingException", "ServiceUnavailable")

**Use Cases**:
- Monitor Bedrock API health
- Identify rate limiting issues
- Track service dependencies
- Set alarms for error spikes

## CloudWatch Alarms

CloudWatch alarms are configured to proactively alert on performance and reliability issues. See [CLOUDWATCH_ALARMS.md](./CLOUDWATCH_ALARMS.md) for complete alarm configuration and deployment instructions.

### Configured Alarms

1. **High Response Time**
   - Metric: ChatbotResponseTime (p95)
   - Threshold: > 7000ms
   - Evaluation Periods: 2 of 3
   - Action: Alert on-call engineer

2. **High Error Rate**
   - Metric: ChatbotFailure / (ChatbotSuccess + ChatbotFailure)
   - Threshold: > 10%
   - Evaluation Periods: 2 of 3
   - Action: Alert on-call engineer

3. **Description Generation Failure Rate**
   - Metric: DescriptionGenerationFailure / (DescriptionGenerationSuccess + DescriptionGenerationFailure)
   - Threshold: > 10%
   - Evaluation Periods: 2 of 3
   - Action: Alert on-call engineer

4. **Bedrock API Error Spike**
   - Metric: BedrockAPIError (Sum)
   - Threshold: > 50 errors in 5 minutes
   - Evaluation Periods: 1 of 1
   - Action: Alert on-call engineer

### Deployment

Deploy alarms using CloudFormation:
```bash
aws cloudformation deploy \
  --template-file cloudwatch-alarms.yaml \
  --stack-name literature-boot-chatbot-alarms-prod \
  --parameter-overrides Environment=production AlarmEmail=alerts@example.com \
  --region us-west-2
```

Or use the Python script:
```bash
python setup_cloudwatch_alarms.py --environment production --email alerts@example.com
```

See [CLOUDWATCH_ALARMS.md](./CLOUDWATCH_ALARMS.md) for detailed deployment instructions and troubleshooting.

## Implementation Details

### Asynchronous Emission

Metrics are emitted asynchronously using a ThreadPoolExecutor to avoid blocking request processing:

```python
# Metrics are submitted to a thread pool
_metrics_executor.submit(
    self._emit_metric_sync,
    metric_name,
    value,
    unit,
    dimensions
)
```

This ensures that:
- Requests return quickly even if CloudWatch is slow
- CloudWatch failures don't break chatbot functionality
- Metrics don't impact user experience

### Error Handling

All metric emission is wrapped in try-except blocks:

```python
try:
    metrics.emit_chatbot_success(user_id, topic_id)
except Exception as e:
    logger.warning(f"Failed to emit metrics: {e}")
```

This ensures that:
- Metrics failures are logged but don't raise exceptions
- Chatbot continues to work even if CloudWatch is unavailable
- Users are not impacted by monitoring infrastructure issues

### Graceful Degradation

If CloudWatch is unavailable:
- Metrics emission fails silently
- Warnings are logged for debugging
- Chatbot functionality continues normally
- Structured logs still provide observability

## Monitoring Dashboard

### Key Metrics to Display

1. **Chatbot Performance**
   - Average response time (last hour)
   - p95 response time (last hour)
   - Success rate (last hour)
   - Timeout rate (last hour)

2. **Description Generation**
   - Success rate (last hour)
   - Average generation time
   - Failure rate by error type

3. **User Engagement**
   - Conversations started (last hour)
   - Conversations completed (last hour)
   - Completion rate

4. **Bedrock API Health**
   - Error rate by error code
   - Total API calls
   - Throttling events

### Sample CloudWatch Insights Queries

**Calculate Success Rate**:
```
fields @timestamp, ChatbotSuccess, ChatbotFailure
| stats sum(ChatbotSuccess) as successes, sum(ChatbotFailure) as failures
| fields (successes / (successes + failures)) * 100 as success_rate_percent
```

**Response Time Percentiles**:
```
fields @timestamp, ChatbotResponseTime
| filter Operation = "ChatbotResponse" and Status = "Success"
| stats avg(ChatbotResponseTime) as avg_ms, pct(ChatbotResponseTime, 50) as p50, pct(ChatbotResponseTime, 95) as p95, pct(ChatbotResponseTime, 99) as p99
```

**Error Distribution**:
```
fields @timestamp, ErrorType
| filter ChatbotFailure = 1
| stats count() by ErrorType
```

## Cost Considerations

CloudWatch custom metrics pricing (as of 2024):
- First 10,000 metrics: $0.30 per metric per month
- Additional metrics: $0.10 per metric per month
- API requests: $0.01 per 1,000 PutMetricData requests

Estimated monthly cost for 1,000 active users:
- ~8 unique metrics
- ~10,000 API calls per day
- Total: ~$2.40 + $3.00 = $5.40/month

## Testing

Metrics are tested at multiple levels:

1. **Unit Tests** (`test_metrics_service.py`):
   - Test each metric emission method
   - Test error handling
   - Test singleton pattern
   - Test dimensions and namespace

2. **Integration Tests** (`test_metrics_integration.py`):
   - Test metrics are emitted during chatbot operations
   - Test metrics don't block requests
   - Test graceful degradation on CloudWatch failures
   - Test correct parameters are passed

3. **Manual Testing**:
   - Verify metrics appear in CloudWatch console
   - Verify dimensions allow proper filtering
   - Verify alarms trigger correctly

## Troubleshooting

### Metrics Not Appearing in CloudWatch

1. Check IAM permissions - Lambda/EC2 role needs `cloudwatch:PutMetricData`
2. Check region - metrics are published to us-west-2
3. Check namespace - look under "LiteratureBoot/Chatbot"
4. Check logs for metric emission warnings

### High Metric Emission Failures

1. Check CloudWatch service health
2. Check IAM role permissions
3. Check network connectivity
4. Review CloudWatch API rate limits

### Metrics Delayed

- Metrics are emitted asynchronously with ThreadPoolExecutor
- CloudWatch can have up to 2-minute delay for metric visibility
- Check thread pool is not exhausted (max 2 workers)
