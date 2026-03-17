"""
End-to-End Error Scenario Tests

Tests error handling and recovery for the chatbot feature:
- AI service timeout → error handling and retry
- AI service failure → fallback to manual entry
- Network/state preservation when errors occur
- Empty description validation

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""
import sys
import os
import json
from unittest.mock import patch, MagicMock
from datetime import timedelta, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from starlette.testclient import TestClient
from botocore.exceptions import ReadTimeoutError, ClientError
from app.main import app
from app.utils.storage import read_json_file, write_json_file
from app.utils.security import create_access_token

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_test_user(email="e2e_error_test@example.com", user_id="e2e-error-user-123"):
    users = read_json_file("users.json")
    users[email] = {"id": user_id, "email": email, "name": "Error Test User", "password": "pw"}
    write_json_file("users.json", users)
    token = create_access_token(data={"sub": email}, expires_delta=timedelta(minutes=30))
    return token, user_id


def cleanup_test_data(user_id):
    data = read_json_file("interest_topics.json")
    if "topics" in data:
        data["topics"] = [t for t in data["topics"] if t.get("userId") != user_id]
        write_json_file("interest_topics.json", data)
    users = read_json_file("users.json")
    users = {k: v for k, v in users.items() if v.get("id") != user_id}
    write_json_file("users.json", users)


def make_bedrock_mock(responses):
    """Return a mock Bedrock client that cycles through the given response strings."""
    mock_bedrock = MagicMock()
    idx = [0]

    def invoke(*args, **kwargs):
        text = responses[idx[0]] if idx[0] < len(responses) else "Thank you!"
        idx[0] += 1
        m = {"body": MagicMock()}
        m["body"].read.return_value = json.dumps({"content": [{"text": text}]}).encode()
        return m

    mock_bedrock.invoke_model.side_effect = invoke
    return mock_bedrock


# ---------------------------------------------------------------------------
# Test 1: AI service timeout → 408 response, conversation state preserved
# ---------------------------------------------------------------------------

@patch('app.services.chatbot_service.boto3.client')
def test_ai_service_timeout_returns_408(mock_boto_client):
    """
    Simulate ReadTimeoutError from boto3 → expect 408 response.
    Conversation state sent before the error must still be retrievable.
    Requirements: 9.1, 9.2
    """
    print("\n=== Test: AI Service Timeout → 408 ===")

    token, user_id = setup_test_user()

    try:
        # Create topic
        resp = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "signal integrity"},
        )
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # First message succeeds (state is saved)
        mock_boto_client.return_value = make_bedrock_mock(
            ["What specific aspects of signal integrity interest you?"]
        )
        resp = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "I want to define signal integrity"},
        )
        assert resp.status_code == 200
        print("✓ First message succeeded")

        # Verify conversation was saved
        conv = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert conv["conversationStatus"] == "in_progress"
        messages_before_timeout = len(conv["conversationHistory"])
        assert messages_before_timeout >= 2
        print(f"✓ Conversation saved: {messages_before_timeout} messages")

        # Second message times out
        timeout_mock = MagicMock()
        timeout_mock.invoke_model.side_effect = ReadTimeoutError(endpoint_url="https://bedrock.us-west-2.amazonaws.com")
        mock_boto_client.return_value = timeout_mock

        resp = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "High-speed PCB design"},
        )
        assert resp.status_code == 408, f"Expected 408, got {resp.status_code}: {resp.text}"
        detail = resp.json()["detail"].lower()
        assert "taking longer" in detail or "timeout" in detail or "try again" in detail
        print(f"✓ Timeout returns 408: '{resp.json()['detail']}'")

        # Conversation state must be unchanged (messages before timeout still there)
        conv_after = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert conv_after["conversationStatus"] == "in_progress"
        assert len(conv_after["conversationHistory"]) == messages_before_timeout
        print(f"✓ Conversation state preserved after timeout ({messages_before_timeout} messages)")

        # Retry succeeds after timeout
        mock_boto_client.return_value = make_bedrock_mock(
            ["Great! What methodologies do you use for PCB design?"]
        )
        resp = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "High-speed PCB design"},
        )
        assert resp.status_code == 200
        print("✓ Retry after timeout succeeds")

        print("\n✅ AI SERVICE TIMEOUT TEST PASSED")
    finally:
        cleanup_test_data(user_id)


# ---------------------------------------------------------------------------
# Test 2: AI service failure (ClientError) → 500, fallback to manual entry
# ---------------------------------------------------------------------------

@patch('app.services.chatbot_service.boto3.client')
def test_ai_service_failure_returns_500(mock_boto_client):
    """
    Simulate ClientError from boto3 → expect 503 or 500 response.
    User can still save a description manually (fallback).
    Requirements: 9.1, 9.3
    """
    print("\n=== Test: AI Service Failure → 500/503, Manual Entry Fallback ===")

    token, user_id = setup_test_user(
        email="e2e_error2@example.com", user_id="e2e-error-user-456"
    )

    try:
        resp = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "quantum computing"},
        )
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # Simulate Bedrock ClientError (service unavailable)
        error_response = {
            "Error": {"Code": "ServiceUnavailableException", "Message": "Service unavailable"}
        }
        client_error_mock = MagicMock()
        client_error_mock.invoke_model.side_effect = ClientError(
            error_response, "InvokeModel"
        )
        mock_boto_client.return_value = client_error_mock

        resp = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "I want to define quantum computing"},
        )
        assert resp.status_code in (500, 503), (
            f"Expected 500 or 503, got {resp.status_code}: {resp.text}"
        )
        detail = resp.json()["detail"].lower()
        assert "ai service" in detail or "unable" in detail or "error" in detail
        print(f"✓ AI failure returns {resp.status_code}: '{resp.json()['detail']}'")

        # Fallback: user manually saves a description without chatbot
        manual_description = (
            "Research on quantum computing algorithms, specifically quantum error "
            "correction and fault-tolerant quantum computation. Applications in "
            "cryptography and optimization problems."
        )
        resp = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": manual_description},
        )
        assert resp.status_code == 200, f"Manual save failed: {resp.text}"
        saved = resp.json()
        assert saved["comprehensiveDescription"] == manual_description
        assert saved["conversationStatus"] == "completed"
        print("✓ Manual description entry succeeds after AI failure")

        # Verify description persists
        topics = client.get(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        topic_data = next(t for t in topics if t["id"] == topic_id)
        assert topic_data["comprehensiveDescription"] == manual_description
        print("✓ Manually entered description persists")

        print("\n✅ AI SERVICE FAILURE + MANUAL FALLBACK TEST PASSED")
    finally:
        cleanup_test_data(user_id)


# ---------------------------------------------------------------------------
# Test 3: Conversation state preserved when errors occur mid-conversation
# ---------------------------------------------------------------------------

@patch('app.services.chatbot_service.boto3.client')
def test_conversation_state_preserved_on_error(mock_boto_client):
    """
    Messages sent before an error are still saved in conversation history.
    Requirements: 9.2
    """
    print("\n=== Test: Conversation State Preserved on Error ===")

    token, user_id = setup_test_user(
        email="e2e_error3@example.com", user_id="e2e-error-user-789"
    )

    try:
        resp = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "machine learning"},
        )
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # Send several successful messages
        successful_responses = [
            "What specific aspects of machine learning interest you?",
            "What methodologies do you use?",
            "What applications are you focused on?",
        ]
        mock_boto_client.return_value = make_bedrock_mock(successful_responses)

        messages_sent = [
            "I want to define machine learning",
            "Deep learning and neural architectures",
            "Gradient descent and backpropagation",
        ]
        for msg in messages_sent:
            resp = client.post(
                f"/api/user/interests/{topic_id}/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": msg},
            )
            assert resp.status_code == 200

        # Capture state before error
        conv_before = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        messages_before = len(conv_before["conversationHistory"])
        assert messages_before >= len(messages_sent) * 2  # user + assistant per exchange
        print(f"✓ {messages_before} messages saved before error")

        # Now simulate a timeout error
        timeout_mock = MagicMock()
        timeout_mock.invoke_model.side_effect = ReadTimeoutError(
            endpoint_url="https://bedrock.us-west-2.amazonaws.com"
        )
        mock_boto_client.return_value = timeout_mock

        resp = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "Computer vision applications"},
        )
        assert resp.status_code == 408
        print("✓ Error occurred (408 timeout)")

        # Conversation history must be unchanged
        conv_after = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert len(conv_after["conversationHistory"]) == messages_before, (
            f"Expected {messages_before} messages, got {len(conv_after['conversationHistory'])}"
        )
        # Status may be in_progress or completed depending on how many areas were covered
        assert conv_after["conversationStatus"] in ("in_progress", "completed")
        print(f"✓ All {messages_before} messages preserved after error (status: {conv_after['conversationStatus']})")

        # Verify message content is intact
        user_messages = [
            m["content"] for m in conv_after["conversationHistory"] if m["role"] == "user"
        ]
        assert any("machine learning" in m.lower() for m in user_messages)
        assert any("deep learning" in m.lower() for m in user_messages)
        print("✓ Message content intact after error")

        # Also simulate a ClientError and verify state still preserved
        client_error_mock = MagicMock()
        client_error_mock.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeModel",
        )
        mock_boto_client.return_value = client_error_mock

        resp = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "Medical imaging"},
        )
        assert resp.status_code in (500, 503)
        print("✓ ClientError also returns 5xx")

        conv_final = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert len(conv_final["conversationHistory"]) == messages_before
        print(f"✓ State still preserved after ClientError ({messages_before} messages)")

        print("\n✅ CONVERSATION STATE PRESERVATION TEST PASSED")
    finally:
        cleanup_test_data(user_id)


# ---------------------------------------------------------------------------
# Test 4: Empty description validation → 422
# ---------------------------------------------------------------------------

def test_empty_description_validation():
    """
    Empty string, whitespace-only, and >5000 char descriptions are rejected with 422.
    Requirements: 9.4, 9.5
    """
    print("\n=== Test: Empty Description Validation ===")

    token, user_id = setup_test_user(
        email="e2e_error4@example.com", user_id="e2e-error-user-abc"
    )

    try:
        resp = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "deep learning"},
        )
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # Empty string → 422
        resp = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": ""},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
        assert "empty" in resp.json()["detail"].lower()
        print("✓ Empty string → 422")

        # Whitespace only → 422
        resp = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": "   \t\n  "},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
        print("✓ Whitespace-only → 422")

        # Over 5000 characters → 422
        resp = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": "A" * 5001},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
        detail = resp.json()["detail"]
        assert "5000" in detail or "too long" in detail.lower()
        print("✓ >5000 chars → 422")

        # Exactly 5000 characters → 200 (boundary)
        resp = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": "B" * 5000},
        )
        assert resp.status_code == 200, f"Expected 200 for 5000 chars, got {resp.status_code}"
        print("✓ Exactly 5000 chars → 200 (boundary accepted)")

        # Topic still has no description from the failed attempts
        topics = client.get(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        topic_data = next(t for t in topics if t["id"] == topic_id)
        # After the successful 5000-char save, description should be set
        assert topic_data["comprehensiveDescription"] is not None
        print("✓ Topic description set only after valid save")

        print("\n✅ EMPTY DESCRIPTION VALIDATION TEST PASSED")
    finally:
        cleanup_test_data(user_id)


# ---------------------------------------------------------------------------
# Test 5: Retry succeeds after timeout (end-to-end retry flow)
# ---------------------------------------------------------------------------

@patch('app.services.chatbot_service.boto3.client')
def test_retry_succeeds_after_timeout(mock_boto_client):
    """
    After a timeout error, the user can retry the same message successfully.
    Requirements: 9.1
    """
    print("\n=== Test: Retry Succeeds After Timeout ===")

    token, user_id = setup_test_user(
        email="e2e_error5@example.com", user_id="e2e-error-user-def"
    )

    try:
        resp = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "natural language processing"},
        )
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # First attempt: timeout
        timeout_mock = MagicMock()
        timeout_mock.invoke_model.side_effect = ReadTimeoutError(
            endpoint_url="https://bedrock.us-west-2.amazonaws.com"
        )
        mock_boto_client.return_value = timeout_mock

        resp = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "I want to define NLP research"},
        )
        assert resp.status_code == 408
        print("✓ First attempt timed out (408)")

        # Conversation should still be empty (no partial state from failed call)
        conv = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        initial_count = len(conv["conversationHistory"])
        print(f"✓ Conversation has {initial_count} messages after timeout")

        # Second attempt: success (retry)
        mock_boto_client.return_value = make_bedrock_mock(
            ["What specific aspects of NLP interest you?"]
        )
        resp = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "I want to define NLP research"},
        )
        assert resp.status_code == 200
        assert resp.json()["conversationStatus"] == "in_progress"
        print("✓ Retry succeeds (200)")

        # Conversation now has messages
        conv_after = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert len(conv_after["conversationHistory"]) > initial_count
        assert conv_after["conversationStatus"] == "in_progress"
        print(f"✓ Conversation has {len(conv_after['conversationHistory'])} messages after retry")

        print("\n✅ RETRY AFTER TIMEOUT TEST PASSED")
    finally:
        cleanup_test_data(user_id)


# ---------------------------------------------------------------------------
# Test 6: AI failure then manual description save (full fallback flow)
# ---------------------------------------------------------------------------

@patch('app.services.chatbot_service.boto3.client')
def test_full_fallback_to_manual_entry(mock_boto_client):
    """
    When AI service fails repeatedly, user can bypass chatbot and save manually.
    Requirements: 9.3
    """
    print("\n=== Test: Full Fallback to Manual Entry ===")

    token, user_id = setup_test_user(
        email="e2e_error6@example.com", user_id="e2e-error-user-ghi"
    )

    try:
        resp = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "computer vision"},
        )
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # All chatbot attempts fail
        error_response = {
            "Error": {"Code": "ModelNotReadyException", "Message": "Model not ready"}
        }
        failing_mock = MagicMock()
        failing_mock.invoke_model.side_effect = ClientError(error_response, "InvokeModel")
        mock_boto_client.return_value = failing_mock

        for attempt in range(3):
            resp = client.post(
                f"/api/user/interests/{topic_id}/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "I want to define computer vision"},
            )
            assert resp.status_code in (500, 503)
        print("✓ All 3 chatbot attempts failed")

        # User falls back to manual description entry
        manual_desc = (
            "Research on computer vision techniques for object detection and image "
            "segmentation. Focuses on deep learning approaches including CNNs and "
            "transformer-based architectures. Applications in autonomous vehicles and "
            "medical imaging. Excludes classical feature-based methods."
        )
        resp = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": manual_desc},
        )
        assert resp.status_code == 200
        saved = resp.json()
        assert saved["comprehensiveDescription"] == manual_desc
        assert saved["conversationStatus"] == "completed"
        print("✓ Manual description saved successfully after AI failures")

        # Verify the description is usable by the relevance evaluator
        from app.services.relevance_evaluator import RelevanceEvaluator

        evaluator = RelevanceEvaluator()
        eval_mock = make_bedrock_mock(
            ["RELEVANT\nMatching topics: computer vision\nConfidence: 0.85"]
        )
        evaluator.bedrock = eval_mock

        test_paper = {
            "id": "paper-cv-001",
            "title": "Transformer-based Object Detection for Autonomous Vehicles",
            "abstract": "Novel transformer architecture for real-time object detection...",
            "keywords": ["computer vision", "transformers", "autonomous vehicles"],
        }

        topics = client.get(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        evaluator.evaluate(test_paper, topics)

        assert eval_mock.invoke_model.called
        call_body = json.loads(eval_mock.invoke_model.call_args[1]["body"])
        prompt_text = call_body["messages"][0]["content"]
        assert "autonomous vehicles" in prompt_text.lower() or "object detection" in prompt_text.lower()
        print("✓ Manually entered description used by relevance evaluator")

        print("\n✅ FULL FALLBACK TO MANUAL ENTRY TEST PASSED")
    finally:
        cleanup_test_data(user_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("End-to-End Error Scenario Tests")
    print("Requirements: 9.1, 9.2, 9.3, 9.4, 9.5")
    print("=" * 70)

    test_ai_service_timeout_returns_408()
    test_ai_service_failure_returns_500()
    test_conversation_state_preserved_on_error()
    test_empty_description_validation()
    test_retry_succeeds_after_timeout()
    test_full_fallback_to_manual_entry()

    print("\n" + "=" * 70)
    print("All error scenario tests completed!")
    print("=" * 70)
