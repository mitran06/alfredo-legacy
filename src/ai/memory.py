"""Conversation memory management for context-aware interactions.

This module handles conversation history, pending actions, and context retrieval
for multi-turn conversations with the AI agent.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from src.utils.logger import log_debug, log_info


@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format for Gemini API.
        
        Returns:
            Dictionary with role and parts
        """
        return {
            "role": "user" if self.role == "user" else "model",
            "parts": [{"text": self.content}]
        }


@dataclass
class PendingAction:
    """Represents an action that requires more information from the user."""
    action_id: str
    action_type: str  # "create_event", "update_event", etc.
    collected_data: Dict[str, Any]
    missing_fields: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    attempts: int = 0  # Number of times we've asked for information
    context: Optional[str] = None  # Additional context about the action
    
    def is_complete(self) -> bool:
        """Check if all required fields have been collected.
        
        Returns:
            True if no missing fields, False otherwise
        """
        return len(self.missing_fields) == 0
    
    def update_field(self, field_name: str, value: Any) -> None:
        """Update a field in the collected data.
        
        Args:
            field_name: Name of the field to update
            value: Value to set
        """
        self.collected_data[field_name] = value
        if field_name in self.missing_fields:
            self.missing_fields.remove(field_name)
            log_debug(f"Collected field '{field_name}' for action {self.action_id}. Remaining: {self.missing_fields}")
        self.last_updated = datetime.now()
    
    def update_multiple_fields(self, updates: Dict[str, Any]) -> List[str]:
        """Update multiple fields at once.
        
        Args:
            updates: Dictionary of field names to values
            
        Returns:
            List of fields that were updated
        """
        updated_fields = []
        for field_name, value in updates.items():
            if value is not None:
                self.update_field(field_name, value)
                updated_fields.append(field_name)
        return updated_fields
    
    def get_next_missing_field(self) -> Optional[str]:
        """Get the next field that needs to be collected.
        
        Returns:
            Next missing field name or None if complete
        """
        if self.missing_fields:
            return self.missing_fields[0]
        return None
    
    def increment_attempts(self) -> int:
        """Increment the attempts counter.
        
        Returns:
            New attempts count
        """
        self.attempts += 1
        return self.attempts


class ConversationMemory:
    """Manages conversation history and context for the AI agent."""
    
    def __init__(self, max_history: int = 50, context_window: int = 10):
        """Initialize conversation memory.
        
        Args:
            max_history: Maximum number of messages to store
            context_window: Number of recent messages to include in context
        """
        self.max_history = max_history
        self.context_window = context_window
        self.messages: List[Message] = []
        self.pending_actions: Dict[str, PendingAction] = {}
        
        log_info(f"Conversation memory initialized (max_history={max_history}, context_window={context_window})")
    
    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a user message to conversation history.
        
        Args:
            content: Message content
            metadata: Optional metadata dictionary
        """
        message = Message(role="user", content=content, metadata=metadata)
        self.messages.append(message)
        self._trim_history()
        log_debug(f"Added user message: '{content[:50]}...'")
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add an assistant message to conversation history.
        
        Args:
            content: Message content
            metadata: Optional metadata dictionary
        """
        message = Message(role="assistant", content=content, metadata=metadata)
        self.messages.append(message)
        self._trim_history()
        log_debug(f"Added assistant message: '{content[:50]}...'")
    
    def create_pending_action(
        self,
        action_type: str,
        collected_data: Dict[str, Any],
        missing_fields: List[str]
    ) -> str:
        """Create a new pending action.
        
        Args:
            action_type: Type of action (e.g., "create_event")
            collected_data: Data already collected
            missing_fields: List of fields still needed
            
        Returns:
            Action ID
        """
        action_id = str(uuid4())[:8]
        action = PendingAction(
            action_id=action_id,
            action_type=action_type,
            collected_data=collected_data,
            missing_fields=missing_fields
        )
        self.pending_actions[action_id] = action
        log_info(f"Created pending action {action_id} ({action_type}). Missing fields: {missing_fields}")
        return action_id
    
    def get_pending_action(self, action_id: str) -> Optional[PendingAction]:
        """Get a pending action by ID.
        
        Args:
            action_id: Action ID
            
        Returns:
            PendingAction if found, None otherwise
        """
        return self.pending_actions.get(action_id)
    
    def get_latest_pending_action(self) -> Optional[PendingAction]:
        """Get the most recently created pending action.
        
        Returns:
            Latest PendingAction if any exist, None otherwise
        """
        if not self.pending_actions:
            return None
        
        # Sort by created_at and return most recent
        sorted_actions = sorted(
            self.pending_actions.values(),
            key=lambda a: a.created_at,
            reverse=True
        )
        return sorted_actions[0]
    
    def complete_pending_action(self, action_id: str) -> None:
        """Mark a pending action as complete and remove it.
        
        Args:
            action_id: Action ID to complete
        """
        if action_id in self.pending_actions:
            action = self.pending_actions.pop(action_id)
            log_info(f"Completed pending action {action_id} ({action.action_type})")
        else:
            log_debug(f"Attempted to complete non-existent action {action_id}")
    
    def update_pending_action(self, action_id: str, field_name: str, value: Any) -> None:
        """Update a field in a pending action.
        
        Args:
            action_id: Action ID
            field_name: Field to update
            value: New value
        """
        action = self.get_pending_action(action_id)
        if action:
            action.update_field(field_name, value)
        else:
            log_debug(f"Cannot update non-existent action {action_id}")
    
    def get_conversation_context(self, window: Optional[int] = None) -> List[Message]:
        """Get recent conversation messages for context.
        
        Args:
            window: Number of messages to retrieve (defaults to context_window)
            
        Returns:
            List of recent messages
        """
        window_size = window or self.context_window
        return self.messages[-window_size:]
    
    def get_context_for_gemini(self, window: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation context formatted for Gemini API.
        
        Args:
            window: Number of messages to retrieve
            
        Returns:
            List of message dictionaries for Gemini
        """
        messages = self.get_conversation_context(window)
        return [msg.to_dict() for msg in messages]
    
    def has_pending_actions(self) -> bool:
        """Check if there are any pending actions.
        
        Returns:
            True if pending actions exist
        """
        return len(self.pending_actions) > 0
    
    def get_pending_actions_summary(self) -> str:
        """Get a summary of pending actions for context.
        
        Returns:
            Human-readable summary string
        """
        if not self.pending_actions:
            return "No pending actions."
        
        summaries = []
        for action in self.pending_actions.values():
            status = "complete" if action.is_complete() else f"waiting for: {', '.join(action.missing_fields)}"
            summaries.append(f"- {action.action_type} ({status})")
        
        return "\n".join(summaries)
    
    def clear(self) -> None:
        """Clear all conversation history and pending actions."""
        self.messages.clear()
        self.pending_actions.clear()
        log_info("Conversation memory cleared")
    
    def _trim_history(self) -> None:
        """Trim message history to max_history size."""
        if len(self.messages) > self.max_history:
            removed = len(self.messages) - self.max_history
            self.messages = self.messages[-self.max_history:]
            log_debug(f"Trimmed {removed} old messages from history")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics.
        
        Returns:
            Dictionary with memory stats
        """
        return {
            "total_messages": len(self.messages),
            "user_messages": sum(1 for m in self.messages if m.role == "user"),
            "assistant_messages": sum(1 for m in self.messages if m.role == "assistant"),
            "pending_actions": len(self.pending_actions),
            "oldest_message": self.messages[0].timestamp if self.messages else None,
            "newest_message": self.messages[-1].timestamp if self.messages else None
        }
