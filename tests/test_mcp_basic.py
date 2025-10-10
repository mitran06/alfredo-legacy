"""Test script for MCP client basic operations."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp.mcp_client import MCPClient
from src.models.calendar import EventCreate
from src.utils.logger import setup_logging, log_info, log_error
from config.config import init_config, validate_config


async def test_mcp_client():
    """Test basic MCP client operations."""
    
    # Set up logging
    setup_logging("INFO")
    
    log_info("=== MCP Client Test Script ===\n")
    
    try:
        # Load configuration
        log_info("Loading configuration...")
        config = init_config()
        
        # Validate configuration
        errors = validate_config(config)
        if errors:
            log_error("Configuration validation failed:")
            for error in errors:
                log_error(f"  - {error}")
            return
        
        log_info("Configuration loaded successfully\n")
        
        # Initialize MCP client
        log_info("Initializing MCP client...")
        mcp_client = MCPClient(
            mcp_server_path=config.google.calendar_mcp_path,
            oauth_credentials_path=config.google.oauth_credentials_path
        )
        
        # Connect to MCP server
        await mcp_client.connect()
        log_info("")
        
        # Test 1: List calendars
        log_info("TEST 1: Listing calendars...")
        calendar_list = await mcp_client.list_calendars()
        log_info(f"Found {calendar_list.total_count} calendar(s):")
        for cal in calendar_list.calendars:
            primary_marker = " (PRIMARY)" if cal.primary else ""
            log_info(f"  - {cal.summary}{primary_marker} ({cal.id})")
        log_info("")
        
        # Test 2: List upcoming events
        log_info("TEST 2: Listing upcoming events (next 7 days)...")
        time_min = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        time_max = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        
        event_list = await mcp_client.list_events(
            calendar_id=config.google.primary_calendar_id,
            time_min=time_min,
            time_max=time_max
        )
        
        if event_list.total_count > 0:
            log_info(f"Found {event_list.total_count} upcoming event(s):")
            for event in event_list.events[:5]:  # Show first 5
                start_time = event.start.date_time or event.start.date
                log_info(f"  - {event.summary} at {start_time}")
        else:
            log_info("No upcoming events found")
        log_info("")
        
        # Test 3: Create a test event
        log_info("TEST 3: Creating a test event...")
        test_event = EventCreate(
            calendar_id=config.google.primary_calendar_id,
            summary="MCP Test Event",
            description="This is a test event created by the MCP client test script",
            start=(datetime.now() + timedelta(days=2, hours=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            end=(datetime.now() + timedelta(days=2, hours=11)).strftime("%Y-%m-%dT%H:%M:%S"),
            location="Test Location"
        )
        
        created_event = await mcp_client.create_event(test_event)
        log_info(f"Created event: {created_event.summary}")
        log_info(f"  Event ID: {created_event.id}")
        log_info(f"  Link: {created_event.html_link}")
        log_info("")
        
        # Test 4: Search for the created event
        log_info("TEST 4: Searching for the test event...")
        search_results = await mcp_client.search_events(
            query="MCP Test",
            calendar_id=config.google.primary_calendar_id
        )
        
        if search_results.total_count > 0:
            log_info(f"Found {search_results.total_count} event(s) matching 'MCP Test'")
        else:
            log_info("No events found (might need to wait for indexing)")
        log_info("")
        
        # Test 5: Update the event
        log_info("TEST 5: Updating the test event...")
        from src.models.calendar import EventUpdate
        
        update_data = EventUpdate(
            calendar_id=config.google.primary_calendar_id,
            event_id=created_event.id,
            summary="MCP Test Event (UPDATED)",
            description="This event was successfully updated by the test script"
        )
        
        updated_event = await mcp_client.update_event(update_data)
        log_info(f"Updated event: {updated_event.summary}")
        log_info("")
        
        # Test 6: Delete the event
        log_info("TEST 6: Deleting the test event...")
        success = await mcp_client.delete_event(
            calendar_id=config.google.primary_calendar_id,
            event_id=created_event.id
        )
        
        if success:
            log_info("Test event deleted successfully")
        else:
            log_error("Failed to delete test event")
        log_info("")
        
        # Test 7: Check free/busy
        log_info("TEST 7: Checking free/busy status...")
        freebusy = await mcp_client.get_freebusy(
            calendars=[config.google.primary_calendar_id],
            time_min=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            time_max=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        )
        log_info(f"Free/busy retrieved for time range:")
        log_info(f"  From: {freebusy.time_min}")
        log_info(f"  To: {freebusy.time_max}")
        log_info("")
        
        # Success!
        log_info("✅ All tests completed successfully!")
        log_info("\nPhase 1 MCP integration is working correctly.")
        
    except FileNotFoundError as e:
        log_error(f"File not found: {e}")
        log_error("\nPlease ensure:")
        log_error("1. Google Calendar MCP server is installed and built")
        log_error("2. OAuth credentials file exists at the specified path")
        log_error("3. .env file is configured correctly")
        
    except Exception as e:
        log_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Disconnect
        if 'mcp_client' in locals():
            await mcp_client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())
