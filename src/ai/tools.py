"""Tool definitions for Gemini function calling.

These tools define the calendar operations available to the AI agent.
"""

from typing import List, Dict, Any


# Tool definitions in Gemini function calling format
CALENDAR_TOOLS = [
    {
        "name": "list_calendars",
        "description": "List all available calendars for the user. Use this to find calendar IDs or show the user their calendars.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_events",
        "description": """List events from a calendar within a time range. 
        Use this to:
        - Show the user their schedule
        - Check what events exist
        - Find events to update or delete
        
        Time format: ISO 8601 (YYYY-MM-DDTHH:MM:SS)""",
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID to query. Use 'primary' for the user's main calendar."
                },
                "time_min": {
                    "type": "string",
                    "description": "Start of time range in ISO 8601 format (YYYY-MM-DDTHH:MM:SS). If not specified, defaults to now."
                },
                "time_max": {
                    "type": "string",
                    "description": "End of time range in ISO 8601 format (YYYY-MM-DDTHH:MM:SS). If not specified, defaults to 7 days from now."
                },
                "time_zone": {
                    "type": "string",
                    "description": "Timezone for the query (e.g., 'America/New_York'). Optional."
                }
            },
            "required": ["calendar_id"]
        }
    },
    {
        "name": "search_events",
        "description": """Search for events by text query across a calendar.
        Use this to find specific events by name, description, or other text.
        
        Examples:
        - Find "team meeting"
        - Find "dentist"
        - Find events with "presentation" """,
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID to search. Use 'primary' for main calendar."
                },
                "query": {
                    "type": "string",
                    "description": "Search query text to find in event titles, descriptions, etc."
                },
                "time_min": {
                    "type": "string",
                    "description": "Start of time range to search (ISO 8601). Optional."
                },
                "time_max": {
                    "type": "string",
                    "description": "End of time range to search (ISO 8601). Optional."
                }
            },
            "required": ["calendar_id", "query"]
        }
    },
    {
        "name": "create_event",
        "description": """Create a new calendar event.
        
        Required information:
        - Event title/summary
        - Start date/time
        - End date/time (or duration)
        
        Optional:
        - Description
        - Location
        - Attendees (email addresses)
        
        Time format: ISO 8601 (YYYY-MM-DDTHH:MM:SS)
        
        IMPORTANT: Before calling this, ensure you have ALL required information from the user.
        If missing start time, end time, or title, ask the user first.""",
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID. Use 'primary' for main calendar."
                },
                "summary": {
                    "type": "string",
                    "description": "Event title/name"
                },
                "start": {
                    "type": "string",
                    "description": "Start date/time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
                },
                "end": {
                    "type": "string",
                    "description": "End date/time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
                },
                "description": {
                    "type": "string",
                    "description": "Event description/notes. Optional."
                },
                "location": {
                    "type": "string",
                    "description": "Event location/address. Optional."
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses. Optional."
                },
                "time_zone": {
                    "type": "string",
                    "description": "Timezone (e.g., 'America/New_York'). Optional."
                }
            },
            "required": ["calendar_id", "summary", "start", "end"]
        }
    },
    {
        "name": "update_event",
        "description": """Update an existing calendar event.
        
        Use this when the user wants to:
        - Change event time
        - Update event title
        - Modify location or description
        - Add/remove attendees
        
        IMPORTANT: You must have the event_id. If you don't have it, use search_events or list_events first.""",
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID where the event exists"
                },
                "event_id": {
                    "type": "string",
                    "description": "ID of the event to update"
                },
                "summary": {
                    "type": "string",
                    "description": "New event title. Optional."
                },
                "start": {
                    "type": "string",
                    "description": "New start time (ISO 8601). Optional."
                },
                "end": {
                    "type": "string",
                    "description": "New end time (ISO 8601). Optional."
                },
                "description": {
                    "type": "string",
                    "description": "New description. Optional."
                },
                "location": {
                    "type": "string",
                    "description": "New location. Optional."
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New attendee list. Optional."
                },
                "time_zone": {
                    "type": "string",
                    "description": "Timezone. Optional."
                }
            },
            "required": ["calendar_id", "event_id"]
        }
    },
    {
        "name": "delete_event",
        "description": """Delete a calendar event permanently.
        
        Use this when user wants to:
        - Cancel an event
        - Remove an event
        - Delete an event
        
        IMPORTANT: Confirm with user before deleting. This cannot be undone.""",
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID where the event exists"
                },
                "event_id": {
                    "type": "string",
                    "description": "ID of the event to delete"
                }
            },
            "required": ["calendar_id", "event_id"]
        }
    },
    {
        "name": "get_freebusy",
        "description": """Check free/busy status for calendars in a time range.
        
        Use this to:
        - Find available time slots
        - Check if user is busy at a specific time
        - Suggest meeting times
        
        Returns busy periods for each calendar.""",
        "parameters": {
            "type": "object",
            "properties": {
                "calendars": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of calendar IDs to check (e.g., ['primary'])"
                },
                "time_min": {
                    "type": "string",
                    "description": "Start of time range (ISO 8601)"
                },
                "time_max": {
                    "type": "string",
                    "description": "End of time range (ISO 8601)"
                },
                "time_zone": {
                    "type": "string",
                    "description": "Timezone. Optional."
                }
            },
            "required": ["calendars", "time_min", "time_max"]
        }
    },
    {
        "name": "get_current_time",
        "description": """Get the current time in the user's calendar timezone.
        
        Use this when:
        - User asks "what time is it"
        - You need to know the current time for date calculations
        - Converting relative dates like "tomorrow" or "next Monday" """,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "create_reminder",
        "description": """Create a custom reminder that will trigger at a specific time.
        
        Use this when user says things like:
        - "Remind me in 2 minutes"
        - "Remind me in an hour to call mom"
        - "Set a reminder for 3pm to take medicine"
        - "Remind me tomorrow at 9am about the presentation"
        
        The reminder will trigger automatically without user input.
        
        IMPORTANT: 
        - For "remind me in X minutes/hours", calculate the exact time
        - For "remind me at X", use that specific time
        - Always include what to remind about (summary)""",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "What to remind the user about. Be specific."
                },
                "minutes_from_now": {
                    "type": "integer",
                    "description": "Minutes from now to send reminder. Use this for 'remind me in X minutes/hours'."
                },
                "remind_at_time": {
                    "type": "string",
                    "description": "Specific time to remind (ISO 8601 format). Use this for 'remind me at 3pm' or 'remind me tomorrow at 9am'."
                }
            },
            "required": ["summary"]
        }
    }
]


def get_tool_by_name(tool_name: str) -> Dict[str, Any]:
    """Get a tool definition by name.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool definition dictionary
        
    Raises:
        ValueError: If tool not found
    """
    for tool in CALENDAR_TOOLS:
        if tool["name"] == tool_name:
            return tool
    raise ValueError(f"Tool '{tool_name}' not found")


def get_tool_names() -> List[str]:
    """Get list of all available tool names.
    
    Returns:
        List of tool names
    """
    return [tool["name"] for tool in CALENDAR_TOOLS]
