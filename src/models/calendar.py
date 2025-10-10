"""Data models for calendar entities."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Reminder(BaseModel):
    """Reminder configuration for an event."""
    method: str = Field(description="Reminder method: 'email' or 'popup'")
    minutes: int = Field(description="Minutes before event to remind")


class Attendee(BaseModel):
    """Event attendee information."""
    email: str = Field(description="Attendee email address")
    response_status: Optional[str] = Field(default=None, description="Response status: needsAction, declined, tentative, accepted")
    display_name: Optional[str] = Field(default=None, description="Attendee display name")
    optional: Optional[bool] = Field(default=False, description="Whether attendance is optional")
    organizer: Optional[bool] = Field(default=False, description="Whether this attendee is the organizer")
    self_attendee: Optional[bool] = Field(default=False, description="Whether this is the calendar owner")
    comment: Optional[str] = Field(default=None, description="Attendee comment")


class EventDateTime(BaseModel):
    """Event date/time information."""
    date_time: Optional[str] = Field(default=None, description="ISO 8601 datetime string with timezone")
    date: Optional[str] = Field(default=None, description="Date only (for all-day events)")
    time_zone: Optional[str] = Field(default=None, description="IANA timezone")


class Event(BaseModel):
    """Calendar event model."""
    id: str = Field(description="Event ID")
    calendar_id: str = Field(description="Calendar ID this event belongs to")
    summary: str = Field(description="Event title/summary")
    description: Optional[str] = Field(default=None, description="Event description")
    start: EventDateTime = Field(description="Event start date/time")
    end: EventDateTime = Field(description="Event end date/time")
    location: Optional[str] = Field(default=None, description="Event location")
    attendees: Optional[List[Attendee]] = Field(default=None, description="List of attendees")
    status: str = Field(default="confirmed", description="Event status: confirmed, tentative, cancelled")
    html_link: Optional[str] = Field(default=None, description="Link to event in Google Calendar")
    reminders: Optional[Dict[str, Any]] = Field(default=None, description="Reminder configuration")
    recurrence: Optional[List[str]] = Field(default=None, description="Recurrence rules (RRULE)")
    color_id: Optional[str] = Field(default=None, description="Event color ID")
    created: Optional[str] = Field(default=None, description="Creation timestamp")
    updated: Optional[str] = Field(default=None, description="Last update timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "abc123",
                "calendar_id": "primary",
                "summary": "Team Meeting",
                "description": "Weekly sync-up",
                "start": {
                    "date_time": "2024-10-15T10:00:00-07:00",
                    "time_zone": "America/Los_Angeles"
                },
                "end": {
                    "date_time": "2024-10-15T11:00:00-07:00",
                    "time_zone": "America/Los_Angeles"
                },
                "location": "Conference Room A",
                "status": "confirmed"
            }
        }


class EventCreate(BaseModel):
    """Model for creating a new event."""
    calendar_id: str = Field(default="primary", description="Calendar ID to create event in")
    summary: str = Field(description="Event title")
    description: Optional[str] = Field(default=None, description="Event description")
    start: str = Field(description="Start datetime in ISO 8601 format")
    end: str = Field(description="End datetime in ISO 8601 format")
    location: Optional[str] = Field(default=None, description="Event location")
    attendees: Optional[List[str]] = Field(default=None, description="List of attendee email addresses")
    reminders: Optional[List[Reminder]] = Field(default=None, description="Custom reminders")
    color_id: Optional[str] = Field(default=None, description="Event color ID")
    time_zone: Optional[str] = Field(default=None, description="Timezone for the event")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "calendar_id": "primary",
                "summary": "Dentist Appointment",
                "start": "2024-10-15T14:00:00",
                "end": "2024-10-15T15:00:00",
                "location": "123 Main St",
                "time_zone": "America/Los_Angeles"
            }
        }


class EventUpdate(BaseModel):
    """Model for updating an existing event."""
    calendar_id: str = Field(description="Calendar ID")
    event_id: str = Field(description="Event ID to update")
    summary: Optional[str] = Field(default=None, description="Updated title")
    description: Optional[str] = Field(default=None, description="Updated description")
    start: Optional[str] = Field(default=None, description="Updated start datetime")
    end: Optional[str] = Field(default=None, description="Updated end datetime")
    location: Optional[str] = Field(default=None, description="Updated location")
    attendees: Optional[List[str]] = Field(default=None, description="Updated attendees")
    status: Optional[str] = Field(default=None, description="Updated status")
    color_id: Optional[str] = Field(default=None, description="Updated color")
    time_zone: Optional[str] = Field(default=None, description="Timezone for updates")


class Calendar(BaseModel):
    """Calendar information model."""
    id: str = Field(description="Calendar ID")
    summary: str = Field(description="Calendar name/summary")
    description: Optional[str] = Field(default=None, description="Calendar description")
    time_zone: str = Field(description="Calendar timezone")
    primary: bool = Field(default=False, description="Whether this is the primary calendar")
    access_role: Optional[str] = Field(default=None, description="Access role: owner, writer, reader")
    background_color: Optional[str] = Field(default=None, description="Background color hex code")
    foreground_color: Optional[str] = Field(default=None, description="Foreground color hex code")


class FreeBusyCalendar(BaseModel):
    """Free/busy information for a calendar."""
    calendar_id: str = Field(description="Calendar ID")
    busy: List[Dict[str, str]] = Field(default_factory=list, description="List of busy time slots")
    errors: Optional[List[Dict[str, str]]] = Field(default=None, description="Any errors encountered")


class FreeBusyInfo(BaseModel):
    """Free/busy query result."""
    time_min: str = Field(description="Query start time")
    time_max: str = Field(description="Query end time")
    calendars: Dict[str, FreeBusyCalendar] = Field(description="Free/busy info per calendar")


class EventList(BaseModel):
    """List of events with metadata."""
    events: List[Event] = Field(description="List of events")
    total_count: int = Field(description="Total number of events")
    calendars: Optional[List[str]] = Field(default=None, description="Calendar IDs queried")


class CalendarList(BaseModel):
    """List of calendars."""
    calendars: List[Calendar] = Field(description="List of calendars")
    total_count: int = Field(description="Total number of calendars")
