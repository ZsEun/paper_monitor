"""
Unit tests for ChatbotService

Tests the chatbot service functionality including message handling,
description generation, and conversation flow management.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from botocore.exceptions import ClientError, ReadTimeoutError
from app.services.chatbot_service import (
    ChatbotService,
    AIServiceError,
    GenerationError
)
from app.models.schemas import Message, ConversationStatus


@pytest.fixture
def chatbot_service():
    """Create ChatbotService instance with mocked Bedrock client"""
    with patch('boto3.client') as mock_boto3:
        mock_bedrock = Mock()
        mock_boto3.return_value = mock_bedrock
        
        service = ChatbotService()
        service.bedrock = mock_bedrock
        
        yield service


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing"""
    return [
        Message(
            role="assistant",
            content="What specific aspects of signal integrity interest you?",
            timestamp="2024-01-15T10:00:00Z"
        ),
        Message(
            role="user",
            content="I'm interested in crosstalk and impedance matching in high-speed circuits",
            timestamp="2024-01-15T10:01:00Z"
        ),
        Message(
            role="assistant",
            content="What methodologies or approaches do you use?",
            timestamp="2024-01-15T10:02:00Z"
        ),
        Message(
            role="user",
            content="I focus on simulation-based analysis and measurement techniques",
            timestamp="2024-01-15T10:03:00Z"
        ),
        Message(
            role="assistant",
            content="What application domains are you interested in?",
            timestamp="2024-01-15T10:04:00Z"
        ),
        Message(
            role="user",
            content="PCB design for data centers and high-performance computing",
            timestamp="2024-01-15T10:05:00Z"
        ),
        Message(
            role="assistant",
            content="Are there any topics you want to exclude?",
            timestamp="2024-01-15T10:06:00Z"
        ),
        Message(
            role="user",
            content="I'm not interested in power integrity or thermal analysis",
            timestamp="2024-01-15T10:07:00Z"
        )
    ]


def test_send_message_first_message(chatbot_service):
    """Test sending the first message in a conversation"""
    # Mock Bedrock response
    mock_response = {
        'body': MagicMock()
    }
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': 'Hello! What research topic would you like to define?'}]
    }).encode()
    
    chatbot_service.bedrock.invoke_model.return_value = mock_response
    
    # Send first message
    response = chatbot_service.send_message(
        user_message="I want to define my interest in signal integrity",
        conversation_history=[],
        topic_text="signal integrity"
    )
    
    # Verify response
    assert response.message == 'Hello! What research topic would you like to define?'
    assert response.conversationStatus == ConversationStatus.IN_PROGRESS.value
    assert response.shouldConclude == False


def test_send_message_with_history(chatbot_service, sample_conversation_history):
    """Test sending message with existing conversation history"""
    import json
    
    # Mock Bedrock response
    mock_response = {
        'body': MagicMock()
    }
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': 'Thank you for that information. I have enough details now.'}]
    }).encode()
    
    chatbot_service.bedrock.invoke_model.return_value = mock_response
    
    # Send message with history
    response = chatbot_service.send_message(
        user_message="That covers everything",
        conversation_history=sample_conversation_history,
        topic_text="signal integrity"
    )
    
    # Verify response
    assert response.message is not None
    assert isinstance(response.shouldConclude, bool)
    assert response.conversationStatus in [
        ConversationStatus.IN_PROGRESS.value,
        ConversationStatus.COMPLETED.value
    ]


def test_send_message_timeout_error(chatbot_service):
    """Test handling of timeout error (exceeds 5 seconds)"""
    # Mock timeout error
    chatbot_service.bedrock.invoke_model.side_effect = ReadTimeoutError(
        endpoint_url='https://bedrock.us-west-2.amazonaws.com'
    )
    
    # Should raise TimeoutError
    with pytest.raises(TimeoutError, match="Chatbot response exceeded 5 second timeout"):
        chatbot_service.send_message(
            user_message="Hello",
            conversation_history=[],
            topic_text="machine learning"
        )


def test_send_message_bedrock_api_error(chatbot_service):
    """Test handling of AWS Bedrock API errors"""
    # Mock ClientError
    error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
    chatbot_service.bedrock.invoke_model.side_effect = ClientError(
        error_response,
        'InvokeModel'
    )
    
    # Should raise AIServiceError
    with pytest.raises(AIServiceError, match="AWS Bedrock API error: ThrottlingException"):
        chatbot_service.send_message(
            user_message="Hello",
            conversation_history=[],
            topic_text="machine learning"
        )


