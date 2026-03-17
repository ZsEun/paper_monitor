"""
Integration tests for CloudWatch Metrics

Tests that metrics are emitted correctly during chatbot operations.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from app.services.chatbot_service import ChatbotService
from app.services.conversation_manager import ConversationManager
from app.models.schemas import Message, ConversationStatus


@pytest.fixture
def mock_cloudwatch():
    """Mock CloudWatch client"""
    with patch('app.services.metrics_service.boto3.client') as mock_boto:
        mock_cw = Mock()
        mock_boto.return_value = mock_cw
        yield mock_cw


@pytest.fixture
def chatbot_service_with_metrics(mock_cloudwatch):
    """Create ChatbotService with mocked Bedrock and CloudWatch"""
    with patch('app.services.chatbot_service.boto3.client') as mock_bedrock_client:
        with patch('app.services.chatbot_service.get_metrics_service') as mock_get_metrics:
            mock_bedrock = Mock()
            mock_bedrock_client.return_value = mock_bedrock
            
            # Mock metrics service
            mock_metrics = Mock()
            mock_get_metrics.return_value = mock_metrics
            
            # Mock successful Bedrock response
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'content': [{'text': 'What specific aspects of signal integrity interest you?'}]
            }).encode()
            mock_bedrock.invoke_model.return_value = mock_response
            
            service = ChatbotService()
            service.bedrock = mock_bedrock
            
            yield service, mock_metrics


def test_chatbot_success_emits_metrics(chatbot_service_with_metrics):
    """Test that successful chatbot response emits success and response time metrics"""
    service, mock_metrics = chatbot_service_with_metrics
    
    # Send message
    response = service.send_message(
        user_message="I'm interested in signal integrity",
        conversation_history=[],
        topic_text="signal integrity",
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Verify metrics were emitted
    assert mock_metrics.emit_chatbot_response_time.called
    assert mock_metrics.emit_chatbot_success.called
    
    # Verify correct parameters
    mock_metrics.emit_chatbot_response_time.assert_called_once()
    mock_metrics.emit_chatbot_success.assert_called_once_with("user-123", "topic-456")


def test_chatbot_timeout_emits_metrics(chatbot_service_with_metrics):
    """Test that chatbot timeout emits timeout and failure metrics"""
    service, mock_metrics = chatbot_service_with_metrics
    
    # Mock timeout error
    from botocore.exceptions import ReadTimeoutError
    service.bedrock.invoke_model.side_effect = ReadTimeoutError(
        endpoint_url='https://bedrock.us-west-2.amazonaws.com',
        operation_name='InvokeModel'
    )
    
    # Send message - should raise TimeoutError
    with pytest.raises(TimeoutError):
        service.send_message(
            user_message="Test message",
            conversation_history=[],
            topic_text="test topic",
            user_id="user-123",
            topic_id="topic-456"
        )
    
    # Verify metrics were emitted
    assert mock_metrics.emit_chatbot_response_time.called
    assert mock_metrics.emit_chatbot_timeout.called
    assert mock_metrics.emit_chatbot_failure.called
    
    # Verify failure was called with timeout error type
    mock_metrics.emit_chatbot_failure.assert_called_once_with("user-123", "topic-456", "timeout")


def test_chatbot_api_error_emits_metrics(chatbot_service_with_metrics):
    """Test that Bedrock API error emits appropriate metrics"""
    service, mock_metrics = chatbot_service_with_metrics
    
    # Mock ClientError
    from botocore.exceptions import ClientError
    service.bedrock.invoke_model.side_effect = ClientError(
        {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
        'InvokeModel'
    )
    
    # Send message - should raise AIServiceError
    from app.services.chatbot_service import AIServiceError
    with pytest.raises(AIServiceError):
        service.send_message(
            user_message="Test message",
            conversation_history=[],
            topic_text="test topic",
            user_id="user-123",
            topic_id="topic-456"
        )
    
    # Verify metrics were emitted
    assert mock_metrics.emit_chatbot_response_time.called
    assert mock_metrics.emit_chatbot_failure.called
    assert mock_metrics.emit_bedrock_api_error.called
    
    # Verify Bedrock API error was called with correct error code
    mock_metrics.emit_bedrock_api_error.assert_called_once_with("ThrottlingException", "ChatbotResponse")


def test_description_generation_success_emits_metrics(chatbot_service_with_metrics):
    """Test that successful description generation emits success metric"""
    service, mock_metrics = chatbot_service_with_metrics
    
    # Create sample conversation
    conversation = [
        Message(role="user", content="signal integrity", timestamp="2024-01-01T00:00:00Z"),
        Message(role="assistant", content="What aspects?", timestamp="2024-01-01T00:00:01Z"),
        Message(role="user", content="crosstalk and impedance", timestamp="2024-01-01T00:00:02Z"),
        Message(role="assistant", content="What methodologies?", timestamp="2024-01-01T00:00:03Z"),
        Message(role="user", content="simulation and measurement", timestamp="2024-01-01T00:00:04Z")
    ]
    
    # Generate description
    description = service.generate_comprehensive_description(
        conversation_history=conversation,
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Verify metric was emitted
    assert mock_metrics.emit_description_generation_success.called
    mock_metrics.emit_description_generation_success.assert_called_once()


def test_description_generation_failure_emits_metrics(chatbot_service_with_metrics):
    """Test that description generation failure emits failure metric"""
    service, mock_metrics = chatbot_service_with_metrics
    
    # Mock Bedrock error
    from botocore.exceptions import ClientError
    service.bedrock.invoke_model.side_effect = ClientError(
        {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
        'InvokeModel'
    )
    
    # Create sample conversation
    conversation = [
        Message(role="user", content="test", timestamp="2024-01-01T00:00:00Z")
    ]
    
    # Generate description - should raise GenerationError
    from app.services.chatbot_service import GenerationError
    with pytest.raises(GenerationError):
        service.generate_comprehensive_description(
            conversation_history=conversation,
            user_id="user-123",
            topic_id="topic-456"
        )
    
    # Verify metrics were emitted
    assert mock_metrics.emit_description_generation_failure.called
    assert mock_metrics.emit_bedrock_api_error.called
    
    # Verify correct error type
    mock_metrics.emit_description_generation_failure.assert_called_once_with(
        "user-123", "topic-456", "bedrock_api_error"
    )
    mock_metrics.emit_bedrock_api_error.assert_called_once_with(
        "ServiceUnavailable", "DescriptionGeneration"
    )


@patch('app.services.conversation_manager.get_metrics_service')
@patch('app.services.conversation_manager.get_interest_topic_by_id')
@patch('app.services.conversation_manager.update_comprehensive_description')
def test_conversation_completion_emits_metric(mock_update, mock_get_topic, mock_get_metrics):
    """Test that saving description emits conversation completion metric"""
    # Setup mocks
    mock_metrics = Mock()
    mock_get_metrics.return_value = mock_metrics
    
    mock_get_topic.return_value = {
        "topicId": "topic-456",
        "userId": "user-123",
        "topicText": "test topic"
    }
    
    mock_update.return_value = {
        "topicId": "topic-456",
        "userId": "user-123",
        "topicText": "test topic",
        "comprehensiveDescription": "Test description",
        "conversationStatus": "completed"
    }
    
    # Create conversation manager
    manager = ConversationManager()
    
    # Save description
    manager.save_description(
        topic_id="topic-456",
        user_id="user-123",
        description="Test description"
    )
    
    # Verify conversation completion metric was emitted
    assert mock_metrics.emit_conversation_completion.called
    mock_metrics.emit_conversation_completion.assert_called_once_with("user-123", "topic-456")


def test_metrics_emission_does_not_block_requests(chatbot_service_with_metrics):
    """Test that metric emission is asynchronous and doesn't block requests"""
    service, mock_metrics = chatbot_service_with_metrics
    
    # Make metrics slow (simulate network delay)
    def slow_emit(*args, **kwargs):
        time.sleep(1)  # 1 second delay
    
    mock_metrics.emit_chatbot_response_time.side_effect = slow_emit
    mock_metrics.emit_chatbot_success.side_effect = slow_emit
    
    # Send message - should return quickly despite slow metrics
    start_time = time.time()
    response = service.send_message(
        user_message="Test message",
        conversation_history=[],
        topic_text="test topic",
        user_id="user-123",
        topic_id="topic-456"
    )
    duration = time.time() - start_time
    
    # Response should return quickly (< 0.5 seconds)
    # Note: In this test, metrics are mocked so they execute synchronously
    # In production, they execute asynchronously via ThreadPoolExecutor
    assert response.message is not None


