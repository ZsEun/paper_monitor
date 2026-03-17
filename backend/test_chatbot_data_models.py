"""
Tests for chatbot data model extensions and backward compatibility.
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
    # Setup: Clear data before each test
    write_json_file("interest_topics.json", {"topics": []})
    yield
    # Teardown: Clear data after each test
    write_json_file("interest_topics.json", {"topics": []})


def test_new_topic_has_default_chatbot_fields():
    """Test that newly created topics have default values for chatbot fields"""
    user_id = "test-user-1"
    topic = add_interest_topic(user_id, "signal integrity")
    
    assert topic["comprehensiveDescription"] is None
    assert topic["conversationHistory"] is None
    assert topic["conversationStatus"] == "not_started"


def test_backward_compatibility_with_old_topics():
    """Test that topics without chatbot fields get default values"""
    user_id = "test-user-1"
    
    # Simulate old topic without chatbot fields
    old_topic = {
        "id": "old-topic-id",
        "userId": user_id,
        "topicText": "machine learning",
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z"
    }
    
    write_json_file("interest_topics.json", {"topics": [old_topic]})
    
    # Retrieve topics - should add default values
    topics = get_user_interest_topics(user_id)
    
    assert len(topics) == 1
    assert topics[0]["comprehensiveDescription"] is None
    assert topics[0]["conversationHistory"] is None
    assert topics[0]["conversationStatus"] == "not_started"


def test_update_conversation_history():
    """Test updating conversation history and status"""
    user_id = "test-user-1"
    topic = add_interest_topic(user_id, "quantum computing")
    
    # Create conversation history
    conversation = [
        {"role": "assistant", "content": "What research interest would you like to define?", "timestamp": datetime.utcnow().isoformat() + "Z"},
        {"role": "user", "content": "quantum computing", "timestamp": datetime.utcnow().isoformat() + "Z"}
    ]
    
    # Update conversation
    updated = update_conversation_history(topic["id"], user_id, conversation, "in_progress")
    
    assert updated is not None
    assert updated["conversationHistory"] == conversation
    assert updated["conversationStatus"] == "in_progress"
    
    # Verify persistence
    retrieved = get_interest_topic_by_id(topic["id"], user_id)
    assert retrieved["conversationHistory"] == conversation
    assert retrieved["conversationStatus"] == "in_progress"


def test_update_comprehensive_description():
    """Test updating comprehensive description"""
    user_id = "test-user-1"
    topic = add_interest_topic(user_id, "neural networks")
    
    description = "Research focused on deep neural networks for image recognition, specifically convolutional architectures."
    
    # Update description
    updated = update_comprehensive_description(topic["id"], user_id, description)
    
    assert updated is not None
    assert updated["comprehensiveDescription"] == description
    assert updated["conversationStatus"] == "completed"

def test_comprehensive_description_validation():
    """Test validation of comprehensive description"""
    user_id = "test-user-1"
    topic = add_interest_topic(user_id, "robotics")
    
    # Test empty description
    with pytest.raises(ValueError, match="cannot be empty"):
        update_comprehensive_description(topic["id"], user_id, "")
    
    with pytest.raises(ValueError, match="cannot be empty"):
        update_comprehensive_description(topic["id"], user_id, "   ")
    
    # Test description too long
    long_description = "x" * 5001
    with pytest.raises(ValueError, match="at most 5000 characters"):
        update_comprehensive_description(topic["id"], user_id, long_description)
    
    # Test valid description
    valid_description = "Research on autonomous robotics systems."
    updated = update_comprehensive_description(topic["id"], user_id, valid_description)
    assert updated["comprehensiveDescription"] == valid_description


def test_reset_conversation():
    """Test resetting conversation history"""
    user_id = "test-user-1"
    topic = add_interest_topic(user_id, "AI ethics")
    
    # Add conversation history
    conversation = [
        {"role": "assistant", "content": "Hello!", "timestamp": datetime.utcnow().isoformat() + "Z"}
    ]
    update_conversation_history(topic["id"], user_id, conversation, "in_progress")
    
    # Verify conversation exists
    retrieved = get_interest_topic_by_id(topic["id"], user_id)
    assert retrieved["conversationHistory"] is not None
    assert retrieved["conversationStatus"] == "in_progress"
    
    # Reset conversation
    reset_result = reset_conversation(topic["id"], user_id)
    
    assert reset_result is not None
    assert reset_result["conversationHistory"] is None
    assert reset_result["conversationStatus"] == "not_started"


def test_get_topic_by_id_with_authorization():
    """Test that get_interest_topic_by_id respects user authorization"""
    user1_id = "user-1"
    user2_id = "user-2"
    
    topic1 = add_interest_topic(user1_id, "topic 1")
    
    # User 1 can access their topic
    retrieved = get_interest_topic_by_id(topic1["id"], user1_id)
    assert retrieved is not None
    assert retrieved["id"] == topic1["id"]
    
    # User 2 cannot access user 1's topic
    retrieved = get_interest_topic_by_id(topic1["id"], user2_id)
    assert retrieved is None


def test_conversation_status_transitions():
    """Test conversation status transitions"""
    user_id = "test-user-1"
    topic = add_interest_topic(user_id, "blockchain")
    
    # Initial status
    assert topic["conversationStatus"] == "not_started"
    
    # Start conversation
    conversation = [{"role": "assistant", "content": "Hi", "timestamp": datetime.utcnow().isoformat() + "Z"}]
    updated = update_conversation_history(topic["id"], user_id, conversation, "in_progress")
    assert updated["conversationStatus"] == "in_progress"
    
    # Complete conversation with description
    description = "Blockchain technology for supply chain management."
    updated = update_comprehensive_description(topic["id"], user_id, description)
    assert updated["conversationStatus"] == "completed"


def test_message_model():
    """Test Message model validation"""
    message = Message(
        role="user",
        content="What is signal integrity?",
        timestamp="2024-01-15T10:00:00Z"
    )
    
    assert message.role == "user"
    assert message.content == "What is signal integrity?"
    assert message.timestamp == "2024-01-15T10:00:00Z"


def test_chatbot_response_model():
    """Test ChatbotResponse model"""
    response = ChatbotResponse(
        message="Tell me more about your research focus.",
        shouldConclude=False,
        conversationStatus="in_progress"
    )
    
    assert response.message == "Tell me more about your research focus."
    assert response.shouldConclude is False
    assert response.conversationStatus == "in_progress"


def test_interest_topic_with_description_model():
    """Test InterestTopicWithDescription model with Message objects"""
    messages = [
        Message(role="assistant", content="Hello", timestamp="2024-01-15T10:00:00Z"),
        Message(role="user", content="Hi", timestamp="2024-01-15T10:01:00Z")
    ]
    
    topic = InterestTopicWithDescription(
        id="topic-id",
        userId="user-id",
        topicText="AI safety",
        comprehensiveDescription="Research on AI alignment and safety.",
        conversationHistory=messages,
        conversationStatus="completed",
        createdAt="2024-01-15T09:00:00Z",
        updatedAt="2024-01-15T10:05:00Z"
    )
    
    assert topic.comprehensiveDescription == "Research on AI alignment and safety."
    assert len(topic.conversationHistory) == 2
    assert topic.conversationHistory[0].role == "assistant"
    assert topic.conversationStatus == "completed"