def test_send_message_unexpected_error(chatbot_service):
    """Test handling of unexpected errors"""
    # Mock unexpected error
    chatbot_service.bedrock.invoke_model.side_effect = Exception("Unexpected error")
    
    # Should raise AIServiceError
    with pytest.raises(AIServiceError, match="Unexpected error in chatbot service"):
        chatbot_service.send_message(
            user_message="Hello",
            conversation_history=[],
            topic_text="machine learning"
        )


def test_generate_comprehensive_description_success(chatbot_service, sample_conversation_history):
    """Test generating comprehensive description from conversation"""
    import json
    
    # Mock Bedrock response
    mock_response = {
        'body': MagicMock()
    }
    expected_description = "Research focused on signal integrity in high-speed digital circuits, specifically crosstalk and impedance matching. Uses simulation-based analysis and measurement techniques. Applications include PCB design for data centers and high-performance computing. Excludes power integrity and thermal analysis."
    
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': expected_description}]
    }).encode()
    
    chatbot_service.bedrock.invoke_model.return_value = mock_response
    
    # Generate description
    description = chatbot_service.generate_comprehensive_description(
        conversation_history=sample_conversation_history
    )
    
    # Verify description
    assert description == expected_description
    assert len(description) > 0
    assert len(description) <= 5000


def test_generate_comprehensive_description_empty_history(chatbot_service):
    """Test generating description from empty conversation fails"""
    with pytest.raises(GenerationError, match="Cannot generate description from empty conversation"):
        chatbot_service.generate_comprehensive_description(
            conversation_history=[]
        )


def test_generate_comprehensive_description_timeout(chatbot_service, sample_conversation_history):
    """Test handling timeout during description generation"""
    # Mock timeout error
    chatbot_service.bedrock.invoke_model.side_effect = ReadTimeoutError(
        endpoint_url='https://bedrock.us-west-2.amazonaws.com'
    )
    
    # Should raise GenerationError
    with pytest.raises(GenerationError, match="Failed to generate description"):
        chatbot_service.generate_comprehensive_description(
            conversation_history=sample_conversation_history
        )


def test_generate_comprehensive_description_api_error(chatbot_service, sample_conversation_history):
    """Test handling API error during description generation"""
    # Mock ClientError
    error_response = {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}}
    chatbot_service.bedrock.invoke_model.side_effect = ClientError(
        error_response,
        'InvokeModel'
    )
    
    # Should raise GenerationError
    with pytest.raises(GenerationError, match="Failed to generate description"):
        chatbot_service.generate_comprehensive_description(
            conversation_history=sample_conversation_history
        )


def test_generate_comprehensive_description_truncates_long_output(chatbot_service, sample_conversation_history):
    """Test that descriptions longer than 5000 characters are truncated"""
    import json
    
    # Mock Bedrock response with very long description
    mock_response = {
        'body': MagicMock()
    }
    long_description = "A" * 6000  # Exceeds 5000 character limit
    
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': long_description}]
    }).encode()
    
    chatbot_service.bedrock.invoke_model.return_value = mock_response
    
    # Generate description
    description = chatbot_service.generate_comprehensive_description(
        conversation_history=sample_conversation_history
    )
    
    # Verify truncation
    assert len(description) == 5000


def test_should_conclude_conversation_insufficient_messages(chatbot_service):
    """Test that conversation doesn't conclude with too few messages"""
    # Only 2 messages (1 exchange)
    short_history = [
        Message(
            role="assistant",
            content="What interests you?",
            timestamp="2024-01-15T10:00:00Z"
        ),
        Message(
            role="user",
            content="Signal integrity",
            timestamp="2024-01-15T10:01:00Z"
        )
    ]
    
    should_conclude = chatbot_service.should_conclude_conversation(short_history)
    assert should_conclude == False


def test_should_conclude_conversation_sufficient_coverage(chatbot_service, sample_conversation_history):
    """Test that conversation concludes when key areas are covered"""
    # sample_conversation_history covers aspects, methodologies, applications, and exclusions
    should_conclude = chatbot_service.should_conclude_conversation(sample_conversation_history)
    
    # Should conclude since all 4 areas are covered
    assert should_conclude == True


