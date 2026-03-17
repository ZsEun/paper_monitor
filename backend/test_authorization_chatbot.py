"""
Test script for chatbot authorization and user isolation
Tests that users cannot access other users' conversations and validates JWT tokens

**Validates: Requirements 11.2**
"""
import sys
import os
import json
from datetime import datetime, timedelta

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from starlette.testclient import TestClient
from app.main import app
from app.utils.storage import read_json_file, write_json_file
from app.utils.security import create_access_token

client = TestClient(app)


def create_test_user(email: str, user_id: str, name: str):
    """Create a test user and return their auth token"""
    users = read_json_file("users.json")
    users[email] = {
        "id": user_id,
        "email": email,
        "name": name,
        "password": "hashed_password"
    }
    write_json_file("users.json", users)
    
    token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=30)
    )
    return token


def create_test_topic(user_id: str, topic_id: str, topic_text: str):
    """Create a test topic for a user"""
    data = read_json_file("interest_topics.json")
    if "topics" not in data:
        data["topics"] = []
    
    topic = {
        "id": topic_id,
        "userId": user_id,
        "topicText": topic_text,
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
        "conversationHistory": [],
        "conversationStatus": "not_started",
        "comprehensiveDescription": None
    }
    data["topics"].append(topic)
    write_json_file("interest_topics.json", data)
    return topic


def cleanup_test_users(user_ids: list):
    """Clean up test users and their topics"""
    # Clean up topics
    data = read_json_file("interest_topics.json")
    if "topics" in data:
        data["topics"] = [t for t in data["topics"] if t.get("userId") not in user_ids]
        write_json_file("interest_topics.json", data)
    
    # Clean up users
    users = read_json_file("users.json")
    users = {k: v for k, v in users.items() if v.get("id") not in user_ids}
    write_json_file("users.json", users)


