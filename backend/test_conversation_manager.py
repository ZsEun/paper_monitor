"""
Unit tests for ConversationManager service
"""

import pytest
from datetime import datetime
from app.services.conversation_manager import ConversationManager
from app.models.schemas import Message, ConversationStatus
from app.utils.storage import (
    add_interest_topic,
    get_interest_topic_by_id,
    write_json_file
)


@pytest.fixture
def conversation_manager():
    """Create ConversationManager instance"""
    return ConversationManager()


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return "test-user-123"


@pytest.fixture
def test_topic(test_user_id):
    """Create a test interest topic"""
    # Clear existing data
    write_json_file("interest_topics.json", {"topics": []})
    
    # Create a test topic
    topic = add_interest_topic(test_user_id, "machine learning")
    return topic


def test_save_conversation_success(conversation_manager, test_user_id, test_topic):
    """Test saving conversation history successfully"""
    # Create sample conversation
    messages = [
        Message(
            role="assistant",
            content="What specific aspects of machine learning interest you?",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ),
        Message(
            role="user",
            content="I'm interested in neural networks for image classification",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    
    # Save conversation
    conversation_manager.save_conversation(
        topic_id=test_topic["id"],
        user_id=test_user_id,
        conversation_history=messages,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Verify it was saved
    topic = get_interest_topic_by_id(test_topic["id"], test_user_id)
    assert topic is not None
    assert topic["conversationStatus"] == "in_progress"
    assert len(topic["conversationHistory"]) == 2
    assert topic["conversationHistory"][0]["role"] == "assistant"
    assert topic["conversationHistory"][1]["role"] == "user"


def test_save_conversation_unauthorized(conversation_manager, test_topic):
    """Test saving conversation fails for unauthorized user"""
    messages = [
        Message(
            role="assistant",
            content="Hello",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    
    # Try to save with different user ID
    with pytest.raises(ValueError, match="Topic not found or does not belong to user"):
        conversation_manager.save_conversation(
            topic_id=test_topic["id"],
            user_id="different-user-456",
            conversation_history=messages,
            status=ConversationStatus.IN_PROGRESS
        )


def test_save_conversation_nonexistent_topic(conversation_manager, test_user_id):
    """Test saving conversation fails for nonexistent topic"""
    messages = [
        Message(
            role="assistant",
            content="Hello",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    
    with pytest.raises(ValueError, match="Topic not found or does not belong to user"):
        conversation_manager.save_conversation(
            topic_id="nonexistent-topic-id",
            user_id=test_user_id,
            conversation_history=messages,
            status=ConversationStatus.IN_PROGRESS
        )


def test_get_conversation_success(conversation_manager, test_user_id, test_topic):
    """Test retrieving conversation history successfully"""
    # First save a conversation
    messages = [
        Message(
            role="assistant",
            content="What interests you?",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ),
        Message(
            role="user",
            content="Neural networks",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    
    conversation_manager.save_conversation(
        topic_id=test_topic["id"],
        user_id=test_user_id,
        conversation_history=messages,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Retrieve conversation
    history, status = conversation_manager.get_conversation(
        topic_id=test_topic["id"],
        user_id=test_user_id
    )
    
    # Verify retrieved data
    assert len(history) == 2
    assert history[0].role == "assistant"
    assert history[0].content == "What interests you?"
    assert history[1].role == "user"
    assert history[1].content == "Neural networks"
    assert status == ConversationStatus.IN_PROGRESS


def test_get_conversation_empty(conversation_manager, test_user_id, test_topic):
    """Test retrieving conversation when no history exists"""
    # Get conversation without saving anything first
    history, status = conversation_manager.get_conversation(
        topic_id=test_topic["id"],
        user_id=test_user_id
    )
    
    # Should return empty history and not_started status
    assert history == []
    assert status == ConversationStatus.NOT_STARTED


def test_get_conversation_unauthorized(conversation_manager, test_topic):
    """Test retrieving conversation fails for unauthorized user"""
    with pytest.raises(ValueError, match="Topic not found or does not belong to user"):
        conversation_manager.get_conversation(
            topic_id=test_topic["id"],
            user_id="different-user-456"
        )


def test_reset_conversation_success(conversation_manager, test_user_id, test_topic):
    """Test resetting conversation successfully"""
    # First save a conversation
    messages = [
        Message(
            role="assistant",
            content="What interests you?",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ),
        Message(
            role="user",
            content="Neural networks",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    
    conversation_manager.save_conversation(
        topic_id=test_topic["id"],
        user_id=test_user_id,
        conversation_history=messages,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Reset conversation
    conversation_manager.reset_conversation(
        topic_id=test_topic["id"],
        user_id=test_user_id
    )
    
    # Verify conversation was reset
    history, status = conversation_manager.get_conversation(
        topic_id=test_topic["id"],
        user_id=test_user_id
    )
    
    assert history == []
    assert status == ConversationStatus.NOT_STARTED


def test_reset_conversation_unauthorized(conversation_manager, test_topic):
    """Test resetting conversation fails for unauthorized user"""
    with pytest.raises(ValueError, match="Topic not found or does not belong to user"):
        conversation_manager.reset_conversation(
            topic_id=test_topic["id"],
            user_id="different-user-456"
        )


def test_save_description_success(conversation_manager, test_user_id, test_topic):
    """Test saving comprehensive description successfully"""
    description = "Research focused on neural networks for image classification, particularly convolutional architectures and transfer learning approaches."
    
    # Save description
    result = conversation_manager.save_description(
        topic_id=test_topic["id"],
        user_id=test_user_id,
        description=description
    )
    
    # Verify result
    assert result is not None
    assert result["comprehensiveDescription"] == description
    assert result["conversationStatus"] == "completed"
    
    # Verify it was persisted
    topic = get_interest_topic_by_id(test_topic["id"], test_user_id)
    assert topic["comprehensiveDescription"] == description
    assert topic["conversationStatus"] == "completed"


def test_save_description_empty_fails(conversation_manager, test_user_id, test_topic):
    """Test saving empty description fails with validation error"""
    with pytest.raises(ValueError, match="Comprehensive description cannot be empty"):
        conversation_manager.save_description(
            topic_id=test_topic["id"],
            user_id=test_user_id,
            description=""
        )
    
    # Also test whitespace-only
    with pytest.raises(ValueError, match="Comprehensive description cannot be empty"):
        conversation_manager.save_description(
            topic_id=test_topic["id"],
            user_id=test_user_id,
            description="   "
        )


def test_save_description_too_long_fails(conversation_manager, test_user_id, test_topic):
    """Test saving description that exceeds 5000 characters fails"""
    # Create description longer than 5000 characters
    long_description = "A" * 5001
    
    with pytest.raises(ValueError, match="Comprehensive description must be at most 5000 characters"):
        conversation_manager.save_description(
            topic_id=test_topic["id"],
            user_id=test_user_id,
            description=long_description
        )


def test_save_description_unauthorized(conversation_manager, test_topic):
    """Test saving description fails for unauthorized user"""
    with pytest.raises(ValueError, match="Topic not found or does not belong to user"):
        conversation_manager.save_description(
            topic_id=test_topic["id"],
            user_id="different-user-456",
            description="Some description"
        )


def test_save_description_trims_whitespace(conversation_manager, test_user_id, test_topic):
    """Test that description whitespace is trimmed"""
    description = "  Research on neural networks  "
    
    result = conversation_manager.save_description(
        topic_id=test_topic["id"],
        user_id=test_user_id,
        description=description
    )
    
    # Verify whitespace was trimmed
    assert result["comprehensiveDescription"] == "Research on neural networks"


def test_conversation_status_transitions(conversation_manager, test_user_id, test_topic):
    """Test conversation status transitions through the workflow"""
    # Initial status should be not_started
    history, status = conversation_manager.get_conversation(test_topic["id"], test_user_id)
    assert status == ConversationStatus.NOT_STARTED
    
    # Save conversation with in_progress status
    messages = [
        Message(
            role="assistant",
            content="Hello",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    conversation_manager.save_conversation(
        topic_id=test_topic["id"],
        user_id=test_user_id,
        conversation_history=messages,
        status=ConversationStatus.IN_PROGRESS
    )
    
    history, status = conversation_manager.get_conversation(test_topic["id"], test_user_id)
    assert status == ConversationStatus.IN_PROGRESS
    
    # Save description (should transition to completed)
    conversation_manager.save_description(
        topic_id=test_topic["id"],
        user_id=test_user_id,
        description="Comprehensive description"
    )
    
    history, status = conversation_manager.get_conversation(test_topic["id"], test_user_id)
    assert status == ConversationStatus.COMPLETED
    
    # Reset conversation (should go back to not_started)
    conversation_manager.reset_conversation(test_topic["id"], test_user_id)
    
    history, status = conversation_manager.get_conversation(test_topic["id"], test_user_id)
    assert status == ConversationStatus.NOT_STARTED


def test_multiple_conversations_independent(conversation_manager, test_user_id):
    """Test that multiple topics have independent conversation histories"""
    # Clear existing data
    write_json_file("interest_topics.json", {"topics": []})
    
    # Create two topics
    topic1 = add_interest_topic(test_user_id, "machine learning")
    topic2 = add_interest_topic(test_user_id, "signal processing")
    
    # Save different conversations for each
    messages1 = [
        Message(
            role="assistant",
            content="Tell me about ML",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    messages2 = [
        Message(
            role="assistant",
            content="Tell me about signals",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    
    conversation_manager.save_conversation(
        topic_id=topic1["id"],
        user_id=test_user_id,
        conversation_history=messages1,
        status=ConversationStatus.IN_PROGRESS
    )
    
    conversation_manager.save_conversation(
        topic_id=topic2["id"],
        user_id=test_user_id,
        conversation_history=messages2,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Verify conversations are independent
    history1, status1 = conversation_manager.get_conversation(topic1["id"], test_user_id)
    history2, status2 = conversation_manager.get_conversation(topic2["id"], test_user_id)
    
    assert len(history1) == 1
    assert len(history2) == 1
    assert history1[0].content == "Tell me about ML"
    assert history2[0].content == "Tell me about signals"
    
    # Reset one conversation
    conversation_manager.reset_conversation(topic1["id"], test_user_id)
    
    # Verify only topic1 was reset
    history1, status1 = conversation_manager.get_conversation(topic1["id"], test_user_id)
    history2, status2 = conversation_manager.get_conversation(topic2["id"], test_user_id)
    
    assert history1 == []
    assert status1 == ConversationStatus.NOT_STARTED
    assert len(history2) == 1
    assert status2 == ConversationStatus.IN_PROGRESS
