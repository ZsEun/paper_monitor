"""
End-to-End Integration Tests for Complete User Journey

Tests the complete user flow:
1. Login → Navigate to Settings → Click "Define with AI"
2. Have conversation → Generate description → Save
3. Verify description is used by relevance evaluator in digest generation
4. Test multiple topics (verify independence)
5. Test conversation pause/resume across sessions

Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 4.5, 5.5, 6.1, 6.2, 7.1, 7.2
"""
import sys
import os
import json
from unittest.mock import patch, MagicMock
from datetime import timedelta, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from starlette.testclient import TestClient
from app.main import app
from app.utils.storage import read_json_file, write_json_file
from app.utils.security import create_access_token

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_test_user(email="e2e_test@example.com", user_id="e2e-test-user-123"):
    users = read_json_file("users.json")
    users[email] = {"id": user_id, "email": email, "name": "E2E Test User", "password": "pw"}
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
        m = {'body': MagicMock()}
        m['body'].read.return_value = json.dumps({'content': [{'text': text}]}).encode()
        return m

    mock_bedrock.invoke_model.side_effect = invoke
    return mock_bedrock



# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch('app.services.chatbot_service.boto3.client')
def test_complete_user_journey(mock_boto_client):
    """Complete user journey: login → create topic → chat → save → verify in evaluator"""
    print("\n=== Test: Complete User Journey ===")
    
    responses = [
        "What specific aspects of neural networks interest you?",
        "What methodologies do you use?",
        "What applications are you focused on?",
        "Any topics to exclude?",
        "Thank you! I have enough information."
    ]
    mock_boto_client.return_value = make_bedrock_mock(responses)
    token, user_id = setup_test_user()
    
    try:
        # Step 1-2: Login and navigate to settings
        resp = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200 and len(resp.json()) == 0
        print("✓ Steps 1-2: Logged in, navigated to Settings")
        
        # Step 3: Create topic
        resp = client.post("/api/user/interests", headers={"Authorization": f"Bearer {token}"}, json={"topicText": "neural networks"})
        assert resp.status_code == 201
        topic = resp.json()
        topic_id = topic["id"]
        print(f"✓ Step 3: Created topic '{topic['topicText']}'")
        
        # Step 4-5: Start and continue conversation
        messages = [
            "I want to define my interest in neural networks",
            "Deep learning architectures, especially CNNs",
            "Empirical experiments and novel architecture design",
            "Computer vision and medical imaging",
            "Not interested in theoretical foundations or NLP"
        ]
        
        for i, msg in enumerate(messages):
            resp = client.post(f"/api/user/interests/{topic_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": msg})
            assert resp.status_code == 200
        print(f"✓ Steps 4-5: Completed conversation ({len(messages)} exchanges)")
        
        # Verify conversation saved
        resp = client.get(f"/api/user/interests/{topic_id}/conversation", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        conv = resp.json()
        # Status may be in_progress or completed depending on chatbot's assessment
        assert conv["conversationStatus"] in ["in_progress", "completed"]
        assert len(conv["conversationHistory"]) >= 2
        print(f"✓ Conversation persisted ({len(conv['conversationHistory'])} messages, status: {conv['conversationStatus']})")
        
        # Step 6-7: Save description
        description = (
            "Research focused on deep learning architectures for computer vision, "
            "specifically convolutional neural networks (CNNs) and their applications "
            "in medical imaging. Employs empirical experiments and novel architecture "
            "design methodologies. Excludes theoretical foundations and NLP applications."
        )
        resp = client.post(f"/api/user/interests/{topic_id}/description/save", headers={"Authorization": f"Bearer {token}"}, json={"description": description})
        assert resp.status_code == 200
        saved = resp.json()
        assert saved["comprehensiveDescription"] == description
        assert saved["conversationStatus"] == "completed"
        print(f"✓ Steps 6-7: Description saved ({len(description)} chars)")
        
        # Step 8: Verify description persists
        resp = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"})
        topics = resp.json()
        assert topics[0]["comprehensiveDescription"] == description
        print("✓ Step 8: Description persists in topic list")
        
        # Step 9: Verify relevance evaluator uses comprehensive description
        from app.services.relevance_evaluator import RelevanceEvaluator
        evaluator = RelevanceEvaluator()
        
        eval_mock = make_bedrock_mock(["RELEVANT\nMatching topics: neural networks\nConfidence: 0.9"])
        evaluator.bedrock = eval_mock
        
        test_paper = {
            "id": "paper-001",
            "title": "Advances in CNN Architectures for Medical Image Segmentation",
            "abstract": "Novel CNN architectures for medical image segmentation...",
            "keywords": ["CNN", "medical imaging", "deep learning"]
        }
        
        evaluator.evaluate(test_paper, topics)
        
        assert eval_mock.invoke_model.called
        call_args = eval_mock.invoke_model.call_args
        prompt_body = json.loads(call_args[1]['body'])
        prompt_text = prompt_body['messages'][0]['content']
        # Comprehensive description content should appear in the prompt
        assert "medical imaging" in prompt_text.lower() or "convolutional" in prompt_text.lower()
        print("✓ Step 9: Relevance evaluator uses comprehensive description")
        
        print("\n✅ COMPLETE USER JOURNEY TEST PASSED")
    finally:
        cleanup_test_data(user_id)



@patch('app.services.chatbot_service.boto3.client')
def test_multiple_topics_independence(mock_boto_client):
    """
    Multiple topics have independent conversation histories.
    Requirements: 7.1, 7.2
    """
    print("\n=== Test: Multiple Topics Independence ===")

    responses = [
        "What aspects of neural networks interest you?",
        "What methodologies do you use for neural networks?",
        "What aspects of quantum computing interest you?",
        "What methodologies do you use for quantum computing?",
    ]
    mock_boto_client.return_value = make_bedrock_mock(responses)
    token, user_id = setup_test_user()

    try:
        # Create two topics
        resp = client.post("/api/user/interests", headers={"Authorization": f"Bearer {token}"}, json={"topicText": "neural networks"})
        assert resp.status_code == 201
        topic1_id = resp.json()["id"]

        resp = client.post("/api/user/interests", headers={"Authorization": f"Bearer {token}"}, json={"topicText": "quantum computing"})
        assert resp.status_code == 201
        topic2_id = resp.json()["id"]
        print("✓ Created two topics")

        # Converse with topic 1
        resp = client.post(f"/api/user/interests/{topic1_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "I want to define neural networks"})
        assert resp.status_code == 200
        resp = client.post(f"/api/user/interests/{topic1_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "Deep learning architectures"})
        assert resp.status_code == 200
        print("✓ Topic 1 conversation: 2 exchanges")

        # Converse with topic 2
        resp = client.post(f"/api/user/interests/{topic2_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "I want to define quantum computing"})
        assert resp.status_code == 200
        resp = client.post(f"/api/user/interests/{topic2_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "Quantum algorithms"})
        assert resp.status_code == 200
        print("✓ Topic 2 conversation: 2 exchanges")

        # Retrieve both conversations
        conv1 = client.get(f"/api/user/interests/{topic1_id}/conversation", headers={"Authorization": f"Bearer {token}"}).json()
        conv2 = client.get(f"/api/user/interests/{topic2_id}/conversation", headers={"Authorization": f"Bearer {token}"}).json()

        assert len(conv1["conversationHistory"]) >= 2
        assert len(conv2["conversationHistory"]) >= 2

        # Verify content independence
        text1 = " ".join(m["content"] for m in conv1["conversationHistory"])
        text2 = " ".join(m["content"] for m in conv2["conversationHistory"])
        assert "neural" in text1.lower() or "deep learning" in text1.lower()
        assert "quantum" in text2.lower()
        assert "quantum" not in text1.lower()
        assert "neural" not in text2.lower() and "deep learning" not in text2.lower()
        print("✓ Conversations are independent (no cross-contamination)")

        # Save independent descriptions
        desc1 = "Research on deep learning architectures, specifically CNNs for computer vision."
        desc2 = "Research on quantum algorithms and error correction for cryptography."

        resp = client.post(f"/api/user/interests/{topic1_id}/description/save", headers={"Authorization": f"Bearer {token}"}, json={"description": desc1})
        assert resp.status_code == 200
        resp = client.post(f"/api/user/interests/{topic2_id}/description/save", headers={"Authorization": f"Bearer {token}"}, json={"description": desc2})
        assert resp.status_code == 200

        all_topics = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json()
        assert len(all_topics) == 2
        t1 = next(t for t in all_topics if t["id"] == topic1_id)
        t2 = next(t for t in all_topics if t["id"] == topic2_id)
        assert t1["comprehensiveDescription"] == desc1
        assert t2["comprehensiveDescription"] == desc2
        print("✓ Both descriptions saved independently")

        # Resetting topic 1 must not affect topic 2
        client.post(f"/api/user/interests/{topic1_id}/conversation/reset", headers={"Authorization": f"Bearer {token}"})
        conv2_after = client.get(f"/api/user/interests/{topic2_id}/conversation", headers={"Authorization": f"Bearer {token}"}).json()
        assert len(conv2_after["conversationHistory"]) >= 2
        print("✓ Resetting topic 1 does not affect topic 2")

        print("\n✅ MULTIPLE TOPICS INDEPENDENCE TEST PASSED")
    finally:
        cleanup_test_data(user_id)



@patch('app.services.chatbot_service.boto3.client')
def test_conversation_pause_resume_across_sessions(mock_boto_client):
    """
    Conversation state is saved when navigating away and restored on return.
    Requirements: 6.1, 6.2
    """
    print("\n=== Test: Conversation Pause/Resume Across Sessions ===")

    responses = [
        "What aspects of signal integrity interest you?",
        "What methodologies do you use?",
        "What applications are you focused on?",
        "Any topics to exclude?",
    ]
    mock_boto_client.return_value = make_bedrock_mock(responses)
    token, user_id = setup_test_user()

    try:
        resp = client.post("/api/user/interests", headers={"Authorization": f"Bearer {token}"}, json={"topicText": "signal integrity"})
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # SESSION 1: start conversation and send two messages
        client.post(f"/api/user/interests/{topic_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "I want to define signal integrity"})
        client.post(f"/api/user/interests/{topic_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "High-speed digital circuits and PCB design"})

        # Verify state saved (simulate "navigate away")
        paused = client.get(f"/api/user/interests/{topic_id}/conversation", headers={"Authorization": f"Bearer {token}"}).json()
        assert paused["conversationStatus"] == "in_progress"
        paused_count = len(paused["conversationHistory"])
        assert paused_count >= 2
        print(f"✓ Session 1: paused with {paused_count} messages")

        # SESSION 2: "return to Settings" — state must be fully restored
        resumed = client.get(f"/api/user/interests/{topic_id}/conversation", headers={"Authorization": f"Bearer {token}"}).json()
        assert resumed["conversationStatus"] == "in_progress"
        assert len(resumed["conversationHistory"]) == paused_count

        first_user_msg = next((m for m in resumed["conversationHistory"] if m["role"] == "user"), None)
        assert first_user_msg is not None
        assert "signal integrity" in first_user_msg["content"].lower()
        print(f"✓ Session 2: restored {len(resumed['conversationHistory'])} messages")

        # Continue conversation from where we left off
        client.post(f"/api/user/interests/{topic_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "Simulation and measurement techniques"})
        client.post(f"/api/user/interests/{topic_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "Data center interconnects"})

        final = client.get(f"/api/user/interests/{topic_id}/conversation", headers={"Authorization": f"Bearer {token}"}).json()
        assert len(final["conversationHistory"]) > paused_count
        print(f"✓ Session 2: conversation grew to {len(final['conversationHistory'])} messages")

        # Complete the journey
        description = (
            "Research on signal integrity in high-speed digital circuits and PCB design. "
            "Uses simulation and measurement techniques. Applications: data center interconnects."
        )
        resp = client.post(f"/api/user/interests/{topic_id}/description/save", headers={"Authorization": f"Bearer {token}"}, json={"description": description})
        assert resp.status_code == 200
        assert resp.json()["conversationStatus"] == "completed"
        print("✓ Session 2: description saved, conversation completed")

        print("\n✅ CONVERSATION PAUSE/RESUME TEST PASSED")
    finally:
        cleanup_test_data(user_id)



@patch('app.services.chatbot_service.boto3.client')
def test_description_used_in_relevance_evaluation(mock_boto_client):
    """
    Relevance evaluator uses comprehensiveDescription when present, falls back to topicText.
    Requirements: 5.5, 5.6, 5.7
    """
    print("\n=== Test: Description Used in Relevance Evaluation ===")

    mock_boto_client.return_value = MagicMock()
    token, user_id = setup_test_user()

    try:
        from app.services.relevance_evaluator import RelevanceEvaluator

        test_paper = {
            "id": "paper-si-001",
            "title": "Advanced Signal Integrity Analysis for High-Speed PCB Design",
            "abstract": "Methods for signal integrity analysis in high-speed PCB designs...",
            "keywords": ["signal integrity", "PCB", "high-speed"]
        }

        prompts_sent = []

        def capture_invoke(*args, **kwargs):
            body = json.loads(kwargs.get('body', '{}'))
            msgs = body.get('messages', [])
            if msgs:
                prompts_sent.append(msgs[0]['content'])
            m = {'body': MagicMock()}
            m['body'].read.return_value = json.dumps({
                'content': [{'text': 'RELEVANT\nMatching topics: signal integrity\nConfidence: 0.9'}]
            }).encode()
            return m

        # Test 1: topic WITHOUT comprehensive description → uses topicText
        evaluator = RelevanceEvaluator()
        evaluator.bedrock = MagicMock()
        evaluator.bedrock.invoke_model.side_effect = capture_invoke

        topic_no_desc = {
            "id": "t-no-desc", "userId": user_id,
            "topicText": "signal integrity",
            "comprehensiveDescription": None,
            "conversationStatus": "not_started"
        }
        prompts_sent.clear()
        evaluator.evaluate(test_paper, [topic_no_desc])
        assert len(prompts_sent) == 1
        prompt_simple = prompts_sent[0]
        assert "signal integrity" in prompt_simple.lower()
        print("✓ Without description: evaluator uses topicText")

        # Test 2: topic WITH comprehensive description → uses description
        comprehensive_desc = (
            "Research on signal integrity in high-speed digital circuits and PCB design. "
            "Includes transmission line effects, crosstalk, and power delivery networks. "
            "Applications in data center interconnects. Excludes analog and RF."
        )
        topic_with_desc = {
            "id": "t-with-desc", "userId": user_id,
            "topicText": "signal integrity",
            "comprehensiveDescription": comprehensive_desc,
            "conversationStatus": "completed"
        }
        prompts_sent.clear()
        evaluator.evaluate(test_paper, [topic_with_desc])
        assert len(prompts_sent) == 1
        prompt_rich = prompts_sent[0]
        assert "transmission line" in prompt_rich.lower() or "crosstalk" in prompt_rich.lower()
        assert len(prompt_rich) > len(prompt_simple)
        print("✓ With description: evaluator uses comprehensiveDescription")

        # The two prompts must differ
        assert prompt_rich != prompt_simple
        print("✓ Prompts differ: comprehensive description changes evaluation context")

        print("\n✅ DESCRIPTION USED IN RELEVANCE EVALUATION TEST PASSED")
    finally:
        cleanup_test_data(user_id)



@patch('app.services.chatbot_service.boto3.client')
def test_conversation_cancellation_doesnt_save(mock_boto_client):
    """
    Canceling a conversation clears history and leaves no description.
    Requirements: 6.3, 6.4
    """
    print("\n=== Test: Conversation Cancellation ===")

    mock_boto_client.return_value = make_bedrock_mock(["What aspects interest you?"])
    token, user_id = setup_test_user()

    try:
        resp = client.post("/api/user/interests", headers={"Authorization": f"Bearer {token}"}, json={"topicText": "machine learning"})
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # Start and partially continue conversation
        client.post(f"/api/user/interests/{topic_id}/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "I want to define machine learning"})

        conv = client.get(f"/api/user/interests/{topic_id}/conversation", headers={"Authorization": f"Bearer {token}"}).json()
        assert len(conv["conversationHistory"]) >= 2
        print(f"✓ Conversation has {len(conv['conversationHistory'])} messages before cancel")

        # Cancel (reset)
        resp = client.post(f"/api/user/interests/{topic_id}/conversation/reset", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # Verify history cleared and status reset
        reset_conv = client.get(f"/api/user/interests/{topic_id}/conversation", headers={"Authorization": f"Bearer {token}"}).json()
        assert reset_conv["conversationStatus"] == "not_started"
        assert len(reset_conv["conversationHistory"]) == 0
        print("✓ Conversation history cleared after cancel")

        # Verify no description was saved
        topics = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json()
        topic_data = next(t for t in topics if t["id"] == topic_id)
        assert topic_data["comprehensiveDescription"] is None
        assert topic_data["conversationStatus"] == "not_started"
        print("✓ No description saved after cancellation")

        print("\n✅ CONVERSATION CANCELLATION TEST PASSED")
    finally:
        cleanup_test_data(user_id)


def test_empty_description_validation():
    """
    Empty, whitespace-only, and over-length descriptions are rejected with 422.
    Requirements: 9.4, 9.5
    """
    print("\n=== Test: Empty Description Validation ===")

    token, user_id = setup_test_user()

    try:
        resp = client.post("/api/user/interests", headers={"Authorization": f"Bearer {token}"}, json={"topicText": "deep learning"})
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # Empty string
        resp = client.post(f"/api/user/interests/{topic_id}/description/save", headers={"Authorization": f"Bearer {token}"}, json={"description": ""})
        assert resp.status_code == 422
        assert "empty" in resp.json()["detail"].lower()
        print("✓ Empty description → 422")

        # Whitespace only
        resp = client.post(f"/api/user/interests/{topic_id}/description/save", headers={"Authorization": f"Bearer {token}"}, json={"description": "   "})
        assert resp.status_code == 422
        print("✓ Whitespace-only description → 422")

        # Over 5000 chars
        resp = client.post(f"/api/user/interests/{topic_id}/description/save", headers={"Authorization": f"Bearer {token}"}, json={"description": "A" * 5001})
        assert resp.status_code == 422
        assert "5000" in resp.json()["detail"] or "too long" in resp.json()["detail"].lower()
        print("✓ Description > 5000 chars → 422")

        # Topic still has no description
        topics = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json()
        assert next(t for t in topics if t["id"] == topic_id)["comprehensiveDescription"] is None
        print("✓ Topic unchanged after all failed saves")

        print("\n✅ EMPTY DESCRIPTION VALIDATION TEST PASSED")
    finally:
        cleanup_test_data(user_id)


def test_user_isolation():
    """
    Users cannot access each other's topics or conversations.
    Requirements: 1.2, 7.1
    """
    print("\n=== Test: User Isolation ===")

    token1, user1_id = setup_test_user("e2e_u1@example.com", "e2e-u1-isolation")
    token2, user2_id = setup_test_user("e2e_u2@example.com", "e2e-u2-isolation")

    try:
        # User 1 creates a topic
        resp = client.post("/api/user/interests", headers={"Authorization": f"Bearer {token1}"}, json={"topicText": "user1 topic"})
        assert resp.status_code == 201
        u1_topic_id = resp.json()["id"]
        print(f"✓ User 1 created topic {u1_topic_id}")

        # User 2 tries to access user 1's conversation → 404
        resp = client.get(f"/api/user/interests/{u1_topic_id}/conversation", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 404
        print("✓ User 2 cannot GET User 1's conversation (404)")

        # User 2 tries to chat with user 1's topic → 404
        resp = client.post(f"/api/user/interests/{u1_topic_id}/chat", headers={"Authorization": f"Bearer {token2}"}, json={"message": "Hello"})
        assert resp.status_code == 404
        print("✓ User 2 cannot POST chat to User 1's topic (404)")

        # User 2 tries to save description to user 1's topic → 404
        resp = client.post(f"/api/user/interests/{u1_topic_id}/description/save", headers={"Authorization": f"Bearer {token2}"}, json={"description": "Unauthorized"})
        assert resp.status_code == 404
        print("✓ User 2 cannot save description to User 1's topic (404)")

        # User 1 can still access their own topic
        resp = client.get(f"/api/user/interests/{u1_topic_id}/conversation", headers={"Authorization": f"Bearer {token1}"})
        assert resp.status_code == 200
        print("✓ User 1 can still access their own topic")

        print("\n✅ USER ISOLATION TEST PASSED")
    finally:
        cleanup_test_data(user1_id)
        cleanup_test_data(user2_id)


if __name__ == "__main__":
    print("=" * 70)
    print("End-to-End User Journey Integration Tests")
    print("=" * 70)

    test_complete_user_journey()
    test_multiple_topics_independence()
    test_conversation_pause_resume_across_sessions()
    test_description_used_in_relevance_evaluation()
    test_conversation_cancellation_doesnt_save()
    test_empty_description_validation()
    test_user_isolation()

    print("\n" + "=" * 70)
    print("All E2E tests completed!")
    print("=" * 70)
