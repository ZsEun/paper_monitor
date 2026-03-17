"""Direct Bedrock connectivity and message format test."""
import os
import json
import sys

# Load .env
from dotenv import load_dotenv
load_dotenv()

import boto3
from botocore.config import Config

MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")

def test_basic_bedrock_call():
    """Test 1: Basic single-message call to Bedrock."""
    print("=" * 60)
    print("TEST 1: Basic Bedrock connectivity")
    print("=" * 60)
    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=REGION,
            config=Config(read_timeout=10, retries={"max_attempts": 1}),
        )
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Say hello in one sentence."}],
        })
        resp = client.invoke_model(modelId=MODEL_ID, body=body)
        result = json.loads(resp["body"].read())
        print(f"  OK: {result['content'][0]['text'][:120]}")
        return True
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        return False

def test_multi_turn_conversation():
    """Test 2: Multi-turn conversation (simulates chatbot flow)."""
    print("\n" + "=" * 60)
    print("TEST 2: Multi-turn conversation (user -> assistant -> user)")
    print("=" * 60)
    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=REGION,
            config=Config(read_timeout=10, retries={"max_attempts": 1}),
        )
        messages = [
            {"role": "user", "content": "I want to define my research interest. The topic is: desense"},
            {"role": "assistant", "content": "Thank you for providing your initial research interest topic on desense. What specific aspects are you interested in?"},
            {"role": "user", "content": "I am interested in the biological mechanisms and clinical manifestations."},
        ]
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "system": "You are a research interest definition assistant.",
            "messages": messages,
        })
        print(f"  Sending {len(messages)} messages...")
        resp = client.invoke_model(modelId=MODEL_ID, body=body)
        result = json.loads(resp["body"].read())
        print(f"  OK: {result['content'][0]['text'][:200]}")
        return True
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        return False

def test_chatbot_service_flow():
    """Test 3: Full ChatbotService send_message flow (the actual code path)."""
    print("\n" + "=" * 60)
    print("TEST 3: ChatbotService.send_message() — real code path")
    print("=" * 60)
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from app.services.chatbot_service import ChatbotService
        from app.models.schemas import Message
        svc = ChatbotService()
        print(f"  Mock mode: {svc.mock_mode}")
        print(f"  Model ID: {svc.model_id}")

        # Step A: Initial empty message (like the frontend sends)
        print("\n  Step A: Initial empty message (greeting trigger)...")
        resp1 = svc.send_message(
            user_message="",
            conversation_history=[],
            topic_text="desense",
            user_id="test-user",
            topic_id="test-topic",
        )
        print(f"  Response: {resp1.message[:150]}...")
        print(f"  Status: {resp1.conversationStatus}")

        # Step B: Second message with history = [assistant greeting only]
        # (This is the scenario that was failing)
        history_after_first = [
            Message(role="assistant", content=resp1.message, timestamp="2026-01-01T00:00:00Z"),
        ]
        print("\n  Step B: User reply with history=[assistant] (the failing scenario)...")
        resp2 = svc.send_message(
            user_message="I am interested in biological mechanisms and clinical manifestations.",
            conversation_history=history_after_first,
            topic_text="desense",
            user_id="test-user",
            topic_id="test-topic",
        )
        print(f"  Response: {resp2.message[:150]}...")
        print(f"  Status: {resp2.conversationStatus}")
        return True
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    r1 = test_basic_bedrock_call()
    r2 = test_multi_turn_conversation()
    r3 = test_chatbot_service_flow()
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Test 1 (Basic Bedrock):     {'PASS' if r1 else 'FAIL'}")
    print(f"  Test 2 (Multi-turn):        {'PASS' if r2 else 'FAIL'}")
    print(f"  Test 3 (ChatbotService):    {'PASS' if r3 else 'FAIL'}")
    sys.exit(0 if all([r1, r2, r3]) else 1)
