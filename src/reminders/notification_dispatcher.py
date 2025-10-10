"""Notification dispatcher for sending reminders to user.

This module handles dispatching notifications through various channels
(terminal, WhatsApp, etc.) when reminders are triggered.
"""

import asyncio
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass
from src.utils.logger import log_info, log_error, log_debug


@dataclass
class Notification:
    """A notification to be sent to the user."""
    message: str
    event_id: str
    event_summary: str
    event_start: datetime
    notification_type: str  # "reminder", "alert", "update"
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class NotificationDispatcher:
    """Manages notification delivery across multiple channels.
    
    The dispatcher can send notifications to:
    - Terminal (immediate display)
    - WhatsApp (future implementation)
    - Email (future implementation)
    """
    
    def __init__(self):
        """Initialize the notification dispatcher."""
        self._terminal_callback: Optional[Callable[[str], None]] = None
        self._whatsapp_callback: Optional[Callable[[str], None]] = None
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._is_running: bool = False
        self._dispatch_task: Optional[asyncio.Task] = None
        
        log_debug("NotificationDispatcher initialized")
    
    def set_terminal_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback function for terminal notifications.
        
        Args:
            callback: Function to call with notification message
        """
        self._terminal_callback = callback
        log_debug("Terminal callback registered")
    
    def set_whatsapp_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback function for WhatsApp notifications.
        
        Args:
            callback: Function to call with notification message
        """
        self._whatsapp_callback = callback
        log_debug("WhatsApp callback registered")
    
    async def start(self) -> None:
        """Start the notification dispatcher background task."""
        if self._is_running:
            log_debug("NotificationDispatcher already running")
            return
        
        self._is_running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        log_info("NotificationDispatcher started")
    
    async def stop(self) -> None:
        """Stop the notification dispatcher."""
        if not self._is_running:
            return
        
        self._is_running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        
        log_info("NotificationDispatcher stopped")
    
    async def send_notification(self, notification: Notification) -> None:
        """Queue a notification for dispatch.
        
        Args:
            notification: Notification to send
        """
        await self._notification_queue.put(notification)
        log_debug(f"Notification queued: {notification.message[:50]}...")
    
    async def send_reminder(
        self,
        event_summary: str,
        event_start: datetime,
        event_id: str,
        minutes_before: int
    ) -> None:
        """Send a reminder notification.
        
        Args:
            event_summary: Event title
            event_start: Event start time
            event_id: Event ID
            minutes_before: Minutes before event this reminder is sent
        """
        # Format the time nicely
        time_str = event_start.strftime("%I:%M %p").lstrip("0")
        date_str = event_start.strftime("%A, %B %d")
        
        # Create appropriate message based on timing
        if minutes_before >= 1440:  # 1 day or more
            days = minutes_before // 1440
            message = f"📅 Reminder: You have '{event_summary}' tomorrow at {time_str}"
        elif minutes_before >= 60:  # 1 hour or more
            hours = minutes_before // 60
            message = f"⏰ Upcoming: '{event_summary}' starts in {hours} hour{'s' if hours > 1 else ''} at {time_str}"
        else:
            message = f"🔔 Soon: '{event_summary}' starts in {minutes_before} minutes at {time_str}"
        
        notification = Notification(
            message=message,
            event_id=event_id,
            event_summary=event_summary,
            event_start=event_start,
            notification_type="reminder",
            created_at=datetime.now(),
            metadata={"minutes_before": minutes_before}
        )
        
        await self.send_notification(notification)
    
    async def _dispatch_loop(self) -> None:
        """Background task that processes the notification queue."""
        log_debug("Notification dispatch loop started")
        
        while self._is_running:
            try:
                # Wait for a notification with timeout to allow checking _is_running
                try:
                    notification = await asyncio.wait_for(
                        self._notification_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Dispatch to all registered channels
                await self._dispatch_to_channels(notification)
                
            except asyncio.CancelledError:
                log_debug("Dispatch loop cancelled")
                break
            except Exception as e:
                log_error(f"Error in dispatch loop: {e}")
                await asyncio.sleep(1)
        
        log_debug("Notification dispatch loop ended")
    
    async def _dispatch_to_channels(self, notification: Notification) -> None:
        """Dispatch notification to all registered channels.
        
        Args:
            notification: Notification to dispatch
        """
        # Terminal channel
        if self._terminal_callback:
            try:
                self._terminal_callback(notification.message)
                log_debug(f"Notification sent to terminal: {notification.event_summary}")
            except Exception as e:
                log_error(f"Failed to send terminal notification: {e}")
        
        # WhatsApp channel (future implementation)
        if self._whatsapp_callback:
            try:
                self._whatsapp_callback(notification.message)
                log_debug(f"Notification sent to WhatsApp: {notification.event_summary}")
            except Exception as e:
                log_error(f"Failed to send WhatsApp notification: {e}")
        
        # If no channels registered, log a warning
        if not self._terminal_callback and not self._whatsapp_callback:
            log_error(f"No notification channels registered for: {notification.message}")
    
    def get_queue_size(self) -> int:
        """Get the current size of the notification queue.
        
        Returns:
            Number of notifications waiting to be dispatched
        """
        return self._notification_queue.qsize()
