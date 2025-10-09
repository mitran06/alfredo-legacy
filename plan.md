# AI Personal Secretary - Implementation Plan

## Project Overview
Build an AI personal secretary that interfaces through the terminal (with WhatsApp integration planned later). The assistant will proactively remind users of scheduled events using Google Calendar MCP integration and Google Gemini API for natural language understanding.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interface Layer                         │
│                    (Terminal / CLI for now)                      │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│                   Conversation Manager                           │
│  - Maintains conversation history                                │
│  - Context awareness & memory management                         │
│  - Multi-turn conversation handling                              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│                    AI Agent Core (Gemini)                        │
│  - Natural language understanding                                │
│  - Intent detection                                              │
│  - Tool selection and execution                                  │
│  - Response generation                                           │
└─────────────────┬──────────────┴──────────────┬─────────────────┘
                  │                              │
        ┌─────────▼────────┐         ┌──────────▼──────────┐
        │   MCP Client     │         │  Reminder Service   │
        │   Integration    │         │  (Background)       │
        └─────────┬────────┘         └──────────┬──────────┘
                  │                              │
        ┌─────────▼────────────────────┐  ┌─────▼──────────┐
        │  Google Calendar MCP Server  │  │  Event Monitor │
        │  - create-event              │  │  - Poll events │
        │  - update-event              │  │  - Send alerts │
        │  - list-events               │  └────────────────┘
        │  - search-events             │
        │  - get-freebusy              │
        │  - list-calendars            │
        └──────────────────────────────┘
```

---

## Component Specifications

### 1. **MCP Client Manager** (`src/mcp/mcp_client.py`)
**Purpose**: Interface with the Google Calendar MCP server

**Responsibilities**:
- Initialize and maintain MCP client connection
- Execute MCP tools (create-event, update-event, list-events, etc.)
- Handle MCP server errors and reconnection
- Transform MCP responses into Python objects

**Key Methods**:
```python
class MCPClient:
    def __init__(self, mcp_server_path: str)
    async def connect() -> None
    async def disconnect() -> None
    async def list_calendars() -> List[Calendar]
    async def list_events(calendar_id: str, time_min: str, time_max: str) -> List[Event]
    async def create_event(event_details: EventCreate) -> Event
    async def update_event(event_id: str, event_update: EventUpdate) -> Event
    async def search_events(query: str, calendar_id: str) -> List[Event]
    async def get_freebusy(calendars: List[str], time_min: str, time_max: str) -> FreeBusyInfo
```

**Dependencies**:
- `@modelcontextprotocol/sdk/client` (via subprocess or Python MCP SDK)
- Google Calendar MCP server (`nspady/google-calendar-mcp`)

---

### 2. **AI Agent Core** (`src/ai/gemini_agent.py`)
**Purpose**: Interface with Google Gemini API for natural language understanding

**Responsibilities**:
- Maintain conversation context
- Call Gemini API with function calling (tool use)
- Decide which calendar tools to invoke
- Generate natural responses
- Handle multi-turn conversations for information gathering

**Key Methods**:
```python
class GeminiAgent:
    def __init__(self, api_key: str, mcp_client: MCPClient)
    async def process_message(user_message: str) -> AgentResponse
    async def _call_gemini(messages: List[Message], tools: List[Tool]) -> GeminiResponse
    def _parse_tool_calls(response: GeminiResponse) -> List[ToolCall]
    async def _execute_tool_call(tool_call: ToolCall) -> ToolResult
    def _build_tool_definitions() -> List[Tool]
```

**Tool Definitions** (for Gemini function calling):
```python
CALENDAR_TOOLS = [
    {
        "name": "create_event",
        "description": "Create a new calendar event",
        "parameters": {...}
    },
    {
        "name": "update_event",
        "description": "Update an existing event",
        "parameters": {...}
    },
    {
        "name": "list_events",
        "description": "List events in a time range",
        "parameters": {...}
    },
    {
        "name": "search_events",
        "description": "Search for events",
        "parameters": {...}
    },
    {
        "name": "get_freebusy",
        "description": "Check calendar availability",
        "parameters": {...}
    }
]
```

---

### 3. **Conversation Memory Manager** (`src/ai/memory.py`)
**Purpose**: Maintain context awareness across multi-turn conversations

**Responsibilities**:
- Store conversation history
- Track pending actions (e.g., awaiting time for "test on Monday")
- Store extracted entities (dates, times, event descriptions)
- Provide context to Gemini for each turn

**Key Methods**:
```python
class ConversationMemory:
    def __init__(self)
    def add_user_message(message: str, timestamp: datetime) -> None
    def add_assistant_message(message: str, timestamp: datetime) -> None
    def add_pending_action(action: PendingAction) -> str  # Returns action_id
    def get_pending_action(action_id: str) -> Optional[PendingAction]
    def complete_pending_action(action_id: str) -> None
    def get_conversation_context(window: int = 10) -> List[Message]
    def clear() -> None
