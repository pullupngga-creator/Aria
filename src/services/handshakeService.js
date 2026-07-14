import { commands } from '../bindings.js';
import { listen } from '@tauri-apps/api/event';

let _unlistenComplete = null;
let _unlistenRejected = null;

export const handshakeService = {
  async init() {
    _unlistenComplete = await listen('peer:handshake_complete', (event) => {
      console.log('[Handshake] Complete:', event.payload);
      // Update peer store, show success indicator
    });

    _unlistenRejected = await listen('peer:handshake_rejected', (event) => {
      console.warn('[Handshake] Rejected:', event.payload);
      // Show error to user
    });
  },

  async sendHandshake(fingerprint) {
    try {
      await commands.sendHandshake(fingerprint);
    } catch (err) {
      console.error('[HandshakeService] Failed to send handshake:', err);
      throw err;
    }
  },

  destroy() {
    if (_unlistenComplete) _unlistenComplete();
    if (_unlistenRejected) _unlistenRejected();
  },
};
