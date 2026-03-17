"""
Manual test script for interest topic API endpoints
Run the server first with: uvicorn app.main:app --reload
Then run this script in another terminal
"""
import requests
import json
from app.utils.security import create_access_token
from app.utils.storage import read_json_file, write_json_file
from datetime import timedelta

BASE_URL = "http://localhost:8000"

def setup_test_user():
    """Create a test user and return auth token"""
    # Create test user
    users = read_json_file("users.json")
    test_email = "apitest@example.com"
    test_user_id = "test-user-api-manual"
    
    users[test_email] = {
        "id": test_user_id,
        "email": test_email,
        "name": "API Test User",
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

def test_api():
    print("=" * 60)
    print("Manual API Test")
    print("=" * 60)
    
    token, user_id = setup_test_user()
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Test 1: List topics (should be empty)
        print("\n1. List topics (empty)...")
        response = requests.get(f"{BASE_URL}/api/user/interests", headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200
        assert len(response.json()) == 0
        print("   ✓ PASSED")
        
        # Test 2: Create a topic
        print("\n2. Create topic...")
        response = requests.post(
            f"{BASE_URL}/api/user/interests",
            headers=headers,
            json={"topicText": "signal integrity"}
        )
        print(f"   Status: {response.status_code}")
        topic1 = response.json()
        print(f"   Response: {json.dumps(topic1, indent=2)}")
        assert response.status_code == 201
        assert topic1["topicText"] == "signal integrity"
        topic1_id = topic1["id"]
        print("   ✓ PASSED")
        
        # Test 3: List topics (should have 1)
        print("\n3. List topics (1 topic)...")
        response = requests.get(f"{BASE_URL}/api/user/interests", headers=headers)
        print(f"   Status: {response.status_code}")
        topics = response.json()
        print(f"   Response: {json.dumps(topics, indent=2)}")
        assert response.status_code == 200
        assert len(topics) == 1
        print("   ✓ PASSED")
        
        # Test 4: Create duplicate (should fail)
        print("\n4. Create duplicate topic...")
        response = requests.post(
            f"{BASE_URL}/api/user/interests",
            headers=headers,
            json={"topicText": "SIGNAL INTEGRITY"}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 409
        print("   ✓ PASSED")
        
        # Test 5: Update topic
        print("\n5. Update topic...")
        response = requests.put(
            f"{BASE_URL}/api/user/interests/{topic1_id}",
            headers=headers,
            json={"topicText": "power integrity"}
        )
        print(f"   Status: {response.status_code}")
        updated = response.json()
        print(f"   Response: {json.dumps(updated, indent=2)}")
        assert response.status_code == 200
        assert updated["topicText"] == "power integrity"
        print("   ✓ PASSED")
        
        # Test 6: Delete topic
        print("\n6. Delete topic...")
        response = requests.delete(
            f"{BASE_URL}/api/user/interests/{topic1_id}",
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200
        print("   ✓ PASSED")
        
        # Test 7: List topics (should be empty again)
        print("\n7. List topics (empty again)...")
        response = requests.get(f"{BASE_URL}/api/user/interests", headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200
        assert len(response.json()) == 0
        print("   ✓ PASSED")
        
        # Test 8: Unauthorized access
        print("\n8. Unauthorized access...")
        response = requests.get(f"{BASE_URL}/api/user/interests")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 401
        print("   ✓ PASSED")
        
        print("\n" + "=" * 60)
        print("All tests PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to server.")
        print("   Make sure the server is running:")
        print("   uvicorn app.main:app --reload")
    finally:
        cleanup_test_user(user_id)
        print("\nCleaned up test data")

if __name__ == "__main__":
    test_api()
