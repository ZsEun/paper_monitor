"""
Test script for chatbot API endpoints
Tests the 4 new endpoints: chat, get conversation, reset, save description
"""
import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from starlette.testclient import TestClient
from app.main import app
from app.utils.storage import read_json_file, write_json_file
from app.utils.security import create_access_token
from datetime import timedelta, datetime

client = TestClient(app)

def setup_test_user_and_topic():
    """Create a test user with a topic and return auth token, user_id, topic_id"""
    # Create test user
    users = read_json_file("users.json")
    test_email = "chatbot_test@example.com"
    test_user_id = "chatbot-test-user-123"
    
    users[test_email] = {
        "id": test_user_id,
        "email": test_email,
        "name": "Chatbot Test User",
        "password": "hashed_password"
    }
    write_json_file("users.json", users)
    
    # Create test topic
    data = read_json_file("interest_topics.json")
    if "topics" not in data:
        data["topics"] = []
    
    test_topic_id = "chatbot-test-topic-123"
    test_topic = {
        "id": test_topic_id,
        "userId": test_user_id,
        "topicText": "neural networks",
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
        "conversationHistory": [],
        "conversationStatus": "not_started",
        "comprehensiveDescription": None
    }
    data["topics"].append(test_topic)
    write_json_file("interest_topics.json", data)
    
    # Create token
    token = create_access_token(
        data={"sub": test_email},
        expires_delta=timedelta(minutes=30)
    )
    
    return token, test_user_id, test_topic_id

def cleanup_test_data(user_id):
    """Clean up test user and their topics"""
    # Clean up topics
    data = read_json_file("interest_topics.json")
    if "topics" in data:
        data["topics"] = [t for t in data["topics"] if t.get("userId") != user_id]
        write_json_file("interest_topics.json", data)
    
    # Clean up user
    users = read_json_file("users.json")
    users = {k: v for k, v in users.items() if v.get("id") != user_id}
    write_json_file("users.json", users)

@patch('app.services.chatbot_service.boto3.client')
def test_chat_endpoint_first_message(mock_boto_client):
    """Test POST /api/user/interests/:id/chat with first message"""
    print("\n=== Test: Chat Endpoint - First Message ===")
    
    # Mock Bedrock response
    mock_bedrock = MagicMock()
    mock_boto_client.return_value = mock_bedrock
    
    mock_response = {
        'body': MagicMock()
    }
    mock_response['body'].read.return_value = json.dumps({
        'content': [{
            'text': 'Great! Neural networks is a fascinating area. What specific aspects of neural networks are you most interested in? For example: architectures (CNNs, RNNs, Transformers), training techniques, or applications?'
        }]
    }).encode()
    mock_bedrock.invoke_model.return_value = mock_response
    
    token, user_id, topic_id = setup_test_user_and_topic()
    
    try:
        response = client.post(
            f"/api/user/interests/{topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "I want to learn about neural networks"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data
        assert "shouldConclude" in data
        assert "conversationStatus" in data
        assert data["conversationStatus"] == "in_progress"
        
        print(f"✓ Chat endpoint returned response: {data['message'][:50]}...")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_data(user_id)

@patch('app.services.chatbot_service.boto3.client')
def test_get_conversation_endpoint(mock_boto_client):
    """Test GET /api/user/interests/:id/conversation"""
    print("\n=== Test: Get Conversation Endpoint ===")
    
    token, user_id, topic_id = setup_test_user_and_topic()
    
    try:
        response = client.get(
            f"/api/user/interests/{topic_id}/conversation",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "conversationHistory" in data
        assert "conversationStatus" in data
        assert isinstance(data["conversationHistory"], list)
        assert data["conversationStatus"] == "not_started"
        
        print(f"✓ Retrieved conversation: status={data['conversationStatus']}, messages={len(data['conversationHistory'])}")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_data(user_id)

def test_reset_conversation_endpoint():
    """Test POST /api/user/interests/:id/conversation/reset"""
    print("\n=== Test: Reset Conversation Endpoint ===")
    
    token, user_id, topic_id = setup_test_user_and_topic()
    
    try:
        response = client.post(
            f"/api/user/interests/{topic_id}/conversation/reset",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["success"] == True
        
        print(f"✓ Successfully reset conversation")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_data(user_id)

def test_save_description_endpoint():
    """Test POST /api/user/interests/:id/description/save"""
    print("\n=== Test: Save Description Endpoint ===")
    
    token, user_id, topic_id = setup_test_user_and_topic()
    
    try:
        description = "Research focused on deep learning architectures for computer vision, particularly convolutional neural networks and their applications in medical imaging."
        
        response = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": description}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["comprehensiveDescription"] == description
        assert data["conversationStatus"] == "completed"
        
        print(f"✓ Successfully saved description: {description[:50]}...")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_data(user_id)

def test_save_empty_description_fails():
    """Test that saving empty description returns 422"""
    print("\n=== Test: Save Empty Description (Should Fail) ===")
    
    token, user_id, topic_id = setup_test_user_and_topic()
    
    try:
        response = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": ""}
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        print(f"✓ Empty description correctly rejected with 422")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_data(user_id)

def test_save_long_description_fails():
    """Test that saving description > 5000 chars returns 422"""
    print("\n=== Test: Save Long Description (Should Fail) ===")
    
    token, user_id, topic_id = setup_test_user_and_topic()
    
    try:
        # Create description longer than 5000 characters
        long_description = "A" * 5001
        
        response = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": long_description}
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        print(f"✓ Long description correctly rejected with 422")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_data(user_id)

def test_chat_unauthorized_topic():
    """Test that chatting with another user's topic returns 404"""
    print("\n=== Test: Chat Unauthorized Topic ===")
    
    token, user_id, topic_id = setup_test_user_and_topic()
    
    # Create another user's topic
    data = read_json_file("interest_topics.json")
    other_topic_id = "other-user-topic-123"
    data["topics"].append({
        "id": other_topic_id,
        "userId": "other-user-456",
        "topicText": "quantum computing",
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
        "conversationHistory": [],
        "conversationStatus": "not_started"
    })
    write_json_file("interest_topics.json", data)
    
    try:
        response = client.post(
            f"/api/user/interests/{other_topic_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "Hello"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Unauthorized access correctly rejected with 404")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_data(user_id)
        # Clean up other user's topic
        data = read_json_file("interest_topics.json")
        data["topics"] = [t for t in data["topics"] if t.get("id") != other_topic_id]
        write_json_file("interest_topics.json", data)

if __name__ == "__main__":
    test_chat_endpoint_first_message()
    test_get_conversation_endpoint()
    test_reset_conversation_endpoint()
    test_save_description_endpoint()
    test_save_empty_description_fails()
    test_save_long_description_fails()
    test_chat_unauthorized_topic()
    
    print("\n=== All Chatbot API Tests Complete ===")