```

**Data Structures**:
```python
@dataclass
class PendingAction:
    action_id: str
    action_type: str  # "create_event", "update_event", etc.
    collected_data: Dict[str, Any]
    missing_fields: List[str]
    created_at: datetime
    
@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
```

---

### 4. **Reminder Service** (`src/reminders/reminder_service.py`)
**Purpose**: Proactively check for upcoming events and send reminders

**Responsibilities**:
- Poll Google Calendar for upcoming events
- Send reminders at configured intervals (e.g., 1 day before, 1 hour before)
- Track which events have been reminded
- Support custom reminder times

**Key Methods**:
```python
class ReminderService:
    def __init__(self, mcp_client: MCPClient, notification_handler: NotificationHandler)
    async def start() -> None  # Start background task
    async def stop() -> None
    async def check_upcoming_events() -> List[Event]
    async def send_reminder(event: Event) -> None
    def add_reminder_rule(rule: ReminderRule) -> None
```

**Reminder Rules**:
```python
@dataclass
class ReminderRule:
    offset_minutes: int  # Remind X minutes before event (e.g., 1440 = 1 day)
    message_template: str
    enabled: bool = True
```

---

### 5. **Event Monitor** (`src/reminders/event_monitor.py`)
**Purpose**: Background service to monitor calendar events

**Responsibilities**:
- Run periodic checks (every 5-15 minutes)
- Query calendar for events in next 24-48 hours
- Check reminder rules and dispatch notifications
- Maintain state of sent reminders (avoid duplicates)

**Key Methods**:
```python
class EventMonitor:
    def __init__(self, mcp_client: MCPClient, reminder_service: ReminderService)
    async def start_monitoring(interval_seconds: int = 300) -> None
    async def stop_monitoring() -> None
    async def _check_and_notify() -> None
    def _should_remind(event: Event) -> bool
```

---

### 6. **Terminal Interface** (`src/ui/terminal_ui.py`)
**Purpose**: Command-line interface for user interaction

**Responsibilities**:
- Display conversation messages
- Accept user input
- Show reminder notifications
- Provide commands (/help, /clear, /status, etc.)

**Key Methods**:
```python
class TerminalUI:
    def __init__(self, agent: GeminiAgent, reminder_service: ReminderService)
    async def start() -> None
    async def _handle_user_input() -> None
    def display_message(role: str, message: str) -> None
    def display_reminder(event: Event, message: str) -> None
    def display_help() -> None
```

**Commands**:
- `/help` - Show available commands
- `/clear` - Clear conversation history
- `/status` - Show upcoming events
- `/reminders` - List active reminders
- `/quit` - Exit application

---

### 7. **Data Models** (`src/models/calendar.py`)
**Purpose**: Define data structures for calendar entities

```python
@dataclass
class Event:
    id: str
    calendar_id: str
    summary: str
    description: Optional[str]
    start: datetime
    end: datetime
    location: Optional[str]
    attendees: List[Attendee]
    status: str
    html_link: str
    reminders: List[Reminder]

@dataclass
class EventCreate:
    calendar_id: str
    summary: str
    description: Optional[str]
    start: str  # ISO 8601 format
    end: str
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    reminders: Optional[List[Reminder]] = None

@dataclass
class Calendar:
    id: str
    summary: str
    description: Optional[str]
    time_zone: str
    primary: bool

@dataclass
class Attendee:
    email: str
    response_status: Optional[str]
    display_name: Optional[str]

@dataclass
class Reminder:
    method: str  # "email" or "popup"
    minutes: int
```

---

### 8. **Configuration** (`config/config.yaml`)
```yaml
google:
  gemini_api_key: "${GEMINI_API_KEY}"
  calendar_mcp_path: "path/to/google-calendar-mcp"
  oauth_credentials_path: "path/to/gcp-oauth.keys.json"

reminders:
  enabled: true
  check_interval_seconds: 300  # Check every 5 minutes
  default_rules:
    - offset_minutes: 1440  # 1 day before
      message_template: "Reminder: You have '{event_summary}' tomorrow at {event_time}"
    - offset_minutes: 60    # 1 hour before
      message_template: "Upcoming: '{event_summary}' starts in 1 hour at {event_time}"

