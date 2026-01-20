"""
Conversation models for managing chat history and context
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class ConversationMessage(BaseModel):
    """Individual message in a conversation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class ConversationSession(BaseModel):
    """Complete conversation session"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    context_summary: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    sentiment: str = "neutral"
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a new message to the conversation"""
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata
        )
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, limit: int = 10) -> List[ConversationMessage]:
        """Get the most recent messages"""
        return self.messages[-limit:] if len(self.messages) > limit else self.messages
    
    def get_conversation_length(self) -> int:
        """Get total number of messages in conversation"""
        return len(self.messages)
    
    def update_context(self, summary: str, topics: List[str], sentiment: str):
        """Update conversation context analysis"""
        self.context_summary = summary
        self.topics = topics
        self.sentiment = sentiment
        self.updated_at = datetime.now()


class ConversationManager:
    """In-memory conversation manager for Phase 1"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
    
    def create_session(self, user_id: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session"""
        session = ConversationSession(user_id=user_id)
        self.sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get an existing conversation session"""
        return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> ConversationSession:
        """Get existing session or create new one"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self.create_session(user_id)
    
    def add_user_message(self, session_id: str, content: str) -> bool:
        """Add user message to session"""
        session = self.get_session(session_id)
        if session:
            session.add_message("user", content)
            return True
        return False
    
    def add_assistant_message(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add assistant message to session"""
        session = self.get_session(session_id)
        if session:
            session.add_message("assistant", content, metadata)
            return True
        return False
    
    def update_session_context(self, session_id: str, summary: str, topics: List[str], sentiment: str) -> bool:
        """Update session context analysis"""
        session = self.get_session(session_id)
        if session:
            session.update_context(summary, topics, sentiment)
            return True
        return False
    
    def get_active_sessions(self, limit: int = 100) -> List[ConversationSession]:
        """Get list of active sessions"""
        sessions = list(self.sessions.values())
        # Sort by updated_at desc
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions[:limit]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove old inactive sessions"""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.updated_at < cutoff_time
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        return len(expired_sessions)


# Global conversation manager instance
conversation_manager = ConversationManager()