"""Phase 4 Test: Reminder Service & Background Notifications

This test verifies that reminders fire automatically without user input.
Key test: User says "remind me in 2 minutes" and gets notified after 2 minutes.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.calendar_mcp.mcp_client import MCPClient
from src.reminders.reminder_service import ReminderService
from src.reminders.notification_dispatcher import NotificationDispatcher
from src.reminders.event_monitor import EventMonitor
from config.config import load_config, ReminderRule
from src.utils.logger import log_info, log_error


# Track received notifications
received_notifications = []


def notification_callback(message: str):
    """Callback for notification testing."""
    received_notifications.append({
        "message": message,
        "timestamp": datetime.now()
    })
    print(f"\n✅ NOTIFICATION RECEIVED: {message}")


async def test_custom_reminder_2_minutes():
    """Test that a 2-minute reminder fires without user input."""
    print("\n" + "=" * 80)
    print("TEST: Custom Reminder in 2 Minutes")
    print("=" * 80)
    
    # Load config
    config = load_config()
    
    # Initialize MCP client
    mcp_client = MCPClient(
        mcp_server_path=config.google.calendar_mcp_path,
        oauth_credentials_path=config.google.oauth_credentials_path
    )
    
    try:
        await mcp_client.connect()
        print("✓ Connected to Google Calendar")
        
        # Initialize reminder service
        reminder_service = ReminderService(
            mcp_client=mcp_client,
            config=config.reminders
        )
        
        # Set callback
        reminder_service.set_terminal_callback(notification_callback)
        
        # Start service
        await reminder_service.start()
        print("✓ Reminder service started")
        
        # Create a 2-minute reminder
        print("\n📝 Creating reminder: 'Check the oven' in 2 minutes")
        remind_at = reminder_service.create_reminder_in_minutes(
            summary="Check the oven",
            minutes=2
        )
        
        print(f"⏰ Reminder scheduled for: {remind_at.strftime('%I:%M:%S %p')}")
        print(f"⏱️  Current time: {datetime.now().strftime('%I:%M:%S %p')}")
        print("\n⏳ Waiting 2 minutes for reminder to fire...")
        print("   (This tests that reminders work without user input)")
        
        # Wait 2.5 minutes to ensure reminder fires
        for i in range(150):  # 150 seconds = 2.5 minutes
            await asyncio.sleep(1)
            elapsed = i + 1
            
            # Show progress every 15 seconds
            if elapsed % 15 == 0:
                print(f"   ... {elapsed}s elapsed ({elapsed//60}m {elapsed%60}s)")
            
            # Check if notification received
            if len(received_notifications) > 0:
                print(f"\n✅ SUCCESS! Reminder fired after {elapsed} seconds")
                notification = received_notifications[0]
                print(f"   Message: {notification['message']}")
                print(f"   Time: {notification['timestamp'].strftime('%I:%M:%S %p')}")
                break
        else:
            print("\n❌ FAILED! Reminder did not fire within 2.5 minutes")
            return False
        
        # Verify notification
        assert len(received_notifications) == 1, "Should have exactly 1 notification"
        assert "Check the oven" in received_notifications[0]["message"], "Notification should mention 'Check the oven'"
        
        print("\n✅ TEST PASSED: 2-minute reminder works without user input!")
        
        # Stop service
        await reminder_service.stop()
        print("✓ Reminder service stopped")
        
        return True
        
    finally:
        await mcp_client.disconnect()
        print("✓ Disconnected from calendar")


async def test_quick_reminder_30_seconds():
    """Test a quick 30-second reminder for faster testing."""
    print("\n" + "=" * 80)
    print("TEST: Quick Reminder in 30 Seconds")
    print("=" * 80)
    
    received_notifications.clear()
    
    # Load config
    config = load_config()
    
    # Initialize MCP client
    mcp_client = MCPClient(
        mcp_server_path=config.google.calendar_mcp_path,
        oauth_credentials_path=config.google.oauth_credentials_path
    )
    
    try:
        await mcp_client.connect()
        print("✓ Connected to Google Calendar")
        
        # Initialize reminder service with faster check interval
        config.reminders.check_interval_seconds = 5  # Check every 5 seconds
        reminder_service = ReminderService(
            mcp_client=mcp_client,
            config=config.reminders
        )
        
        # Set callback
        reminder_service.set_terminal_callback(notification_callback)
        
        # Start service
        await reminder_service.start()
        print("✓ Reminder service started (checking every 5 seconds)")
        
        # Create multiple reminders
        print("\n📝 Creating reminders:")
        
        remind_at_1 = reminder_service.create_reminder_in_minutes(
            summary="First reminder - Take medicine",
            minutes=0.5  # 30 seconds
        )
        print(f"   1. 'Take medicine' at {remind_at_1.strftime('%I:%M:%S %p')}")
        
        remind_at_2 = reminder_service.create_reminder_in_minutes(
            summary="Second reminder - Call mom",
            minutes=1  # 60 seconds
        )
        print(f"   2. 'Call mom' at {remind_at_2.strftime('%I:%M:%S %p')}")
        
        print(f"\n⏱️  Current time: {datetime.now().strftime('%I:%M:%S %p')}")
        print("⏳ Waiting for reminders to fire...")
        
        # Wait up to 90 seconds for both reminders
        for i in range(90):
            await asyncio.sleep(1)
            elapsed = i + 1
            
            # Show progress
            if elapsed % 10 == 0:
                print(f"   ... {elapsed}s elapsed, {len(received_notifications)} notifications received")
            
            # Check if both received
            if len(received_notifications) >= 2:
                print(f"\n✅ SUCCESS! Both reminders fired")
                break
        
        # Verify
        print(f"\n📊 Results:")
        print(f"   Notifications received: {len(received_notifications)}")
        
        for idx, notif in enumerate(received_notifications, 1):
            print(f"   {idx}. {notif['message']}")
            print(f"      at {notif['timestamp'].strftime('%I:%M:%S %p')}")
        
        assert len(received_notifications) >= 1, "Should receive at least 1 notification"
        
        print("\n✅ TEST PASSED: Quick reminders work!")
        
        # Stop service
        await reminder_service.stop()
        print("✓ Reminder service stopped")
        
        return True
        
    finally:
        await mcp_client.disconnect()
        print("✓ Disconnected from calendar")


async def test_calendar_event_reminder():
    """Test reminder for an actual calendar event."""
    print("\n" + "=" * 80)
    print("TEST: Calendar Event Reminder")
    print("=" * 80)
    
    received_notifications.clear()
    
    # Load config
    config = load_config()
    
    # Initialize MCP client
    mcp_client = MCPClient(
        mcp_server_path=config.google.calendar_mcp_path,
        oauth_credentials_path=config.google.oauth_credentials_path
    )
    
    try:
        await mcp_client.connect()
        print("✓ Connected to Google Calendar")
        
        # Create a calendar event 5 minutes from now
        event_start = datetime.now() + timedelta(minutes=5)
        event_end = event_start + timedelta(minutes=30)
        
        from src.models.calendar import EventCreate
        
        event = EventCreate(
            calendar_id="primary",
            summary="Test Event for Reminder",
            start=event_start.isoformat(),
            end=event_end.isoformat(),
            description="This is a test event for Phase 4 reminder testing"
        )
        
        print(f"\n📅 Creating test event: '{event.summary}'")
        print(f"   Start: {event_start.strftime('%I:%M %p')}")
        
        created_event = await mcp_client.create_event(event)
        print(f"✓ Event created with ID: {created_event.id}")
        
        # Initialize reminder service with custom rule: 3 minutes before
        config.reminders.check_interval_seconds = 10
        config.reminders.default_rules = [
            ReminderRule(
                offset_minutes=3,
                message_template="Reminder: '{event_summary}' starts in 3 minutes at {event_time}",
                enabled=True
            )
        ]
        
        reminder_service = ReminderService(
            mcp_client=mcp_client,
            config=config.reminders
        )
        
        # Set callback
        reminder_service.set_terminal_callback(notification_callback)
        
        # Start service
        await reminder_service.start()
        print("✓ Reminder service started")
        print("⏰ Will remind 3 minutes before event (in ~2 minutes)")
        
        print(f"\n⏱️  Current time: {datetime.now().strftime('%I:%M:%S %p')}")
        print("⏳ Waiting for event reminder...")
        
        # Wait up to 3 minutes
        for i in range(180):
            await asyncio.sleep(1)
            elapsed = i + 1
            
            if elapsed % 15 == 0:
                print(f"   ... {elapsed}s elapsed")
            
            if len(received_notifications) > 0:
                print(f"\n✅ SUCCESS! Event reminder fired")
                break
        else:
            print("\n⚠️  No reminder received (may need to wait longer)")
        
        # Display results
        if received_notifications:
            print(f"\n📊 Received {len(received_notifications)} notification(s):")
            for notif in received_notifications:
                print(f"   • {notif['message']}")
        
        # Cleanup: Delete test event
        print(f"\n🗑️  Cleaning up test event...")
        await mcp_client.delete_event(
            calendar_id="primary",
            event_id=created_event.id
        )
        print("✓ Test event deleted")
        
        # Stop service
        await reminder_service.stop()
        print("✓ Reminder service stopped")
        
        return len(received_notifications) > 0
        
    finally:
        await mcp_client.disconnect()
        print("✓ Disconnected from calendar")


async def main():
    """Run all Phase 4 tests."""
    print("\n")
    print("=" * 80)
    print("  PHASE 4 TESTS: Reminder Service & Background Notifications")
    print("=" * 80)
    print("\nThese tests verify that reminders work autonomously without user input.")
    print("You can sit back and watch - notifications will appear automatically!")
    print()
    
    # Ask user which test to run
    print("Choose a test:")
    print("  1. Quick test (30-60 seconds)")
    print("  2. Full test (2 minutes)")
    print("  3. Calendar event reminder (5 minutes)")
    print("  4. Run all tests")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    results = {}
    
    try:
        if choice == "1":
            results["quick"] = await test_quick_reminder_30_seconds()
        
        elif choice == "2":
            results["2min"] = await test_custom_reminder_2_minutes()
        
        elif choice == "3":
            results["calendar"] = await test_calendar_event_reminder()
        
        elif choice == "4":
            print("\n🚀 Running all tests (this will take ~8 minutes)...\n")
            results["quick"] = await test_quick_reminder_30_seconds()
            await asyncio.sleep(2)
            results["2min"] = await test_custom_reminder_2_minutes()
            await asyncio.sleep(2)
            results["calendar"] = await test_calendar_event_reminder()
        
        else:
            print("Invalid choice. Running quick test...")
            results["quick"] = await test_quick_reminder_30_seconds()
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {test_name}: {status}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Phase 4 is complete!")
            print("\n✅ Verified:")
            print("   • Reminders fire autonomously without user input")
            print("   • Multiple reminders can be scheduled")
            print("   • Notifications appear in real-time")
            print("   • Background service runs independently")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        log_error(f"Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
