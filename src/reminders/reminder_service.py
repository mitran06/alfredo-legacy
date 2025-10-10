"""Reminder service that coordinates monitoring and notifications.

This module provides the main ReminderService class that ties together
the EventMonitor and NotificationDispatcher.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta

from src.calendar_mcp.mcp_client import MCPClient
from src.reminders.event_monitor import EventMonitor
from src.reminders.notification_dispatcher import NotificationDispatcher
from config.config import RemindersConfig
from src.utils.logger import log_info, log_error, log_debug


class ReminderService:
    """Main service for managing reminders and notifications.
    
    This service:
    - Coordinates the EventMonitor and NotificationDispatcher
    - Provides high-level API for creating custom reminders
    - Manages service lifecycle (start/stop)
    """
    
    def __init__(
        self,
        mcp_client: MCPClient,
        config: RemindersConfig
    ):
        """Initialize the reminder service.
        
        Args:
            mcp_client: Connected MCP client for calendar access
            config: Reminders configuration
        """
        self.mcp_client = mcp_client
        self.config = config
        
        # Initialize components
        self.dispatcher = NotificationDispatcher()
        self.monitor = EventMonitor(
            mcp_client=mcp_client,
            notification_dispatcher=self.dispatcher,
            reminder_rules=config.default_rules,
            check_interval_seconds=config.check_interval_seconds
        )
        
        self._is_started = False
        
        log_info("ReminderService initialized")
    
    async def start(self) -> None:
        """Start the reminder service."""
        if self._is_started:
            log_debug("ReminderService already started")
            return
        
        if not self.config.enabled:
            log_info("Reminders disabled in configuration")
            return
        
        # Start dispatcher first (it processes the queue)
        await self.dispatcher.start()
        
        # Then start monitor (it adds to the queue)
        await self.monitor.start()
        
        self._is_started = True
        log_info("ReminderService started successfully")
    
    async def stop(self) -> None:
        """Stop the reminder service."""
        if not self._is_started:
            return
        
        # Stop monitor first (stop adding to queue)
        await self.monitor.stop()
        
        # Then stop dispatcher (process remaining queue items)
        await self.dispatcher.stop()
        
        self._is_started = False
        log_info("ReminderService stopped")
    
    def set_terminal_callback(self, callback) -> None:
        """Set callback for terminal notifications.
        
        Args:
            callback: Function to call when notification should be displayed
        """
        self.dispatcher.set_terminal_callback(callback)
        log_debug("Terminal callback set for ReminderService")
    
    def set_whatsapp_callback(self, callback) -> None:
        """Set callback for WhatsApp notifications.
        
        Args:
            callback: Function to call when notification should be sent via WhatsApp
        """
        self.dispatcher.set_whatsapp_callback(callback)
        log_debug("WhatsApp callback set for ReminderService")
    
    def create_reminder_in_minutes(
        self,
        summary: str,
        minutes: int,
        event_id: Optional[str] = None
    ) -> datetime:
        """Create a reminder that will fire in X minutes.
        
        This is used when user says "remind me in 2 minutes".
        
        Args:
            summary: What to remind about
            minutes: Minutes from now to remind
            event_id: Optional event ID if tied to calendar event
            
        Returns:
            The datetime when reminder will fire
        """
        remind_at = datetime.now() + timedelta(minutes=minutes)
        
        self.monitor.add_custom_reminder(
            event_summary=summary,
            remind_at=remind_at,
            event_id=event_id,
            event_start=remind_at
        )
        
        log_info(f"Created reminder: '{summary}' in {minutes} minutes")
        return remind_at
    
    def create_reminder_at_time(
        self,
        summary: str,
        remind_at: datetime,
        event_id: Optional[str] = None
    ) -> None:
        """Create a reminder at a specific time.
        
        Args:
            summary: What to remind about
            remind_at: When to send reminder
            event_id: Optional event ID if tied to calendar event
        """
        self.monitor.add_custom_reminder(
            event_summary=summary,
            remind_at=remind_at,
            event_id=event_id,
            event_start=remind_at
        )
        
        log_info(f"Created reminder: '{summary}' at {remind_at.strftime('%I:%M %p')}")
    
    def get_stats(self) -> dict:
        """Get reminder service statistics.
        
        Returns:
            Dictionary with service stats
        """
        monitor_stats = self.monitor.get_stats()
        dispatcher_stats = {
            "queue_size": self.dispatcher.get_queue_size()
        }
        
        return {
            "is_started": self._is_started,
            "enabled": self.config.enabled,
            "monitor": monitor_stats,
            "dispatcher": dispatcher_stats
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