def test_chat_endpoint_user_isolation():
    """
    Test that User A cannot access User B's conversation via chat endpoint.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: Chat Endpoint - User Isolation ===")
    
    # Create two users
    user_a_id = "auth-test-user-a"
    user_b_id = "auth-test-user-b"
    
    token_a = create_test_user("user_a@example.com", user_a_id, "User A")
    token_b = create_test_user("user_b@example.com", user_b_id, "User B")
    
    # Create topics for both users
    topic_a_id = "topic-user-a-123"
    topic_b_id = "topic-user-b-456"
    
    create_test_topic(user_a_id, topic_a_id, "neural networks")
    create_test_topic(user_b_id, topic_b_id, "quantum computing")
    
    try:
        # User A tries to chat with User B's topic - should fail
        response = client.post(
            f"/api/user/interests/{topic_b_id}/chat",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"message": "Hello"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "not found" in response.json()["detail"].lower() or "not belong" in response.json()["detail"].lower()
        
        print(f"✓ User A cannot access User B's topic via chat endpoint")
        
        # User B tries to chat with User A's topic - should also fail
        response = client.post(
            f"/api/user/interests/{topic_a_id}/chat",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"message": "Hello"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ User B cannot access User A's topic via chat endpoint")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_a_id, user_b_id])


def test_get_conversation_user_isolation():
    """
    Test that User A cannot retrieve User B's conversation history.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: Get Conversation - User Isolation ===")
    
    # Create two users
    user_a_id = "auth-test-user-a-conv"
    user_b_id = "auth-test-user-b-conv"
    
    token_a = create_test_user("user_a_conv@example.com", user_a_id, "User A Conv")
    token_b = create_test_user("user_b_conv@example.com", user_b_id, "User B Conv")
    
    # Create topics with conversation history
    topic_a_id = "topic-user-a-conv-123"
    topic_b_id = "topic-user-b-conv-456"
    
    topic_a = create_test_topic(user_a_id, topic_a_id, "machine learning")
    topic_b = create_test_topic(user_b_id, topic_b_id, "robotics")
    
    # Add conversation history to User B's topic
    data = read_json_file("interest_topics.json")
    for topic in data["topics"]:
        if topic["id"] == topic_b_id:
            topic["conversationHistory"] = [
                {
                    "role": "assistant",
                    "content": "What interests you about robotics?",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                {
                    "role": "user",
                    "content": "I'm interested in autonomous navigation",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ]
            topic["conversationStatus"] = "in_progress"
    write_json_file("interest_topics.json", data)
    
    try:
        # User A tries to get User B's conversation - should fail
        response = client.get(
            f"/api/user/interests/{topic_b_id}/conversation",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ User A cannot retrieve User B's conversation history")
        
        # User B can access their own conversation - should succeed
        response = client.get(
            f"/api/user/interests/{topic_b_id}/conversation",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert len(data["conversationHistory"]) == 2
        assert data["conversationStatus"] == "in_progress"
        
        print(f"✓ User B can access their own conversation history")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_a_id, user_b_id])


def test_reset_conversation_user_isolation():
    """
    Test that User A cannot reset User B's conversation.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: Reset Conversation - User Isolation ===")
    
    # Create two users
    user_a_id = "auth-test-user-a-reset"
    user_b_id = "auth-test-user-b-reset"
    
    token_a = create_test_user("user_a_reset@example.com", user_a_id, "User A Reset")
    token_b = create_test_user("user_b_reset@example.com", user_b_id, "User B Reset")
    
    # Create topics
    topic_a_id = "topic-user-a-reset-123"
    topic_b_id = "topic-user-b-reset-456"
    
    create_test_topic(user_a_id, topic_a_id, "deep learning")
    create_test_topic(user_b_id, topic_b_id, "computer vision")
    
    # Add conversation history to User B's topic
    data = read_json_file("interest_topics.json")
    for topic in data["topics"]:
        if topic["id"] == topic_b_id:
            topic["conversationHistory"] = [
                {
                    "role": "assistant",
                    "content": "What interests you?",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                {
                    "role": "user",
                    "content": "Image recognition",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ]
            topic["conversationStatus"] = "in_progress"
    write_json_file("interest_topics.json", data)
    
    try:
        # User A tries to reset User B's conversation - should fail
        response = client.post(
            f"/api/user/interests/{topic_b_id}/conversation/reset",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ User A cannot reset User B's conversation")
        
        # Verify User B's conversation is still intact
        data = read_json_file("interest_topics.json")
        topic_b = next((t for t in data["topics"] if t["id"] == topic_b_id), None)
        assert topic_b is not None
        assert len(topic_b["conversationHistory"]) == 2
        
        print(f"✓ User B's conversation remains intact after unauthorized reset attempt")
        
        # User B can reset their own conversation - should succeed
        response = client.post(
            f"/api/user/interests/{topic_b_id}/conversation/reset",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json()["success"] == True
        
        print(f"✓ User B can reset their own conversation")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_a_id, user_b_id])


def test_save_description_user_isolation():
    """
    Test that User A cannot save description to User B's topic.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: Save Description - User Isolation ===")
    
    # Create two users
    user_a_id = "auth-test-user-a-desc"
    user_b_id = "auth-test-user-b-desc"
    
    token_a = create_test_user("user_a_desc@example.com", user_a_id, "User A Desc")
    token_b = create_test_user("user_b_desc@example.com", user_b_id, "User B Desc")
    
    # Create topics
    topic_a_id = "topic-user-a-desc-123"
    topic_b_id = "topic-user-b-desc-456"
    
    create_test_topic(user_a_id, topic_a_id, "natural language processing")
    create_test_topic(user_b_id, topic_b_id, "speech recognition")
    
    try:
        # User A tries to save description to User B's topic - should fail
        description = "Research focused on speech recognition algorithms"
        response = client.post(
            f"/api/user/interests/{topic_b_id}/description/save",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"description": description}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ User A cannot save description to User B's topic")
        
        # Verify User B's topic has no description
        data = read_json_file("interest_topics.json")
        topic_b = next((t for t in data["topics"] if t["id"] == topic_b_id), None)
        assert topic_b is not None
        assert topic_b.get("comprehensiveDescription") is None
        
        print(f"✓ User B's topic remains unchanged after unauthorized save attempt")
        
        # User B can save description to their own topic - should succeed
        response = client.post(
            f"/api/user/interests/{topic_b_id}/description/save",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"description": description}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json()["comprehensiveDescription"] == description
        
        print(f"✓ User B can save description to their own topic")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_a_id, user_b_id])