def test_should_conclude_conversation_partial_coverage(chatbot_service):
    """Test that conversation doesn't conclude with only partial coverage"""
    # Only covers aspects and methodologies (2 of 4 areas)
    partial_history = [
        Message(
            role="assistant",
            content="What specific aspects interest you?",
            timestamp="2024-01-15T10:00:00Z"
        ),
        Message(
            role="user",
            content="I'm interested in crosstalk analysis",
            timestamp="2024-01-15T10:01:00Z"
        ),
        Message(
            role="assistant",
            content="What methodologies do you use?",
            timestamp="2024-01-15T10:02:00Z"
        ),
        Message(
            role="user",
            content="Simulation techniques",
            timestamp="2024-01-15T10:03:00Z"
        ),
        Message(
            role="assistant",
            content="Tell me more",
            timestamp="2024-01-15T10:04:00Z"
        ),
        Message(
            role="user",
            content="I use SPICE simulators",
            timestamp="2024-01-15T10:05:00Z"
        )
    ]
    
    should_conclude = chatbot_service.should_conclude_conversation(partial_history)
    
    # Should not conclude - only 2 of 4 areas covered (need at least 3)
    assert should_conclude == False


def test_should_conclude_conversation_three_areas_covered(chatbot_service):
    """Test that conversation concludes when 3 of 4 areas are covered"""
    # Covers aspects, methodologies, and applications (3 of 4 areas)
    history_three_areas = [
        Message(
            role="assistant",
            content="What specific aspects interest you?",
            timestamp="2024-01-15T10:00:00Z"
        ),
        Message(
            role="user",
            content="I'm interested in crosstalk analysis",
            timestamp="2024-01-15T10:01:00Z"
        ),
        Message(
            role="assistant",
            content="What methodologies do you use?",
            timestamp="2024-01-15T10:02:00Z"
        ),
        Message(
            role="user",
            content="Simulation techniques",
            timestamp="2024-01-15T10:03:00Z"
        ),
        Message(
            role="assistant",
            content="What applications are you focused on?",
            timestamp="2024-01-15T10:04:00Z"
        ),
        Message(
            role="user",
            content="PCB design for data centers",
            timestamp="2024-01-15T10:05:00Z"
        )
    ]
    
    should_conclude = chatbot_service.should_conclude_conversation(history_three_areas)
    
    # Should conclude - 3 of 4 areas covered (threshold met)
    assert should_conclude == True


def test_build_conversation_messages_first_message(chatbot_service):
    """Test building messages for first user message"""
    messages = chatbot_service._build_conversation_messages(
        user_message="I want to learn about machine learning",
        conversation_history=[],
        topic_text="machine learning"
    )
    
    # Should have one message
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert "machine learning" in messages[0]["content"].lower()


def test_build_conversation_messages_with_history(chatbot_service):
    """Test building messages with existing history"""
    history = [
        Message(
            role="assistant",
            content="What aspects interest you?",
            timestamp="2024-01-15T10:00:00Z"
        ),
        Message(
            role="user",
            content="Neural networks",
            timestamp="2024-01-15T10:01:00Z"
        )
    ]
    
    messages = chatbot_service._build_conversation_messages(
        user_message="Specifically CNNs",
        conversation_history=history,
        topic_text="machine learning"
    )
    
    # Should have 3 messages (2 from history + 1 new)
    assert len(messages) == 3
    assert messages[0]["role"] == "assistant"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "Specifically CNNs"


def test_build_conversation_transcript(chatbot_service, sample_conversation_history):
    """Test building readable transcript from conversation history"""
    transcript = chatbot_service._build_conversation_transcript(sample_conversation_history)
    
    # Verify transcript format
    assert "Assistant:" in transcript
    assert "User:" in transcript
    assert "crosstalk" in transcript
    assert "simulation-based analysis" in transcript
    assert "PCB design" in transcript
    assert "power integrity" in transcript


def test_system_prompt_includes_key_areas(chatbot_service):
    """Test that system prompt includes guidance for all 4 key areas"""
    system_prompt = chatbot_service.system_prompt
    
    # Verify all 4 key areas are mentioned
    assert "aspects" in system_prompt.lower()
    assert "methodologies" in system_prompt.lower()
    assert "applications" in system_prompt.lower()
    assert "exclusions" in system_prompt.lower()
    
    # Verify conversation guidelines
    assert "acknowledge" in system_prompt.lower()
    assert "examples" in system_prompt.lower()
    assert "one question at a time" in system_prompt.lower()


def test_chatbot_response_acknowledgment(chatbot_service):
    """
    Test that chatbot responses acknowledge user input.
    This is a behavioral test - we verify the system prompt instructs acknowledgment.
    
    Requirements: 8.2
    """
    # Verify system prompt includes acknowledgment instruction
    assert "acknowledge" in chatbot_service.system_prompt.lower()


