"""
Test structured logging for chatbot interactions.

Validates that all chatbot operations log appropriate structured events
with correlation IDs, timestamps, and relevant metadata.

Requirements: 8.1
"""

import pytest
import json
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.api.interests import chat_with_bot, reset_conversation_endpoint, save_description_endpoint
from app.services.chatbot_service import ChatbotService, AIServiceError, GenerationError
from app.services.conversation_manager import ConversationManager
from app.models.schemas import (
    ChatMessageRequest,
    DescriptionSaveRequest,
    Message,
    ConversationStatus,
    ChatbotResponse
)


class TestChatbotLogging:
    """Test structured logging for chatbot interactions"""
    
    def test_chat_endpoint_logs_conversation_start(self, caplog):
        """
        Test that chat endpoint logs conversation start event with correlation ID.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.INFO):
            with patch('app.services.chatbot_service.ChatbotService') as mock_service_class, \
                 patch('app.services.conversation_manager.ConversationManager') as mock_manager_class, \
                 patch('app.utils.storage.get_interest_topic_by_id') as mock_get_topic:
                
                # Setup mocks
                mock_service = Mock()
                mock_manager = Mock()
                mock_service_class.return_value = mock_service
                mock_manager_class.return_value = mock_manager
                
                mock_get_topic.return_value = {"topicText": "test topic"}
                mock_manager.get_conversation.return_value = ([], ConversationStatus.NOT_STARTED)
                mock_service.send_message.return_value = ChatbotResponse(
                    message="Hello",
                    shouldConclude=False,
                    conversationStatus="in_progress"
                )
                
                # Call endpoint
                request = ChatMessageRequest(message="Hi")
                try:
                    chat_with_bot("topic-123", request, "user-456")
                except Exception:
                    pass  # We're testing logging, not functionality
                
                # Verify conversation start was logged
                log_records = [r for r in caplog.records if r.levelname == "INFO"]
                assert len(log_records) > 0
                
                # Find the conversation_message_start log
                start_logs = [r for r in log_records if "conversation_message_start" in r.message]
                assert len(start_logs) > 0
                
                # Parse and verify log structure
                log_data = json.loads(start_logs[0].message)
                assert log_data["event_type"] == "conversation_message_start"
                assert "correlation_id" in log_data
                assert log_data["user_id"] == "user-456"
                assert log_data["topic_id"] == "topic-123"
                assert "timestamp" in log_data
                assert log_data["message_length"] == 2
    
    def test_chat_endpoint_logs_conversation_complete(self, caplog):
        """
        Test that chat endpoint logs conversation completion with duration and status.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.INFO):
            with patch('app.services.chatbot_service.ChatbotService') as mock_service_class, \
                 patch('app.services.conversation_manager.ConversationManager') as mock_manager_class, \
                 patch('app.utils.storage.get_interest_topic_by_id') as mock_get_topic:
                
                # Setup mocks
                mock_service = Mock()
                mock_manager = Mock()
                mock_service_class.return_value = mock_service
                mock_manager_class.return_value = mock_manager
                
                mock_get_topic.return_value = {"topicText": "test topic"}
                mock_manager.get_conversation.return_value = ([], ConversationStatus.NOT_STARTED)
                mock_service.send_message.return_value = ChatbotResponse(
                    message="Response message",
                    shouldConclude=False,
                    conversationStatus="in_progress"
                )
                mock_manager.save_conversation.return_value = None
                
                # Call endpoint
                request = ChatMessageRequest(message="Test message")
                chat_with_bot("topic-123", request, "user-456")
                
                # Verify conversation complete was logged
                log_records = [r for r in caplog.records if r.levelname == "INFO"]
                complete_logs = [r for r in log_records if "conversation_message_complete" in r.message]
                assert len(complete_logs) > 0
                
                # Parse and verify log structure
                log_data = json.loads(complete_logs[0].message)
                assert log_data["event_type"] == "conversation_message_complete"
                assert "correlation_id" in log_data
                assert log_data["user_id"] == "user-456"
                assert log_data["topic_id"] == "topic-123"
                assert "timestamp" in log_data
                assert "duration_ms" in log_data
                assert log_data["status"] == "success"
                assert log_data["conversation_status"] == "in_progress"
                assert log_data["response_length"] == len("Response message")
    
    def test_chat_endpoint_logs_timeout(self, caplog):
        """
        Test that chat endpoint logs timeout events with appropriate level.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.WARNING):
            with patch('app.services.chatbot_service.ChatbotService') as mock_service_class, \
                 patch('app.services.conversation_manager.ConversationManager') as mock_manager_class, \
                 patch('app.utils.storage.get_interest_topic_by_id') as mock_get_topic:
                
                # Setup mocks
                mock_service = Mock()
                mock_manager = Mock()
                mock_service_class.return_value = mock_service
                mock_manager_class.return_value = mock_manager
                
                mock_get_topic.return_value = {"topicText": "test topic"}
                mock_manager.get_conversation.return_value = ([], ConversationStatus.NOT_STARTED)
                mock_service.send_message.side_effect = TimeoutError("Timeout")
                
                # Call endpoint
                request = ChatMessageRequest(message="Test")
                with pytest.raises(Exception):  # HTTPException
                    chat_with_bot("topic-123", request, "user-456")
                
                # Verify timeout was logged
                log_records = [r for r in caplog.records if r.levelname == "WARNING"]
                timeout_logs = [r for r in log_records if "conversation_message_timeout" in r.message]
                assert len(timeout_logs) > 0
                
                # Parse and verify log structure
                log_data = json.loads(timeout_logs[0].message)
                assert log_data["event_type"] == "conversation_message_timeout"
                assert "correlation_id" in log_data
                assert log_data["status"] == "timeout"
                assert "duration_ms" in log_data
    
    def test_chat_endpoint_logs_ai_service_error(self, caplog):
        """
        Test that chat endpoint logs AI service errors.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.ERROR):
            with patch('app.services.chatbot_service.ChatbotService') as mock_service_class, \
                 patch('app.services.conversation_manager.ConversationManager') as mock_manager_class, \
                 patch('app.utils.storage.get_interest_topic_by_id') as mock_get_topic:
                
                # Setup mocks
                mock_service = Mock()
                mock_manager = Mock()
                mock_service_class.return_value = mock_service
                mock_manager_class.return_value = mock_manager
                
                mock_get_topic.return_value = {"topicText": "test topic"}
                mock_manager.get_conversation.return_value = ([], ConversationStatus.NOT_STARTED)
                mock_service.send_message.side_effect = AIServiceError("Service unavailable")
                
                # Call endpoint
                request = ChatMessageRequest(message="Test")
                with pytest.raises(Exception):  # HTTPException
                    chat_with_bot("topic-123", request, "user-456")
                
                # Verify error was logged
                log_records = [r for r in caplog.records if r.levelname == "ERROR"]
                error_logs = [r for r in log_records if "conversation_message_failed" in r.message]
                assert len(error_logs) > 0
                
                # Parse and verify log structure
                log_data = json.loads(error_logs[0].message)
                assert log_data["event_type"] == "conversation_message_failed"
                assert log_data["error_type"] == "ai_service_error"
                assert "correlation_id" in log_data
    
    def test_reset_conversation_logs_cancellation(self, caplog):
        """
        Test that reset conversation endpoint logs cancellation event.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.INFO):
            with patch('app.services.conversation_manager.ConversationManager') as mock_manager_class:
                
                # Setup mocks
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager
                mock_manager.reset_conversation.return_value = None
                
                # Call endpoint
                reset_conversation_endpoint("topic-123", "user-456")
                
                # Verify cancellation was logged
                log_records = [r for r in caplog.records if r.levelname == "INFO"]
                cancel_logs = [r for r in log_records if "conversation_cancelled" in r.message]
                assert len(cancel_logs) > 0
                
                # Parse and verify log structure
                log_data = json.loads(cancel_logs[0].message)
                assert log_data["event_type"] == "conversation_cancelled"
                assert log_data["user_id"] == "user-456"
                assert log_data["topic_id"] == "topic-123"
                assert "timestamp" in log_data
    
    def test_save_description_logs_generation(self, caplog):
        """
        Test that save description endpoint logs generation with input/output lengths.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.INFO):
            with patch('app.services.conversation_manager.ConversationManager') as mock_manager_class:
                
                # Setup mocks
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager
                mock_manager.save_description.return_value = {
                    "id": "topic-123",
                    "userId": "user-456",
                    "topicText": "test",
                    "comprehensiveDescription": "A comprehensive description",
                    "conversationStatus": "completed",
                    "createdAt": datetime.utcnow().isoformat() + "Z",
                    "updatedAt": datetime.utcnow().isoformat() + "Z"
                }
                
                # Call endpoint
                request = DescriptionSaveRequest(description="A comprehensive description")
                save_description_endpoint("topic-123", request, "user-456")
                
                # Verify generation was logged
                log_records = [r for r in caplog.records if r.levelname == "INFO"]
                gen_logs = [r for r in log_records if "description_generation" in r.message]
                assert len(gen_logs) >= 2  # start and complete
                
                # Verify start log
                start_logs = [r for r in gen_logs if "description_generation_start" in r.message]
                assert len(start_logs) > 0
                start_data = json.loads(start_logs[0].message)
                assert start_data["event_type"] == "description_generation_start"
                assert "correlation_id" in start_data
                assert start_data["input_length"] == len("A comprehensive description")
                
                # Verify complete log
                complete_logs = [r for r in gen_logs if "description_generation_complete" in r.message]
                assert len(complete_logs) > 0
                complete_data = json.loads(complete_logs[0].message)
                assert complete_data["event_type"] == "description_generation_complete"
                assert "duration_ms" in complete_data
                assert complete_data["status"] == "success"
                assert "output_length" in complete_data
    
    def test_chatbot_service_logs_response_times(self, caplog):
        """
        Test that ChatbotService logs response times for send_message.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.INFO):
            with patch('app.services.chatbot_service.boto3.client') as mock_boto:
                
                # Setup mock Bedrock client
                mock_bedrock = Mock()
                mock_boto.return_value = mock_bedrock
                
                mock_response = {
                    'body': Mock(read=lambda: json.dumps({
                        'content': [{'text': 'Test response'}]
                    }).encode())
                }
                mock_bedrock.invoke_model.return_value = mock_response
                
                # Create service and call send_message
                service = ChatbotService()
                service.send_message("Hello", [], "test topic")
                
                # Verify response success was logged
                log_records = [r for r in caplog.records if r.levelname == "INFO"]
                response_logs = [r for r in log_records if "chatbot_response_success" in r.message]
                assert len(response_logs) > 0
                
                # Parse and verify log structure
                log_data = json.loads(response_logs[0].message)
                assert log_data["event_type"] == "chatbot_response_success"
                assert "duration_ms" in log_data
                assert log_data["status"] == "success"
                assert "conversation_length" in log_data
    
    def test_chatbot_service_logs_timeout(self, caplog):
        """
        Test that ChatbotService logs timeout events.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.WARNING):
            with patch('app.services.chatbot_service.boto3.client') as mock_boto:
                from botocore.exceptions import ReadTimeoutError
                
                # Setup mock Bedrock client that times out
                mock_bedrock = Mock()
                mock_boto.return_value = mock_bedrock
                mock_bedrock.invoke_model.side_effect = ReadTimeoutError(
                    endpoint_url="test", 
                    operation_name="InvokeModel"
                )
                
                # Create service and call send_message
                service = ChatbotService()
                with pytest.raises(TimeoutError):
                    service.send_message("Hello", [], "test topic")
                
                # Verify timeout was logged
                log_records = [r for r in caplog.records if r.levelname == "WARNING"]
                timeout_logs = [r for r in log_records if "chatbot_response_timeout" in r.message]
                assert len(timeout_logs) > 0
                
                # Parse and verify log structure
                log_data = json.loads(timeout_logs[0].message)
                assert log_data["event_type"] == "chatbot_response_timeout"
                assert log_data["status"] == "timeout"
                assert "duration_ms" in log_data
    
    def test_generate_description_logs_with_lengths(self, caplog):
        """
        Test that generate_comprehensive_description logs input/output lengths.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.INFO):
            with patch('app.services.chatbot_service.boto3.client') as mock_boto:
                
                # Setup mock Bedrock client
                mock_bedrock = Mock()
                mock_boto.return_value = mock_bedrock
                
                mock_response = {
                    'body': Mock(read=lambda: json.dumps({
                        'content': [{'text': 'Generated comprehensive description'}]
                    }).encode())
                }
                mock_bedrock.invoke_model.return_value = mock_response
                
                # Create service and generate description
                service = ChatbotService()
                conversation = [
                    Message(role="user", content="Hello", timestamp="2024-01-01T00:00:00Z"),
                    Message(role="assistant", content="Hi", timestamp="2024-01-01T00:00:01Z")
                ]
                service.generate_comprehensive_description(conversation)
                
                # Verify generation was logged
                log_records = [r for r in caplog.records if r.levelname == "INFO"]
                gen_logs = [r for r in log_records if "description_generation" in r.message]
                assert len(gen_logs) >= 2  # start and complete
                
                # Verify complete log has lengths
                complete_logs = [r for r in gen_logs if "description_generation_complete" in r.message]
                assert len(complete_logs) > 0
                log_data = json.loads(complete_logs[0].message)
                assert "input_length" in log_data
                assert "output_length" in log_data
                assert log_data["status"] == "success"
    
    def test_conversation_manager_logs_save(self, caplog):
        """
        Test that ConversationManager logs conversation saves.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.INFO):
            with patch('app.services.conversation_manager.get_interest_topic_by_id') as mock_get, \
                 patch('app.services.conversation_manager.update_conversation_history') as mock_update:
                
                # Setup mocks
                mock_get.return_value = {"id": "topic-123", "topicText": "test"}
                mock_update.return_value = True
                
                # Create manager and save conversation
                manager = ConversationManager()
                messages = [
                    Message(role="user", content="Hello", timestamp="2024-01-01T00:00:00Z")
                ]
                manager.save_conversation("topic-123", "user-456", messages, ConversationStatus.IN_PROGRESS)
                
                # Verify save was logged
                log_records = [r for r in caplog.records if r.levelname == "INFO"]
                save_logs = [r for r in log_records if "conversation_saved" in r.message]
                assert len(save_logs) > 0
                
                # Parse and verify log structure
                log_data = json.loads(save_logs[0].message)
                assert log_data["event_type"] == "conversation_saved"
                assert log_data["user_id"] == "user-456"
                assert log_data["topic_id"] == "topic-123"
                assert log_data["conversation_length"] == 1
                assert log_data["conversation_status"] == "in_progress"
    
    def test_logging_does_not_include_conversation_content(self, caplog):
        """
        Test that logs do NOT include full conversation content (privacy requirement).
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.INFO):
            with patch('app.services.chatbot_service.ChatbotService') as mock_service_class, \
                 patch('app.services.conversation_manager.ConversationManager') as mock_manager_class, \
                 patch('app.utils.storage.get_interest_topic_by_id') as mock_get_topic:
                
                # Setup mocks
                mock_service = Mock()
                mock_manager = Mock()
                mock_service_class.return_value = mock_service
                mock_manager_class.return_value = mock_manager
                
                mock_get_topic.return_value = {"topicText": "test topic"}
                mock_manager.get_conversation.return_value = ([], ConversationStatus.NOT_STARTED)
                mock_service.send_message.return_value = ChatbotResponse(
                    message="Sensitive research content",
                    shouldConclude=False,
                    conversationStatus="in_progress"
                )
                mock_manager.save_conversation.return_value = None
                
                # Call endpoint with sensitive message
                request = ChatMessageRequest(message="My secret research topic")
                chat_with_bot("topic-123", request, "user-456")
                
                # Verify logs do NOT contain message content
                all_logs = " ".join([r.message for r in caplog.records])
                assert "My secret research topic" not in all_logs
                assert "Sensitive research content" not in all_logs
                
                # Verify logs only contain metadata (lengths, not content)
                log_records = [r for r in caplog.records if r.levelname == "INFO"]
                for record in log_records:
                    if "conversation_message" in record.message:
                        log_data = json.loads(record.message)
                        # Should have length but not content
                        assert "message_length" in log_data or "response_length" in log_data
                        assert "message_content" not in log_data
                        assert "response_content" not in log_data
    
    def test_logging_includes_correlation_ids(self, caplog):
        """
        Test that all logs for a single request include the same correlation ID.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.INFO):
            with patch('app.services.chatbot_service.ChatbotService') as mock_service_class, \
                 patch('app.services.conversation_manager.ConversationManager') as mock_manager_class, \
                 patch('app.utils.storage.get_interest_topic_by_id') as mock_get_topic:
                
                # Setup mocks
                mock_service = Mock()
                mock_manager = Mock()
                mock_service_class.return_value = mock_service
                mock_manager_class.return_value = mock_manager
                
                mock_get_topic.return_value = {"topicText": "test topic"}
                mock_manager.get_conversation.return_value = ([], ConversationStatus.NOT_STARTED)
                mock_service.send_message.return_value = ChatbotResponse(
                    message="Response",
                    shouldConclude=False,
                    conversationStatus="in_progress"
                )
                mock_manager.save_conversation.return_value = None
                
                # Call endpoint
                request = ChatMessageRequest(message="Test")
                chat_with_bot("topic-123", request, "user-456")
                
                # Extract correlation IDs from logs
                log_records = [r for r in caplog.records if r.levelname == "INFO"]
                correlation_ids = []
                for record in log_records:
                    if "conversation_message" in record.message:
                        log_data = json.loads(record.message)
                        if "correlation_id" in log_data:
                            correlation_ids.append(log_data["correlation_id"])
                
                # Verify all logs for this request have the same correlation ID
                assert len(correlation_ids) >= 2  # start and complete
                assert len(set(correlation_ids)) == 1  # All the same
    
    def test_description_save_logs_validation_failures(self, caplog):
        """
        Test that description save logs validation failures appropriately.
        
        Requirements: 8.1
        """
        with caplog.at_level(logging.WARNING):
            # Test empty description
            request = DescriptionSaveRequest(description="")
            with pytest.raises(Exception):  # HTTPException
                save_description_endpoint("topic-123", request, "user-456")
            
            # Verify validation failure was logged
            log_records = [r for r in caplog.records if r.levelname == "WARNING"]
            validation_logs = [r for r in log_records if "description_validation_failed" in r.message]
            assert len(validation_logs) > 0
            
            # Parse and verify log structure
            log_data = json.loads(validation_logs[0].message)
            assert log_data["event_type"] == "description_validation_failed"
            assert log_data["error_type"] == "empty_description"
