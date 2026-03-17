"""
Test script for cascade deletion of interest topics.
Verifies that deleting a topic also deletes conversation history and comprehensive description.

Requirements: 11.4

Test Coverage:
1. Cascade delete conversation history - Verifies conversationHistory is deleted with topic
2. Cascade delete comprehensive description - Verifies comprehensiveDescription is deleted with topic
3. Cascade delete all fields - Verifies both conversationHistory and comprehensiveDescription are deleted
4. Cascade delete isolation - Verifies deleting one topic doesn't affect other topics
5. Cascade delete via API - Verifies cascade deletion works through the REST API
6. Delete without conversation data - Verifies deletion works for topics without conversation data (backward compatibility)
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from utils.storage import (
    add_interest_topic,
    get_user_interest_topics,
    get_interest_topic_by_id,
    delete_interest_topic,
    update_conversation_history,
    update_comprehensive_description
)
from datetime import datetime


def test_cascade_delete_conversation_history():
    """Test that deleting a topic also deletes its conversation history"""
    print("\n=== Test: Cascade Delete Conversation History ===")
    
    test_user_id = "cascade-test-user-1"
    
    # Clean up any existing test data
    topics = get_user_interest_topics(test_user_id)
    for topic in topics:
        delete_interest_topic(topic["id"], test_user_id)
    
    try:
        # Create a topic
        topic = add_interest_topic(test_user_id, "signal integrity")
        topic_id = topic["id"]
        print(f"✓ Created topic: {topic['topicText']}")
        
        # Add conversation history
        conversation_history = [
            {
                "role": "user",
                "content": "I'm interested in signal integrity",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            {
                "role": "assistant",
                "content": "Great! Can you tell me more about specific aspects?",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ]
        
        updated_topic = update_conversation_history(
            topic_id,
            test_user_id,
            conversation_history,
            "in_progress"
        )
        
        assert updated_topic is not None, "Failed to update conversation history"
        assert updated_topic["conversationHistory"] is not None
        assert len(updated_topic["conversationHistory"]) == 2
        print(f"✓ Added conversation history with {len(conversation_history)} messages")
        
        # Verify conversation history exists before deletion
        topic_before = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_before is not None
        assert topic_before["conversationHistory"] is not None
        assert len(topic_before["conversationHistory"]) == 2
        print(f"✓ Verified conversation history exists before deletion")
        
        # Delete the topic
        deleted = delete_interest_topic(topic_id, test_user_id)
        assert deleted, "Delete operation failed"
        print(f"✓ Deleted topic")
        
        # Verify topic and conversation history are gone
        topic_after = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_after is None, "Topic should be deleted"
        print(f"✓ Verified topic and conversation history are cascade deleted")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        # Clean up
        topics = get_user_interest_topics(test_user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], test_user_id)


def test_cascade_delete_comprehensive_description():
    """Test that deleting a topic also deletes its comprehensive description"""
    print("\n=== Test: Cascade Delete Comprehensive Description ===")
    
    test_user_id = "cascade-test-user-2"
    
    # Clean up any existing test data
    topics = get_user_interest_topics(test_user_id)
    for topic in topics:
        delete_interest_topic(topic["id"], test_user_id)
    
    try:
        # Create a topic
        topic = add_interest_topic(test_user_id, "power integrity")
        topic_id = topic["id"]
        print(f"✓ Created topic: {topic['topicText']}")
        
        # Add comprehensive description
        description = "Research focused on power integrity in high-speed digital circuits, " \
                     "including power distribution network design, decoupling capacitor placement, " \
                     "and voltage droop analysis."
        
        updated_topic = update_comprehensive_description(
            topic_id,
            test_user_id,
            description
        )
        
        assert updated_topic is not None, "Failed to update description"
        assert updated_topic["comprehensiveDescription"] == description
        print(f"✓ Added comprehensive description ({len(description)} characters)")
        
        # Verify description exists before deletion
        topic_before = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_before is not None
        assert topic_before["comprehensiveDescription"] == description
        print(f"✓ Verified comprehensive description exists before deletion")
        
        # Delete the topic
        deleted = delete_interest_topic(topic_id, test_user_id)
        assert deleted, "Delete operation failed"
        print(f"✓ Deleted topic")
        
        # Verify topic and description are gone
        topic_after = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_after is None, "Topic should be deleted"
        print(f"✓ Verified topic and comprehensive description are cascade deleted")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        # Clean up
        topics = get_user_interest_topics(test_user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], test_user_id)


def test_cascade_delete_all_fields():
    """Test that deleting a topic deletes all associated fields"""
    print("\n=== Test: Cascade Delete All Fields ===")
    
    test_user_id = "cascade-test-user-3"
    
    # Clean up any existing test data
    topics = get_user_interest_topics(test_user_id)
    for topic in topics:
        delete_interest_topic(topic["id"], test_user_id)
    
    try:
        # Create a topic
        topic = add_interest_topic(test_user_id, "EMC design")
        topic_id = topic["id"]
        print(f"✓ Created topic: {topic['topicText']}")
        
        # Add both conversation history and comprehensive description
        conversation_history = [
            {
                "role": "user",
                "content": "I want to learn about EMC design",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            {
                "role": "assistant",
                "content": "Tell me about specific aspects you're interested in",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            {
                "role": "user",
                "content": "I'm interested in PCB layout techniques",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ]
        
        update_conversation_history(
            topic_id,
            test_user_id,
            conversation_history,
            "in_progress"
        )
        print(f"✓ Added conversation history with {len(conversation_history)} messages")
        
        description = "Research on electromagnetic compatibility design with focus on " \
                     "PCB layout techniques, grounding strategies, and shielding methods."
        
        update_comprehensive_description(
            topic_id,
            test_user_id,
            description
        )
        print(f"✓ Added comprehensive description")
        
        # Verify all fields exist before deletion
        topic_before = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_before is not None
        assert topic_before["conversationHistory"] is not None
        assert len(topic_before["conversationHistory"]) == 3
        assert topic_before["comprehensiveDescription"] == description
        assert topic_before["conversationStatus"] == "completed"
        print(f"✓ Verified all fields exist before deletion")
        
        # Delete the topic
        deleted = delete_interest_topic(topic_id, test_user_id)
        assert deleted, "Delete operation failed"
        print(f"✓ Deleted topic")
        
        # Verify everything is gone
        topic_after = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_after is None, "Topic should be completely deleted"
        print(f"✓ Verified complete cascade deletion of all fields")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        # Clean up
        topics = get_user_interest_topics(test_user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], test_user_id)


def test_cascade_delete_multiple_topics():
    """Test that deleting one topic doesn't affect other topics"""
    print("\n=== Test: Cascade Delete Isolation ===")
    
    test_user_id = "cascade-test-user-4"
    
    # Clean up any existing test data
    topics = get_user_interest_topics(test_user_id)
    for topic in topics:
        delete_interest_topic(topic["id"], test_user_id)
    
    try:
        # Create two topics with conversation data
        topic1 = add_interest_topic(test_user_id, "topic 1")
        topic2 = add_interest_topic(test_user_id, "topic 2")
        
        # Add data to both topics
        conversation1 = [
            {"role": "user", "content": "Message 1", "timestamp": datetime.utcnow().isoformat() + "Z"}
        ]
        conversation2 = [
            {"role": "user", "content": "Message 2", "timestamp": datetime.utcnow().isoformat() + "Z"}
        ]
        
        update_conversation_history(topic1["id"], test_user_id, conversation1, "in_progress")
        update_conversation_history(topic2["id"], test_user_id, conversation2, "in_progress")
        
        update_comprehensive_description(topic1["id"], test_user_id, "Description 1")
        update_comprehensive_description(topic2["id"], test_user_id, "Description 2")
        
        print(f"✓ Created two topics with conversation data")
        
        # Delete topic 1
        deleted = delete_interest_topic(topic1["id"], test_user_id)
        assert deleted, "Delete operation failed"
        print(f"✓ Deleted topic 1")
        
        # Verify topic 1 is gone
        topic1_after = get_interest_topic_by_id(topic1["id"], test_user_id)
        assert topic1_after is None, "Topic 1 should be deleted"
        print(f"✓ Verified topic 1 is deleted")
        
        # Verify topic 2 still exists with all its data
        topic2_after = get_interest_topic_by_id(topic2["id"], test_user_id)
        assert topic2_after is not None, "Topic 2 should still exist"
        assert topic2_after["conversationHistory"] is not None
        assert len(topic2_after["conversationHistory"]) == 1
        assert topic2_after["comprehensiveDescription"] == "Description 2"
        print(f"✓ Verified topic 2 still exists with all data intact")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        # Clean up
        topics = get_user_interest_topics(test_user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], test_user_id)


