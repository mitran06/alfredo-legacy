"""Gemini AI agent for natural language calendar interactions.

This module implements the core AI agent that processes user messages,
calls calendar tools, and generates natural responses.
"""

import google.generativeai as genai
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

from src.ai.tools import CALENDAR_TOOLS, get_tool_names
from src.ai.memory import ConversationMemory, PendingAction
from src.calendar_mcp.mcp_client import MCPClient
from src.models.calendar import EventCreate, EventUpdate
from src.utils.logger import log_info, log_error, log_debug
from src.utils.date_parser import parse_datetime_range, parse_natural_date, to_iso_format
from src.utils.info_extractor import InformationExtractor


class AgentResponse:
    """Response from the AI agent."""
    
    def __init__(self, message: str, tools_used: List[str] = None, metadata: Dict[str, Any] = None):
        """Initialize agent response.
        
        Args:
            message: Response message to user
            tools_used: List of tool names that were called
            metadata: Additional response metadata
        """
        self.message = message
        self.tools_used = tools_used or []
        self.metadata = metadata or {}


class GeminiAgent:
    """AI agent powered by Google Gemini for calendar management."""
    
    def __init__(self, api_key: str, mcp_client: MCPClient, model_name: str = "gemini-2.5-flash", reminder_service=None):
        """Initialize the Gemini agent.
        
        Args:
            api_key: Google Gemini API key
            mcp_client: Connected MCP client for calendar operations
            model_name: Gemini model to use
            reminder_service: Optional ReminderService for creating custom reminders
        """
        self.api_key = api_key
        self.mcp_client = mcp_client
        self.model_name = model_name
        self.reminder_service = reminder_service
        self.memory = ConversationMemory()
        self.extractor = InformationExtractor()  # For extracting structured info
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=self._build_tool_declarations()
        )
        
        # System instruction for the agent
        self.system_instruction = """
You are a helpful personal assistant managing the user's Google Calendar.

Your responsibilities:
- Help users create, update, view, and delete calendar events through natural conversation
- Gather information step-by-step if the user doesn't provide everything at once
- Answer questions about their schedule
- Be conversational, friendly, and patient
- Use the calendar tools provided to interact with Google Calendar

Information gathering approach:
- When a user mentions an event without complete details, acknowledge what they said and ask for missing information ONE FIELD AT A TIME
- For creating events, you MUST have: event title/summary, start date/time, and end date/time (or duration)
- Ask questions naturally: "What time?" instead of "Please provide the start time"
- If user provides partial info (e.g., "Monday at 8 AM"), acknowledge it and ask for remaining info (e.g., "Got it! How long should I block out?")
- Keep track of what you've already collected and don't re-ask for it

Important guidelines:
- ALWAYS use get_current_time FIRST when user mentions relative dates ("tomorrow", "next Monday", "Wednesday")
- Use 'primary' as the calendar_id for the user's main calendar
- Confirm before deleting events
- When user says "yes" or "ok" after you've asked if they want to create an event, proceed with creation
- Keep responses concise but warm and encouraging

Context awareness:
- Remember what the user has told you in this conversation
- If they say "Wednesday" and you asked about what day, understand they're answering your question
- If they give a time like "2 PM", check if you were waiting for a time
- Build up the event details progressively through the conversation
"""
        
        log_info(f"Gemini agent initialized with model: {model_name}")
    
    def _build_tool_declarations(self) -> List[Dict[str, Any]]:
        """Build tool declarations for Gemini function calling.
        
        Returns:
            List of tool declarations in Gemini format
        """
        declarations = []
        for tool in CALENDAR_TOOLS:
            declaration = {
                "function_declarations": [{
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }]
            }
            declarations.append(declaration)
        
        log_debug(f"Built {len(declarations)} tool declarations for Gemini")
        return declarations
    
    async def process_message(self, user_message: str) -> AgentResponse:
        """Process a user message and generate a response.
        
        This is the main entry point for the agent. It:
        1. Adds message to conversation history
        2. Checks for pending actions
        3. Calls Gemini with context and tools
        4. Executes any tool calls
        5. Generates final response
        
        Args:
            user_message: User's input message
            
        Returns:
            AgentResponse with reply and metadata
        """
        log_info(f"[LOG] Processing user message...")
        self.memory.add_user_message(user_message)
        
        try:
            # Check if we have pending actions
            pending = self.memory.get_latest_pending_action()
            if pending:
                log_debug(f"Found pending action: {pending.action_id} ({pending.action_type})")
                # Try to extract info from user message for pending action
                response = await self._handle_pending_action(user_message, pending)
                if response:
                    return response
            
            # Build conversation context
            context = self._build_context()
            
            # Call Gemini
            response = await self._call_gemini(context, user_message)
            
            # Store assistant response
            self.memory.add_assistant_message(response.message)
            
            return response
            
        except Exception as e:
            log_error(f"Error processing message: {e}")
            import traceback
            log_error(traceback.format_exc())
            
            error_response = AgentResponse(
                message="I'm sorry, I encountered an error processing your request. Please try again.",
                metadata={"error": str(e)}
            )
            self.memory.add_assistant_message(error_response.message)
            return error_response
    
    async def _call_gemini(self, context: str, user_message: str) -> AgentResponse:
        """Call Gemini API with context and tools.
        
        Args:
            context: Conversation context string
            user_message: Latest user message
            
        Returns:
            AgentResponse
        """
        log_debug("Calling Gemini API...")
        
        # Build conversation history for Gemini
        history = self.memory.get_context_for_gemini(window=5)  # Last 5 messages
        
        # Start chat with history
        chat = self.model.start_chat(history=history[:-1] if history else [])
        
        # Build the prompt with context
        prompt = f"{self.system_instruction}\n\n{context}\n\nUser: {user_message}"
        
        # Send message and enable automatic function calling
        response = chat.send_message(prompt)
        
        tools_used = []
        
        # Handle function calls
        while response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            
            # Check if this is a function call
            if hasattr(part, 'function_call') and part.function_call:
                function_call = part.function_call
                tool_name = function_call.name
                tool_args = dict(function_call.args)
                
                log_info(f"[LOG] Gemini requesting tool: {tool_name}")
                log_debug(f"Tool arguments: {tool_args}")
                
                # Execute the tool
                tool_result = await self._execute_tool(tool_name, tool_args)
                tools_used.append(tool_name)
                
                # Send result back to Gemini
                response = chat.send_message(
                    {
                        "role": "function",
                        "parts": [{
                            "function_response": {
                                "name": tool_name,
                                "response": tool_result
                            }
                        }]
                    }
                )
            else:
                # Got text response
                break
        
        # Extract final text response
        final_text = response.text if response.text else "I've processed your request."
        
        log_debug(f"Gemini response: {final_text[:100]}...")
        
        return AgentResponse(
            message=final_text,
            tools_used=tools_used,
            metadata={"model": self.model_name}
        )
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a calendar tool via MCP client.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        log_info(f"[LOG] Executing tool: {tool_name}")
        
        try:
            if tool_name == "list_calendars":
                result = await self.mcp_client.list_calendars()
                return {
                    "success": True,
                    "calendars": [
                        {
                            "id": cal.id,
                            "summary": cal.summary,
                            "primary": cal.primary
                        }
                        for cal in result.calendars
                    ]
                }
            
            elif tool_name == "list_events":
                result = await self.mcp_client.list_events(
                    calendar_id=arguments.get("calendar_id", "primary"),
                    time_min=arguments.get("time_min"),
                    time_max=arguments.get("time_max"),
                    time_zone=arguments.get("time_zone")
                )
                return {
                    "success": True,
                    "events": [
                        {
                            "id": event.id,
                            "summary": event.summary,
                            "start": event.start.date_time if event.start else None,
                            "end": event.end.date_time if event.end else None,
                            "location": event.location,
                            "description": event.description
                        }
                        for event in result.events
                    ],
                    "count": result.total_count
                }
            
            elif tool_name == "search_events":
                result = await self.mcp_client.search_events(
                    calendar_id=arguments.get("calendar_id", "primary"),
                    query=arguments["query"],
                    time_min=arguments.get("time_min"),
                    time_max=arguments.get("time_max")
                )
                return {
                    "success": True,
                    "events": [
                        {
                            "id": event.id,
                            "summary": event.summary,
                            "start": event.start.date_time if event.start else None,
                            "end": event.end.date_time if event.end else None
                        }
                        for event in result.events
                    ],
                    "count": result.total_count
                }
            
            elif tool_name == "create_event":
                event_create = EventCreate(
                    calendar_id=arguments.get("calendar_id", "primary"),
                    summary=arguments["summary"],
                    start=arguments["start"],
                    end=arguments["end"],
                    description=arguments.get("description"),
                    location=arguments.get("location"),
                    attendees=arguments.get("attendees"),
                    time_zone=arguments.get("time_zone")
                )
                result = await self.mcp_client.create_event(event_create)
                return {
                    "success": True,
                    "event_id": result.id,
                    "summary": result.summary,
                    "start": result.start.date_time if result.start else None,
                    "link": result.html_link
                }
            
            elif tool_name == "update_event":
                event_update = EventUpdate(
                    calendar_id=arguments["calendar_id"],
                    event_id=arguments["event_id"],
                    summary=arguments.get("summary"),
                    start=arguments.get("start"),
                    end=arguments.get("end"),
                    description=arguments.get("description"),
                    location=arguments.get("location"),
                    attendees=arguments.get("attendees"),
                    time_zone=arguments.get("time_zone")
                )
                result = await self.mcp_client.update_event(event_update)
                return {
                    "success": True,
                    "event_id": result.id,
                    "summary": result.summary
                }
            
            elif tool_name == "delete_event":
                await self.mcp_client.delete_event(
                    calendar_id=arguments["calendar_id"],
                    event_id=arguments["event_id"]
                )
                return {
                    "success": True,
                    "message": "Event deleted successfully"
                }
            
            elif tool_name == "get_freebusy":
                result = await self.mcp_client.get_freebusy(
                    calendars=arguments["calendars"],
                    time_min=arguments["time_min"],
                    time_max=arguments["time_max"],
                    time_zone=arguments.get("time_zone")
                )
                return {
                    "success": True,
                    "time_min": result.time_min,
                    "time_max": result.time_max,
                    "busy_periods": {
                        cal_id: cal_data.busy
                        for cal_id, cal_data in result.calendars.items()
                    }
                }
            
            elif tool_name == "get_current_time":
                result = await self.mcp_client.get_current_time()
                return {
                    "success": True,
                    "current_time": result.get("currentTime"),
                    "timezone": result.get("timeZone")
                }
            
            elif tool_name == "create_reminder":
                # Handle reminder creation
                if not self.reminder_service:
                    return {
                        "success": False,
                        "error": "Reminder service not available"
                    }
                
                summary = arguments.get("summary", "Reminder")
                minutes_from_now = arguments.get("minutes_from_now")
                remind_at_time = arguments.get("remind_at_time")
                
                if minutes_from_now is not None:
                    # Create reminder X minutes from now
                    remind_at = self.reminder_service.create_reminder_in_minutes(
                        summary=summary,
                        minutes=minutes_from_now
                    )
                    return {
                        "success": True,
                        "message": f"Reminder set for {remind_at.strftime('%I:%M %p')}",
                        "summary": summary,
                        "remind_at": remind_at.isoformat()
                    }
                elif remind_at_time:
                    # Create reminder at specific time
                    from dateutil import parser
                    remind_at = parser.parse(remind_at_time)
                    self.reminder_service.create_reminder_at_time(
                        summary=summary,
                        remind_at=remind_at
                    )
                    return {
                        "success": True,
                        "message": f"Reminder set for {remind_at.strftime('%I:%M %p on %B %d')}",
                        "summary": summary,
                        "remind_at": remind_at.isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "error": "Must specify either minutes_from_now or remind_at_time"
                    }
            
            else:
                log_error(f"Unknown tool: {tool_name}")
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        except Exception as e:
            log_error(f"Tool execution error ({tool_name}): {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_pending_action(
        self,
        user_message: str,
        pending: PendingAction
    ) -> Optional[AgentResponse]:
        """Handle a pending action by extracting info from user message.
        
        This method attempts to extract information from the user's message
        to fill in missing fields for a pending action. If enough information
        is collected, it may execute the action.
        
        Args:
            user_message: User's message
            pending: Pending action
            
        Returns:
            AgentResponse if we want to handle this directly, None to let Gemini handle it
        """
        # Extract information from the message
        extracted = self.extractor.extract_from_message(user_message)
        
        # Get current time for context
        try:
            current_time_result = await self.mcp_client.get_current_time()
            current_date = datetime.fromisoformat(current_time_result.get('currentTime').replace('Z', '+00:00'))
        except:
            current_date = datetime.now()
        
        # Merge extracted info with existing data
        updated_data = self.extractor.merge_extracted_info(
            pending.collected_data,
            extracted,
            current_date
        )
        
        # Update the pending action
        updates_made = pending.update_multiple_fields(updated_data)
        
        if updates_made:
            log_info(f"[LOG] Updated pending action with: {', '.join(updates_made)}")
        
        # Check if we have enough to proceed
        if pending.action_type == "create_event":
            required = ['summary', 'start', 'end']
            missing = [f for f in required if f not in pending.collected_data or not pending.collected_data[f]]
            pending.missing_fields = missing
            
            if not missing:
                # We have everything! Execute the action
                log_info(f"[LOG] All fields collected for event creation. Executing...")
                try:
                    event_create = EventCreate(
                        calendar_id=pending.collected_data.get('calendar_id', 'primary'),
                        summary=pending.collected_data['summary'],
                        start=pending.collected_data['start'],
                        end=pending.collected_data['end'],
                        description=pending.collected_data.get('description'),
                        location=pending.collected_data.get('location')
                    )
                    result = await self.mcp_client.create_event(event_create)
                    
                    # Complete the pending action
                    self.memory.complete_pending_action(pending.action_id)
                    
                    response_msg = f"✅ Perfect! I've created '{result.summary}' on {result.start.date_time if result.start else 'your calendar'}."
                    if result.html_link:
                        response_msg += f"\n\nYou can view it here: {result.html_link}"
                    
                    response = AgentResponse(
                        message=response_msg,
                        tools_used=["create_event"],
                        metadata={"event_id": result.id}
                    )
                    self.memory.add_assistant_message(response.message)
                    return response
                    
                except Exception as e:
                    log_error(f"Error creating event from pending action: {e}")
                    # Fall through to let Gemini handle it
        
        # If we updated something but still need more info, let Gemini continue the conversation
        # with awareness of what we've collected
        return None
    
    def _build_context(self) -> str:
        """Build context string for Gemini.
        
        Returns:
            Context string with pending action details
        """
        context_parts = []
        
        # Add detailed pending actions info
        if self.memory.has_pending_actions():
            pending = self.memory.get_latest_pending_action()
            if pending:
                context_parts.append(f"🔄 ACTIVE TASK: Creating {pending.action_type.replace('_', ' ')}")
                context_parts.append(f"\nWhat we have so far:")
                for key, value in pending.collected_data.items():
                    if not key.startswith('_') and value:  # Skip internal keys
                        context_parts.append(f"  ✓ {key}: {value}")
                
                if pending.missing_fields:
                    context_parts.append(f"\nStill need:")
                    for field in pending.missing_fields:
                        field_label = field.replace('_', ' ').title()
                        context_parts.append(f"  ⏳ {field_label}")
                    
                    # Give guidance on what to ask next
                    next_field = pending.get_next_missing_field()
                    if next_field:
                        context_parts.append(f"\n💡 Ask the user for: {next_field.replace('_', ' ')}")
        
        # Add conversation stats
        stats = self.memory.get_stats()
        context_parts.append(f"\n📊 Conversation: {stats['total_messages']} messages, {stats['pending_actions']} pending actions")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def clear_conversation(self) -> None:
        """Clear conversation history and pending actions."""
        self.memory.clear()
        log_info("Conversation cleared")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics.
        
        Returns:
            Dictionary with stats
        """
        return self.memory.get_stats()
