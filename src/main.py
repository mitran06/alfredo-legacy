"""Main application entry point for the AI Personal Secretary."""

import asyncio
import sys

from src.app.assistant_app import AssistantApp
from src.utils.logger import log_info, log_error


# Global queue for notifications
notification_queue = asyncio.Queue()


def display_notification(message: str):
    """Callback for displaying notifications from reminder service.
    
    This is called by the reminder service when a notification needs to be shown.
    It queues the notification for async display.
    
    Args:
        message: Notification message to display
    """
    try:
        # Queue notification (non-blocking from sync context)
        asyncio.create_task(notification_queue.put(message))
    except RuntimeError:
        # If no event loop, print directly
        print(f"\n🔔 {message}\n")
        print("You: ", end="", flush=True)


async def notification_display_task():
    """Background task that displays notifications as they arrive.
    
    This runs concurrently with the main loop and prints notifications
    immediately, even while waiting for user input.
    """
    while True:
        try:
            # Wait for next notification
            message = await notification_queue.get()
            
            # Print notification with bell emoji
            # Use carriage return to overwrite input prompt if needed
            print(f"\r🔔 {message}")
            print("You: ", end="", flush=True)
            
            log_info(f"[LOG] Notification displayed: {message}")
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            log_error(f"Error displaying notification: {e}")


async def main():
    """Main application loop."""
    
    print("=" * 60)
    print("  AI PERSONAL SECRETARY - Phase 4")
    print("  Natural Language Calendar Assistant with Reminders")
    print("=" * 60)
    print()
    
    assistant = AssistantApp()

    # Start notification display task
    notification_task = asyncio.create_task(notification_display_task())

    try:
        log_info("Starting assistant services...")
        await assistant.startup()
        assistant.register_notification_callback(display_notification)
        log_info("Assistant services ready")
        
        print()
        print("Assistant: Hello! I'm your personal calendar assistant.")
        print("             I can help you manage your Google Calendar and set reminders.")
        print("             Try saying things like:")
        print("               • 'I have a test on Monday at 8 AM'")
        print("               • 'What do I have tomorrow?'")
        print("               • 'Remind me in 2 minutes to check the oven'")
        print("               • 'Set a reminder for 3pm to call mom'")
        print()
        print("             Commands: /help, /clear, /stats, /quit")
        print()
        print("-" * 60)
        print()
        
        # Main conversation loop
        while True:
            try:
                # Get user input (blocking, but notifications display concurrently)
                user_input = await asyncio.to_thread(input, "You: ")
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    if user_input == "/quit" or user_input == "/exit":
                        print("\nAssistant: Goodbye! Have a great day! 👋")
                        break
                    
                    elif user_input == "/help":
                        print("\nAvailable commands:")
                        print("  /help   - Show this help message")
                        print("  /clear  - Clear conversation history")
                        print("  /stats  - Show conversation statistics")
                        print("  /quit   - Exit the application")
                        print()
                        continue
                    
                    elif user_input == "/clear":
                        assistant.clear_conversation()
                        print("\nAssistant: Conversation cleared! Starting fresh.\n")
                        continue
                    
                    elif user_input == "/stats":
                        stats = assistant.get_conversation_stats()
                        reminder_stats = assistant.get_reminder_stats()
                        print(f"\nConversation Statistics:")
                        print(f"  Total messages: {stats['total_messages']}")
                        print(f"  User messages: {stats['user_messages']}")
                        print(f"  Assistant messages: {stats['assistant_messages']}")
                        print(f"  Pending actions: {stats['pending_actions']}")
                        print(f"\nReminder Service:")
                        print(f"  Reminders sent: {reminder_stats['monitor']['sent_reminders']}")
                        print(f"  Custom reminders pending: {reminder_stats['monitor']['custom_reminders_pending']}")
                        print(f"  Service running: {'Yes' if reminder_stats['is_started'] else 'No'}")
                        print()
                        continue
                    
                    else:
                        print(f"\nUnknown command: {user_input}")
                        print("Type /help for available commands.\n")
                        continue
                
                # Process message with AI agent
                response = await assistant.process_message(user_input)
                
                # Display response
                print(f"\nAssistant: {response.message}\n")
                
                # Show tools used (for debugging)
                if response.tools_used:
                    log_info(f"[LOG] Tools used: {', '.join(response.tools_used)}")
            
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type /quit to exit gracefully.\n")
                continue
            
            except Exception as e:
                log_error(f"Error in conversation loop: {e}")
                print(f"\nAssistant: I encountered an error. Please try again.\n")
                continue
    
    except Exception as e:
        log_error(f"Fatal error: {e}")
        import traceback
        log_error(traceback.format_exc())
        print(f"\nFatal error: {e}")
    
    finally:
        # Cleanup
        log_info("Shutting down...")
        
        # Cancel notification task
        if 'notification_task' in locals():
            notification_task.cancel()
            try:
                await notification_task
            except asyncio.CancelledError:
                pass
        
        # Stop reminder service
        await assistant.shutdown()
        print("\nDisconnected from calendar. Goodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