def test_jwt_token_validation_missing_token():
    """
    Test that all chatbot endpoints reject requests without JWT token.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: JWT Token Validation - Missing Token ===")
    
    # Create a user and topic
    user_id = "auth-test-jwt-user"
    token = create_test_user("jwt_test@example.com", user_id, "JWT Test User")
    
    topic_id = "topic-jwt-test-123"
    create_test_topic(user_id, topic_id, "artificial intelligence")
    
    try:
        # Test POST /chat without token
        response = client.post(
            f"/api/user/interests/{topic_id}/chat",
            json={"message": "Hello"}
        )
        assert response.status_code == 401, f"Chat endpoint: Expected 401, got {response.status_code}"
        print(f"✓ POST /chat rejects missing token (401)")
        
        # Test GET /conversation without token
        response = client.get(
            f"/api/user/interests/{topic_id}/conversation"
        )
        assert response.status_code == 401, f"Get conversation endpoint: Expected 401, got {response.status_code}"
        print(f"✓ GET /conversation rejects missing token (401)")
        
        # Test POST /conversation/reset without token
        response = client.post(
            f"/api/user/interests/{topic_id}/conversation/reset"
        )
        assert response.status_code == 401, f"Reset endpoint: Expected 401, got {response.status_code}"
        print(f"✓ POST /conversation/reset rejects missing token (401)")
        
        # Test POST /description/save without token
        response = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            json={"description": "Test description"}
        )
        assert response.status_code == 401, f"Save description endpoint: Expected 401, got {response.status_code}"
        print(f"✓ POST /description/save rejects missing token (401)")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_id])


def test_jwt_token_validation_invalid_token():
    """
    Test that all chatbot endpoints reject requests with invalid JWT token.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: JWT Token Validation - Invalid Token ===")
    
    # Create a user and topic
    user_id = "auth-test-invalid-jwt-user"
    token = create_test_user("invalid_jwt@example.com", user_id, "Invalid JWT User")
    
    topic_id = "topic-invalid-jwt-123"
    create_test_topic(user_id, topic_id, "data science")
    
    invalid_token = "invalid.jwt.token.here"
    
    try:
        # Test POST /chat with invalid token
        response = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {invalid_token}"},
            json={"message": "Hello"}
        )
        assert response.status_code == 401, f"Chat endpoint: Expected 401, got {response.status_code}"
        print(f"✓ POST /chat rejects invalid token (401)")
        
        # Test GET /conversation with invalid token
        response = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        assert response.status_code == 401, f"Get conversation endpoint: Expected 401, got {response.status_code}"
        print(f"✓ GET /conversation rejects invalid token (401)")
        
        # Test POST /conversation/reset with invalid token
        response = client.post(
            f"/api/user/interests/{topic_id}/conversation/reset",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        assert response.status_code == 401, f"Reset endpoint: Expected 401, got {response.status_code}"
        print(f"✓ POST /conversation/reset rejects invalid token (401)")
        
        # Test POST /description/save with invalid token
        response = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {invalid_token}"},
            json={"description": "Test description"}
        )
        assert response.status_code == 401, f"Save description endpoint: Expected 401, got {response.status_code}"
        print(f"✓ POST /description/save rejects invalid token (401)")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_id])