conversation:
  max_history: 50
  context_window: 10

terminal:
  prompt: "You: "
  show_timestamps: true
```

---

## Implementation Phases

### **Phase 1: MCP Integration & Basic Calendar Operations** (Week 1)
**Objectives**:
- Set up Google Calendar MCP server locally
- Implement MCPClient class
- Test basic calendar operations (list, create, update)
- Create data models

**Deliverables**:
- `src/mcp/mcp_client.py` - Fully functional MCP client
- `src/models/calendar.py` - Data models
- `tests/test_mcp_client.py` - Unit tests
- Working connection to Google Calendar

**Validation**:
```python
# Test script
mcp_client = MCPClient()
await mcp_client.connect()
events = await mcp_client.list_events("primary", time_min, time_max)
print(f"Found {len(events)} events")
```

---

### **Phase 2: Gemini Integration & Basic Conversation** (Week 1-2)
**Objectives**:
- Integrate Google Gemini API
- Implement function calling with calendar tools
- Create basic conversation flow
- Implement ConversationMemory

**Deliverables**:
- `src/ai/gemini_agent.py` - Gemini agent implementation
- `src/ai/memory.py` - Conversation memory
- Tool definitions for Gemini
- Basic multi-turn conversation support

**Validation**:
```
User: "I have a test on Monday"
Bot: "All the best! At what time is your test?"
User: "At 8 AM"
Bot: "Got it! I've created a reminder for your test on Monday at 8:00 AM. Would you like me to remind you a day before?"
```

---

### **Phase 3: Context-Aware Multi-Turn Conversations** (Week 2)
**Objectives**:
- Enhance conversation memory with pending actions
- Implement information gathering for incomplete event details
- Add natural language date/time parsing
- Handle edge cases and clarifications

**Deliverables**:
- Enhanced `ConversationMemory` with pending actions
- Improved `GeminiAgent` with state management
- Natural language date parsing utilities

**Example Conversation Flow**:
```
User: "I have a dentist appointment next week"
Bot: "Sure! Which day next week?"
User: "Wednesday"
Bot: "What time on Wednesday?"
User: "2 PM"
Bot: "How long should I block out?"
User: "30 minutes"
Bot: "Perfect! I've scheduled your dentist appointment for Wednesday at 2:00 PM for 30 minutes."
```

---

### **Phase 4: Reminder Service & Event Monitoring** (Week 2-3)
**Objectives**:
- Implement ReminderService
- Create EventMonitor background task
- Add reminder rules configuration
- Implement notification dispatch

**Deliverables**:
- `src/reminders/reminder_service.py`
- `src/reminders/event_monitor.py`
- Background monitoring with asyncio
- Configurable reminder rules

**Validation**:
- Create event for tomorrow
- Verify reminder is sent 1 day before
- Verify reminder is sent 1 hour before

---

### **Phase 5: Terminal Interface & Polish** (Week 3)
**Objectives**:
- Create polished terminal UI
- Add commands (/help, /status, etc.)
- Display reminders prominently
- Add error handling and recovery
- Write documentation

**Deliverables**:
- `src/ui/terminal_ui.py` - Complete terminal interface
- `README.md` - Setup and usage instructions
- `docs/` - User and developer documentation
- Error handling throughout

---

### **Phase 6: Testing & Refinement** (Week 3-4)
**Objectives**:
- Write comprehensive tests
- Test multi-turn conversations
- Test reminder accuracy
- Performance optimization
- Bug fixes

**Deliverables**:
- Test suite with >80% coverage
- Integration tests
- Performance benchmarks
- Bug-free application

---

## Technical Stack

### **Core Technologies**:
- **Language**: Python 3.10+
- **AI Model**: Google Gemini API (gemini-1.5-pro or gemini-2.0-flash-exp)
- **MCP Server**: Google Calendar MCP (nspady/google-calendar-mcp)
- **Async Framework**: asyncio
- **CLI Framework**: Rich (for beautiful terminal UI)

### **Key Libraries**:
```txt
google-generativeai>=0.3.0  # Gemini API
mcp>=0.1.0                   # MCP Python SDK
rich>=13.0.0                 # Terminal UI
python-dateutil>=2.8.0       # Date parsing
pydantic>=2.0.0              # Data validation
pyyaml>=6.0                  # Configuration
pytest>=7.0.0                # Testing
pytest-asyncio>=0.21.0       # Async testing
```

---

## Project Structure

```
whatsapp_assistant/
├── config/
│   ├── config.yaml              # Main configuration
│   └── config.py                # Configuration loader
├── src/
│   ├── __init__.py
│   ├── main.py                  # Application entry point
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── mcp_client.py        # MCP client implementation
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── gemini_agent.py      # Gemini integration
│   │   └── memory.py            # Conversation memory
│   ├── reminders/
│   │   ├── __init__.py
│   │   ├── reminder_service.py  # Reminder logic
│   │   └── event_monitor.py     # Background monitoring
│   ├── models/
│   │   ├── __init__.py
│   │   └── calendar.py          # Data models
│   ├── ui/
│   │   ├── __init__.py
│   │   └── terminal_ui.py       # Terminal interface
│   └── utils/
│       ├── __init__.py
│       ├── date_parser.py       # Date/time utilities
│       └── logger.py            # Logging utilities
├── tests/
│   ├── __init__.py
│   ├── test_mcp_client.py
│   ├── test_gemini_agent.py
│   ├── test_memory.py
│   └── test_reminder_service.py
├── docs/
│   ├── setup.md                 # Setup instructions
│   ├── usage.md                 # Usage guide
│   └── architecture.md          # Architecture details
├── .env.example                 # Environment variables template
├── .gitignore
├── README.md
├── requirements.txt
├── plan.md                      # This file
└── pyproject.toml              # Python project configuration
```

---

## Environment Setup Requirements

### **Prerequisites**:
1. **Python 3.10+** installed
2. **Node.js 18+** (for Google Calendar MCP server)
3. **Google Cloud Project** with Calendar API enabled
4. **Google Gemini API key**
5. **OAuth 2.0 credentials** (Desktop app type)

### **Setup Steps**:

1. **Clone and setup Google Calendar MCP server**:
```bash
git clone https://github.com/nspady/google-calendar-mcp.git
cd google-calendar-mcp
npm install
npm run build

