"""Simple MCP connection test."""

import asyncio
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_simple_connection():
    """Test basic MCP connection."""
    
    mcp_path = Path("C:/Users/Mitran/Documents/Programming/Android/whatsapp_assistant/google-calendar-mcp")
    oauth_path = Path("C:/Users/Mitran/Documents/Programming/Android/whatsapp_assistant/gcp-oauth.keys.json")
    
    print("Setting up server parameters...")
    server_params = StdioServerParameters(
        command="node",
        args=[str(mcp_path / "build" / "index.js")],
        env={
            "GOOGLE_OAUTH_CREDENTIALS": str(oauth_path),
            **dict(os.environ)
        }
    )
    
    print("Creating stdio client...")
    try:
        async with stdio_client(server_params) as streams:
            read_stream, write_stream = streams
            print("Stdio client created, creating session...")
            
            async with ClientSession(read_stream, write_stream) as session:
                print("Initializing session...")
                result = await session.initialize()
                
                print(f"✅ Connection successful!")
                print(f"Server: {result.serverInfo.name} v{result.serverInfo.version}")
                print(f"Protocol: {result.protocolVersion}")
                
                # List tools
                print("\nListing tools...")
                tools = await session.list_tools()
                print(f"Found {len(tools.tools)} tools:")
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_connection())
