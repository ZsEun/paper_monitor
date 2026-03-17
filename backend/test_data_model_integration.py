"""
Integration tests for chatbot data model extensions.
Tests the complete flow from API to storage layer.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.utils.storage import write_json_file, read_json_file
from app.utils.security import create_access_token
from datetime import datetime


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test"""
    # Setup: Create test user and clear data
    users = {
        "test@example.com": {
            "id": "test-user-id",
            "email": "test@example.com",
            "name": "Test User",
            "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/qvQu6"  # hashed "password"
        }
    }
    write_json_file("users.json", users)
    write_json_file("interest_topics.json", {"topics": []})
    
    yield
    
    # Teardown: Clear data
    write_json_file("users.json", {})
    write_json_file("interest_topics.json", {"topics": []})


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authorization headers with valid JWT token"""
    token = create_access_token({"sub": "test@example.com"})
    return {"Authorization": f"Bearer {token}"}


def test_create_topic_includes_chatbot_fields(client, auth_headers):
    """Test that creating a topic includes default chatbot fields"""
    response = client.post(
        "/api/user/interests",
        json={"topicText": "machine learning"},
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify chatbot fields are present with defaults
    assert "comprehensiveDescription" in data
    assert data["comprehensiveDescription"] is None
    assert "conversationHistory" in data
    assert data["conversationHistory"] is None
    assert "conversationStatus" in data
    assert data["conversationStatus"] == "not_started"


def test_list_topics_includes_chatbot_fields(client, auth_headers):
    """Test that listing topics includes chatbot fields"""
    # Create a topic
    client.post(
        "/api/user/interests",
        json={"topicText": "quantum computing"},
        headers=auth_headers
    )
    
    # List topics
    response = client.get("/api/user/interests", headers=auth_headers)
    
    assert response.status_code == 200
    topics = response.json()
    assert len(topics) == 1
    
    # Verify chatbot fields are present
    topic = topics[0]
    assert "comprehensiveDescription" in topic
    assert "conversationHistory" in topic
    assert "conversationStatus" in topic
    assert topic["conversationStatus"] == "not_started"


def test_backward_compatibility_with_old_data(client, auth_headers):
    """Test that old topics without chatbot fields work correctly"""
    # Manually create an old-style topic without chatbot fields
    old_topic = {
        "id": "old-topic-id",
        "userId": "test-user-id",
        "topicText": "neural networks",
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z"
    }
    
    write_json_file("interest_topics.json", {"topics": [old_topic]})
    
    # List topics through API
    response = client.get("/api/user/interests", headers=auth_headers)
    
    assert response.status_code == 200
    topics = response.json()
    assert len(topics) == 1
    
    # Verify chatbot fields are added with defaults
    topic = topics[0]
    assert topic["id"] == "old-topic-id"
    assert topic["topicText"] == "neural networks"
    assert topic["comprehensiveDescription"] is None
    assert topic["conversationHistory"] is None
    assert topic["conversationStatus"] == "not_started"


def test_export_includes_chatbot_fields(client, auth_headers):
    """Test that export includes chatbot fields"""
    # Create a topic
    client.post(
        "/api/user/interests",
        json={"topicText": "robotics"},
        headers=auth_headers
    )
    
    # Export topics
    response = client.post("/api/user/interests/export", headers=auth_headers)
    
    assert response.status_code == 200
    export_data = response.json()
    
    assert "topics" in export_data
    assert len(export_data["topics"]) == 1
    
    topic = export_data["topics"][0]
    assert "comprehensiveDescription" in topic
    assert "conversationStatus" in topic
    # conversationHistory should not be exported per design
    

def test_storage_layer_handles_missing_fields():
    """Test that storage layer gracefully handles missing chatbot fields"""
    from app.utils.storage import get_user_interest_topics, get_interest_topic_by_id
    
    user_id = "test-user-2"
    
    # Create topic without chatbot fields directly in storage
    old_topic = {
        "id": "topic-without-fields",
        "userId": user_id,
        "topicText": "data science",
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z"
    }
    
    write_json_file("interest_topics.json", {"topics": [old_topic]})
    
    # Test get_user_interest_topics
    topics = get_user_interest_topics(user_id)
    assert len(topics) == 1
    assert topics[0]["comprehensiveDescription"] is None
    assert topics[0]["conversationHistory"] is None
    assert topics[0]["conversationStatus"] == "not_started"
    
    # Test get_interest_topic_by_id
    topic = get_interest_topic_by_id("topic-without-fields", user_id)
    assert topic is not None
    assert topic["comprehensiveDescription"] is None
    assert topic["conversationHistory"] is None
    assert topic["conversationStatus"] == "not_started"