def test_cascade_delete_via_api():
    """Test cascade deletion through the API endpoint"""
    print("\n=== Test: Cascade Delete via API ===")
    
    from starlette.testclient import TestClient
    from app.main import app
    from app.utils.security import create_access_token
    from datetime import timedelta
    
    client = TestClient(app)
    test_user_id = "cascade-api-test-user"
    test_email = "cascade@example.com"
    
    # Setup test user
    from app.utils.storage import read_json_file, write_json_file
    users = read_json_file("users.json")
    users[test_email] = {
        "id": test_user_id,
        "email": test_email,
        "name": "Cascade Test User",
        "password": "hashed_password"
    }
    write_json_file("users.json", users)
    
    token = create_access_token(
        data={"sub": test_email},
        expires_delta=timedelta(minutes=30)
    )
    
    try:
        # Create a topic via API
        response1 = client.post(
            "/api/user/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"topicText": "API test topic"}
        )
        assert response1.status_code == 201
        topic = response1.json()
        topic_id = topic["id"]
        print(f"✓ Created topic via API")
        
        # Add conversation history directly (simulating chatbot interaction)
        conversation = [
            {"role": "user", "content": "Test message", "timestamp": datetime.utcnow().isoformat() + "Z"}
        ]
        update_conversation_history(topic_id, test_user_id, conversation, "in_progress")
        
        # Add comprehensive description
        update_comprehensive_description(topic_id, test_user_id, "Test description for API cascade delete")
        print(f"✓ Added conversation history and description")
        
        # Verify data exists
        topic_before = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_before["conversationHistory"] is not None
        assert topic_before["comprehensiveDescription"] is not None
        print(f"✓ Verified data exists before deletion")
        
        # Delete via API
        response2 = client.delete(
            f"/api/user/interests/{topic_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response2.status_code == 200
        result = response2.json()
        assert result["success"] is True
        print(f"✓ Deleted topic via API")
        
        # Verify complete deletion
        topic_after = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_after is None, "Topic should be completely deleted"
        print(f"✓ Verified cascade deletion via API")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        # Clean up
        topics = get_user_interest_topics(test_user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], test_user_id)
        
        # Clean up user
        users = read_json_file("users.json")
        users = {k: v for k, v in users.items() if v.get("id") != test_user_id}
        write_json_file("users.json", users)


