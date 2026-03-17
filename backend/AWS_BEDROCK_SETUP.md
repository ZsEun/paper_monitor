# AWS Bedrock Setup Instructions

The Academic Journal Monitor now uses AWS Bedrock for AI-powered features:
- **AI-generated summaries**: Each paper gets a concise 100-word summary
- **AI topic extraction**: Topics are automatically extracted from paper content

## Prerequisites

1. **AWS Account** with Bedrock access
2. **Bedrock Model Access**: You need to enable Claude 3 Sonnet model in your AWS account

## Setup Steps

### Option 1: Use AWS CLI (Recommended)

1. Install AWS CLI if you haven't already:
   ```bash
   brew install awscli  # macOS
   ```

2. Configure AWS credentials:
   ```bash
   aws configure
   ```
   
   Enter your:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., `us-east-1`)
   - Default output format (e.g., `json`)

3. Enable Bedrock Model Access:
   - Go to AWS Console → Bedrock → Model access
   - Request access to "Claude 3 Sonnet" model
   - Wait for approval (usually instant)

### Option 2: Use Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your AWS credentials:
   ```
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   ```

3. Install python-dotenv:
   ```bash
   pip install python-dotenv
   ```

4. Update `app/services/ai_service.py` to load from .env

## Testing

After setup, generate a new digest:
1. Go to Dashboard
2. Click "Generate New Digest"
3. The system will:
   - Scrape papers from IEEE Xplore
   - Generate AI summaries for each paper (this may take 1-2 minutes)
   - Extract topics using AI
   - Create the digest

## Cost Considerations

- AWS Bedrock charges per API call
- Claude 3 Sonnet: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
- For 20 papers with summaries: approximately $0.10-0.20 per digest
- Monitor your AWS costs in the AWS Console

## Troubleshooting

### Error: "Could not connect to Bedrock"
- Check your AWS credentials are configured correctly
- Verify your AWS region supports Bedrock (us-east-1, us-west-2, etc.)
- Ensure you have Bedrock permissions in your IAM policy

### Error: "Model access denied"
- Go to AWS Console → Bedrock → Model access
- Request access to Claude 3 Sonnet model
- Wait for approval

### Fallback Mode
If AI fails, the system automatically falls back to:
- Using the original abstract as the summary
- Using rule-based topic classification

## Disable AI Features

To disable AI and use rule-based classification only:

Edit `app/scrapers/monitor.py`:
```python
self.use_ai = False  # Change to False
```
