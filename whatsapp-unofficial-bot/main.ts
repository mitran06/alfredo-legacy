const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// Calendar API Configuration
const CALENDAR_API_BASE = 'http://100.127.243.52:8000';

const client = new Client({
    authStrategy: new LocalAuth()
});

client.on('ready', () => {
    console.log('Client is ready!');
});

client.on('qr', qr => {
    qrcode.generate(qr, {small: true});
});

client.initialize();

// Store active agents per chat
const activeAgents = new Map();
// Store chat mode state per chat
const chatModeActive = new Map();

// Helper function to call Calendar API
async function callCalendarAPI(endpoint: string, method: string = 'GET', data: any = null) {
	try {
		const config: any = {
			method,
			url: `${CALENDAR_API_BASE}${endpoint}`,
			headers: { 'Content-Type': 'application/json' },
			timeout: 60000
		};
		if (data) {
			config.data = data;
		}
		const response = await axios(config);
		return { success: true, data: response.data };
	} catch (error: any) {
		console.error(`API Error (${endpoint}):`, error.message);
		return { 
			success: false, 
			error: error.response?.data?.detail || error.message 
		};
	}
}

// Generate help message
function getHelpMessage() {
	return `🤖 *ALFREDO CALENDAR ASSISTANT*

*Basic Commands:*
• \`alfredo activate\` - Activate caps mode
• \`alfredo deactivate\` - Deactivate caps mode
• \`!ping\` - Test bot connection

*Calendar Commands:*
• \`alfredo help\` - Show this help
• \`alfredo health\` - Check API health
• \`alfredo stats\` - Get conversation stats
• \`alfredo notifications\` - Get pending reminders
• \`alfredo clear\` - Clear conversation history

*Chat Mode:*
• \`alfredo chat\` - Enter chat mode (talk directly to calendar assistant)
• \`alfredo exit\` - Exit chat mode

*In Chat Mode:*
Just send your message naturally, like:
• "What's on my calendar tomorrow?"
• "Schedule a meeting with John on Friday at 2pm"
• "Remind me to call Alex at 9am"
• "List my events for next week"`;
}

