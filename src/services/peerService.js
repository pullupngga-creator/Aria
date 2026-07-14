import { commands } from '../bindings.js';
import { listen } from '@tauri-apps/api/event';
import { peerStore } from '../stores/peerStore.js';

export const peerService = {
  /** @type {Array<function>} unlisten handles */
  _unlisteners: [],

  /** @type {function|null} callback for network changes */
  _onNetworkChange: null,

  /** @type {function|null} callback for mDNS disabled */
  _onMdnsDisabled: null,

  async init() {
    // 1. Hydrate store from DB (known peers survive app restarts)
    const result = await commands.listPeers();
    if (result.status === 'ok') {
      result.data.forEach(peer => peerStore.upsert(peer));
    }

    // 2. Listen for live discovery events
    const unPeerDisc = await listen('peer:discovered', (event) => {
      const payload = event.payload;
      const existing = peerStore.get(payload.fingerprint);

      peerStore.upsert({
        ...existing,
        fingerprint: payload.fingerprint,
        display_name: payload.display_name || existing?.display_name,
        is_online: payload.is_online,
        trust_level: existing?.trust_level || 'untrusted',
        id: existing?.id || 0,
        port: existing?.port || 9473,
        ip_address: payload.ip_address || existing?.ip_address,
        hostname: payload.hostname || existing?.hostname
      });
    });

    const unPeerOff = await listen('peer:offline', (event) => {
      peerStore.setOffline(event.payload.fingerprint);
    });

    // 3. Listen for network interface changes
    const unNetChanged = await listen('network:changed', (event) => {
      const payload = event.payload;
      peerStore.setNetworkState({
        ips: payload.ips,
        changed: payload.changed,
        mdnsDegraded: payload.mdns_degraded
      });
      if (this._onNetworkChange) {
        this._onNetworkChange(payload);
      }
    });

    // 4. Listen for mDNS disabled event
    const unMdnsDisabled = await listen('network:mdns_disabled', (event) => {
      const payload = event.payload;
      peerStore.setNetworkState({
        ips: [],
        changed: true,
        mdnsDegraded: true
      });
      if (this._onMdnsDisabled) {
        this._onMdnsDisabled(payload);
      }
    });

    this._unlisteners.push(unPeerDisc, unPeerOff, unNetChanged, unMdnsDisabled);
  },

  /**
   * Register a callback for network change events
   * @param {function} fn
   */
  onNetworkChange(fn) {
    this._onNetworkChange = fn;
  },

  /**
   * Register a callback for mDNS disabled events
   * @param {function} fn
   */
  onMdnsDisabled(fn) {
    this._onMdnsDisabled = fn;
  },

  /** @param {string} fingerprint */
  async trust(fingerprint) {
    await commands.trustPeer(fingerprint);
    const peer = peerStore.get(fingerprint);
    if (peer) {
      peerStore.upsert({ ...peer, trust_level: 'trusted' });
    }
  },

  /** @param {string} fingerprint */
  async block(fingerprint) {
    await commands.blockPeer(fingerprint);
    const peer = peerStore.get(fingerprint);
    if (peer) {
      peerStore.upsert({ ...peer, trust_level: 'blocked' });
    }
  },

  /** @param {string} fingerprint */
  async unblock(fingerprint) {
    await commands.untrustPeer(fingerprint);
    const peer = peerStore.get(fingerprint);
    if (peer) {
      peerStore.upsert({ ...peer, trust_level: 'untrusted' });
    }
  },

  destroy() {
    this._unlisteners.forEach(fn => fn());
    this._unlisteners = [];
  },
};