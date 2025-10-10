"""Simple complete event creation test."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.gemini_agent import GeminiAgent
from src.calendar_mcp.mcp_client import MCPClient
from config.config import load_config
from src.utils.logger import log_info


async def test_complete_event():
    """Test creating an event with all information at once."""
    
    print("=" * 70)
    print("COMPLETE EVENT CREATION TEST")
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
        # Test 1: Complete info
        print("You: Create a test event on Monday October 13th from 8 AM to 10 AM")
        response = await agent.process_message(
            "Create a test event on Monday October 13th from 8 AM to 10 AM"
        )
        print(f"\nAssistant: {response.message}\n")
        
        if "create_event" in response.tools_used:
            print("✅ Event created successfully!")
        else:
            print("⚠️  Waiting for confirmation or more info")
        
        # Test 2: Follow up
        print("\n" + "-" * 70 + "\n")
        print("You: yes, create it")
        response2 = await agent.process_message("yes, create it")
        print(f"\nAssistant: {response2.message}\n")
        
        if "create_event" in response2.tools_used:
            print("✅ Event created after confirmation!")
        
        # Test 3: List events to verify
        print("\n" + "-" * 70 + "\n")
        print("You: Show me my events for Monday October 13th")
        response3 = await agent.process_message("Show me my events for Monday October 13th")
        print(f"\nAssistant: {response3.message}\n")
        
    finally:
        await mcp_client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_complete_event())
