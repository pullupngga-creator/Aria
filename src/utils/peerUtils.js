const palette = ['#4F7DF3', '#34C759', '#E86A33', '#AF52DE', '#FF9500'];
import { peerStore } from '../stores/peerStore.js';

/**
 * Gets the deterministic avatar color and initials for a peer
 * @param {import("../bindings.js").PeerRow} peer
 * @returns {{color: string, initials: string, name: string}}
 */
export function getPeerDisplayInfo(peer) {
    const name = peer.display_name || peer.hostname || peer.fingerprint.substring(0,6);
    const initials = name.substring(0, 2).toUpperCase();
    const colorIndex = parseInt(peer.fingerprint.substring(0, 6), 16) % palette.length;
    const color = palette[colorIndex];
    return { name, initials, color };
}

/**
 * Gets peer display info by fingerprint (looks up from store)
 * @param {string} fingerprint
 * @returns {{displayName: string, initial: string, color: string}}
 */
export function getPeerDisplayInfoByFingerprint(fingerprint) {
    const peer = peerStore.getPeer(fingerprint);
    
    if (!peer) {
        return {
            displayName: 'Unknown Peer',
            initial: '?',
            color: '#9ca3af'
        };
    }
    
    const info = getPeerDisplayInfo(peer);
    return {
        displayName: info.name,
        initial: info.initials,
        color: info.color
    };
}

