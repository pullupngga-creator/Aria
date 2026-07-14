import { commands } from '../bindings.js';
import { typingStore } from '../stores/typingStore.js';
import { listen } from '@tauri-apps/api/event';

let _unlistenTyping = null;

export const typingService = {
  async init() {
    _unlistenTyping = await listen('typing:received', (event) => {
      console.log('[TypingService] Received typing indicator:', event.payload);
      const { fingerprint, is_typing } = event.payload;
      typingStore.setTyping(fingerprint, is_typing);
    });
  },

  async sendTyping(fingerprint, isTyping) {
    try {
      await commands.sendTyping({ fingerprint, is_typing });
      console.log('[TypingService] Sent typing indicator:', { fingerprint, isTyping });
    } catch (err) {
      console.error('[TypingService] Failed to send typing indicator:', err);
      throw err;
    }
  },

  destroy() {
    if (_unlistenTyping) {
      _unlistenTyping();
      _unlistenTyping = null;
    }
  },
};
