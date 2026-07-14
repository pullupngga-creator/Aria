/**
 * Lightweight pub/sub store tracking which peer fingerprints have an active TCP connection.
 * Follows the same pattern as peerStore.js per RULES.md §3.
 */

/** @type {Set<string>} */
const connectedFingerprints = new Set();
const listeners = new Set();

function notify() {
  const snapshot = [...connectedFingerprints];
  listeners.forEach(fn => fn(snapshot));
}

export const connectionStore = {
  /**
   * Check if a peer fingerprint has an active connection.
   * @param {string} fingerprint
   * @returns {boolean}
   */
  isConnected(fingerprint) {
    return connectedFingerprints.has(fingerprint);
  },

  /**
   * Mark a peer as connected.
   * @param {string} fingerprint
   */
  setConnected(fingerprint) {
    connectedFingerprints.add(fingerprint);
    notify();
  },

  /**
   * Mark a peer as disconnected.
   * @param {string} fingerprint
   */
  setDisconnected(fingerprint) {
    connectedFingerprints.delete(fingerprint);
    notify();
  },

  /**
   * Get all currently connected peer fingerprints.
   * @returns {string[]}
   */
  getAll() {
    return [...connectedFingerprints];
  },

  /**
   * Subscribe to connection state changes.
   * @param {function(string[]): void} fn
   * @returns {function(): void} unsubscribe function
   */
  subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};