# Set up OAuth credentials
export GOOGLE_OAUTH_CREDENTIALS="/path/to/gcp-oauth.keys.json"
npm run auth  # Complete OAuth flow
```

2. **Create Python virtual environment**:
```bash
cd whatsapp_assistant
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Run the application**:
```bash
python src/main.py
```

---

## Key Design Decisions

### **1. Why MCP?**
- **Standardized Interface**: MCP provides a standard way to interact with calendar APIs
- **Tool Abstraction**: Calendar operations are already defined as MCP tools
- **Future Extensibility**: Can easily add more MCP servers (email, tasks, etc.)

### **2. Why Google Gemini?**
- **Native Function Calling**: Built-in support for tool/function calling
- **Context Window**: Large context window (1M+ tokens in Gemini 1.5)
- **Cost-Effective**: Competitive pricing compared to alternatives
- **Multimodal**: Future support for voice, images (for WhatsApp)

### **3. Why Async/Await?**
- **Non-blocking I/O**: Handle multiple conversations simultaneously
- **Background Tasks**: Event monitoring runs independently
- **Scalability**: Easier to add WhatsApp integration later

### **4. Why Terminal First?**
- **Rapid Development**: Focus on core logic without UI complexity
- **Easy Testing**: Simple to test conversation flows
- **Clear Migration Path**: Terminal → WhatsApp bot is straightforward

---

## Conversation Flow Examples

### **Example 1: Simple Event Creation**
```
User: "I have a meeting tomorrow at 3 PM"
Assistant: "Got it! I'll create a meeting for tomorrow at 3:00 PM. What should I call this meeting?"
User: "Team standup"
Assistant: "Perfect! I've scheduled 'Team standup' for tomorrow at 3:00 PM. Would you like me to add any details or attendees?"
User: "No, that's all"
Assistant: "✅ Event created! I'll remind you 1 day before and 1 hour before the meeting."
```

### **Example 2: Multi-Turn with Incomplete Information**
```
User: "Remind me about my test"
Assistant: "Sure! When is your test scheduled?"
User: "Monday"
Assistant: "What time on Monday?"
User: "8 AM"
Assistant: "How long should I block out for the test?"
User: "2 hours"
Assistant: "Got it! I've created a reminder for your test on Monday at 8:00 AM (2 hours). I'll remind you the day before. Good luck! 🍀"
```

