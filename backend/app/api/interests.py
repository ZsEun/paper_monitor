from fastapi import APIRouter, HTTPException, status, Depends, Header, UploadFile, File
from fastapi.responses import JSONResponse
from app.models.schemas import (
    InterestTopic,
    InterestTopicCreate,
    InterestTopicUpdate,
    ChatMessageRequest,
    DescriptionSaveRequest,
    ConversationHistoryResponse,
    ChatbotResponse
)
from app.utils.storage import (
    get_user_interest_topics,
    add_interest_topic,
    update_interest_topic,
    delete_interest_topic,
    count_user_topics
)
from app.utils.security import decode_access_token
from typing import List, Optional, Dict, Any
import json
import logging
import uuid
import time
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract and validate user ID from JWT token in Authorization header.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        User ID from token
        
    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = parts[1]
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get user email from token
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # For now, we'll use email as user_id since we need to look up the actual user_id
    # In a real implementation, we'd query the users table here
    from app.utils.storage import read_json_file
    users = read_json_file("users.json")
    
    if email not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return users[email]["id"]


@router.get("", response_model=List[InterestTopic])
def list_interest_topics(user_id: str = Depends(get_current_user_id)):
    """
    List all interest topics for the authenticated user.
    
    Returns:
        List of interest topics
    """
    topics = get_user_interest_topics(user_id)
    return topics


@router.post("", response_model=InterestTopic, status_code=status.HTTP_201_CREATED)
def create_interest_topic(
    topic: InterestTopicCreate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Add a new interest topic for the authenticated user.
    
    Args:
        topic: Topic data with topicText
        
    Returns:
        Created interest topic
        
    Raises:
        HTTPException: 400 if topic limit exceeded, 409 if duplicate topic
    """
    try:
        new_topic = add_interest_topic(user_id, topic.topicText)
        return new_topic
    except ValueError as e:
        error_msg = str(e)
        
        # Check if it's a duplicate error
        if "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Topic already exists in your interest profile"
            )
        
        # Check if it's a limit error
        if "maximum" in error_msg.lower() or "20" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum of 20 interest topics allowed per user"
            )
        
        # Other validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )


@router.put("/{topic_id}", response_model=InterestTopic)
def update_interest_topic_endpoint(
    topic_id: str,
    topic: InterestTopicUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update an existing interest topic.
    
    Args:
        topic_id: ID of the topic to update
        topic: Updated topic data with topicText
        
    Returns:
        Updated interest topic
        
    Raises:
        HTTPException: 404 if topic not found, 409 if duplicate topic
    """
    try:
        updated_topic = update_interest_topic(topic_id, user_id, topic.topicText)
        
        if not updated_topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interest topic not found or does not belong to your account"
            )
        
        return updated_topic
    except ValueError as e:
        error_msg = str(e)
        
        # Check if it's a duplicate error
        if "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Topic already exists in your interest profile"
            )
        
        # Other validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )


@router.delete("/{topic_id}")
def delete_interest_topic_endpoint(
    topic_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete an interest topic and cascade delete all associated data.
    
    This endpoint performs cascade deletion, removing:
    - The interest topic itself
    - Conversation history (all chat messages)
    - Comprehensive description
    - All other topic metadata
    
    Args:
        topic_id: ID of the topic to delete
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 404 if topic not found
        
    Requirements: 11.4 (Cascade Deletion)
    """
    success = delete_interest_topic(topic_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interest topic not found or does not belong to your account"
        )
    
    return {"success": True}


@router.post("/export")
def export_interest_topics(user_id: str = Depends(get_current_user_id)):
    """
    Export all interest topics for the authenticated user as JSON.
    Includes comprehensiveDescription and conversationStatus but NOT conversationHistory (privacy).
    
    Returns:
        JSON response with topics and metadata
        
    Requirements: 10.1, 10.2
    """
    topics = get_user_interest_topics(user_id)
    
    # Remove conversationHistory from export (privacy and file size)
    topics_for_export = []
    for topic in topics:
        topic_copy = topic.copy()
        # Remove conversationHistory if present
        topic_copy.pop('conversationHistory', None)
        topics_for_export.append(topic_copy)
    
    export_data = {
        "exportedAt": datetime.utcnow().isoformat() + "Z",
        "userId": user_id,
        "topicCount": len(topics_for_export),
        "topics": topics_for_export
    }
    
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=interest_topics_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )


@router.post("/import")
async def import_interest_topics(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Import interest topics from a JSON file.
    Handles comprehensiveDescription and conversationStatus fields with validation.
    
    Args:
        file: JSON file containing topics to import
        
    Returns:
        Import results with counts of added, skipped, and duplicate topics
        
    Raises:
        HTTPException: 400 if file format is invalid
        
    Requirements: 10.3, 10.4, 10.5
    """
    # Read and parse the uploaded file
    try:
        content = await file.read()
        import_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON file format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Validate the JSON structure
    if not isinstance(import_data, dict) or "topics" not in import_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format: missing 'topics' field"
        )
    
    topics_to_import = import_data.get("topics", [])
    if not isinstance(topics_to_import, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format: 'topics' must be an array"
        )
    
    # Import topics
    results = {
        "added": 0,
        "skipped": 0,
        "duplicates": 0,
        "errors": []
    }
    
    from app.utils.storage import add_interest_topic_with_description
    
    for topic_data in topics_to_import:
        # Validate topic structure
        if not isinstance(topic_data, dict) or "topicText" not in topic_data:
            results["skipped"] += 1
            results["errors"].append(f"Invalid topic structure: {topic_data}")
            continue
        
        topic_text = topic_data.get("topicText", "").strip()
        
        # Validate topic text
        if not topic_text or len(topic_text) < 2 or len(topic_text) > 200:
            results["skipped"] += 1
            results["errors"].append(f"Invalid topic text length: {topic_text}")
            continue
        
        # Extract optional fields
        comprehensive_description = topic_data.get("comprehensiveDescription")
        conversation_status = topic_data.get("conversationStatus", "not_started")
        
        # Validate description length if provided
        if comprehensive_description and len(comprehensive_description) > 5000:
            results["skipped"] += 1
            results["errors"].append(f"Description too long for topic '{topic_text}': {len(comprehensive_description)} characters (max 5000)")
            continue
        
        # Try to add the topic with description
        try:
            add_interest_topic_with_description(
                user_id, 
                topic_text,
                comprehensive_description,
                conversation_status
            )
            results["added"] += 1
        except ValueError as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                results["duplicates"] += 1
            elif "maximum" in error_msg.lower() or "20" in error_msg:
                # Stop importing if we hit the limit
                results["errors"].append("Maximum topic limit (20) reached")
                break
            else:
                results["skipped"] += 1
                results["errors"].append(f"Error adding topic '{topic_text}': {error_msg}")
    
    return {
        "success": True,
        "results": results
    }


