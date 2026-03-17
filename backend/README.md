# Academic Journal Monitor - Backend API

FastAPI backend for the Academic Journal Monitor application.

## Setup

1. Create virtual environment and install dependencies
2. Run the server with uvicorn

## Running the Server

The API runs on http://127.0.0.1:8000

## API Endpoints

- POST /api/auth/register - Register new user
- POST /api/auth/login - Login user
- GET /api/journals - Get all journals
- POST /api/journals - Add new journal
- GET /api/digests - Get all digests

## Monitoring and Alarms

### CloudWatch Metrics

The Interest Definition Chatbot emits custom metrics to AWS CloudWatch for monitoring performance and reliability. See [METRICS.md](./METRICS.md) for complete metrics documentation.

### CloudWatch Alarms

CloudWatch alarms are configured to alert on:
- High chatbot response time (p95 > 7 seconds)
- High error rate (> 10%)
- Description generation failure rate (> 10%)
- Bedrock API error spikes (> 50 errors in 5 minutes)

See [CLOUDWATCH_ALARMS.md](./CLOUDWATCH_ALARMS.md) for complete alarm configuration and deployment instructions.

#### Quick Deployment

**Using CloudFormation**:
```bash
aws cloudformation deploy \
  --template-file cloudwatch-alarms.yaml \
  --stack-name literature-boot-chatbot-alarms-prod \
  --parameter-overrides Environment=production AlarmEmail=alerts@example.com \
  --region us-west-2
```

**Using Python Script**:
```bash
python setup_cloudwatch_alarms.py --environment production --email alerts@example.com
```

**Using AWS CDK**:
```bash
# Add to your CDK app
from cloudwatch_alarms_cdk import ChatbotAlarmsStack

ChatbotAlarmsStack(app, "ChatbotAlarms",
    environment="production",
    alarm_email="alerts@example.com"
)
```
