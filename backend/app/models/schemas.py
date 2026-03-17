from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

# User models
class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# Journal models
class JournalBase(BaseModel):
    name: str
    platform: str
    url: str

class JournalCreate(JournalBase):
    pass

class Journal(JournalBase):
    id: str
    addedAt: str
    isSubscribed: bool = True

    class Config:
        from_attributes = True

# Credential models
class CredentialBase(BaseModel):
    journalId: str
    journalName: str
    username: str
    credentialType: str

class CredentialCreate(CredentialBase):
    password: str

class Credential(CredentialBase):
    id: str
    addedAt: str
    maskedValue: str

    class Config:
        from_attributes = True

# Paper models
class Paper(BaseModel):
    id: str
    title: str
    authors: List[str]
    abstract: str
    aiSummary: Optional[str] = None
    url: str
    publishedDate: str
    journalId: str
    topics: List[str]

# Evaluation metadata models
class EvaluationMetadata(BaseModel):
    """Metadata about relevance evaluation for a digest"""
    totalPapersEvaluated: int
    relevantPapersIncluded: int
    evaluationErrors: int
    hadInterestTopics: bool

class PaperMatches(BaseModel):
    """Matching interest topics for a specific paper"""
    paperId: str
    matchingTopics: List[str]

# Digest models
class TopicGroup(BaseModel):
    topic: str
    paperCount: int
    papers: List[Paper]

class Digest(BaseModel):
    id: str
    generatedAt: str
    startDate: str
    endDate: str
    papers: List[Paper]
    papersByTopic: Dict[str, List[Paper]]
    topicGroups: List[TopicGroup]
    evaluationMetadata: Optional[EvaluationMetadata] = None
    paperMatches: Optional[List[PaperMatches]] = None

# Chatbot models
class Message(BaseModel):
    """Single message in a conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str  # ISO 8601

class ConversationStatus(str, Enum):
    """Status of a conversation session"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class ChatbotResponse(BaseModel):
    """Response from chatbot service"""
    message: str
    shouldConclude: bool
    conversationStatus: str

class ChatMessageRequest(BaseModel):
    """Request model for sending a message to the chatbot"""
    message: str

class DescriptionSaveRequest(BaseModel):
    """Request model for saving a comprehensive description"""
    description: str

class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history"""
    conversationHistory: List[Message]
    conversationStatus: str

# Interest Topic models
class InterestTopicBase(BaseModel):
    topicText: str

    @field_validator('topicText')
    @classmethod
    def validate_topic_text(cls, v: str) -> str:
        # Trim whitespace
        v = v.strip()
        
        # Check if empty or whitespace-only
        if not v:
            raise ValueError('Topic cannot be empty or whitespace only')
        
        # Check length constraints
        if len(v) < 2:
            raise ValueError('Topic must be at least 2 characters')
        if len(v) > 200:
            raise ValueError('Topic must be at most 200 characters')
        
        return v

class InterestTopicCreate(InterestTopicBase):
    pass

class InterestTopicUpdate(InterestTopicBase):
    pass

class InterestTopic(InterestTopicBase):
    id: str
    userId: str
    createdAt: str
    updatedAt: str
    comprehensiveDescription: Optional[str] = None
    conversationHistory: Optional[List[Dict[str, str]]] = None
    conversationStatus: str = "not_started"

    class Config:
        from_attributes = True

class InterestTopicWithDescription(BaseModel):
    """Extended interest topic model with comprehensive description"""
    id: str
    userId: str
    topicText: str
    comprehensiveDescription: Optional[str] = None
    conversationHistory: Optional[List[Message]] = None
    conversationStatus: str = "not_started"
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True