# Chatbot endpoints

@router.post("/{topic_id}/chat", response_model=ChatbotResponse)
def chat_with_bot(
    topic_id: str,
    request: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a message to the chatbot for defining research interests.

    Args:
        topic_id: ID of the interest topic
        request: Chat message request with user message

    Returns:
        Chatbot response with message and conversation state

    Raises:
        HTTPException: 404 if topic not found, 500 if chatbot fails, 408 if timeout

    Requirements: 1.2, 2.1, 2.2, 2.3, 2.4, 2.5, 8.1, 9.1
    """
    from app.services.chatbot_service import ChatbotService, AIServiceError
    from app.services.conversation_manager import ConversationManager
    from app.models.schemas import Message, ConversationStatus

    # Generate correlation ID for request tracing
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    # Log conversation start
    logger.info(json.dumps({
        "event_type": "conversation_message_start",
        "correlation_id": correlation_id,
        "user_id": user_id,
        "topic_id": topic_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message_length": len(request.message)
    }))

    # Initialize services
    chatbot_service = ChatbotService()
    conversation_manager = ConversationManager()

    try:
        # Get conversation history
        conversation_history, conv_status = conversation_manager.get_conversation(
            topic_id, user_id
        )

        # Get topic for context
        from app.utils.storage import get_interest_topic_by_id
        topic = get_interest_topic_by_id(topic_id, user_id)
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interest topic not found or does not belong to your account"
            )

        # Send message to chatbot
        response = chatbot_service.send_message(
            user_message=request.message,
            conversation_history=conversation_history,
            topic_text=topic.get("topicText", ""),
            user_id=user_id,
            topic_id=topic_id
        )

        # Update conversation history with new messages
        # Skip saving empty user messages (e.g. the initial trigger to start conversation)
        new_history = list(conversation_history)
        if request.message.strip():
            new_history.append(Message(
                role="user",
                content=request.message,
                timestamp=datetime.utcnow().isoformat() + "Z"
            ))
        new_history.append(Message(
            role="assistant",
            content=response.message,
            timestamp=datetime.utcnow().isoformat() + "Z"
        ))

        # Sanitize: ensure strict user/assistant alternation before saving
        sanitized_history = []
        for msg in new_history:
            if sanitized_history and sanitized_history[-1].role == msg.role:
                continue  # drop consecutive duplicate roles
            sanitized_history.append(msg)
        new_history = sanitized_history

        # Save conversation state
        conversation_manager.save_conversation(
            topic_id=topic_id,
            user_id=user_id,
            conversation_history=new_history,
            status=ConversationStatus(response.conversationStatus)
        )

        # Calculate duration and log success
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(json.dumps({
            "event_type": "conversation_message_complete",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": "success",
            "conversation_status": response.conversationStatus,
            "response_length": len(response.message)
        }))

        return response

    except ValueError as e:
        # Topic not found or authorization failure
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(json.dumps({
            "event_type": "conversation_message_failed",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": "failed",
            "error_type": "not_found",
            "error_message": str(e)
        }))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except TimeoutError as e:
        # Chatbot response timeout
        duration_ms = int((time.time() - start_time) * 1000)
        logger.warning(json.dumps({
            "event_type": "conversation_message_timeout",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": "timeout",
            "error_message": str(e)
        }))
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="The chatbot is taking longer than expected. Please try again."
        )
    except AIServiceError as e:
        # AI service failure
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(json.dumps({
            "event_type": "conversation_message_failed",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": "failed",
            "error_type": "ai_service_error",
            "error_message": str(e)
        }))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to connect to AI service. Please try again."
        )
    except Exception as e:
        # Unexpected error
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(json.dumps({
            "event_type": "conversation_message_failed",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": "failed",
            "error_type": "unexpected_error",
            "error_message": str(e)
        }))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{topic_id}/conversation", response_model=ConversationHistoryResponse)
def get_conversation_history(
    topic_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieve conversation history for an interest topic.

    Args:
        topic_id: ID of the interest topic

    Returns:
        Conversation history and status

    Raises:
        HTTPException: 404 if topic not found

    Requirements: 6.2
    """
    from app.services.conversation_manager import ConversationManager

    conversation_manager = ConversationManager()

    try:
        conversation_history, conv_status = conversation_manager.get_conversation(
            topic_id, user_id
        )

        return ConversationHistoryResponse(
            conversationHistory=conversation_history,
            conversationStatus=conv_status.value
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{topic_id}/conversation/reset")
def reset_conversation_endpoint(
    topic_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Reset conversation history and status for an interest topic.

    Args:
        topic_id: ID of the interest topic

    Returns:
        Success response

    Raises:
        HTTPException: 404 if topic not found

    Requirements: 6.3, 6.4
    """
    from app.services.conversation_manager import ConversationManager

    # Log conversation cancellation
    logger.info(json.dumps({
        "event_type": "conversation_cancelled",
        "user_id": user_id,
        "topic_id": topic_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }))

    conversation_manager = ConversationManager()

    try:
        conversation_manager.reset_conversation(topic_id, user_id)
        return {"success": True}

    except ValueError as e:
        logger.error(json.dumps({
            "event_type": "conversation_reset_failed",
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error_message": str(e)
        }))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{topic_id}/description/generate")
def generate_description_endpoint(
    topic_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate a comprehensive description from the chatbot conversation history.
    Uses the real AI service (Bedrock or mock depending on config).
    """
    from app.services.chatbot_service import ChatbotService, GenerationError
    from app.services.conversation_manager import ConversationManager

    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    chatbot_service = ChatbotService()
    conversation_manager = ConversationManager()

    try:
        # Get conversation history
        conversation_history, conv_status = conversation_manager.get_conversation(
            topic_id, user_id
        )

        # Get topic for context
        from app.utils.storage import get_interest_topic_by_id
        topic = get_interest_topic_by_id(topic_id, user_id)
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interest topic not found"
            )

        # Generate description via AI service
        description = chatbot_service.generate_comprehensive_description(
            conversation_history=conversation_history,
            topic_text=topic.get("topicText", ""),
            user_id=user_id
        )

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(json.dumps({
            "event_type": "description_ai_generation_complete",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "duration_ms": duration_ms,
            "output_length": len(description)
        }))

        return {"description": description}

    except GenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate description: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{topic_id}/description/save", response_model=InterestTopic)
def save_description_endpoint(
    topic_id: str,
    request: DescriptionSaveRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Save comprehensive description for an interest topic.

    Args:
        topic_id: ID of the interest topic
        request: Description save request with description text

    Returns:
        Updated interest topic with description

    Raises:
        HTTPException: 404 if topic not found, 422 if validation fails

    Requirements: 4.5, 5.1, 9.4, 9.5
    """
    from app.services.conversation_manager import ConversationManager

    # Generate correlation ID for request tracing
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    # Log description generation start
    logger.info(json.dumps({
        "event_type": "description_generation_start",
        "correlation_id": correlation_id,
        "user_id": user_id,
        "topic_id": topic_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input_length": len(request.description)
    }))

    conversation_manager = ConversationManager()

    # Validate description is not empty
    if not request.description or not request.description.strip():
        logger.warning(json.dumps({
            "event_type": "description_validation_failed",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error_type": "empty_description"
        }))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comprehensive description cannot be empty"
        )

    # Validate description length
    if len(request.description) > 5000:
        logger.warning(json.dumps({
            "event_type": "description_validation_failed",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error_type": "description_too_long",
            "description_length": len(request.description)
        }))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Description is too long. Maximum length is 5000 characters."
        )

    try:
        # Save description
        updated_topic = conversation_manager.save_description(
            topic_id=topic_id,
            user_id=user_id,
            description=request.description.strip()
        )

        # Calculate duration and log success
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(json.dumps({
            "event_type": "description_generation_complete",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": "success",
            "output_length": len(request.description.strip())
        }))

        # Convert dict to InterestTopic model
        return InterestTopic(**updated_topic)

    except ValueError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        logger.error(json.dumps({
            "event_type": "description_generation_failed",
            "correlation_id": correlation_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": "failed",
            "error_message": error_msg
        }))
        
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif "empty" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save description: {error_msg}"
            )

