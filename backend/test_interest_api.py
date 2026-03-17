"""
Test script for interest topic API endpoints
"""
import sys
import os
import json

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from starlette.testclient import TestClient
from app.main import app
from app.utils.storage import read_json_file, write_json_file
from app.utils.security import create_access_token
from datetime import timedelta

client = TestClient(app)

def setup_test_user():
    """Create a test user and return auth token"""
    # Create test user
    users = read_json_file("users.json")
    test_email = "test@example.com"
    test_user_id = "test-user-api-123"
    
    users[test_email] = {
        "id": test_user_id,
        "email": test_email,
        "name": "Test User",
        "password": "hashed_password"
    }
    write_json_file("users.json", users)
    
    # Create token
    token = create_access_token(
        data={"sub": test_email},
        expires_delta=timedelta(minutes=30)
    )
    
    return token, test_user_id

def cleanup_test_user(user_id):
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

def test_list_topics_empty():
    """Test listing topics when user has none"""
    print("\n=== Test: List Topics (Empty) ===")
    
    token, user_id = setup_test_user()
    
    try:
        response = client.get(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        topics = response.json()
        assert isinstance(topics, list), "Response should be a list"
        assert len(topics) == 0, f"Expected 0 topics, got {len(topics)}"
        
        print(f"✓ Successfully listed empty topics")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)

def test_create_topic():
    """Test creating a new topic"""
    print("\n=== Test: Create Topic ===")
    
    token, user_id = setup_test_user()
    
    try:
        response = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "signal integrity"}
        )
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        topic = response.json()
        assert topic["topicText"] == "signal integrity"
        assert topic["userId"] == user_id
        assert "id" in topic
        assert "createdAt" in topic
        
        print(f"✓ Successfully created topic: {topic['topicText']}")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)

def test_create_duplicate_topic():
    """Test creating a duplicate topic (should fail)"""
    print("\n=== Test: Create Duplicate Topic ===")
    
    token, user_id = setup_test_user()
    
    try:
        # Create first topic
        response1 = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "power integrity"}
        )
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "POWER INTEGRITY"}  # Case-insensitive
        )
        
        assert response2.status_code == 409, f"Expected 409, got {response2.status_code}"
        error = response2.json()
        assert "already exists" in error["detail"].lower()
        
        print(f"✓ Correctly rejected duplicate topic")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)

def test_topic_limit():
    """Test the 20 topic limit"""
    print("\n=== Test: Topic Limit ===")
    
    token, user_id = setup_test_user()
    
    try:
        # Create 20 topics
        for i in range(20):
            response = client.post(
                "/api/user/interests",
                headers={"Authorization": f"Bearer {token}"},
                json={"topicText": f"topic {i}"}
            )
            assert response.status_code == 201, f"Failed to create topic {i}"
        
        print(f"✓ Successfully created 20 topics")
        
        # Try to create 21st topic
        response = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "topic 21"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        error = response.json()
        assert "maximum" in error["detail"].lower() or "20" in error["detail"]
        
        print(f"✓ Correctly rejected 21st topic")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)

def test_update_topic():
    """Test updating a topic"""
    print("\n=== Test: Update Topic ===")
    
    token, user_id = setup_test_user()
    
    try:
        # Create a topic
        response1 = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "EMC design"}
        )
        assert response1.status_code == 201
        topic = response1.json()
        topic_id = topic["id"]
        
        # Update the topic
        response2 = client.put(
            f"/api/user/interests/{topic_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "RF design"}
        )
        
        assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
        updated = response2.json()
        assert updated["topicText"] == "RF design"
        assert updated["id"] == topic_id
        
        print(f"✓ Successfully updated topic to: {updated['topicText']}")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)

def test_update_nonexistent_topic():
    """Test updating a topic that doesn't exist"""
    print("\n=== Test: Update Nonexistent Topic ===")
    
    token, user_id = setup_test_user()
    
    try:
        response = client.put(
            "/api/user/interests/nonexistent-id",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "test topic"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Correctly returned 404 for nonexistent topic")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)

def test_delete_topic():
    """Test deleting a topic"""
    print("\n=== Test: Delete Topic ===")
    
    token, user_id = setup_test_user()
    
    try:
        # Create a topic
        response1 = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "test topic"}
        )
        assert response1.status_code == 201
        topic = response1.json()
        topic_id = topic["id"]
        
        # Delete the topic
        response2 = client.delete(
            f"/api/user/interests/{topic_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
        result = response2.json()
        assert result["success"] is True
        
        # Verify it's deleted
        response3 = client.get(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"}
        )
        topics = response3.json()
        assert len(topics) == 0, "Topic should be deleted"
        
        print(f"✓ Successfully deleted topic")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)

def test_delete_nonexistent_topic():
    """Test deleting a topic that doesn't exist"""
    print("\n=== Test: Delete Nonexistent Topic ===")
    
    token, user_id = setup_test_user()
    
    try:
        response = client.delete(
            "/api/user/interests/nonexistent-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Correctly returned 404 for nonexistent topic")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)

def test_unauthorized_access():
    """Test accessing endpoints without authentication"""
    print("\n=== Test: Unauthorized Access ===")
    
    try:
        # Try to list topics without token
        response = client.get("/api/user/interests")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        print(f"✓ Correctly rejected unauthorized access")
    except Exception as e:
        print(f"✗ Test failed: {e}")

def test_validation_errors():
    """Test input validation"""
    print("\n=== Test: Validation Errors ===")
    
    token, user_id = setup_test_user()
    
    try:
        # Test empty topic
        response1 = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": ""}
        )
        assert response1.status_code == 422, f"Expected 422, got {response1.status_code}"
        print(f"✓ Rejected empty topic")
        
        # Test topic too short
        response2 = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "a"}
        )
        assert response2.status_code == 422, f"Expected 422, got {response2.status_code}"
        print(f"✓ Rejected topic too short")
        
        # Test topic too long
        response3 = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "a" * 201}
        )
        assert response3.status_code == 422, f"Expected 422, got {response3.status_code}"
        print(f"✓ Rejected topic too long")
        
        # Test whitespace-only topic
        response4 = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "   "}
        )
        assert response4.status_code == 422, f"Expected 422, got {response4.status_code}"
        print(f"✓ Rejected whitespace-only topic")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)

if __name__ == "__main__":
    print("=" * 60)
    print("Interest Topic API Tests")
    print("=" * 60)
    
    test_list_topics_empty()
    test_create_topic()
    test_create_duplicate_topic()
    test_topic_limit()
    test_update_topic()
    test_update_nonexistent_topic()
    test_delete_topic()
    test_delete_nonexistent_topic()
    test_unauthorized_access()
    test_validation_errors()
    
    print("\n" + "=" * 60)
    print("All API tests completed!")
    print("=" * 60)
