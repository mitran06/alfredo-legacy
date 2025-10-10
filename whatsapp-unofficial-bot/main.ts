const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

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

// Listening to all incoming messages
client.on('message_create', async message => {
	// Ignore messages from yourself
	if (message.fromMe) return;
	
	console.log(`${message.from}: ${message.body}`);
	
	const chatId = message.from;
	const messageText = message.body.trim().toLowerCase();
	
	// Check for activation command
	if (messageText === 'alfredo activate') {
		activeAgents.set(chatId, true);
		await message.reply('🤖 ALFREDO AGENT ACTIVATED! I WILL NOW RESPOND IN ALL CAPS!');
		return;
	}
	
	// Check for deactivation command
	if (messageText === 'alfredo deactivate') {
		activeAgents.delete(chatId);
		await message.reply('🤖 Alfredo agent deactivated. Back to normal mode.');
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
