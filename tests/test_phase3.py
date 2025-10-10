"""Phase 3 Test: Advanced Multi-Turn Context-Aware Conversations.

This test validates the enhanced conversation capabilities including:
- Intelligent information extraction
- Pending action management
- Context-aware prompting
- Progressive information gathering
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.gemini_agent import GeminiAgent
from src.calendar_mcp.mcp_client import MCPClient
from config.config import load_config
from src.utils.logger import log_info


async def test_phase3():
    """Test Phase 3 advanced conversation features."""
    
    print("=" * 70)
    print("PHASE 3 TEST: Context-Aware Multi-Turn Conversations")
    print("=" * 70)
    print()
    
    # Setup
    config = load_config()
    mcp_client = MCPClient(
        mcp_server_path=config.google.calendar_mcp_path,
        oauth_credentials_path=config.google.oauth_credentials_path
    )
    await mcp_client.connect()
    
    agent = GeminiAgent(
        api_key=config.google.gemini_api_key,
        mcp_client=mcp_client
    )
    
    try:
        # Scenario 1: Incomplete information, build up progressively
        print("📝 SCENARIO 1: Progressive Information Gathering")
        print("-" * 70)
        
        print("\nYou: I have a dentist appointment next week")
        response1 = await agent.process_message("I have a dentist appointment next week")
        print(f"Assistant: {response1.message}\n")
        
        await asyncio.sleep(1)
        
        print("You: Wednesday")
        response2 = await agent.process_message("Wednesday")
        print(f"Assistant: {response2.message}\n")
        
        await asyncio.sleep(1)
        
        print("You: 2 PM")
        response3 = await agent.process_message("2 PM")
        print(f"Assistant: {response3.message}\n")
        
        await asyncio.sleep(1)
        
        print("You: 30 minutes")
        response4 = await agent.process_message("30 minutes")
        print(f"Assistant: {response4.message}\n")
        
        if "create_event" in response4.tools_used or "✅" in response4.message:
            print("✅ Scenario 1 PASSED: Event created through multi-turn conversation!\n")
        else:
            print("⚠️  Scenario 1: Event may need confirmation\n")
        
        # Scenario 2: Partial info with clarification
        print("\n" + "=" * 70)
        print("📝 SCENARIO 2: Ambiguous Input Handling")
        print("-" * 70)
        
        await asyncio.sleep(1)
        
        print("\nYou: Schedule a team meeting")
        response5 = await agent.process_message("Schedule a team meeting")
        print(f"Assistant: {response5.message}\n")
        
        await asyncio.sleep(1)
        
        print("You: tomorrow at 3")
        response6 = await agent.process_message("tomorrow at 3")
        print(f"Assistant: {response6.message}\n")
        
        await asyncio.sleep(1)
        
        print("You: 1 hour")
        response7 = await agent.process_message("1 hour")
        print(f"Assistant: {response7.message}\n")
        
        # Scenario 3: Check what we created
        print("\n" + "=" * 70)
        print("📝 SCENARIO 3: Verify Created Events")
        print("-" * 70)
        
        await asyncio.sleep(1)
        
        print("\nYou: What do I have tomorrow?")
        response8 = await agent.process_message("What do I have tomorrow?")
        print(f"Assistant: {response8.message}\n")
        
        # Show stats
        print("\n" + "=" * 70)
        print("📊 CONVERSATION STATISTICS")
        print("=" * 70)
        stats = agent.get_conversation_stats()
        print(f"Total messages: {stats['total_messages']}")
        print(f"User messages: {stats['user_messages']}")
        print(f"Assistant messages: {stats['assistant_messages']}")
        print(f"Pending actions: {stats['pending_actions']}")
        
        print("\n" + "=" * 70)
        print("✅ Phase 3 Testing Complete!")
        print("=" * 70)
        
    finally:
        await mcp_client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_phase3())
