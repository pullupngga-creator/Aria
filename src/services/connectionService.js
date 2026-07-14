/**
 * Connection service - manages TCP connections to peers.
 * Listens for Tauri events and keeps connectionStore in sync.
 */

import { listen } from '@tauri-apps/api/event';
import { commands } from '../bindings.js';
import { connectionStore } from '../stores/connectionStore.js';

let _unlistenConnected = null;
let _unlistenDisconnected = null;

export const connectionService = {
  /**
   * Initialize the connection service by setting up event listeners.
   * Call this once at app startup.
   */
  async init() {
    _unlistenConnected = await listen('peer:connected', (event) => {
      const { fingerprint } = event.payload;
      if (fingerprint) {
        connectionStore.setConnected(fingerprint);
      }
    });

    _unlistenDisconnected = await listen('peer:disconnected', (event) => {
      const { fingerprint } = event.payload;
      if (fingerprint) {
        connectionStore.setDisconnected(fingerprint);
      }
    });
  },

  /**
   * Initiate an outbound TCP connection to a peer.
   * Non-blocking - fires and forgets. Connection status updates via events.
   * @param {string} fingerprint
   */
  async connectToPeer(fingerprint) {
    try {
      await commands.connectToPeer(fingerprint);
    } catch (err) {
      console.error('[ConnectionService] Failed to connect to peer:', err);
      throw err;
    }
  },

  /**
   * Check if a peer is currently connected.
   * @param {string} fingerprint
   * @returns {Promise<boolean>}
   */
  async getConnectionStatus(fingerprint) {
    try {
      return await commands.getConnectionStatus(fingerprint);
    } catch (err) {
      console.error('[ConnectionService] Failed to get connection status:', err);
      return false;
    }
  },

  /**
   * Drop the TCP connection to a peer.
   * @param {string} fingerprint
   */
  async disconnectPeer(fingerprint) {
    try {
      await commands.disconnectPeer(fingerprint);
      connectionStore.setDisconnected(fingerprint);
    } catch (err) {
      console.error('[ConnectionService] Failed to disconnect peer:', err);
      throw err;
    }
  },

  /**
   * Cleanup event listeners. Call this on app shutdown.
   */
  destroy() {
    if (_unlistenConnected) _unlistenConnected();
    if (_unlistenDisconnected) _unlistenDisconnected();
  },
};
