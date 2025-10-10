"""MCP client for Google Calendar integration."""

import json
import asyncio
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..models.calendar import (
    Event, EventCreate, EventUpdate, Calendar, FreeBusyInfo,
    EventList, CalendarList, EventDateTime, Attendee
)
from ..utils.logger import log_info, log_error, log_debug, log_warning


class MCPClient:
    """Client for interfacing with Google Calendar MCP server."""
    
    def __init__(self, mcp_server_path: str, oauth_credentials_path: str):
        """Initialize the MCP client.
        
        Args:
            mcp_server_path: Path to the Google Calendar MCP server directory
            oauth_credentials_path: Path to OAuth credentials JSON file
        """
        self.mcp_server_path = Path(mcp_server_path)
        self.oauth_credentials_path = Path(oauth_credentials_path)
        self.session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None
        self._stdio_context = None
        self._session_context = None
        
        # Validate paths
        if not self.mcp_server_path.exists():
            raise FileNotFoundError(f"MCP server path not found: {mcp_server_path}")
        
        server_entry = self.mcp_server_path / "build" / "index.js"
        if not server_entry.exists():
            raise FileNotFoundError(
                f"MCP server not built. Run 'npm run build' in {mcp_server_path}"
            )
        
        if not self.oauth_credentials_path.exists():
            raise FileNotFoundError(
                f"OAuth credentials not found: {oauth_credentials_path}"
            )
    
    async def connect(self) -> None:
        """Connect to the MCP server."""
        log_info("Connecting to Google Calendar MCP server...")
        
        try:
            # Set up server parameters
            server_params = StdioServerParameters(
                command="node",
                args=[str(self.mcp_server_path / "build" / "index.js")],
                env={
                    "GOOGLE_OAUTH_CREDENTIALS": str(self.oauth_credentials_path),
                    **dict(os.environ)
                }
            )
            
            log_debug(f"Starting MCP server with command: node {self.mcp_server_path / 'build' / 'index.js'}")
            
            # Connect via stdio using context manager
            self._stdio_context = stdio_client(server_params)
            streams = await self._stdio_context.__aenter__()
            self._read_stream, self._write_stream = streams
            
            log_debug("Stdio streams established, creating session...")
            self._session_context = ClientSession(self._read_stream, self._write_stream)
            self.session = await self._session_context.__aenter__()
            
            log_debug("Initializing session...")
            result = await self.session.initialize()
            
            log_info("Successfully connected to MCP server")
            log_debug(f"Server: {result.serverInfo.name} v{result.serverInfo.version}")
            
        except Exception as e:
            log_error(f"Failed to connect to MCP server: {e}")
            import traceback
            log_error(traceback.format_exc())
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self.session:
            log_info("Disconnecting from MCP server...")
            try:
                # Close session context first
                if self._session_context:
                    await self._session_context.__aexit__(None, None, None)
                
                # Close stdio context
                if self._stdio_context:
                    await self._stdio_context.__aexit__(None, None, None)
                    
                log_info("Disconnected from MCP server")
            except Exception as e:
                log_error(f"Error during disconnect: {e}")
            finally:
                self.session = None
                self._stdio_context = None
                self._session_context = None
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool and return the result.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool response as dictionary
        """
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")
        
        log_debug(f"Calling MCP tool: {tool_name} with args: {arguments}")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            
            # Parse the response
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    response_data = json.loads(content.text)
                    log_debug(f"Tool {tool_name} completed successfully")
                    return response_data
            
            log_warning(f"Tool {tool_name} returned empty response")
            return {}
            
        except Exception as e:
            log_error(f"Error calling tool {tool_name}: {e}")
            raise
    
    async def list_calendars(self) -> CalendarList:
        """List all available calendars.
        
        Returns:
            CalendarList with all calendars
        """
        log_info("Fetching calendar list...")
        
        try:
            result = await self._call_tool("list-calendars", {})
            
            calendars = []
            for cal_data in result.get("calendars", []):
                calendar = Calendar(
                    id=cal_data["id"],
                    summary=cal_data.get("summary", ""),
                    description=cal_data.get("description"),
                    time_zone=cal_data.get("timeZone", "UTC"),
                    primary=cal_data.get("primary", False),
                    access_role=cal_data.get("accessRole"),
                    background_color=cal_data.get("backgroundColor"),
                    foreground_color=cal_data.get("foregroundColor")
                )
                calendars.append(calendar)
            
            log_info(f"Found {len(calendars)} calendars")
            return CalendarList(calendars=calendars, total_count=len(calendars))
            
        except Exception as e:
            log_error(f"Failed to list calendars: {e}")
            raise
    
    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        time_zone: Optional[str] = None
    ) -> EventList:
        """List events from a calendar.
        
        Args:
            calendar_id: Calendar ID (default: "primary")
            time_min: Start time in ISO 8601 format
            time_max: End time in ISO 8601 format
            time_zone: Timezone for the query
            
        Returns:
            EventList with matching events
        """
        log_info(f"Fetching events from calendar: {calendar_id}")
        
        # Default to next 7 days if not specified
        if not time_min:
            time_min = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if not time_max:
            time_max = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        
        arguments = {
            "calendarId": calendar_id,
            "timeMin": time_min,
            "timeMax": time_max
        }
        
        if time_zone:
            arguments["timeZone"] = time_zone
        
        try:
            result = await self._call_tool("list-events", arguments)
            
            events = []
            for event_data in result.get("events", []):
                event = self._parse_event(event_data, calendar_id)
                events.append(event)
            
            log_info(f"Found {len(events)} events")
            return EventList(
                events=events,
                total_count=len(events),
                calendars=[calendar_id]
            )
            
        except Exception as e:
            log_error(f"Failed to list events: {e}")
            raise
    
    async def create_event(self, event_create: EventCreate) -> Event:
        """Create a new calendar event.
        
        Args:
            event_create: Event creation data
            
        Returns:
            Created Event
        """
        log_info(f"Creating event: {event_create.summary}")
        
        arguments = {
            "calendarId": event_create.calendar_id,
            "summary": event_create.summary,
            "start": event_create.start,
            "end": event_create.end
        }
        
        # Add optional fields
        if event_create.description:
            arguments["description"] = event_create.description
        if event_create.location:
            arguments["location"] = event_create.location
        if event_create.attendees:
            arguments["attendees"] = event_create.attendees
        if event_create.color_id:
            arguments["colorId"] = event_create.color_id
        if event_create.time_zone:
            arguments["timeZone"] = event_create.time_zone
        
        try:
            result = await self._call_tool("create-event", arguments)
            
            event_data = result.get("event", {})
            event = self._parse_event(event_data, event_create.calendar_id)
            
            log_info(f"Successfully created event: {event.id}")
            return event
            
        except Exception as e:
            log_error(f"Failed to create event: {e}")
            raise
    
    async def update_event(self, event_update: EventUpdate) -> Event:
        """Update an existing calendar event.
        
        Args:
            event_update: Event update data
            
        Returns:
            Updated Event
        """
        log_info(f"Updating event: {event_update.event_id}")
        
        arguments = {
            "calendarId": event_update.calendar_id,
            "eventId": event_update.event_id
        }
        
        # Add fields to update
        if event_update.summary is not None:
            arguments["summary"] = event_update.summary
        if event_update.description is not None:
            arguments["description"] = event_update.description
        if event_update.start is not None:
            arguments["start"] = event_update.start
        if event_update.end is not None:
            arguments["end"] = event_update.end
        if event_update.location is not None:
            arguments["location"] = event_update.location
        if event_update.status is not None:
            arguments["status"] = event_update.status
        if event_update.color_id is not None:
            arguments["colorId"] = event_update.color_id
        if event_update.time_zone is not None:
            arguments["timeZone"] = event_update.time_zone
        
        try:
            result = await self._call_tool("update-event", arguments)
            
            event_data = result.get("event", {})
            event = self._parse_event(event_data, event_update.calendar_id)
            
            log_info(f"Successfully updated event: {event.id}")
            return event
            
        except Exception as e:
            log_error(f"Failed to update event: {e}")
            raise
    
    async def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete a calendar event.
        
        Args:
            calendar_id: Calendar ID
            event_id: Event ID to delete
            
        Returns:
            True if successful
        """
        log_info(f"Deleting event: {event_id}")
        
        arguments = {
            "calendarId": calendar_id,
            "eventId": event_id,
            "sendUpdates": "all"
        }
        
        try:
            result = await self._call_tool("delete-event", arguments)
            
            success = result.get("success", False)
            if success:
                log_info(f"Successfully deleted event: {event_id}")
            else:
                log_warning(f"Delete event returned success=False for: {event_id}")
            
            return success
            
        except Exception as e:
            log_error(f"Failed to delete event: {e}")
            raise
    
    async def search_events(
        self,
        query: str,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None
    ) -> EventList:
        """Search for events by text query.
        
        Args:
            query: Search query string
            calendar_id: Calendar ID to search
            time_min: Start time filter
            time_max: End time filter
            
        Returns:
            EventList with matching events
        """
        log_info(f"Searching events with query: '{query}'")
        
        # Default time range
        if not time_min:
            time_min = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if not time_max:
            time_max = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")
        
        arguments = {
            "calendarId": calendar_id,
            "query": query,
            "timeMin": time_min,
            "timeMax": time_max
        }
        
        try:
            result = await self._call_tool("search-events", arguments)
            
            events = []
            for event_data in result.get("events", []):
                event = self._parse_event(event_data, calendar_id)
                events.append(event)
            
            log_info(f"Found {len(events)} events matching query")
            return EventList(
                events=events,
                total_count=len(events),
                calendars=[calendar_id]
            )
            
        except Exception as e:
            log_error(f"Failed to search events: {e}")
            raise
    
    async def get_freebusy(
        self,
        calendars: List[str],
        time_min: str,
        time_max: str,
        time_zone: Optional[str] = None
    ) -> FreeBusyInfo:
        """Get free/busy information for calendars.
        
        Args:
            calendars: List of calendar IDs
            time_min: Start time in ISO 8601 format
            time_max: End time in ISO 8601 format
            time_zone: Timezone for the query
            
        Returns:
            FreeBusyInfo with availability data
        """
        log_info(f"Checking free/busy for {len(calendars)} calendar(s)")
        
        arguments = {
            "calendars": [{"id": cal_id} for cal_id in calendars],
            "timeMin": time_min,
            "timeMax": time_max
        }
        
        if time_zone:
            arguments["timeZone"] = time_zone
        
        try:
            result = await self._call_tool("get-freebusy", arguments)
            
            # Parse the result and add calendar_id to each entry
            calendars_data = result.get("calendars", {})
            parsed_calendars = {}
            for cal_id, cal_data in calendars_data.items():
                parsed_calendars[cal_id] = {
                    "calendar_id": cal_id,
                    "busy": cal_data.get("busy", []),
                    "errors": cal_data.get("errors")
                }
            
            freebusy_info = FreeBusyInfo(
                time_min=result.get("timeMin", time_min),
                time_max=result.get("timeMax", time_max),
                calendars=parsed_calendars
            )
            
            log_info("Successfully retrieved free/busy information")
            return freebusy_info
            
        except Exception as e:
            log_error(f"Failed to get free/busy info: {e}")
            raise
    
    async def get_current_time(self) -> Dict[str, Any]:
        """Get current time in the primary calendar's timezone.
        
        Returns:
            Dictionary with currentTime and timeZone
        """
        log_info("Getting current time...")
        
        try:
            result = await self._call_tool("get-current-time", {})
            log_info(f"Current time: {result.get('currentTime')}")
            return result
            
        except Exception as e:
            log_error(f"Failed to get current time: {e}")
            raise
    
    def _parse_event(self, event_data: Dict[str, Any], calendar_id: str) -> Event:
        """Parse event data from MCP response into Event model.
        
        Args:
            event_data: Raw event data from MCP
            calendar_id: Calendar ID
            
        Returns:
            Parsed Event object
        """
        # Parse start datetime
        start_data = event_data.get("start", {})
        start = EventDateTime(
            date_time=start_data.get("dateTime"),
            date=start_data.get("date"),
            time_zone=start_data.get("timeZone")
        )
        
        # Parse end datetime
        end_data = event_data.get("end", {})
        end = EventDateTime(
            date_time=end_data.get("dateTime"),
            date=end_data.get("date"),
            time_zone=end_data.get("timeZone")
        )
        
        # Parse attendees
        attendees = None
        if event_data.get("attendees"):
            attendees = [
                Attendee(
                    email=att.get("email", ""),
                    response_status=att.get("responseStatus"),
                    display_name=att.get("displayName"),
                    optional=att.get("optional"),
                    organizer=att.get("organizer"),
                    self_attendee=att.get("self"),
                    comment=att.get("comment")
                )
                for att in event_data["attendees"]
            ]
        
        return Event(
            id=event_data.get("id", ""),
            calendar_id=calendar_id,
            summary=event_data.get("summary", "Untitled Event"),
            description=event_data.get("description"),
            start=start,
            end=end,
            location=event_data.get("location"),
            attendees=attendees,
            status=event_data.get("status", "confirmed"),
            html_link=event_data.get("htmlLink"),
            reminders=event_data.get("reminders"),
            recurrence=event_data.get("recurrence"),
            color_id=event_data.get("colorId"),
            created=event_data.get("created"),
            updated=event_data.get("updated")
        )