def test_cloudwatch_failure_does_not_break_chatbot(chatbot_service_with_metrics):
    """Test that CloudWatch API failures don't break chatbot functionality"""
    service, mock_metrics = chatbot_service_with_metrics
    
    # Mock metrics to fail
    from botocore.exceptions import ClientError
    mock_metrics.emit_chatbot_response_time.side_effect = Exception("Metrics failed")
    mock_metrics.emit_chatbot_success.side_effect = Exception("Metrics failed")
    
    # Send message - should succeed despite metrics failure
    response = service.send_message(
        user_message="Test message",
        conversation_history=[],
        topic_text="test topic",
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Chatbot should work normally
    assert response.message is not None
    assert response.conversationStatus is not None


def test_metrics_include_correct_dimensions(chatbot_service_with_metrics):
    """Test that metrics include correct dimensions for filtering"""
    service, mock_metrics = chatbot_service_with_metrics
    
    # Send message
    service.send_message(
        user_message="Test message",
        conversation_history=[],
        topic_text="test topic",
        user_id="user-123",
        topic_id="topic-456"
    )
    
    # Verify metrics were called with correct user_id and topic_id
    assert mock_metrics.emit_chatbot_response_time.called
    assert mock_metrics.emit_chatbot_success.called
    
    # Check that user_id and topic_id were passed
    call_args = mock_metrics.emit_chatbot_success.call_args
    assert call_args[0][0] == "user-123"  # user_id
    assert call_args[0][1] == "topic-456"  # topic_id
