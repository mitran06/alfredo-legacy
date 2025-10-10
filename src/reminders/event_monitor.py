"""Event monitor for background calendar polling and reminder triggering.

This module implements the core monitoring loop that checks for upcoming
events and triggers reminders at appropriate times.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field

from src.calendar_mcp.mcp_client import MCPClient
from src.models.calendar import Event
from src.reminders.notification_dispatcher import NotificationDispatcher
from config.config import ReminderRule
from src.utils.logger import log_info, log_error, log_debug


@dataclass
class ScheduledReminder:
    """A reminder scheduled for a specific event."""
    event_id: str
    event_summary: str
    event_start: datetime
    remind_at: datetime
    offset_minutes: int
    rule_index: int  # Which rule triggered this reminder
    
    def __hash__(self):
        """Make hashable for set storage."""
        return hash((self.event_id, self.offset_minutes))
    
    def __eq__(self, other):
        """Equality check for deduplication."""
        if not isinstance(other, ScheduledReminder):
            return False
        return self.event_id == other.event_id and self.offset_minutes == other.offset_minutes


class EventMonitor:
    """Monitors calendar events and triggers reminders.
    
    This runs as a background asyncio task that:
    1. Polls upcoming events periodically
    2. Schedules reminders based on configured rules
    3. Triggers notifications when reminder time arrives
    4. Supports custom one-time reminders
    """
    
    def __init__(
        self,
        mcp_client: MCPClient,
        notification_dispatcher: NotificationDispatcher,
        reminder_rules: List[ReminderRule],
        check_interval_seconds: int = 60
    ):
        """Initialize the event monitor.
        
        Args:
            mcp_client: Connected MCP client for calendar access
            notification_dispatcher: Dispatcher for sending notifications
            reminder_rules: List of reminder rules to apply
            check_interval_seconds: How often to check for events
        """
        self.mcp_client = mcp_client
        self.dispatcher = notification_dispatcher
        self.reminder_rules = [rule for rule in reminder_rules if rule.enabled]
        self.check_interval = check_interval_seconds
        
        # Track reminders that have already been sent
        self._sent_reminders: Set[ScheduledReminder] = set()
        
        # Track custom reminders (set by user via "remind me in X minutes")
        self._custom_reminders: List[ScheduledReminder] = []
        
        # Control flags
        self._is_running: bool = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        log_info(f"EventMonitor initialized with {len(self.reminder_rules)} rules, "
                f"check interval: {check_interval_seconds}s")
    
    async def start(self) -> None:
        """Start the event monitoring background task."""
        if self._is_running:
            log_debug("EventMonitor already running")
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        log_info("EventMonitor started")
    
    async def stop(self) -> None:
        """Stop the event monitoring."""
        if not self._is_running:
            return
        
        self._is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        log_info("EventMonitor stopped")
    
    def add_custom_reminder(
        self,
        event_summary: str,
        remind_at: datetime,
        event_id: Optional[str] = None,
        event_start: Optional[datetime] = None
    ) -> None:
        """Add a custom one-time reminder.
        
        This allows users to say "remind me in 2 minutes" and have it work.
        
        Args:
            event_summary: What to remind about
            remind_at: When to send the reminder
            event_id: Optional event ID if tied to a calendar event
            event_start: Optional event start time
        """
        reminder = ScheduledReminder(
            event_id=event_id or f"custom_{datetime.now().timestamp()}",
            event_summary=event_summary,
            event_start=event_start or remind_at,
            remind_at=remind_at,
            offset_minutes=0,  # Custom reminder
            rule_index=-1  # Indicates custom reminder
        )
        
        self._custom_reminders.append(reminder)
        log_info(f"Custom reminder added: '{event_summary}' at {remind_at.strftime('%I:%M %p')}")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop that runs in the background."""
        log_debug("Event monitor loop started")
        
        while self._is_running:
            try:
                # Check and send any pending reminders
                await self._check_and_send_reminders()
                
                # Wait for next check interval
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                log_debug("Monitor loop cancelled")
                break
            except Exception as e:
                log_error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.check_interval)
        
        log_debug("Event monitor loop ended")
    
    async def _check_and_send_reminders(self) -> None:
        """Check for events and send any due reminders."""
        now = datetime.now()
        
        # Check custom reminders first
        await self._check_custom_reminders(now)
        
        # Check calendar events
        await self._check_calendar_reminders(now)
    
    async def _check_custom_reminders(self, now: datetime) -> None:
        """Check and send custom reminders.
        
        Args:
            now: Current time
        """
        due_reminders = []
        
        for reminder in self._custom_reminders[:]:  # Copy list to allow modification
            if reminder.remind_at <= now:
                due_reminders.append(reminder)
                self._custom_reminders.remove(reminder)
        
        for reminder in due_reminders:
            log_debug(f"Sending custom reminder: {reminder.event_summary}")
            
            # Send notification
            await self.dispatcher.send_reminder(
                event_summary=reminder.event_summary,
                event_start=reminder.event_start,
                event_id=reminder.event_id,
                minutes_before=0  # Custom reminder, no offset
            )
    
    async def _check_calendar_reminders(self, now: datetime) -> None:
        """Check calendar events and send reminders.
        
        Args:
            now: Current time
        """
        try:
            # Get maximum lookahead time based on reminder rules
            max_offset = max(rule.offset_minutes for rule in self.reminder_rules) if self.reminder_rules else 1440
            time_max = now + timedelta(minutes=max_offset + 60)  # Add buffer
            
            # Format times properly for MCP (YYYY-MM-DDTHH:MM:SS format, no microseconds)
            time_min_str = now.strftime("%Y-%m-%dT%H:%M:%S")
            time_max_str = time_max.strftime("%Y-%m-%dT%H:%M:%S")
            
            # List upcoming events
            event_list = await self.mcp_client.list_events(
                calendar_id="primary",
                time_min=time_min_str,
                time_max=time_max_str
            )
            
            # Get events from EventList
            events = event_list.events if hasattr(event_list, 'events') else event_list
            log_debug(f"Found {len(events)} upcoming events")
            
            # Check each event against reminder rules
            for event in events:
                await self._process_event_reminders(event, now)
                
        except Exception as e:
            log_error(f"Error checking calendar reminders: {e}")
    
    async def _process_event_reminders(self, event: Event, now: datetime) -> None:
        """Process reminders for a specific event.
        
        Args:
            event: Event to process
            now: Current time
        """
        if not event.start or not event.summary:
            return
        
        event_start = event.start
        
        # Check each reminder rule
        for rule_index, rule in enumerate(self.reminder_rules):
            remind_at = event_start - timedelta(minutes=rule.offset_minutes)
            
            # Skip if reminder time hasn't arrived yet
            if remind_at > now:
                continue
            
            # Create reminder object for tracking
            reminder = ScheduledReminder(
                event_id=event.id,
                event_summary=event.summary,
                event_start=event_start,
                remind_at=remind_at,
                offset_minutes=rule.offset_minutes,
                rule_index=rule_index
            )
            
            # Skip if already sent
            if reminder in self._sent_reminders:
                continue
            
            # Send the reminder
            log_info(f"Triggering reminder for '{event.summary}' "
                    f"({rule.offset_minutes} min before)")
            
            await self.dispatcher.send_reminder(
                event_summary=event.summary,
                event_start=event_start,
                event_id=event.id,
                minutes_before=rule.offset_minutes
            )
            
            # Mark as sent
            self._sent_reminders.add(reminder)
    
    def get_stats(self) -> Dict[str, int]:
        """Get monitoring statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "sent_reminders": len(self._sent_reminders),
            "custom_reminders_pending": len(self._custom_reminders),
            "active_rules": len(self.reminder_rules),
            "is_running": int(self._is_running)
        }
