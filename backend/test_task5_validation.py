"""
Validation tests for Task 5: Extend data models and database schema
Verifies all requirements from the task are met.
"""
import pytest
from app.models.schemas import (
    InterestTopic,
    InterestTopicWithDescription,
    Message,
    ConversationStatus,
    ChatbotResponse
)
from app.utils.storage import (
    add_interest_topic,
    get_user_interest_topics,
    get_interest_topic_by_id,
    update_conversation_history,
    update_comprehensive_description,
    reset_conversation,
    write_json_file
)
from datetime import datetime


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test"""
    write_json_file("interest_topics.json", {"topics": []})
    write_json_file("users.json", {})
    yield
    write_json_file("interest_topics.json", {"topics": []})
    write_json_file("users.json", {})


def test_requirement_comprehensive_description_field():
    """Verify comprehensiveDescription field exists and works"""
    user_id = "test-user"
    topic = add_interest_topic(user_id, "test topic")
    
    # Field exists with default None
    assert "comprehensiveDescription" in topic
    assert topic["comprehensiveDescription"] is None
    
    # Can be updated
    description = "A comprehensive description of the research interest."
    updated = update_comprehensive_description(topic["id"], user_id, description)
    assert updated["comprehensiveDescription"] == description
    
    # Max 5000 characters enforced
    with pytest.raises(ValueError, match="5000 characters"):
        update_comprehensive_description(topic["id"], user_id, "x" * 5001)


def test_requirement_conversation_history_field():
    """Verify conversationHistory field exists and stores Message objects"""
    user_id = "test-user"
    topic = add_interest_topic(user_id, "test topic")
    
    # Field exists with default None
    assert "conversationHistory" in topic
    assert topic["conversationHistory"] is None
    
    # Can store JSON array of messages
    messages = [
        {"role": "assistant", "content": "Hello", "timestamp": "2024-01-15T10:00:00Z"},
        {"role": "user", "content": "Hi", "timestamp": "2024-01-15T10:01:00Z"}
    ]
    updated = update_conversation_history(topic["id"], user_id, messages, "in_progress")
    assert updated["conversationHistory"] == messages
    assert len(updated["conversationHistory"]) == 2


def test_requirement_conversation_status_field():
    """Verify conversationStatus field exists with enum values"""
    user_id = "test-user"
    topic = add_interest_topic(user_id, "test topic")
    
    # Field exists with default 'not_started'
    assert "conversationStatus" in topic
    assert topic["conversationStatus"] == "not_started"
    
    # Can transition through states
    messages = [{"role": "assistant", "content": "Hi", "timestamp": "2024-01-15T10:00:00Z"}]
    
    # not_started -> in_progress
    updated = update_conversation_history(topic["id"], user_id, messages, "in_progress")
    assert updated["conversationStatus"] == "in_progress"
    
    # in_progress -> completed
    updated = update_comprehensive_description(topic["id"], user_id, "Description")
    assert updated["conversationStatus"] == "completed"
    
    # Can reset back to not_started
    updated = reset_conversation(topic["id"], user_id)
    assert updated["conversationStatus"] == "not_started"


def test_requirement_message_model_created():
    """Verify Message data model exists and works"""
    message = Message(
        role="user",
        content="What is machine learning?",
        timestamp="2024-01-15T10:00:00Z"
    )
    
    assert message.role == "user"
    assert message.content == "What is machine learning?"
    assert message.timestamp == "2024-01-15T10:00:00Z"


def test_requirement_conversation_status_model_created():
    """Verify ConversationStatus enum exists with correct values"""
    assert ConversationStatus.NOT_STARTED.value == "not_started"
    assert ConversationStatus.IN_PROGRESS.value == "in_progress"
    assert ConversationStatus.COMPLETED.value == "completed"


def test_requirement_chatbot_response_model_created():
    """Verify ChatbotResponse model exists and works"""
    response = ChatbotResponse(
        message="Tell me more",
        shouldConclude=False,
        conversationStatus="in_progress"
    )
    
    assert response.message == "Tell me more"
    assert response.shouldConclude is False
    assert response.conversationStatus == "in_progress"


def test_requirement_interest_topic_with_description_model_created():
    """Verify InterestTopicWithDescription model exists and works"""
    messages = [
        Message(role="assistant", content="Hello", timestamp="2024-01-15T10:00:00Z")
    ]
    
    topic = InterestTopicWithDescription(
        id="topic-id",
        userId="user-id",
        topicText="AI research",
        comprehensiveDescription="Detailed description",
        conversationHistory=messages,
        conversationStatus="completed",
        createdAt="2024-01-15T09:00:00Z",
        updatedAt="2024-01-15T10:00:00Z"
    )
    
    assert topic.comprehensiveDescription == "Detailed description"
    assert len(topic.conversationHistory) == 1
    assert topic.conversationStatus == "completed"


def test_requirement_database_access_layer_updated():
    """Verify database access layer handles new fields"""
    user_id = "test-user"
    
    # Test get_interest_topic_by_id
    topic = add_interest_topic(user_id, "test topic")
    retrieved = get_interest_topic_by_id(topic["id"], user_id)
    assert retrieved is not None
    assert "comprehensiveDescription" in retrieved
    assert "conversationHistory" in retrieved
    assert "conversationStatus" in retrieved
    
    # Test update_conversation_history
    messages = [{"role": "assistant", "content": "Hi", "timestamp": "2024-01-15T10:00:00Z"}]
    updated = update_conversation_history(topic["id"], user_id, messages, "in_progress")
    assert updated is not None
    assert updated["conversationHistory"] == messages
    
    # Test update_comprehensive_description
    updated = update_comprehensive_description(topic["id"], user_id, "Description")
    assert updated is not None
    assert updated["comprehensiveDescription"] == "Description"
    
    # Test reset_conversation
    updated = reset_conversation(topic["id"], user_id)
    assert updated is not None
    assert updated["conversationHistory"] is None


def test_requirement_backward_compatibility():
    """Verify backward compatibility with existing topics"""
    user_id = "test-user"
    
    # Create old-style topic without new fields
    old_topic = {
        "id": "old-id",
        "userId": user_id,
        "topicText": "old topic",
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z"
    }
    write_json_file("interest_topics.json", {"topics": [old_topic]})
    
    # Retrieve through storage layer - should add defaults
    topics = get_user_interest_topics(user_id)
    assert len(topics) == 1
    assert topics[0]["comprehensiveDescription"] is None
    assert topics[0]["conversationHistory"] is None
    assert topics[0]["conversationStatus"] == "not_started"
    
    # Retrieve by ID - should add defaults
    topic = get_interest_topic_by_id("old-id", user_id)
    assert topic is not None
    assert topic["comprehensiveDescription"] is None
    assert topic["conversationHistory"] is None
    assert topic["conversationStatus"] == "not_started"


def test_requirement_sensible_defaults():
    """Verify all fields have sensible defaults"""
    user_id = "test-user"
    topic = add_interest_topic(user_id, "new topic")
    
    # comprehensiveDescription defaults to None
    assert topic["comprehensiveDescription"] is None
    
    # conversationHistory defaults to None
    assert topic["conversationHistory"] is None
    
    # conversationStatus defaults to 'not_started'
    assert topic["conversationStatus"] == "not_started"


def test_requirement_ddb_compatible_patterns():
    """Verify data structures are DynamoDB-compatible"""
    user_id = "test-user"
    topic = add_interest_topic(user_id, "test topic")
    
    # conversationHistory stored as JSON array (DDB List of Maps)
    messages = [
        {"role": "assistant", "content": "Hello", "timestamp": "2024-01-15T10:00:00Z"},
        {"role": "user", "content": "Hi", "timestamp": "2024-01-15T10:01:00Z"}
    ]
    updated = update_conversation_history(topic["id"], user_id, messages, "in_progress")
    
    # Verify structure is JSON-serializable (DDB compatible)
    assert isinstance(updated["conversationHistory"], list)
    assert all(isinstance(msg, dict) for msg in updated["conversationHistory"])
    assert all("role" in msg and "content" in msg and "timestamp" in msg 
               for msg in updated["conversationHistory"])
    
    # conversationStatus is string enum (DDB String)
    assert isinstance(updated["conversationStatus"], str)
    assert updated["conversationStatus"] in ["not_started", "in_progress", "completed"]
    
    # comprehensiveDescription is optional string (DDB String)
    description = "Test description"
    updated = update_comprehensive_description(topic["id"], user_id, description)
    assert isinstance(updated["comprehensiveDescription"], str)