def test_cascade_delete_without_conversation_data():
    """Test that deleting a topic without conversation data works correctly"""
    print("\n=== Test: Delete Topic Without Conversation Data ===")
    
    test_user_id = "cascade-test-user-5"
    
    # Clean up any existing test data
    topics = get_user_interest_topics(test_user_id)
    for topic in topics:
        delete_interest_topic(topic["id"], test_user_id)
    
    try:
        # Create a topic without any conversation data
        topic = add_interest_topic(test_user_id, "simple topic")
        topic_id = topic["id"]
        print(f"✓ Created topic without conversation data")
        
        # Verify no conversation data exists
        topic_before = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_before["conversationHistory"] is None
        assert topic_before["comprehensiveDescription"] is None
        assert topic_before["conversationStatus"] == "not_started"
        print(f"✓ Verified topic has no conversation data")
        
        # Delete the topic
        deleted = delete_interest_topic(topic_id, test_user_id)
        assert deleted, "Delete operation failed"
        print(f"✓ Deleted topic")
        
        # Verify deletion
        topic_after = get_interest_topic_by_id(topic_id, test_user_id)
        assert topic_after is None, "Topic should be deleted"
        print(f"✓ Verified deletion works for topics without conversation data")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        # Clean up
        topics = get_user_interest_topics(test_user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], test_user_id)


if __name__ == "__main__":
    print("=" * 60)
    print("Cascade Deletion Tests")
    print("=" * 60)
    
    test_cascade_delete_conversation_history()
    test_cascade_delete_comprehensive_description()
    test_cascade_delete_all_fields()
    test_cascade_delete_multiple_topics()
    test_cascade_delete_via_api()
    test_cascade_delete_without_conversation_data()
    
    print("\n" + "=" * 60)
    print("All cascade deletion tests completed!")
    print("=" * 60)
