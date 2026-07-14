/**
 * peerStore — Lightweight pub/sub store for the live peer list.
 * Peers are keyed by fingerprint (string).
 * @module peerStore
 */

/** @type {Map<string, import("../bindings.js").PeerRow>} */
const _peers = new Map();

/** @type {Set<function>} */
const _listeners = new Set();

/** @type {Set<function>} */
const _networkListeners = new Set();

/**
 * @typedef {Object} NetworkState
 * @property {string[]} ips
 * @property {boolean} changed
 * @property {boolean} mdnsDegraded
 */

/** @type {NetworkState} */
let _networkState = {
  ips: [],
  changed: false,
  mdnsDegraded: false,
};

export const peerStore = {
  /** @param {import("../bindings.js").PeerRow} peer */
  upsert(peer) {
    _peers.set(peer.fingerprint, peer);
    this._notify();
  },

  /** @param {string} fingerprint */
  setOffline(fingerprint) {
    const peer = _peers.get(fingerprint);
    if (peer) {
      peer.is_online = false;
      this._notify();
    }
  },

  /**
   * Update network state
   * @param {Partial<NetworkState>} state
   */
  setNetworkState(state) {
    _networkState = { ..._networkState, ...state };
    _networkListeners.forEach(fn => fn(_networkState));
  },

  /** @returns {NetworkState} */
  getNetworkState() {
    return { ..._networkState };
  },

  /**
   * Subscribe to network state changes
   * @param {function(NetworkState): void} fn
   * @returns {function} unsubscribe
   */
  subscribeNetwork(fn) {
    _networkListeners.add(fn);
    fn(_networkState);
    return () => _networkListeners.delete(fn);
  },

  /** @returns {import("../bindings.js").PeerRow[]} sorted: online first, then by last_seen */
  getAll() {
    return Array.from(_peers.values()).sort((a, b) => {
      if (a.is_online && !b.is_online) return -1;
      if (!a.is_online && b.is_online) return 1;
      
      const timeA = a.last_seen ? new Date(a.last_seen).getTime() : 0;
      const timeB = b.last_seen ? new Date(b.last_seen).getTime() : 0;
      
      if (timeA !== timeB) {
         return timeB - timeA;
      }
      
      // Fallback to name sort
      const nameA = a.display_name || a.hostname || a.fingerprint;
      const nameB = b.display_name || b.hostname || b.fingerprint;
      return nameA.localeCompare(nameB);
    });
  },

  /** @param {string} fingerprint @returns {import("../bindings.js").PeerRow | undefined} */
  get(fingerprint) {
    return _peers.get(fingerprint);
  },

  /** @param {function(import("../bindings.js").PeerRow[]): void} fn @returns {function} unsubscribe */
  subscribe(fn) {
    _listeners.add(fn);
    fn(this.getAll()); // emit current state immediately on subscribe
    return () => _listeners.delete(fn);
  },
  
  _notify() {
      const all = this.getAll();
      _listeners.forEach(fn => fn(all));
  }
};