### **Example 3: Event Update**
```
User: "My meeting tomorrow got moved to 4 PM instead of 3 PM"
Assistant: "I found 'Team standup' scheduled for tomorrow at 3:00 PM. Should I update it to 4:00 PM?"
User: "Yes"
Assistant: "✅ Updated! 'Team standup' is now at 4:00 PM tomorrow."
```

### **Example 4: Checking Schedule**
```
User: "What do I have tomorrow?"
Assistant: "Here's your schedule for tomorrow:
• 9:00 AM - Morning workout (1 hour)
• 2:00 PM - Dentist appointment (30 minutes)
• 4:00 PM - Team standup (1 hour)

You have 3 events scheduled. Anything you'd like to change?"
```

---

## Testing Strategy

### **Unit Tests**:
- Test each component in isolation
- Mock external dependencies (Gemini API, MCP server)
- Test edge cases and error conditions

### **Integration Tests**:
- Test end-to-end conversation flows
- Test MCP server integration
- Test reminder service with real events

### **Conversation Tests**:
```python
# Example test
async def test_multi_turn_event_creation():
    agent = GeminiAgent(mcp_client=mock_mcp)
    
    # Turn 1
    response1 = await agent.process_message("I have a test on Monday")
    assert "what time" in response1.message.lower()
    
    # Turn 2
    response2 = await agent.process_message("at 8 AM")
    assert response2.tools_used == ["create_event"]
    assert "created" in response2.message.lower()
```

---

## Future Enhancements (Post-MVP)

1. **WhatsApp Integration**:
   - Use Twilio API or WhatsApp Business API
   - Replace terminal UI with message handling
   - Support multimedia messages

2. **Smart Scheduling**:
   - Auto-suggest meeting times based on free/busy
   - Handle recurring events
   - Conflict detection and resolution

3. **Natural Language Improvements**:
   - Better date/time parsing
   - Support for relative dates ("next Friday", "in 2 weeks")
   - Multiple event creation in one message

4. **Advanced Reminders**:
   - Location-based reminders
   - Weather-aware reminders
   - Smart reminder timing based on travel time

5. **Multi-Calendar Support**:
   - Manage multiple calendars
   - Cross-calendar scheduling
   - Calendar sharing and delegation

6. **Voice Interface**:
   - Speech-to-text for input
   - Text-to-speech for responses
   - Voice reminders via WhatsApp calls

---

## Success Metrics

1. **Functionality**:
   - ✅ Create events via natural conversation (multi-turn)
   - ✅ Update existing events
   - ✅ List and search events
   - ✅ Proactive reminders (1 day and 1 hour before)
   - ✅ Context awareness across conversation

2. **User Experience**:
   - ✅ Natural conversation flow (not command-based)
   - ✅ Graceful handling of incomplete information
   - ✅ Clear confirmation messages
   - ✅ Timely and relevant reminders

3. **Technical**:
   - ✅ <2 second response time for simple queries
   - ✅ Reliable reminder delivery (no missed reminders)
   - ✅ Proper error handling and recovery
   - ✅ Test coverage >80%

---

## Risk Mitigation

### **Risk 1: MCP Server Stability**
- **Mitigation**: Implement retry logic and graceful degradation
- **Fallback**: Direct Google Calendar API integration if MCP fails

### **Risk 2: Gemini API Rate Limits**
- **Mitigation**: Implement request throttling and caching
- **Fallback**: Queue messages during rate limit periods

### **Risk 3: Context Loss in Long Conversations**
- **Mitigation**: Implement conversation summarization
- **Strategy**: Use sliding window with key information extraction

### **Risk 4: Reminder Accuracy**
- **Mitigation**: Persistent storage of reminder state
- **Strategy**: Multiple reminder checks with idempotency

---

## Timeline Estimate

- **Week 1**: Phases 1-2 (MCP + Gemini Integration)
- **Week 2**: Phase 3 (Context-Aware Conversations)
- **Week 3**: Phases 4-5 (Reminders + UI)
- **Week 4**: Phase 6 (Testing + Polish)

**Total**: ~4 weeks for MVP

---

## Conclusion

This plan provides a comprehensive roadmap to build a functional AI personal secretary with:
- ✅ Natural language conversation (via Gemini)
- ✅ Multi-turn context awareness
- ✅ Full Google Calendar integration (via MCP)
- ✅ Proactive reminder system
- ✅ Terminal interface (WhatsApp-ready architecture)

The modular architecture ensures each component can be developed, tested, and refined independently, while the phased approach allows for incremental delivery and early feedback.

Once approved, we'll proceed with Phase 1 implementation! 🚀
