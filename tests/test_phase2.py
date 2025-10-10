"""Test script for Phase 2 multi-turn conversation.

This script tests the complete flow:
1. User: "I have a test on Monday"
2. Assistant asks for time
3. User: "8 AM"
4. Assistant creates the event
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.gemini_agent import GeminiAgent
from src.calendar_mcp.mcp_client import MCPClient
from config.config import load_config
from src.utils.logger import log_info, log_error


async def test_multi_turn_conversation():
    """Test multi-turn conversation for event creation."""
    
    print("=" * 70)
    print("PHASE 2 TEST: Multi-Turn Conversation")
    print("=" * 70)
    print()
    
    # Load configuration
    log_info("Loading configuration...")
    config = load_config()
    
    # Initialize MCP client
    log_info("Connecting to Google Calendar...")
    mcp_client = MCPClient(
        mcp_server_path=config.google.calendar_mcp_path,
        oauth_credentials_path=config.google.oauth_credentials_path
    )
    await mcp_client.connect()
    
    # Initialize Gemini agent
    log_info("Initializing AI agent...")
    agent = GeminiAgent(
        api_key=config.google.gemini_api_key,
        mcp_client=mcp_client
    )
    
    try:
        print("\n" + "=" * 70)
        print("TEST 1: Multi-turn event creation")
        print("=" * 70 + "\n")
        
        # Turn 1: User mentions test on Monday (incomplete info)
        print("You: I have a test on Monday")
        response1 = await agent.process_message("I have a test on Monday")
        print(f"\nAssistant: {response1.message}\n")
        
        # Give agent time to process
        await asyncio.sleep(2)
        
        # Turn 2: User provides time
        print("You: at 8 AM")
        response2 = await agent.process_message("at 8 AM")
        print(f"\nAssistant: {response2.message}\n")
        
        # Check if event was created
        if "create_event" in response2.tools_used:
            print("✅ Event created successfully!")
        else:
            print("⚠️  Event not created yet, may need more information")
        
        print("\n" + "=" * 70)
        print("TEST 2: List tomorrow's events")
        print("=" * 70 + "\n")
        
        # Test listing events
        print("You: What do I have tomorrow?")
        response3 = await agent.process_message("What do I have tomorrow?")
        print(f"\nAssistant: {response3.message}\n")
        
        print("\n" + "=" * 70)
        print("TEST 3: Simple event creation (all info at once)")
        print("=" * 70 + "\n")
        
        print("You: Schedule a dentist appointment for next Wednesday at 2 PM")
        response4 = await agent.process_message("Schedule a dentist appointment for next Wednesday at 2 PM")
        print(f"\nAssistant: {response4.message}\n")
        
        # Show conversation stats
        stats = agent.get_conversation_stats()
        print("\n" + "=" * 70)
        print("CONVERSATION STATISTICS")
        print("=" * 70)
        print(f"Total messages: {stats['total_messages']}")
        print(f"User messages: {stats['user_messages']}")
        print(f"Assistant messages: {stats['assistant_messages']}")
        print(f"Pending actions: {stats['pending_actions']}")
        print()
        
        print("✅ Phase 2 testing complete!")
        
    except Exception as e:
        log_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await mcp_client.disconnect()
        log_info("Disconnected from calendar")


if __name__ == "__main__":
    asyncio.run(test_multi_turn_conversation())
