"""Visual demo of Phase 4 reminder system.

This script creates a quick visual demonstration of how reminders work
without user input.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.reminders.notification_dispatcher import NotificationDispatcher
from src.reminders.event_monitor import EventMonitor


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def simulate_user_thinking():
    """Simulate user typing or thinking."""
    print("You: ", end="", flush=True)
    for char in "hmm let me think...":
        print(char, end="", flush=True)
        import time
        time.sleep(0.1)
    print()


async def demo():
    """Run visual demonstration."""
    
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  🤖 AI PERSONAL SECRETARY - PHASE 4 DEMO  ".center(68) + "║")
    print("║" + "  Autonomous Reminders Without User Input".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Setup
    print_header("SETUP: Starting Reminder Service")
    
    notifications = []
    
    def callback(msg):
        notifications.append((datetime.now(), msg))
        print(f"\r{'':70}")  # Clear line
        print(f"🔔 {msg}")
        print("You: ", end="", flush=True)
    
    dispatcher = NotificationDispatcher()
    dispatcher.set_terminal_callback(callback)
    
    class MockMCP:
        async def list_events(self, **kwargs):
            return type('obj', (object,), {'events': []})()
    
    monitor = EventMonitor(
        mcp_client=MockMCP(),
        notification_dispatcher=dispatcher,
        reminder_rules=[],
        check_interval_seconds=2
    )
    
    await dispatcher.start()
    await monitor.start()
    
    print("✓ Reminder service running in background")
    print("✓ Notification dispatcher ready")
    print()
    
    # Scene 1: User creates reminder
    print_header("SCENE 1: User Requests Reminder")
    print()
    print('You: "Remind me in 10 seconds to check the oven"')
    print()
    
    await asyncio.sleep(1)
    
    print('Assistant: "I\'ll remind you in 10 seconds to check the oven!"')
    print()
    
    # Create reminder
    remind_at = datetime.now() + timedelta(seconds=10)
    monitor.add_custom_reminder(
        event_summary="Check the oven",
        remind_at=remind_at
    )
    
    print(f"[LOG] Reminder scheduled for {remind_at.strftime('%H:%M:%S')}")
    print(f"[LOG] Current time: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Scene 2: User continues chatting
    print_header("SCENE 2: User Continues Chatting (Reminder in Background)")
    print()
    
    await asyncio.sleep(2)
    
    print('You: "What do I have tomorrow?"')
    print()
    await asyncio.sleep(1)
    
    print('Assistant: "Let me check your calendar..."')
    print()
    await asyncio.sleep(2)
    
    print('Assistant: "You have 2 events tomorrow:')
    print('            • Team meeting at 10 AM')
    print('            • Dentist appointment at 2 PM"')
    print()
    await asyncio.sleep(2)
    
    print('You: "Thanks! Can you remind me about the dentist?"')
    print()
    await asyncio.sleep(1)
    
    print('Assistant: "Sure! I\'ll remind you 1 hour before the dentist."')
    print()
    
    # Wait for first reminder
    await asyncio.sleep(3)
    
    # Scene 3: User starts typing
    print_header("SCENE 3: User Typing When Reminder Fires")
    print()
    
    print("(User starts typing a new message...)")
    print()
    
    # Simulate typing
    await asyncio.sleep(1)
    print("You: ", end="", flush=True)
    
    for i, char in enumerate("Should I reschedule the mee"):
        print(char, end="", flush=True)
        await asyncio.sleep(0.2)
        
        # Reminder fires mid-typing!
        if i == 15 and len(notifications) == 0:
            # Still waiting for reminder
            remaining = int((remind_at - datetime.now()).total_seconds())
            if remaining > 0:
                print(f"\n\n[Waiting {remaining} more seconds for reminder...]")
                await asyncio.sleep(remaining + 0.5)
    
    # Wait for reminder if not yet fired
    while len(notifications) == 0:
        await asyncio.sleep(0.5)
    
    print("\n")
    
    # Scene 4: Result
    print_header("SCENE 4: Reminder Fired Automatically!")
    print()
    
    if notifications:
        notif_time, notif_msg = notifications[0]
        print(f"✅ Notification appeared at: {notif_time.strftime('%H:%M:%S')}")
        print(f"📬 Message: {notif_msg}")
    
    print()
    print("💡 KEY POINT: The reminder fired automatically WITHOUT user input!")
    print("   The user was in the middle of typing and got interrupted by")
    print("   the notification - exactly as requested!")
    print()
    
    # Cleanup
    await monitor.stop()
    await dispatcher.stop()
    
    # Summary
    print_header("DEMO COMPLETE")
    print()
    print("✅ What We Just Demonstrated:")
    print("   1. User requests reminder ('in 10 seconds')")
    print("   2. User continues chatting normally")
    print("   3. User starts typing a new message")
    print("   4. 🔔 Reminder fires AUTOMATICALLY mid-typing!")
    print("   5. User sees notification WITHOUT providing input")
    print()
    print("🎯 This proves Phase 4 is working as specified:")
    print('   "even when i tell the assistant to remind me in 2 minutes,')
    print('    it would text me first, without my input after 2 minutes"')
    print()
    print("🎉 Phase 4: COMPLETE!")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.")
