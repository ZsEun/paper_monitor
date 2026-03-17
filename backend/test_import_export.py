"""
Test import/export endpoints for interest topics
"""
import sys
import os
import json

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from fastapi.testclient import TestClient
from app.main import app
from app.utils.storage import write_json_file, read_json_file
from app.utils.security import create_access_token
from datetime import timedelta
from io import BytesIO


def get_client():
    """Get test client instance"""
    return TestClient(app)

def setup_test_user():
    """Create a test user and return auth token"""
    test_email = "test_export@example.com"
    test_user_id = "test-export-user-123"
    
    # Create test user
    users = read_json_file("users.json")
    users[test_email] = {
        "id": test_user_id,
        "email": test_email,
        "name": "Test Export User",
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
    """Clean up test data"""
    # Clean up interest topics
    data = read_json_file("interest_topics.json")
    if "topics" in data:
        data["topics"] = [
            t for t in data["topics"] 
            if t.get("userId") != user_id
        ]
        write_json_file("interest_topics.json", data)
    
    # Clean up users
    users = read_json_file("users.json")
    users = {k: v for k, v in users.items() if v.get("id") != user_id}
    write_json_file("users.json", users)


def test_export_empty_topics():
    """Test exporting when user has no topics"""
    print("\n=== Test: Export Empty Topics ===")
    
    client = get_client()
    token, user_id = setup_test_user()
    
    try:
        response = client.post(
            "/api/user/interests/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "exportedAt" in data
        assert "userId" in data
        assert "topicCount" in data
        assert "topics" in data
        assert data["topicCount"] == 0
        assert data["topics"] == []
        
        print(f"✓ Successfully exported empty topics")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)


def test_export_with_topics():
    """Test exporting topics"""
    print("\n=== Test: Export With Topics ===")
    
    client = get_client()
    token, user_id = setup_test_user()
    
    try:
        # Add some topics first
        topics_to_add = [
            "Machine Learning",
            "Natural Language Processing",
            "Computer Vision"
        ]
        
        for topic_text in topics_to_add:
            response = client.post(
                "/api/user/interests",
                json={"topicText": topic_text},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 201, f"Failed to add topic: {topic_text}"
        
        # Export topics
        response = client.post(
            "/api/user/interests/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["topicCount"] == 3, f"Expected 3 topics, got {data['topicCount']}"
        assert len(data["topics"]) == 3
        
        # Verify all topics are present
        exported_texts = [t["topicText"] for t in data["topics"]]
        for topic_text in topics_to_add:
            assert topic_text in exported_texts, f"Topic '{topic_text}' not in export"
        
        # Verify each topic has required fields
        for topic in data["topics"]:
            assert "id" in topic
            assert "userId" in topic
            assert "topicText" in topic
            assert "createdAt" in topic
            assert "updatedAt" in topic
        
        print(f"✓ Successfully exported {len(data['topics'])} topics")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)


def test_import_valid_json():
    """Test importing topics from valid JSON"""
    print("\n=== Test: Import Valid JSON ===")
    
    client = get_client()
    token, user_id = setup_test_user()
    
    try:
        # Create import data
        import_data = {
            "exportedAt": "2024-01-01T00:00:00Z",
            "userId": "some-user-id",
            "topicCount": 3,
            "topics": [
                {"topicText": "Deep Learning"},
                {"topicText": "Reinforcement Learning"},
                {"topicText": "Neural Networks"}
            ]
        }
        
        # Create file-like object
        file_content = json.dumps(import_data).encode()
        files = {"file": ("topics.json", BytesIO(file_content), "application/json")}
        
        # Import topics
        response = client.post(
            "/api/user/interests/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        result = response.json()
        
        assert result["success"] is True
        assert result["results"]["added"] == 3, f"Expected 3 added, got {result['results']['added']}"
        assert result["results"]["duplicates"] == 0
        assert result["results"]["skipped"] == 0
        
        # Verify topics were added
        response = client.get(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        topics = response.json()
        assert len(topics) == 3, f"Expected 3 topics, got {len(topics)}"
        
        print(f"✓ Successfully imported 3 topics")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)


def test_import_with_duplicates():
    """Test importing topics with duplicates"""
    print("\n=== Test: Import With Duplicates ===")
    
    client = get_client()
    token, user_id = setup_test_user()
    
    try:
        # Add a topic first
        response = client.post(
            "/api/user/interests",
            json={"topicText": "Quantum Computing"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        
        # Try to import the same topic
        import_data = {
            "topics": [
                {"topicText": "Quantum Computing"},  # Duplicate
                {"topicText": "Blockchain Technology"}  # New
            ]
        }
        
        file_content = json.dumps(import_data).encode()
        files = {"file": ("topics.json", BytesIO(file_content), "application/json")}
        
        response = client.post(
            "/api/user/interests/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        result = response.json()
        
        assert result["results"]["added"] == 1, f"Expected 1 added, got {result['results']['added']}"
        assert result["results"]["duplicates"] == 1, f"Expected 1 duplicate, got {result['results']['duplicates']}"
        
        print(f"✓ Correctly handled duplicate during import")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)


def test_import_invalid_json():
    """Test importing invalid JSON"""
    print("\n=== Test: Import Invalid JSON ===")
    
    client = get_client()
    token, user_id = setup_test_user()
    
    try:
        # Create invalid JSON
        file_content = b"not valid json"
        files = {"file": ("topics.json", BytesIO(file_content), "application/json")}
        
        response = client.post(
            "/api/user/interests/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Invalid JSON" in response.json()["detail"]
        
        print(f"✓ Correctly rejected invalid JSON")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)


def test_export_import_roundtrip():
    """Test exporting and then importing topics"""
    print("\n=== Test: Export/Import Roundtrip ===")
    
    client = get_client()
    token, user_id = setup_test_user()
    
    try:
        # Add topics
        original_topics = ["Topic A", "Topic B", "Topic C"]
        for topic_text in original_topics:
            response = client.post(
                "/api/user/interests",
                json={"topicText": topic_text},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 201
        
        # Export
        response = client.post(
            "/api/user/interests/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        export_data = response.json()
        
        # Delete all topics
        response = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"})
        topics = response.json()
        for topic in topics:
            client.delete(
                f"/api/user/interests/{topic['id']}",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        # Verify topics are deleted
        response = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"})
        assert len(response.json()) == 0
        
        # Import
        file_content = json.dumps(export_data).encode()
        files = {"file": ("topics.json", BytesIO(file_content), "application/json")}
        
        response = client.post(
            "/api/user/interests/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["results"]["added"] == 3
        
        # Verify topics are restored
        response = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"})
        restored_topics = response.json()
        assert len(restored_topics) == 3
        
        restored_texts = [t["topicText"] for t in restored_topics]
        for topic_text in original_topics:
            assert topic_text in restored_texts
        
        print(f"✓ Successfully completed export/import roundtrip")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        cleanup_test_user(user_id)


if __name__ == "__main__":
    print("=" * 60)
    print("Interest Topic Import/Export Tests")
    print("=" * 60)
    
    test_export_empty_topics()
    test_export_with_topics()
    test_import_valid_json()
    test_import_with_duplicates()
    test_import_invalid_json()
    test_export_import_roundtrip()
    
    print("\n" + "=" * 60)
    print("All import/export tests completed!")
    print("=" * 60)
