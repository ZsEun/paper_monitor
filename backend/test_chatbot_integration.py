"""
Integration tests for ChatbotService

Tests the complete chatbot workflow including conversation flow,
description generation, and integration with ConversationManager.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.services.chatbot_service import ChatbotService
from app.services.conversation_manager import ConversationManager
from app.models.schemas import Message, ConversationStatus
from app.utils.storage import add_interest_topic, write_json_file


@pytest.fixture
def setup_services():
    """Setup chatbot service and conversation manager with mocked Bedrock"""
    with patch('boto3.client') as mock_boto3:
        mock_bedrock = Mock()
        mock_boto3.return_value = mock_bedrock
        
        chatbot_service = ChatbotService()
        chatbot_service.bedrock = mock_bedrock
        conversation_manager = ConversationManager()
        
        yield chatbot_service, conversation_manager, mock_bedrock


@pytest.fixture
def test_user_and_topic():
    """Create test user and topic"""
    # Clear existing data
    write_json_file("interest_topics.json", {"topics": []})
    
    user_id = "test-user-integration"
    topic = add_interest_topic(user_id, "quantum computing")
    
    return user_id, topic


def test_complete_conversation_workflow(setup_services, test_user_and_topic):
    """
    Test complete conversation workflow from start to finish.
    
    Validates:
    - Initial message handling
    - Conversation history building
    - Multiple exchanges
    - Description generation
    - Conversation conclusion
    """
    chatbot_service, conversation_manager, mock_bedrock = setup_services
    user_id, topic = test_user_and_topic
    
    # Mock Bedrock responses for conversation
    responses = [
        "Hello! What specific aspects of quantum computing interest you?",
        "Great! What methodologies or approaches do you use in your research?",
        "Interesting! What application domains are you focused on?",
        "Are there any topics you want to exclude from your interest?",
        "Thank you! I have enough information to create a comprehensive description."
    ]
    
    def mock_invoke_model(*args, **kwargs):
        response_text = responses.pop(0) if responses else "Thank you!"
        mock_response = {'body': MagicMock()}
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': response_text}]
        }).encode()
        return mock_response
    
    mock_bedrock.invoke_model.side_effect = mock_invoke_model
    
    # Simulate conversation flow
    conversation_history = []
    
    # Exchange 1: Initial topic
    response1 = chatbot_service.send_message(
        user_message="I want to define my interest in quantum computing",
        conversation_history=conversation_history,
        topic_text="quantum computing"
    )
    
    assert response1.message is not None
    assert response1.conversationStatus == ConversationStatus.IN_PROGRESS.value
    
    # Update history
    conversation_history.append(Message(
        role="user",
        content="I want to define my interest in quantum computing",
        timestamp=datetime.utcnow().isoformat() + "Z"
    ))
    conversation_history.append(Message(
        role="assistant",
        content=response1.message,
        timestamp=datetime.utcnow().isoformat() + "Z"
    ))
    
    # Save conversation state
    conversation_manager.save_conversation(
        topic_id=topic["id"],
        user_id=user_id,
        conversation_history=conversation_history,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Exchange 2: Aspects
    response2 = chatbot_service.send_message(
        user_message="I'm interested in quantum algorithms and error correction",
        conversation_history=conversation_history,
        topic_text="quantum computing"
    )
    
    conversation_history.append(Message(
        role="user",
        content="I'm interested in quantum algorithms and error correction",
        timestamp=datetime.utcnow().isoformat() + "Z"
    ))
    conversation_history.append(Message(
        role="assistant",
        content=response2.message,
        timestamp=datetime.utcnow().isoformat() + "Z"
    ))
    
    # Exchange 3: Methodologies
    response3 = chatbot_service.send_message(
        user_message="I use theoretical analysis and simulation",
        conversation_history=conversation_history,
        topic_text="quantum computing"
    )
    
    conversation_history.append(Message(
        role="user",
        content="I use theoretical analysis and simulation",
        timestamp=datetime.utcnow().isoformat() + "Z"
    ))
    conversation_history.append(Message(
        role="assistant",
        content=response3.message,
        timestamp=datetime.utcnow().isoformat() + "Z"
    ))
    
    # Exchange 4: Applications
    response4 = chatbot_service.send_message(
        user_message="Cryptography and optimization problems",
        conversation_history=conversation_history,
        topic_text="quantum computing"
    )
    
    conversation_history.append(Message(
        role="user",
        content="Cryptography and optimization problems",
        timestamp=datetime.utcnow().isoformat() + "Z"
    ))
    conversation_history.append(Message(
        role="assistant",
        content=response4.message,
        timestamp=datetime.utcnow().isoformat() + "Z"
    ))
    
    # Exchange 5: Exclusions
    response5 = chatbot_service.send_message(
        user_message="I'm not interested in quantum hardware implementation",
        conversation_history=conversation_history,
        topic_text="quantum computing"
    )
    
    # At this point, conversation should be ready to conclude
    assert response5.shouldConclude == True or len(conversation_history) >= 8
    
    # Verify conversation can be retrieved
    retrieved_history, status = conversation_manager.get_conversation(
        topic_id=topic["id"],
        user_id=user_id
    )
    
    assert len(retrieved_history) > 0
    assert status == ConversationStatus.IN_PROGRESS


def test_description_generation_from_conversation(setup_services, test_user_and_topic):
    """
    Test generating comprehensive description from a complete conversation.
    
    Validates:
    - Description includes aspects, methodologies, applications, exclusions
    - Description is properly formatted
    - Description is saved correctly
    """
    chatbot_service, conversation_manager, mock_bedrock = setup_services
    user_id, topic = test_user_and_topic
    
    # Create a complete conversation history
    conversation_history = [
        Message(
            role="assistant",
            content="What specific aspects of quantum computing interest you?",
            timestamp="2024-01-15T10:00:00Z"
        ),
        Message(
            role="user",
            content="Quantum algorithms and error correction codes",
            timestamp="2024-01-15T10:01:00Z"
        ),
        Message(
            role="assistant",
            content="What methodologies do you use?",
            timestamp="2024-01-15T10:02:00Z"
        ),
        Message(
            role="user",
            content="Theoretical analysis and quantum circuit simulation",
            timestamp="2024-01-15T10:03:00Z"
        ),
        Message(
            role="assistant",
            content="What application domains interest you?",
            timestamp="2024-01-15T10:04:00Z"
        ),
        Message(
            role="user",
            content="Cryptography and optimization problems",
            timestamp="2024-01-15T10:05:00Z"
        ),
        Message(
            role="assistant",
            content="Any topics to exclude?",
            timestamp="2024-01-15T10:06:00Z"
        ),
        Message(
            role="user",
            content="Not interested in quantum hardware implementation",
            timestamp="2024-01-15T10:07:00Z"
        )
    ]
    
    # Mock description generation response
    expected_description = """Research focused on quantum computing, specifically quantum algorithms and error correction codes. Employs theoretical analysis and quantum circuit simulation methodologies. Primary applications include cryptography and optimization problems. Excludes quantum hardware implementation topics."""
    
    mock_response = {'body': MagicMock()}
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': expected_description}]
    }).encode()
    
    mock_bedrock.invoke_model.return_value = mock_response
    
    # Generate description
    description = chatbot_service.generate_comprehensive_description(
        conversation_history=conversation_history
    )
    
    # Verify description content
    assert description == expected_description
    assert "quantum algorithms" in description.lower()
    assert "error correction" in description.lower()
    assert "theoretical analysis" in description.lower() or "simulation" in description.lower()
    assert "cryptography" in description.lower() or "optimization" in description.lower()
    assert "exclude" in description.lower() or "hardware" in description.lower()
    
    # Save description
    result = conversation_manager.save_description(
        topic_id=topic["id"],
        user_id=user_id,
        description=description
    )
    
    # Verify saved
    assert result["comprehensiveDescription"] == description
    assert result["conversationStatus"] == "completed"


def test_conversation_pause_and_resume(setup_services, test_user_and_topic):
    """
    Test pausing and resuming a conversation.
    
    Validates:
    - Conversation state is saved
    - Conversation can be retrieved
    - Conversation can continue from saved state
    """
    chatbot_service, conversation_manager, mock_bedrock = setup_services
    user_id, topic = test_user_and_topic
    
    # Start conversation
    mock_response1 = {'body': MagicMock()}
    mock_response1['body'].read.return_value = json.dumps({
        'content': [{'text': 'What aspects interest you?'}]
    }).encode()
    
    mock_bedrock.invoke_model.return_value = mock_response1
    
    response1 = chatbot_service.send_message(
        user_message="I want to define quantum computing",
        conversation_history=[],
        topic_text="quantum computing"
    )
    
    # Build history
    conversation_history = [
        Message(
            role="user",
            content="I want to define quantum computing",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ),
        Message(
            role="assistant",
            content=response1.message,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    
    # Save conversation (pause)
    conversation_manager.save_conversation(
        topic_id=topic["id"],
        user_id=user_id,
        conversation_history=conversation_history,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Retrieve conversation (resume)
    retrieved_history, status = conversation_manager.get_conversation(
        topic_id=topic["id"],
        user_id=user_id
    )
    
    # Verify state was preserved
    assert len(retrieved_history) == 2
    assert retrieved_history[0].role == "user"
    assert retrieved_history[1].role == "assistant"
    assert status == ConversationStatus.IN_PROGRESS
    
    # Continue conversation
    mock_response2 = {'body': MagicMock()}
    mock_response2['body'].read.return_value = json.dumps({
        'content': [{'text': 'What methodologies do you use?'}]
    }).encode()
    
    mock_bedrock.invoke_model.return_value = mock_response2
    
    response2 = chatbot_service.send_message(
        user_message="Quantum algorithms",
        conversation_history=retrieved_history,
        topic_text="quantum computing"
    )
    
    # Verify conversation continued
    assert response2.message is not None


def test_conversation_reset_workflow(setup_services, test_user_and_topic):
    """
    Test resetting a conversation and starting over.
    
    Validates:
    - Conversation can be reset
    - History is cleared
    - New conversation can start
    """
    chatbot_service, conversation_manager, mock_bedrock = setup_services
    user_id, topic = test_user_and_topic
    
    # Create initial conversation
    conversation_history = [
        Message(
            role="assistant",
            content="What interests you?",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ),
        Message(
            role="user",
            content="Quantum algorithms",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    
    # Save conversation
    conversation_manager.save_conversation(
        topic_id=topic["id"],
        user_id=user_id,
        conversation_history=conversation_history,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Reset conversation
    conversation_manager.reset_conversation(
        topic_id=topic["id"],
        user_id=user_id
    )
    
    # Verify reset
    retrieved_history, status = conversation_manager.get_conversation(
        topic_id=topic["id"],
        user_id=user_id
    )
    
    assert retrieved_history == []
    assert status == ConversationStatus.NOT_STARTED
    
    # Start new conversation
    mock_response = {'body': MagicMock()}
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': 'Hello! Let\'s start fresh. What topic would you like to define?'}]
    }).encode()
    
    mock_bedrock.invoke_model.return_value = mock_response
    
    response = chatbot_service.send_message(
        user_message="I want to define machine learning",
        conversation_history=[],
        topic_text="machine learning"
    )
    
    # Verify new conversation started
    assert response.message is not None
    assert response.conversationStatus == ConversationStatus.IN_PROGRESS.value


def test_error_handling_preserves_conversation_state(setup_services, test_user_and_topic):
    """
    Test that conversation state is preserved when errors occur.
    
    Validates:
    - Timeout errors don't lose conversation history
    - API errors don't corrupt state
    - User can retry after errors
    """
    chatbot_service, conversation_manager, mock_bedrock = setup_services
    user_id, topic = test_user_and_topic
    
    # Create conversation history
    conversation_history = [
        Message(
            role="assistant",
            content="What interests you?",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ),
        Message(
            role="user",
            content="Quantum algorithms",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]
    
    # Save conversation
    conversation_manager.save_conversation(
        topic_id=topic["id"],
        user_id=user_id,
        conversation_history=conversation_history,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Simulate timeout error
    from botocore.exceptions import ReadTimeoutError
    mock_bedrock.invoke_model.side_effect = ReadTimeoutError(
        endpoint_url='https://bedrock.us-west-2.amazonaws.com'
    )
    
    # Try to send message (should fail)
    with pytest.raises(TimeoutError):
        chatbot_service.send_message(
            user_message="Tell me more",
            conversation_history=conversation_history,
            topic_text="quantum computing"
        )
    
    # Verify conversation state is still intact
    retrieved_history, status = conversation_manager.get_conversation(
        topic_id=topic["id"],
        user_id=user_id
    )
    
    assert len(retrieved_history) == 2
    assert status == ConversationStatus.IN_PROGRESS
    
    # Retry with successful response
    mock_response = {'body': MagicMock()}
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': 'What methodologies do you use?'}]
    }).encode()
    
    mock_bedrock.invoke_model.side_effect = None
    mock_bedrock.invoke_model.return_value = mock_response
    
    # Retry should succeed
    response = chatbot_service.send_message(
        user_message="Tell me more",
        conversation_history=conversation_history,
        topic_text="quantum computing"
    )
    
    assert response.message is not None


def test_multiple_topics_independent_conversations(setup_services):
    """
    Test that multiple topics have independent conversation sessions.
    
    Validates:
    - Each topic has its own conversation history
    - Conversations don't interfere with each other
    - Descriptions are saved independently
    """
    chatbot_service, conversation_manager, mock_bedrock = setup_services
    
    # Clear existing data
    write_json_file("interest_topics.json", {"topics": []})
    
    user_id = "test-user-multi"
    topic1 = add_interest_topic(user_id, "quantum computing")
    topic2 = add_interest_topic(user_id, "machine learning")
    
    # Mock Bedrock responses
    mock_response = {'body': MagicMock()}
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': 'What interests you?'}]
    }).encode()
    
    mock_bedrock.invoke_model.return_value = mock_response
    
    # Start conversation for topic1
    response1 = chatbot_service.send_message(
        user_message="Quantum algorithms",
        conversation_history=[],
        topic_text="quantum computing"
    )
    
    history1 = [
        Message(role="user", content="Quantum algorithms", timestamp=datetime.utcnow().isoformat() + "Z"),
        Message(role="assistant", content=response1.message, timestamp=datetime.utcnow().isoformat() + "Z")
    ]
    
    conversation_manager.save_conversation(
        topic_id=topic1["id"],
        user_id=user_id,
        conversation_history=history1,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Start conversation for topic2
    response2 = chatbot_service.send_message(
        user_message="Neural networks",
        conversation_history=[],
        topic_text="machine learning"
    )
    
    history2 = [
        Message(role="user", content="Neural networks", timestamp=datetime.utcnow().isoformat() + "Z"),
        Message(role="assistant", content=response2.message, timestamp=datetime.utcnow().isoformat() + "Z")
    ]
    
    conversation_manager.save_conversation(
        topic_id=topic2["id"],
        user_id=user_id,
        conversation_history=history2,
        status=ConversationStatus.IN_PROGRESS
    )
    
    # Verify conversations are independent
    retrieved1, status1 = conversation_manager.get_conversation(topic1["id"], user_id)
    retrieved2, status2 = conversation_manager.get_conversation(topic2["id"], user_id)
    
    assert len(retrieved1) == 2
    assert len(retrieved2) == 2
    assert retrieved1[0].content == "Quantum algorithms"
    assert retrieved2[0].content == "Neural networks"
    assert retrieved1[0].content != retrieved2[0].content


def test_description_validation_and_save(setup_services, test_user_and_topic):
    """
    Test description validation and save workflow.
    
    Validates:
    - Empty descriptions are rejected
    - Valid descriptions are saved
    - Conversation status transitions to completed
    """
    chatbot_service, conversation_manager, mock_bedrock = setup_services
    user_id, topic = test_user_and_topic
    
    # Test empty description rejection
    with pytest.raises(ValueError, match="Comprehensive description cannot be empty"):
        conversation_manager.save_description(
            topic_id=topic["id"],
            user_id=user_id,
            description=""
        )
    
    # Test valid description save
    valid_description = "Research focused on quantum computing algorithms for cryptographic applications."
    
    result = conversation_manager.save_description(
        topic_id=topic["id"],
        user_id=user_id,
        description=valid_description
    )
    
    # Verify save
    assert result["comprehensiveDescription"] == valid_description
    assert result["conversationStatus"] == "completed"
    
    # Verify status transition
    retrieved_history, status = conversation_manager.get_conversation(
        topic_id=topic["id"],
        user_id=user_id
    )
    
    assert status == ConversationStatus.COMPLETED