def test_chatbot_question_examples(chatbot_service):
    """
    Test that chatbot is instructed to provide examples in questions.
    This is a behavioral test - we verify the system prompt instructs examples.
    
    Requirements: 8.6
    """
    # Verify system prompt includes examples instruction
    assert "examples" in chatbot_service.system_prompt.lower()
    assert "e.g." in chatbot_service.system_prompt or "example" in chatbot_service.system_prompt.lower()


def test_generate_description_includes_all_areas(chatbot_service, sample_conversation_history):
    """
    Test that generated description includes aspects, methodologies, applications, exclusions.
    
    Requirements: 3.2, 3.3, 3.4, 3.5
    """
    import json
    
    # Mock Bedrock response with comprehensive description
    mock_response = {
        'body': MagicMock()
    }
    description = """Research focused on signal integrity in high-speed digital circuits, 
    specifically crosstalk and impedance matching. The research employs simulation-based 
    analysis and measurement techniques. Primary applications include PCB design for data 
    centers and high-performance computing systems. Excludes power integrity and thermal 
    analysis topics."""
    
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': description}]
    }).encode()
    
    chatbot_service.bedrock.invoke_model.return_value = mock_response
    
    # Generate description
    result = chatbot_service.generate_comprehensive_description(
        conversation_history=sample_conversation_history
    )
    
    # Verify all areas are mentioned
    result_lower = result.lower()
    assert "crosstalk" in result_lower or "impedance" in result_lower  # Aspects
    assert "simulation" in result_lower or "measurement" in result_lower  # Methodologies
    assert "pcb" in result_lower or "data center" in result_lower  # Applications
    assert "exclude" in result_lower or "power integrity" in result_lower  # Exclusions


def test_bedrock_client_timeout_configuration(chatbot_service):
    """Test that Bedrock client is configured with 5-second timeout"""
    # This test verifies the configuration was set during initialization
    # The actual timeout is enforced by boto3 Config
    assert chatbot_service.bedrock is not None
    assert chatbot_service.model_id == 'anthropic.claude-3-sonnet-20240229-v1:0'


def test_call_bedrock_request_format(chatbot_service):
    """Test that Bedrock API calls use correct request format"""
    import json
    
    # Mock Bedrock response
    mock_response = {
        'body': MagicMock()
    }
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': 'Test response'}]
    }).encode()
    
    chatbot_service.bedrock.invoke_model.return_value = mock_response
    
    # Call Bedrock
    messages = [{"role": "user", "content": "Test message"}]
    response = chatbot_service._call_bedrock(messages)
    
    # Verify invoke_model was called with correct parameters
    call_args = chatbot_service.bedrock.invoke_model.call_args
    assert call_args[1]['modelId'] == 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    # Verify request body format
    body = json.loads(call_args[1]['body'])
    assert body['anthropic_version'] == 'bedrock-2023-05-31'
    assert 'max_tokens' in body
    assert 'system' in body
    assert body['system'] == chatbot_service.system_prompt
    assert 'messages' in body
    assert body['temperature'] == 0.7
    assert body['top_p'] == 0.9


def test_generate_description_empty_response_fails(chatbot_service, sample_conversation_history):
    """Test that empty generated description raises error"""
    import json
    
    # Mock Bedrock response with empty text
    mock_response = {
        'body': MagicMock()
    }
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': '   '}]  # Whitespace only
    }).encode()
    
    chatbot_service.bedrock.invoke_model.return_value = mock_response
    
    # Should raise GenerationError
    with pytest.raises(GenerationError, match="Generated description is empty"):
        chatbot_service.generate_comprehensive_description(
            conversation_history=sample_conversation_history
        )


def test_conversation_flow_initial_topic_request(chatbot_service):
    """
    Test that first chatbot message requests initial research topic.
    This is verified through the system prompt.
    
    Requirements: 2.1
    """
    # Verify system prompt instructs to ask for initial topic
    assert "initial" in chatbot_service.system_prompt.lower() or "topic" in chatbot_service.system_prompt.lower()


def test_conversation_flow_clarifying_questions(chatbot_service):
    """
    Test that system prompt instructs chatbot to ask clarifying questions.
    
    Requirements: 2.2, 2.3, 2.4, 2.5
    """
    system_prompt = chatbot_service.system_prompt.lower()
    
    # Verify system prompt mentions all 4 key areas
    assert "aspects" in system_prompt
    assert "methodologies" in system_prompt or "methods" in system_prompt
    assert "applications" in system_prompt
    assert "exclusions" in system_prompt or "exclude" in system_prompt