// Listening to all incoming messages
client.on('message_create', async message => {
	// Ignore messages from yourself
	if (message.fromMe) return;
	
	console.log(`${message.from}: ${message.body}`);
	
	const chatId = message.from;
	const messageText = message.body.trim().toLowerCase();
	
	// Check if in chat mode
	if (chatModeActive.get(chatId)) {
		// Exit chat mode
		if (messageText === 'alfredo exit' || messageText === 'exit' || messageText === 'quit') {
			chatModeActive.delete(chatId);
			await message.reply('👋 Exited chat mode. Use `alfredo help` for commands.');
			return;
		}
		
		// Show typing indicator while processing
		const chat = await message.getChat();
		await chat.sendStateTyping();
		
		// Send message to calendar API
		const result = await callCalendarAPI('/chat', 'POST', { message: message.body });
		
		if (result.success) {
			const response = result.data.message;
			const toolsUsed = result.data.tools_used || [];
			let reply = response;
			if (toolsUsed.length > 0) {
				reply += `\n\n_Tools used: ${toolsUsed.join(', ')}_`;
			}
			await message.reply(reply);
		} else {
			await message.reply(`❌ Error: ${result.error}`);
		}
		return;
	}
	
	// Check for activation command (caps mode)
	if (messageText === 'alfredo activate') {
		activeAgents.set(chatId, true);
		await message.reply('🤖 ALFREDO AGENT ACTIVATED! I WILL NOW RESPOND IN ALL CAPS!');
		return;
	}
	
	// Check for deactivation command (caps mode)
	if (messageText === 'alfredo deactivate') {
		activeAgents.delete(chatId);
		await message.reply('🤖 Alfredo agent deactivated. Back to normal mode.');
		return;
	}
	
	// Help command
	if (messageText === 'alfredo help' || messageText === 'h') {
		await message.reply(getHelpMessage());
		return;
	}
	
	// Enter chat mode
	if (messageText === 'alfredo chat') {
		chatModeActive.set(chatId, true);
		await message.reply('💬 *Chat mode activated!*\n\nNow you can talk directly to the calendar assistant. Send any message and I\'ll relay it to the API.\n\nType `alfredo exit` to leave chat mode.');
		return;
	}
	
	// Health check
	if (messageText === 'alfredo health') {
		await message.reply('🔍 Checking API health...');
		const result = await callCalendarAPI('/health');
		
		if (result.success) {
			const health = result.data;
			let reply = '✅ *API Health Status*\n\n';
			reply += `• Started: ${health.is_started ? '✓' : '✗'}\n`;
			reply += `• Config Loaded: ${health.config_loaded ? '✓' : '✗'}\n`;
			reply += `\n*Conversation Stats:*\n`;
			reply += `• Total messages: ${health.conversation_stats?.total_messages || 0}\n`;
			reply += `• User messages: ${health.conversation_stats?.user_messages || 0}\n`;
			reply += `• Pending actions: ${health.conversation_stats?.pending_actions || 0}\n`;
			reply += `\n*Reminder Service:*\n`;
			reply += `• Status: ${health.reminder_stats?.is_started ? '✓ Running' : '✗ Stopped'}\n`;
			reply += `• Sent reminders: ${health.reminder_stats?.monitor?.sent_reminders || 0}\n`;
			reply += `• Pending: ${health.reminder_stats?.monitor?.custom_reminders_pending || 0}`;
			await message.reply(reply);
		} else {
			await message.reply(`❌ Health check failed: ${result.error}`);
		}
		return;
	}
	
	// Stats command
	if (messageText === 'alfredo stats') {
		await message.reply('📊 Fetching stats...');
		const result = await callCalendarAPI('/stats');
		
		if (result.success) {
			const stats = result.data;
			let reply = '📊 *Calendar Assistant Stats*\n\n';
			reply += '*Conversation:*\n';
			reply += `• Total: ${stats.conversation?.total_messages || 0} messages\n`;
			reply += `• User: ${stats.conversation?.user_messages || 0}\n`;
			reply += `• Assistant: ${stats.conversation?.assistant_messages || 0}\n`;
			reply += `• Pending actions: ${stats.conversation?.pending_actions || 0}\n`;
			reply += `\n*Reminders:*\n`;
			reply += `• Sent: ${stats.reminders?.monitor?.sent_reminders || 0}\n`;
			reply += `• Pending: ${stats.reminders?.monitor?.custom_reminders_pending || 0}\n`;
			reply += `• Queue size: ${stats.reminders?.dispatcher?.queue_size || 0}`;
			await message.reply(reply);
		} else {
			await message.reply(`❌ Failed to fetch stats: ${result.error}`);
		}
		return;
	}
	
	// Notifications command
	if (messageText === 'alfredo notifications') {
		await message.reply('🔔 Fetching notifications...');
		const result = await callCalendarAPI('/notifications?limit=10&flush=false');
		
		if (result.success) {
			const notifications = result.data.notifications || [];
			if (notifications.length === 0) {
				await message.reply('📭 No notifications at the moment.');
			} else {
				let reply = `🔔 *${notifications.length} Notification(s)*\n\n`;
				notifications.forEach((notif: any, index: number) => {
					reply += `${index + 1}. ${notif.message}\n`;
					reply += `   _${new Date(notif.created_at).toLocaleString()}_\n\n`;
				});
				await message.reply(reply);
			}
		} else {
			await message.reply(`❌ Failed to fetch notifications: ${result.error}`);
		}
		return;
	}
	
	// Clear conversation command
	if (messageText === 'alfredo clear') {
		await message.reply('🗑️ Clearing conversation history...');
		const result = await callCalendarAPI('/conversation/clear', 'POST');
		
		if (result.success) {
			await message.reply('✅ Conversation history cleared!');
		} else {
			await message.reply(`❌ Failed to clear: ${result.error}`);
		}
		return;
	}
	
	// If agent is active for this chat, respond in all caps
	if (activeAgents.get(chatId)) {
		const response = message.body.toUpperCase();
		await message.reply(response);
		return;
	}
	
	// Original ping-pong functionality
	if (message.body === '!ping') {
		await client.sendMessage(message.from, 'pong');
	}
});
