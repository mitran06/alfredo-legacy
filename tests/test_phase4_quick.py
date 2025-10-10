"""Simple Phase 4 Test: Test reminder components in isolation.

This test verifies the reminder system without requiring full MCP integration.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.reminders.notification_dispatcher import NotificationDispatcher, Notification
from src.reminders.event_monitor import EventMonitor, ScheduledReminder


# Track notifications
received_notifications = []


def callback(message: str):
    """Test callback."""
    received_notifications.append({
        "message": message,
        "time": datetime.now()
    })
    print(f"📬 NOTIFICATION: {message}")


async def test_notification_dispatcher():
    """Test that NotificationDispatcher works."""
    print("\n" + "=" * 70)
    print("TEST 1: NotificationDispatcher")
    print("=" * 70)
    
    received_notifications.clear()
    
    # Create dispatcher
    dispatcher = NotificationDispatcher()
    dispatcher.set_terminal_callback(callback)
    
    # Start dispatcher
    await dispatcher.start()
    print("✓ Dispatcher started")
    
    # Send a test notification
    notification = Notification(
        message="Test reminder: Check the oven!",
        event_id="test-1",
        event_summary="Check oven",
        event_start=datetime.now(),
        notification_type="reminder",
        created_at=datetime.now()
    )
    
    print("📤 Sending test notification...")
    await dispatcher.send_notification(notification)
    
    # Wait for dispatch
    await asyncio.sleep(1)
    
    # Check
    assert len(received_notifications) == 1, "Should receive notification"
    assert "Check the oven" in received_notifications[0]["message"]
    
    print("✅ TEST PASSED: NotificationDispatcher works!")
    
    await dispatcher.stop()
    return True


async def test_custom_reminder_quick():
    """Test custom reminder with mock MCP client."""
    print("\n" + "=" * 70)
    print("TEST 2: Custom Reminder (30 seconds)")
    print("=" * 70)
    
    received_notifications.clear()
    
    # Create components
    dispatcher = NotificationDispatcher()
    dispatcher.set_terminal_callback(callback)
    
    # Mock MCP client (not needed for custom reminders)
    class MockMCPClient:
        async def list_events(self, **kwargs):
            return type('obj', (object,), {'events': []})()
    
    mock_mcp = MockMCPClient()
    
    # Create monitor with empty rules (we'll use custom reminders)
    monitor = EventMonitor(
        mcp_client=mock_mcp,
        notification_dispatcher=dispatcher,
        reminder_rules=[],
        check_interval_seconds=5
    )
    
    # Start both
    await dispatcher.start()
    await monitor.start()
    print("✓ Services started")
    
    # Add custom reminder for 30 seconds from now
    remind_time = datetime.now() + timedelta(seconds=30)
    monitor.add_custom_reminder(
        event_summary="Test reminder - Take medicine",
        remind_at=remind_time,
        event_id="custom-test-1"
    )
    
    print(f"⏰ Reminder set for: {remind_time.strftime('%H:%M:%S')}")
    print(f"⏱️  Current time: {datetime.now().strftime('%H:%M:%S')}")
    print("\n⏳ Waiting 35 seconds for reminder to fire...")
    
    # Wait 35 seconds
    for i in range(35):
        await asyncio.sleep(1)
        if (i + 1) % 10 == 0:
            print(f"   {i + 1}s elapsed...")
        
        if len(received_notifications) > 0:
            elapsed = i + 1
            print(f"\n✅ Reminder fired after {elapsed} seconds!")
            break
    
    # Check results
    print(f"\n📊 Received {len(received_notifications)} notification(s)")
    
    if received_notifications:
        for notif in received_notifications:
            print(f"   • {notif['message']}")
            print(f"     at {notif['time'].strftime('%H:%M:%S')}")
    
    success = len(received_notifications) > 0
    
    if success:
        print("\n✅ TEST PASSED: Custom reminder works without user input!")
    else:
        print("\n❌ TEST FAILED: No notification received")
    
    # Cleanup
    await monitor.stop()
    await dispatcher.stop()
    
    return success


async def test_multiple_reminders():
    """Test multiple simultaneous reminders."""
    print("\n" + "=" * 70)
    print("TEST 3: Multiple Reminders (20s, 30s)")
    print("=" * 70)
    
    received_notifications.clear()
    
    # Create components
    dispatcher = NotificationDispatcher()
    dispatcher.set_terminal_callback(callback)
    
    class MockMCPClient:
        async def list_events(self, **kwargs):
            return type('obj', (object,), {'events': []})()
    
    monitor = EventMonitor(
        mcp_client=MockMCPClient(),
        notification_dispatcher=dispatcher,
        reminder_rules=[],
        check_interval_seconds=3
    )
    
    await dispatcher.start()
    await monitor.start()
    print("✓ Services started")
    
    # Add two reminders
    now = datetime.now()
    
    monitor.add_custom_reminder(
        event_summary="First reminder - 20 seconds",
        remind_at=now + timedelta(seconds=20),
        event_id="multi-1"
    )
    print(f"⏰ Reminder 1 set for: {(now + timedelta(seconds=20)).strftime('%H:%M:%S')}")
    
    monitor.add_custom_reminder(
        event_summary="Second reminder - 30 seconds",
        remind_at=now + timedelta(seconds=30),
        event_id="multi-2"
    )
    print(f"⏰ Reminder 2 set for: {(now + timedelta(seconds=30)).strftime('%H:%M:%S')}")
    
    print(f"\n⏱️  Current time: {datetime.now().strftime('%H:%M:%S')}")
    print("⏳ Waiting 35 seconds for both reminders...")
    
    # Wait 35 seconds
    for i in range(35):
        await asyncio.sleep(1)
        if (i + 1) % 10 == 0:
            print(f"   {i + 1}s, {len(received_notifications)} received")
    
    # Check results
    print(f"\n📊 Received {len(received_notifications)} notification(s)")
    
    for idx, notif in enumerate(received_notifications, 1):
        print(f"   {idx}. {notif['message']}")
        print(f"      at {notif['time'].strftime('%H:%M:%S')}")
    
    success = len(received_notifications) >= 2
    
    if success:
        print("\n✅ TEST PASSED: Multiple reminders work!")
    else:
        print(f"\n⚠️  Only received {len(received_notifications)}/2 reminders")
    
    # Cleanup
    await monitor.stop()
    await dispatcher.stop()
    
    return success


async def main():
    """Run Phase 4 component tests."""
    print("\n" + "=" * 70)
    print("  PHASE 4 COMPONENT TESTS")
    print("  Background Reminder Service")
    print("=" * 70)
    print("\nThese tests verify reminders fire autonomously without user input.")
    print()
    
    results = {}
    
    try:
        # Test 1: Basic notification
        results["dispatcher"] = await test_notification_dispatcher()
        await asyncio.sleep(2)
        
        # Test 2: Single custom reminder
        results["single_reminder"] = await test_custom_reminder_quick()
        await asyncio.sleep(2)
        
        # Test 3: Multiple reminders
        results["multiple_reminders"] = await test_multiple_reminders()
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {test_name}: {status}")
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
            print("\n✅ Phase 4 Core Features Verified:")
            print("   • Notifications dispatch correctly")
            print("   • Custom reminders fire without user input")
            print("   • Multiple reminders work simultaneously")
            print("   • Background services run independently")
            print("\n📝 Key Achievement:")
            print("   When user says 'remind me in 2 minutes', the system")
            print("   will automatically send a notification after 2 minutes")
            print("   WITHOUT requiring any user input!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
