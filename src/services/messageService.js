import { commands } from '../bindings.js';
import { messageStore } from '../stores/messageStore.js';
import { threadStore } from '../stores/threadStore.js';
import { listen } from '@tauri-apps/api/event';

let _unlistenSent = null;
let _unlistenReceived = null;
let _unlistenDelivered = null;

export const messageService = {
  async init() {
    _unlistenSent = await listen('message:sent', (event) => {
      console.log('[MessageService] Sent:', event.payload);
      const { fingerprint, ...message } = event.payload;
      messageStore.addMessage(fingerprint, { ...message, direction: 'sent', status: 'pending' });
      
      // Update thread last message preview
      threadStore.updateLastMessage(fingerprint, message.content, message.timestamp, true);
    });

    _unlistenReceived = await listen('message:received', (event) => {
      console.log('[MessageService] Received:', event.payload);
      const { fingerprint, ...message } = event.payload;
      messageStore.addMessage(fingerprint, { ...message, direction: 'received', status: 'received' });
      
      // Update thread last message preview and increment unread
      threadStore.updateLastMessage(fingerprint, message.content, message.timestamp, false);
      threadStore.incrementUnread(fingerprint);
    });

    _unlistenDelivered = await listen('message:delivered', (event) => {
      console.log('[MessageService] Delivered:', event.payload);
      const { fingerprint, message_id, status } = event.payload;
      messageStore.updateMessageStatus(fingerprint, message_id, status);
    });
  },

  async sendMessage(fingerprint, content, replyTo = null) {
    try {
      const messageId = await commands.sendMessage(fingerprint, content, replyTo);
      return messageId;
    } catch (err) {
      console.error('[MessageService] Failed to send message:', err);
      throw err;
    }
  },

  async loadMessages(fingerprint) {
    try {
      const messages = await commands.getMessages(fingerprint);
      messageStore.setMessages(fingerprint, messages);
      return messages;
    } catch (err) {
      console.error('[MessageService] Failed to load messages:', err);
      throw err;
    }
  },

  destroy() {
    if (_unlistenSent) _unlistenSent();
    if (_unlistenReceived) _unlistenReceived();
    if (_unlistenDelivered) _unlistenDelivered();
  },
};
