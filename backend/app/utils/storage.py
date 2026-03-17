import json
import os
from typing import Any, Dict

DATA_DIR = "data"

def ensure_data_dir():
    """Ensure data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def read_json_file(filename: str) -> Dict[str, Any]:
    """Read data from JSON file"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r') as f:
        return json.load(f)

def write_json_file(filename: str, data: Dict[str, Any]):
    """Write data to JSON file"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

# Interest Topic Storage
from typing import List, Optional
from datetime import datetime
import uuid

INTEREST_TOPICS_FILE = "interest_topics.json"

def get_user_interest_topics(user_id: str) -> List[Dict[str, Any]]:
    """Get all interest topics for a user with backward compatibility for new fields"""
    data = read_json_file(INTEREST_TOPICS_FILE)
    topics = data.get("topics", [])
    user_topics = [topic for topic in topics if topic.get("userId") == user_id]
    
    # Ensure backward compatibility: add default values for new fields if missing
    for topic in user_topics:
        if "comprehensiveDescription" not in topic:
            topic["comprehensiveDescription"] = None
        if "conversationHistory" not in topic:
            topic["conversationHistory"] = None
        if "conversationStatus" not in topic:
            topic["conversationStatus"] = "not_started"
    
    return user_topics

def add_interest_topic(user_id: str, topic_text: str) -> Dict[str, Any]:
    """Add a new interest topic for a user"""
    # Trim whitespace
    topic_text = topic_text.strip()
    
    # Load existing topics
    data = read_json_file(INTEREST_TOPICS_FILE)
    if "topics" not in data:
        data["topics"] = []
    
    # Check for duplicate (case-insensitive)
    existing_topics = [t for t in data["topics"] if t.get("userId") == user_id]
    for topic in existing_topics:
        if topic.get("topicText", "").lower() == topic_text.lower():
            raise ValueError("Topic already exists in your interest profile")
    
    # Check topic count limit
    if len(existing_topics) >= 20:
        raise ValueError("Maximum of 20 interest topics allowed per user")
    
    # Create new topic with new fields
    now = datetime.utcnow().isoformat() + "Z"
    new_topic = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "topicText": topic_text,
        "createdAt": now,
        "updatedAt": now,
        "comprehensiveDescription": None,
        "conversationHistory": None,
        "conversationStatus": "not_started"
    }
    
    data["topics"].append(new_topic)
    write_json_file(INTEREST_TOPICS_FILE, data)
    
    return new_topic

def add_interest_topic_with_description(
    user_id: str,
    topic_text: str,
    comprehensive_description: Optional[str] = None,
    conversation_status: str = "not_started"
) -> Dict[str, Any]:
    """
    Add a new interest topic with optional comprehensive description (for import).

    Args:
        user_id: User ID
        topic_text: Topic text (2-200 characters)
        comprehensive_description: Optional comprehensive description (max 5000 characters)
        conversation_status: Conversation status (default: not_started)

    Returns:
        Created topic dictionary

    Raises:
        ValueError: If validation fails or topic already exists
    """
    # Trim whitespace
    topic_text = topic_text.strip()

    # Validate description if provided
    if comprehensive_description is not None:
        comprehensive_description = comprehensive_description.strip()
        if len(comprehensive_description) > 5000:
            raise ValueError(f"Description too long: {len(comprehensive_description)} characters (max 5000)")

    # Validate conversation status
    valid_statuses = ['not_started', 'in_progress', 'completed']
    if conversation_status not in valid_statuses:
        conversation_status = 'not_started'

    # Load existing topics
    data = read_json_file(INTEREST_TOPICS_FILE)
    if "topics" not in data:
        data["topics"] = []

    # Check for duplicate (case-insensitive)
    existing_topics = [t for t in data["topics"] if t.get("userId") == user_id]
    for topic in existing_topics:
        if topic.get("topicText", "").lower() == topic_text.lower():
            raise ValueError("Topic already exists in your interest profile")

    # Check topic count limit
    if len(existing_topics) >= 20:
        raise ValueError("Maximum of 20 interest topics allowed per user")

    # Create new topic with all fields
    now = datetime.utcnow().isoformat() + "Z"
    new_topic = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "topicText": topic_text,
        "createdAt": now,
        "updatedAt": now,
        "comprehensiveDescription": comprehensive_description if comprehensive_description else None,
        "conversationHistory": None,
        "conversationStatus": conversation_status
    }

    data["topics"].append(new_topic)
    write_json_file(INTEREST_TOPICS_FILE, data)

    return new_topic


def update_interest_topic(topic_id: str, user_id: str, topic_text: str) -> Optional[Dict[str, Any]]:
    """Update an existing interest topic"""
    # Trim whitespace
    topic_text = topic_text.strip()
    
    # Load existing topics
    data = read_json_file(INTEREST_TOPICS_FILE)
    topics = data.get("topics", [])
    
    # Find the topic
    topic_index = None
    for i, topic in enumerate(topics):
        if topic.get("id") == topic_id and topic.get("userId") == user_id:
            topic_index = i
            break
    
    if topic_index is None:
        return None
    
    # Check for duplicate (case-insensitive) excluding current topic
    for i, topic in enumerate(topics):
        if i != topic_index and topic.get("userId") == user_id:
            if topic.get("topicText", "").lower() == topic_text.lower():
                raise ValueError("Topic already exists in your interest profile")
    
    # Update the topic
    topics[topic_index]["topicText"] = topic_text
    topics[topic_index]["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    
    write_json_file(INTEREST_TOPICS_FILE, data)
    
    return topics[topic_index]


def count_user_topics(user_id: str) -> int:
    """Count the number of interest topics for a user"""
    topics = get_user_interest_topics(user_id)
    return len(topics)

# Chatbot-related storage functions

def get_interest_topic_by_id(topic_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific interest topic by ID"""
    data = read_json_file(INTEREST_TOPICS_FILE)
    topics = data.get("topics", [])
    
    for topic in topics:
        if topic.get("id") == topic_id and topic.get("userId") == user_id:
            # Ensure backward compatibility
            if "comprehensiveDescription" not in topic:
                topic["comprehensiveDescription"] = None
            if "conversationHistory" not in topic:
                topic["conversationHistory"] = None
            if "conversationStatus" not in topic:
                topic["conversationStatus"] = "not_started"
            return topic
    
    return None

