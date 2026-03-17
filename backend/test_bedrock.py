#!/usr/bin/env python3
"""Test AWS Bedrock connectivity and model access"""

import boto3
import json

def test_bedrock_access():
    print("Testing AWS Bedrock access...")
    print(f"Account: 624057415440")
    print(f"Region: us-west-2\n")
    
    try:
        # Initialize Bedrock client
        bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-west-2'
        )
        
        print("✓ Bedrock client initialized successfully")
        
        # Test with a simple prompt
        model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "Say 'Hello, Bedrock is working!' in exactly 5 words."
                }
            ],
            "temperature": 0.3
        })
        
        print(f"\nTesting model: {model_id}")
        print("Sending test request...")
        
        response = bedrock.invoke_model(
            modelId=model_id,
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        result = response_body['content'][0]['text']
        
        print(f"\n✓ SUCCESS! Bedrock response:")
        print(f"  {result}\n")
        print("=" * 60)
        print("AWS Bedrock is configured correctly!")
        print("You can now generate AI-powered digests.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        
        if "AccessDeniedException" in str(e):
            print("=" * 60)
            print("Model Access Not Enabled")
            print("=" * 60)
            print("\nTo enable Bedrock model access:")
            print("1. Go to: https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/modelaccess")
            print("2. Click 'Manage model access'")
            print("3. Enable 'Claude 3 Sonnet'")
            print("4. Click 'Save changes'")
            print("5. Wait for approval (usually instant)")
            print("\nThen run this test again.")
        
        return False

if __name__ == "__main__":
    test_bedrock_access()
