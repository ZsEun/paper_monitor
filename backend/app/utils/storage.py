import json
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime
import uuid

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Storage Backend Abstraction
# ---------------------------------------------------------------------------

DATA_DIR = "data"


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol defining the storage backend interface."""

    def read_json(self, filename: str) -> Dict[str, Any]: ...
    def write_json(self, filename: str, data: Dict[str, Any]) -> None: ...


class LocalStorageBackend:
    """Local JSON file storage backend — wraps the original file-based logic."""

    def __init__(self, data_dir: str = DATA_DIR):
        self._data_dir = data_dir

    def _ensure_data_dir(self) -> None:
        if not os.path.exists(self._data_dir):
            os.makedirs(self._data_dir)

    def read_json(self, filename: str) -> Dict[str, Any]:
        self._ensure_data_dir()
        filepath = os.path.join(self._data_dir, filename)
        if not os.path.exists(filepath):
            return {}
        with open(filepath, "r") as f:
            return json.load(f)

    def write_json(self, filename: str, data: Dict[str, Any]) -> None:
        self._ensure_data_dir()
        filepath = os.path.join(self._data_dir, filename)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# DynamoDB helpers
# ---------------------------------------------------------------------------

def _convert_decimals(obj: Any) -> Any:
    """Recursively convert ``Decimal`` values from DynamoDB to int/float."""
    if isinstance(obj, list):
        return [_convert_decimals(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


def _convert_to_decimals(obj: Any) -> Any:
    """Recursively convert float/int values to ``Decimal`` for DynamoDB."""
    if isinstance(obj, list):
        return [_convert_to_decimals(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _convert_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, int) and not isinstance(obj, bool):
        return Decimal(str(obj))
    return obj


class DynamoDBStorageBackend:
    """DynamoDB-backed storage backend."""

    # Map JSON filenames to env-var names for table lookup
    _ENV_VAR_MAP: Dict[str, str] = {
        "users.json": "DYNAMODB_USERS_TABLE",
        "journals.json": "DYNAMODB_JOURNALS_TABLE",
        "digests.json": "DYNAMODB_DIGESTS_TABLE",
        "interest_topics.json": "DYNAMODB_TOPICS_TABLE",
        "credentials.json": "DYNAMODB_CREDENTIALS_TABLE",
    }

    # Primary key field used when reconstructing dicts from scans
    _PK_FIELD: Dict[str, str] = {
        "users.json": "email",
        "journals.json": "id",
        "digests.json": "id",
        "credentials.json": "id",
    }

    def __init__(self, table_name_map: Dict[str, str]) -> None:
        self._table_name_map = table_name_map
        self._dynamodb = boto3.resource("dynamodb")

    # -- public interface ----------------------------------------------------

    def read_json(self, filename: str) -> Dict[str, Any]:
        table = self._get_table(filename)
        try:
            items = self._scan_all(table)
        except ClientError as exc:
            raise self._to_http_exception(exc, filename)

        items = _convert_decimals(items)

        # interest_topics uses a list wrapper: {"topics": [...]}
        if filename == "interest_topics.json":
            return {"topics": items}

        # All other files are dicts keyed by their primary key
        pk = self._PK_FIELD.get(filename, "id")
        return {item[pk]: item for item in items if pk in item}

    def write_json(self, filename: str, data: Dict[str, Any]) -> None:
        table = self._get_table(filename)
        try:
            if filename == "interest_topics.json":
                for topic in data.get("topics", []):
                    table.put_item(Item=_convert_to_decimals(topic))
            else:
                for _key, item in data.items():
                    table.put_item(Item=_convert_to_decimals(item))
        except ClientError as exc:
            raise self._to_http_exception(exc, filename)

    # -- helpers -------------------------------------------------------------

    def _get_table(self, filename: str):
        table_name = self._table_name_map.get(filename)
        if not table_name:
            raise HTTPException(
                status_code=500,
                detail=f"No DynamoDB table mapping for '{filename}'",
            )
        return self._dynamodb.Table(table_name)

    @staticmethod
    def _scan_all(table) -> List[Dict[str, Any]]:
        """Paginated scan that returns all items."""
        items: List[Dict[str, Any]] = []
        response = table.scan()
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return items

    @staticmethod
    def _to_http_exception(exc: ClientError, filename: str) -> HTTPException:
        error_code = exc.response["Error"]["Code"]
        error_msg = exc.response["Error"]["Message"]
        if error_code == "ResourceNotFoundException":
            return HTTPException(
                status_code=500,
                detail=f"DynamoDB table for '{filename}' not found: {error_msg}",
            )
        if error_code == "ProvisionedThroughputExceededException":
            return HTTPException(
                status_code=503,
                detail=f"DynamoDB throughput exceeded for '{filename}'. Please retry later.",
            )
        return HTTPException(
            status_code=500,
            detail=f"DynamoDB error for '{filename}': [{error_code}] {error_msg}",
        )


# Singleton-style cached backend instance
_storage_backend: Optional[StorageBackend] = None


def get_storage_backend() -> StorageBackend:
    """Factory that returns the active storage backend.

    Reads the ``STORAGE_BACKEND`` environment variable:
    - ``"local"`` (default) → ``LocalStorageBackend``
    - ``"dynamodb"`` → ``DynamoDBStorageBackend``
    """
    global _storage_backend
    if _storage_backend is not None:
        return _storage_backend

    backend_type = os.environ.get("STORAGE_BACKEND", "local")
    if backend_type == "dynamodb":
        table_name_map: Dict[str, str] = {}
        for filename, env_var in DynamoDBStorageBackend._ENV_VAR_MAP.items():
            table_name = os.environ.get(env_var)
            if table_name:
                table_name_map[filename] = table_name
        _storage_backend = DynamoDBStorageBackend(table_name_map)
        return _storage_backend
    _storage_backend = LocalStorageBackend()
    return _storage_backend


# ---------------------------------------------------------------------------
# Legacy helper kept for backward compatibility
# ---------------------------------------------------------------------------

def ensure_data_dir() -> None:
    """Ensure data directory exists (delegates to backend for local)."""
    backend = get_storage_backend()
    if isinstance(backend, LocalStorageBackend):
        backend._ensure_data_dir()


# ---------------------------------------------------------------------------
# Top-level convenience functions — delegate to the active backend
# ---------------------------------------------------------------------------

def read_json_file(filename: str) -> Dict[str, Any]:
    """Read data from the active storage backend."""
    return get_storage_backend().read_json(filename)


def write_json_file(filename: str, data: Dict[str, Any]) -> None:
    """Write data to the active storage backend."""
    get_storage_backend().write_json(filename, data)


# ---------------------------------------------------------------------------
# Interest Topic Storage
# ---------------------------------------------------------------------------

INTEREST_TOPICS_FILE = "interest_topics.json"


def get_user_interest_topics(user_id: str) -> List[Dict[str, Any]]:
    """Get all interest topics for a user with backward compatibility for new fields."""
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
    """Add a new interest topic for a user."""
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
        "conversationStatus": "not_started",
    }

    data["topics"].append(new_topic)
    write_json_file(INTEREST_TOPICS_FILE, data)

    return new_topic


def add_interest_topic_with_description(
    user_id: str,
    topic_text: str,
    comprehensive_description: Optional[str] = None,
    conversation_status: str = "not_started",
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
            raise ValueError(
                f"Description too long: {len(comprehensive_description)} characters (max 5000)"
            )

    # Validate conversation status
    valid_statuses = ["not_started", "in_progress", "completed"]
    if conversation_status not in valid_statuses:
        conversation_status = "not_started"

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
        "conversationStatus": conversation_status,
    }

    data["topics"].append(new_topic)
    write_json_file(INTEREST_TOPICS_FILE, data)

    return new_topic


def update_interest_topic(
    topic_id: str, user_id: str, topic_text: str
) -> Optional[Dict[str, Any]]:
    """Update an existing interest topic."""
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
    """Count the number of interest topics for a user."""
    topics = get_user_interest_topics(user_id)
    return len(topics)


# ---------------------------------------------------------------------------
# Chatbot-related storage functions
# ---------------------------------------------------------------------------

def get_interest_topic_by_id(
    topic_id: str, user_id: str
) -> Optional[Dict[str, Any]]:
    """Get a specific interest topic by ID."""
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
    conversation_status: str,
) -> Optional[Dict[str, Any]]:
    """Update conversation history and status for an interest topic."""
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
        topic
        for topic in topics
        if not (topic.get("id") == topic_id and topic.get("userId") == user_id)
    ]

    if len(data["topics"]) == initial_length:
        return False

    write_json_file(INTEREST_TOPICS_FILE, data)
    return True


def update_comprehensive_description(
    topic_id: str,
    user_id: str,
    description: str,
) -> Optional[Dict[str, Any]]:
    """Update comprehensive description for an interest topic."""
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


def reset_conversation(
    topic_id: str, user_id: str
) -> Optional[Dict[str, Any]]:
    """Reset conversation history and status for an interest topic."""
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
