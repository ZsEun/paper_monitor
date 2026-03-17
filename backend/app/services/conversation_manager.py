"""
Conversation Manager Service

Manages conversation state persistence and retrieval for the Interest Definition Chatbot.
Handles conversation history storage, status transitions, and user authorization.
"""

import json
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from app.models.schemas import Message, ConversationStatus
from app.utils.storage import (
    get_interest_topic_by_id,
    update_conversation_history,
    update_comprehensive_description,
    reset_conversation as storage_reset_conversation
)
from app.services.metrics_service import get_metrics_service

# Configure logging
logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation state persistence and retrieval.
    Uses DynamoDB-compatible patterns (boto3 ready) through storage layer.
    """
    
    def save_conversation(
        self,
        topic_id: str,
        user_id: str,
        conversation_history: List[Message],
        status: ConversationStatus
    ) -> None:
        """
        Save conversation state to database.
        
        Args:
            topic_id: Interest topic ID
            user_id: User ID for authorization
            conversation_history: Messages to save
            status: Current conversation status
            
        Raises:
            ValueError: If topic not found or doesn't belong to user
        """
        # Verify user authorization - topic must belong to user
        topic = get_interest_topic_by_id(topic_id, user_id)
        if not topic:
            logger.error(json.dumps({
                "event_type": "conversation_save_failed",
                "user_id": user_id,
                "topic_id": topic_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error_type": "not_found",
                "error_message": "Topic not found or does not belong to user"
            }))
            raise ValueError("Topic not found or does not belong to user")
        
        # Convert Message objects to dict format for storage
        history_dicts = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in conversation_history
        ]
        
        # Save to database using storage layer
        result = update_conversation_history(
            topic_id=topic_id,
            user_id=user_id,
            conversation_history=history_dicts,
            conversation_status=status.value
        )
        
        if not result:
            logger.error(json.dumps({
                "event_type": "conversation_save_failed",
                "user_id": user_id,
                "topic_id": topic_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error_type": "storage_error",
                "error_message": "Failed to save conversation"
            }))
            raise ValueError("Failed to save conversation")
        
        # Log successful save
        logger.info(json.dumps({
            "event_type": "conversation_saved",
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "conversation_length": len(conversation_history),
            "conversation_status": status.value
        }))
    
    def get_conversation(
        self,
        topic_id: str,
        user_id: str
    ) -> Tuple[List[Message], ConversationStatus]:
        """
        Retrieve conversation state from database.
        
        Args:
            topic_id: Interest topic ID
            user_id: User ID for authorization
            
        Returns:
            Tuple of (conversation_history, status)
            
        Raises:
            ValueError: If topic not found or doesn't belong to user
        """
        # Verify user authorization and retrieve topic
        topic = get_interest_topic_by_id(topic_id, user_id)
        if not topic:
            raise ValueError("Topic not found or does not belong to user")
        
        # Handle missing conversation data gracefully (backward compatibility)
        conversation_history_raw = topic.get("conversationHistory")
        conversation_status_raw = topic.get("conversationStatus", "not_started")
        
        # Convert dict format to Message objects
        if conversation_history_raw:
            conversation_history = [
                Message(
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg["timestamp"]
                )
                for msg in conversation_history_raw
                if msg.get("content", "").strip()  # skip empty-content messages
            ]
            # Enforce strict alternation (sanitize corrupted history)
            sanitized = []
            for msg in conversation_history:
                if sanitized and sanitized[-1].role == msg.role:
                    continue
                sanitized.append(msg)
            conversation_history = sanitized
        else:
            conversation_history = []
        
        # Convert status string to enum
        status = ConversationStatus(conversation_status_raw)
        
        return conversation_history, status
    
    def reset_conversation(
        self,
        topic_id: str,
        user_id: str
    ) -> None:
        """
        Clear conversation history and reset status to not_started.
        
        Args:
            topic_id: Interest topic ID
            user_id: User ID for authorization
            
        Raises:
            ValueError: If topic not found or doesn't belong to user
        """
        # Verify user authorization
        topic = get_interest_topic_by_id(topic_id, user_id)
        if not topic:
            logger.error(json.dumps({
                "event_type": "conversation_reset_failed",
                "user_id": user_id,
                "topic_id": topic_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error_type": "not_found",
                "error_message": "Topic not found or does not belong to user"
            }))
            raise ValueError("Topic not found or does not belong to user")
        
        # Reset conversation using storage layer
        result = storage_reset_conversation(topic_id, user_id)
        
        if not result:
            logger.error(json.dumps({
                "event_type": "conversation_reset_failed",
                "user_id": user_id,
                "topic_id": topic_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error_type": "storage_error",
                "error_message": "Failed to reset conversation"
            }))
            raise ValueError("Failed to reset conversation")
        
        # Log successful reset
        logger.info(json.dumps({
            "event_type": "conversation_reset",
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }))
    
    def save_description(
        self,
        topic_id: str,
        user_id: str,
        description: str
    ) -> Dict:
        """
        Save comprehensive description to interest topic.
        Updates conversationStatus to completed.
        
        Args:
            topic_id: Interest topic ID
            user_id: User ID for authorization
            description: Comprehensive description text
            
        Returns:
            Updated interest topic dict
            
        Raises:
            ValueError: If topic not found, doesn't belong to user, or description is invalid
        """
        metrics = get_metrics_service()
        
        # Verify user authorization
        topic = get_interest_topic_by_id(topic_id, user_id)
        if not topic:
            logger.error(json.dumps({
                "event_type": "description_save_failed",
                "user_id": user_id,
                "topic_id": topic_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error_type": "not_found",
                "error_message": "Topic not found or does not belong to user"
            }))
            raise ValueError("Topic not found or does not belong to user")
        
        # Validate description is not empty
        if not description or not description.strip():
            logger.warning(json.dumps({
                "event_type": "description_save_failed",
                "user_id": user_id,
                "topic_id": topic_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error_type": "empty_description",
                "error_message": "Comprehensive description cannot be empty"
            }))
            raise ValueError("Comprehensive description cannot be empty")
        
        # Save description using storage layer (includes validation and status update)
        result = update_comprehensive_description(
            topic_id=topic_id,
            user_id=user_id,
            description=description
        )
        
        if not result:
            logger.error(json.dumps({
                "event_type": "description_save_failed",
                "user_id": user_id,
                "topic_id": topic_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error_type": "storage_error",
                "error_message": "Failed to save description"
            }))
            raise ValueError("Failed to save description")
        
        # Log successful save
        logger.info(json.dumps({
            "event_type": "description_saved",
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "description_length": len(description)
        }))
        
        # Emit CloudWatch metrics - conversation completed (don't let metrics failures break the response)
        try:
            metrics.emit_conversation_completion(user_id, topic_id)
        except Exception as e:
            logger.warning(f"Failed to emit conversation completion metrics: {e}")
        
        return result