def test_jwt_token_validation_expired_token():
    """
    Test that all chatbot endpoints reject requests with expired JWT token.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: JWT Token Validation - Expired Token ===")
    
    # Create a user and topic
    user_id = "auth-test-expired-jwt-user"
    
    users = read_json_file("users.json")
    email = "expired_jwt@example.com"
    users[email] = {
        "id": user_id,
        "email": email,
        "name": "Expired JWT User",
        "password": "hashed_password"
    }
    write_json_file("users.json", users)
    
    # Create expired token (negative expiry)
    expired_token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=-30)  # Already expired
    )
    
    topic_id = "topic-expired-jwt-123"
    create_test_topic(user_id, topic_id, "bioinformatics")
    
    try:
        # Test POST /chat with expired token
        response = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {expired_token}"},
            json={"message": "Hello"}
        )
        assert response.status_code == 401, f"Chat endpoint: Expected 401, got {response.status_code}"
        print(f"✓ POST /chat rejects expired token (401)")
        
        # Test GET /conversation with expired token
        response = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401, f"Get conversation endpoint: Expected 401, got {response.status_code}"
        print(f"✓ GET /conversation rejects expired token (401)")
        
        # Test POST /conversation/reset with expired token
        response = client.post(
            f"/api/user/interests/{topic_id}/conversation/reset",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401, f"Reset endpoint: Expected 401, got {response.status_code}"
        print(f"✓ POST /conversation/reset rejects expired token (401)")
        
        # Test POST /description/save with expired token
        response = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {expired_token}"},
            json={"description": "Test description"}
        )
        assert response.status_code == 401, f"Save description endpoint: Expected 401, got {response.status_code}"
        print(f"✓ POST /description/save rejects expired token (401)")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_id])


def test_cross_user_conversation_data_leakage():
    """
    Test that conversation data from one user is never leaked to another user.
    This is a comprehensive test that verifies complete isolation.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: Cross-User Conversation Data Leakage ===")
    
    # Create two users with similar topics
    user_a_id = "auth-test-user-a-leak"
    user_b_id = "auth-test-user-b-leak"
    
    token_a = create_test_user("user_a_leak@example.com", user_a_id, "User A Leak")
    token_b = create_test_user("user_b_leak@example.com", user_b_id, "User B Leak")
    
    # Create topics with same text but different IDs
    topic_a_id = "topic-user-a-leak-123"
    topic_b_id = "topic-user-b-leak-456"
    
    create_test_topic(user_a_id, topic_a_id, "quantum computing")
    create_test_topic(user_b_id, topic_b_id, "quantum computing")
    
    # Add different conversation histories
    data = read_json_file("interest_topics.json")
    for topic in data["topics"]:
        if topic["id"] == topic_a_id:
            topic["conversationHistory"] = [
                {
                    "role": "user",
                    "content": "User A's private conversation about quantum algorithms",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ]
            topic["conversationStatus"] = "in_progress"
            topic["comprehensiveDescription"] = "User A's private description"
        elif topic["id"] == topic_b_id:
            topic["conversationHistory"] = [
                {
                    "role": "user",
                    "content": "User B's private conversation about quantum hardware",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ]
            topic["conversationStatus"] = "in_progress"
            topic["comprehensiveDescription"] = "User B's private description"
    write_json_file("interest_topics.json", data)
    
    try:
        # User A retrieves their own conversation
        response_a = client.get(
            f"/api/user/interests/{topic_a_id}/conversation",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert response_a.status_code == 200
        data_a = response_a.json()
        
        # Verify User A sees only their own data
        assert "User A's private conversation" in data_a["conversationHistory"][0]["content"]
        assert "User B's private conversation" not in str(data_a)
        
        print(f"✓ User A sees only their own conversation data")
        
        # User B retrieves their own conversation
        response_b = client.get(
            f"/api/user/interests/{topic_b_id}/conversation",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert response_b.status_code == 200
        data_b = response_b.json()
        
        # Verify User B sees only their own data
        assert "User B's private conversation" in data_b["conversationHistory"][0]["content"]
        assert "User A's private conversation" not in str(data_b)
        
        print(f"✓ User B sees only their own conversation data")
        
        # User A tries to access User B's topic - should fail
        response = client.get(
            f"/api/user/interests/{topic_b_id}/conversation",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert response.status_code == 404
        
        print(f"✓ User A cannot access User B's conversation at all")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_a_id, user_b_id])


def test_all_endpoints_authorization_comprehensive():
    """
    Comprehensive test that verifies all 4 chatbot endpoints enforce authorization.
    Tests multiple scenarios: missing token, invalid token, wrong user.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: All Endpoints Authorization - Comprehensive ===")
    
    # Create two users
    user_a_id = "auth-test-comprehensive-a"
    user_b_id = "auth-test-comprehensive-b"
    
    token_a = create_test_user("comp_a@example.com", user_a_id, "Comprehensive A")
    token_b = create_test_user("comp_b@example.com", user_b_id, "Comprehensive B")
    
    # Create topic for User B
    topic_b_id = "topic-comprehensive-b-123"
    create_test_topic(user_b_id, topic_b_id, "blockchain")
    
    endpoints_to_test = [
        ("POST", f"/api/user/interests/{topic_b_id}/chat", {"message": "Test"}),
        ("GET", f"/api/user/interests/{topic_b_id}/conversation", None),
        ("POST", f"/api/user/interests/{topic_b_id}/conversation/reset", None),
        ("POST", f"/api/user/interests/{topic_b_id}/description/save", {"description": "Test desc"})
    ]
    
    try:
        for method, endpoint, payload in endpoints_to_test:
            # Test 1: User A (wrong user) tries to access User B's topic
            if method == "POST":
                response = client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {token_a}"},
                    json=payload
                )
            else:
                response = client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {token_a}"}
                )
            
            assert response.status_code == 404, f"{method} {endpoint}: Expected 404 for wrong user, got {response.status_code}"
            print(f"✓ {method} {endpoint}: Rejects wrong user (404)")
            
            # Test 2: Missing token
            if method == "POST":
                response = client.post(endpoint, json=payload)
            else:
                response = client.get(endpoint)
            
            assert response.status_code == 401, f"{method} {endpoint}: Expected 401 for missing token, got {response.status_code}"
            print(f"✓ {method} {endpoint}: Rejects missing token (401)")
            
            # Test 3: Invalid token format
            if method == "POST":
                response = client.post(
                    endpoint,
                    headers={"Authorization": "Bearer invalid_token"},
                    json=payload
                )
            else:
                response = client.get(
                    endpoint,
                    headers={"Authorization": "Bearer invalid_token"}
                )
            
            assert response.status_code == 401, f"{method} {endpoint}: Expected 401 for invalid token, got {response.status_code}"
            print(f"✓ {method} {endpoint}: Rejects invalid token (401)")
        
        print(f"\n✓ All 4 endpoints enforce authorization correctly")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_a_id, user_b_id])


def test_nonexistent_topic_authorization():
    """
    Test that accessing non-existent topics returns 404 even with valid token.
    
    **Validates: Requirements 11.2**
    """
    print("\n=== Test: Non-existent Topic Authorization ===")
    
    # Create a user
    user_id = "auth-test-nonexistent"
    token = create_test_user("nonexistent@example.com", user_id, "Nonexistent User")
    
    nonexistent_topic_id = "topic-does-not-exist-999"
    
    try:
        # Test POST /chat with non-existent topic
        response = client.post(
            f"/api/user/interests/{nonexistent_topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "Hello"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ POST /chat returns 404 for non-existent topic")
        
        # Test GET /conversation with non-existent topic
        response = client.get(
            f"/api/user/interests/{nonexistent_topic_id}/conversation",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ GET /conversation returns 404 for non-existent topic")
        
        # Test POST /conversation/reset with non-existent topic
        response = client.post(
            f"/api/user/interests/{nonexistent_topic_id}/conversation/reset",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ POST /conversation/reset returns 404 for non-existent topic")
        
        # Test POST /description/save with non-existent topic
        response = client.post(
            f"/api/user/interests/{nonexistent_topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": "Test description"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ POST /description/save returns 404 for non-existent topic")
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        cleanup_test_users([user_id])


if __name__ == "__main__":
    print("=" * 70)
    print("CHATBOT AUTHORIZATION AND USER ISOLATION TESTS")
    print("=" * 70)
    
    try:
        test_chat_endpoint_user_isolation()
        test_get_conversation_user_isolation()
        test_reset_conversation_user_isolation()
        test_save_description_user_isolation()
        test_jwt_token_validation_missing_token()
        test_jwt_token_validation_invalid_token()
        test_jwt_token_validation_expired_token()
        test_cross_user_conversation_data_leakage()
        test_nonexistent_topic_authorization()
        
        print("\n" + "=" * 70)
        print("✓ ALL AUTHORIZATION TESTS PASSED")
        print("=" * 70)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"✗ AUTHORIZATION TESTS FAILED: {e}")
        print("=" * 70)
        raise
