"""
Test script for interest topic storage functionality
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from utils.storage import (
    add_interest_topic,
    get_user_interest_topics,
    update_interest_topic,
    delete_interest_topic,
    count_user_topics
)
from models.schemas import InterestTopicCreate, InterestTopic
from pydantic import ValidationError

def test_interest_topic_validation():
    """Test Pydantic validation for interest topics"""
    print("\n=== Testing Interest Topic Validation ===")
    
    # Test valid topic
    try:
        topic = InterestTopicCreate(topicText="signal integrity")
        print(f"✓ Valid topic created: '{topic.topicText}'")
    except ValidationError as e:
        print(f"✗ Unexpected validation error: {e}")
    
    # Test topic with whitespace (should be trimmed)
    try:
        topic = InterestTopicCreate(topicText="  power integrity  ")
        print(f"✓ Topic with whitespace trimmed: '{topic.topicText}'")
    except ValidationError as e:
        print(f"✗ Unexpected validation error: {e}")
    
    # Test topic too short
    try:
        topic = InterestTopicCreate(topicText="a")
        print(f"✗ Should have rejected topic too short")
    except ValidationError as e:
        print(f"✓ Correctly rejected topic too short: {e.errors()[0]['msg']}")
    
    # Test topic too long
    try:
        topic = InterestTopicCreate(topicText="a" * 201)
        print(f"✗ Should have rejected topic too long")
    except ValidationError as e:
        print(f"✓ Correctly rejected topic too long: {e.errors()[0]['msg']}")
    
    # Test empty topic
    try:
        topic = InterestTopicCreate(topicText="")
        print(f"✗ Should have rejected empty topic")
    except ValidationError as e:
        print(f"✓ Correctly rejected empty topic: {e.errors()[0]['msg']}")
    
    # Test whitespace-only topic
    try:
        topic = InterestTopicCreate(topicText="   ")
        print(f"✗ Should have rejected whitespace-only topic")
    except ValidationError as e:
        print(f"✓ Correctly rejected whitespace-only topic: {e.errors()[0]['msg']}")

def test_interest_topic_storage():
    """Test storage operations for interest topics"""
    print("\n=== Testing Interest Topic Storage ===")
    
    test_user_id = "test-user-123"
    
    # Clean up any existing test data
    try:
        topics = get_user_interest_topics(test_user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], test_user_id)
        print(f"✓ Cleaned up existing test data")
    except Exception as e:
        print(f"Note: {e}")
    
    # Test adding a topic
    try:
        topic1 = add_interest_topic(test_user_id, "signal integrity")
        print(f"✓ Added topic: '{topic1['topicText']}' with ID: {topic1['id']}")
    except Exception as e:
        print(f"✗ Failed to add topic: {e}")
        return
    
    # Test getting topics
    try:
        topics = get_user_interest_topics(test_user_id)
        assert len(topics) == 1, f"Expected 1 topic, got {len(topics)}"
        print(f"✓ Retrieved {len(topics)} topic(s)")
    except Exception as e:
        print(f"✗ Failed to get topics: {e}")
    
    # Test adding another topic
    try:
        topic2 = add_interest_topic(test_user_id, "power integrity")
        print(f"✓ Added second topic: '{topic2['topicText']}'")
    except Exception as e:
        print(f"✗ Failed to add second topic: {e}")
    
    # Test duplicate detection (case-insensitive)
    try:
        add_interest_topic(test_user_id, "SIGNAL INTEGRITY")
        print(f"✗ Should have rejected duplicate topic")
    except ValueError as e:
        print(f"✓ Correctly rejected duplicate topic: {e}")
    
    # Test topic count
    try:
        count = count_user_topics(test_user_id)
        assert count == 2, f"Expected 2 topics, got {count}"
        print(f"✓ Topic count correct: {count}")
    except Exception as e:
        print(f"✗ Failed to count topics: {e}")
    
    # Test updating a topic
    try:
        updated = update_interest_topic(topic1["id"], test_user_id, "EMC design")
        assert updated is not None, "Update returned None"
        assert updated["topicText"] == "EMC design", f"Expected 'EMC design', got '{updated['topicText']}'"
        print(f"✓ Updated topic to: '{updated['topicText']}'")
    except Exception as e:
        print(f"✗ Failed to update topic: {e}")
    
    # Test deleting a topic
    try:
        deleted = delete_interest_topic(topic2["id"], test_user_id)
        assert deleted, "Delete returned False"
        count = count_user_topics(test_user_id)
        assert count == 1, f"Expected 1 topic after delete, got {count}"
        print(f"✓ Deleted topic, count now: {count}")
    except Exception as e:
        print(f"✗ Failed to delete topic: {e}")
    
    # Test whitespace trimming in storage
    try:
        topic3 = add_interest_topic(test_user_id, "  RF design  ")
        assert topic3["topicText"] == "RF design", f"Expected 'RF design', got '{topic3['topicText']}'"
        print(f"✓ Whitespace trimmed in storage: '{topic3['topicText']}'")
    except Exception as e:
        print(f"✗ Failed whitespace trim test: {e}")
    
    # Clean up
    try:
        topics = get_user_interest_topics(test_user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], test_user_id)
        print(f"✓ Cleaned up test data")
    except Exception as e:
        print(f"✗ Failed to clean up: {e}")

def test_user_isolation():
    """Test that topics are isolated between users"""
    print("\n=== Testing User Isolation ===")
    
    user1_id = "user-1"
    user2_id = "user-2"
    
    # Clean up
    for user_id in [user1_id, user2_id]:
        topics = get_user_interest_topics(user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], user_id)
    
    # Add topics for user 1
    try:
        topic1 = add_interest_topic(user1_id, "user 1 topic")
        print(f"✓ Added topic for user 1")
    except Exception as e:
        print(f"✗ Failed to add topic for user 1: {e}")
        return
    
    # Add topics for user 2
    try:
        topic2 = add_interest_topic(user2_id, "user 2 topic")
        print(f"✓ Added topic for user 2")
    except Exception as e:
        print(f"✗ Failed to add topic for user 2: {e}")
        return
    
    # Verify isolation
    try:
        user1_topics = get_user_interest_topics(user1_id)
        user2_topics = get_user_interest_topics(user2_id)
        
        assert len(user1_topics) == 1, f"User 1 should have 1 topic, got {len(user1_topics)}"
        assert len(user2_topics) == 1, f"User 2 should have 1 topic, got {len(user2_topics)}"
        assert user1_topics[0]["topicText"] == "user 1 topic"
        assert user2_topics[0]["topicText"] == "user 2 topic"
        
        print(f"✓ Topics correctly isolated between users")
    except Exception as e:
        print(f"✗ User isolation test failed: {e}")
    
    # Clean up
    for user_id in [user1_id, user2_id]:
        topics = get_user_interest_topics(user_id)
        for topic in topics:
            delete_interest_topic(topic["id"], user_id)

def test_topic_limit():
    """Test the 20 topic limit per user"""
    print("\n=== Testing Topic Limit ===")
    
    test_user_id = "limit-test-user"
    
    # Clean up
    topics = get_user_interest_topics(test_user_id)
    for topic in topics:
        delete_interest_topic(topic["id"], test_user_id)
    
    # Add 20 topics
    try:
        for i in range(20):
            add_interest_topic(test_user_id, f"topic {i}")
        print(f"✓ Successfully added 20 topics")
    except Exception as e:
        print(f"✗ Failed to add 20 topics: {e}")
        return
    
    # Try to add 21st topic
    try:
        add_interest_topic(test_user_id, "topic 21")
        print(f"✗ Should have rejected 21st topic")
    except ValueError as e:
        print(f"✓ Correctly rejected 21st topic: {e}")
    
    # Clean up
    topics = get_user_interest_topics(test_user_id)
    for topic in topics:
        delete_interest_topic(topic["id"], test_user_id)

if __name__ == "__main__":
    print("=" * 60)
    print("Interest Topic Storage Tests")
    print("=" * 60)
    
    test_interest_topic_validation()
    test_interest_topic_storage()
    test_user_isolation()
    test_topic_limit()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