def update_conversation_history(
    topic_id: str,
    user_id: str,
    conversation_history: List[Dict[str, str]],
    conversation_status: str
) -> Optional[Dict[str, Any]]:
    """Update conversation history and status for an interest topic"""
    data = read_json_file(INTEREST_TOPICS_FILE)
    topics = data.get("topics", [])
    
    # Find the topic
    topic_index = None
    for i, topic in enumerate(topics):
        if topic.get("id") == topic_id and topic.get("userId") == user_id:
            topic_index = i
            break
    
    if topic_index is None:
        return None
    
    # Update conversation fields
    topics[topic_index]["conversationHistory"] = conversation_history
    topics[topic_index]["conversationStatus"] = conversation_status
    topics[topic_index]["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    
    write_json_file(INTEREST_TOPICS_FILE, data)
    
    return topics[topic_index]

def delete_interest_topic(topic_id: str, user_id: str) -> bool:
    """
    Delete an interest topic and cascade delete all associated data.

    This function performs cascade deletion by removing the entire topic object,
    which includes:
    - conversationHistory: All chat messages with the AI assistant
    - comprehensiveDescription: The detailed research interest description
    - All other topic metadata

    Args:
        topic_id: ID of the topic to delete
        user_id: User ID for authorization

    Returns:
        True if topic was deleted, False if not found

    Requirements: 11.4 (Cascade Deletion)
    """
    # Load existing topics
    data = read_json_file(INTEREST_TOPICS_FILE)
    topics = data.get("topics", [])

    # Find and remove the topic (cascade deletes all fields including
    # conversationHistory and comprehensiveDescription)
    initial_length = len(topics)
    data["topics"] = [
        topic for topic in topics
        if not (topic.get("id") == topic_id and topic.get("userId") == user_id)
    ]

    if len(data["topics"]) == initial_length:
        return False

    write_json_file(INTEREST_TOPICS_FILE, data)
    return True


def count_user_topics(user_id: str) -> int:
    """Count the number of interest topics for a user"""
    topics = get_user_interest_topics(user_id)
    return len(topics)

# Chatbot-related storage functions

def get_interest_topic_by_id(topic_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific interest topic by ID"""
    data = read_json_file(INTEREST_TOPICS_FILE)
    topics = data.get("topics", [])
    
    for topic in topics:
        if topic.get("id") == topic_id and topic.get("userId") == user_id:
            # Ensure backward compatibility
            if "comprehensiveDescription" not in topic:
                topic["comprehensiveDescription"] = None
            if "conversationHistory" not in topic:
                topic["conversationHistory"] = None
            if "conversationStatus" not in topic:
                topic["conversationStatus"] = "not_started"
            return topic
    
    return None

def update_conversation_history(
    topic_id: str,
    user_id: str,
    conversation_history: List[Dict[str, str]],
    conversation_status: str
) -> Optional[Dict[str, Any]]:
    """Update conversation history and status for an interest topic"""
    data = read_json_file(INTEREST_TOPICS_FILE)
    topics = data.get("topics", [])
    
    # Find the topic
    topic_index = None
    for i, topic in enumerate(topics):
        if topic.get("id") == topic_id and topic.get("userId") == user_id:
            topic_index = i
            break
    
    if topic_index is None:
        return None
    
    # Update conversation fields
    topics[topic_index]["conversationHistory"] = conversation_history
    topics[topic_index]["conversationStatus"] = conversation_status
    topics[topic_index]["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    
    write_json_file(INTEREST_TOPICS_FILE, data)
    
    return topics[topic_index]

def update_comprehensive_description(
    topic_id: str,
    user_id: str,
    description: str
) -> Optional[Dict[str, Any]]:
    """Update comprehensive description for an interest topic"""
    # Validate description
    if not description or not description.strip():
        raise ValueError("Comprehensive description cannot be empty")
    
    if len(description) > 5000:
        raise ValueError("Comprehensive description must be at most 5000 characters")
    
    data = read_json_file(INTEREST_TOPICS_FILE)
    topics = data.get("topics", [])
    
    # Find the topic
    topic_index = None
    for i, topic in enumerate(topics):
        if topic.get("id") == topic_id and topic.get("userId") == user_id:
            topic_index = i
            break
    
    if topic_index is None:
        return None
    
    # Update description and mark conversation as completed
    topics[topic_index]["comprehensiveDescription"] = description.strip()
    topics[topic_index]["conversationStatus"] = "completed"
    topics[topic_index]["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    
    write_json_file(INTEREST_TOPICS_FILE, data)
    
    return topics[topic_index]

def reset_conversation(topic_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Reset conversation history and status for an interest topic"""
    data = read_json_file(INTEREST_TOPICS_FILE)
    topics = data.get("topics", [])
    
    # Find the topic
    topic_index = None
    for i, topic in enumerate(topics):
        if topic.get("id") == topic_id and topic.get("userId") == user_id:
            topic_index = i
            break
    
    if topic_index is None:
        return None
    
    # Reset conversation fields
    topics[topic_index]["conversationHistory"] = None
    topics[topic_index]["conversationStatus"] = "not_started"
    topics[topic_index]["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    
    write_json_file(INTEREST_TOPICS_FILE, data)
    
    return topics[topic_index]
