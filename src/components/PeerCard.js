import { getPeerDisplayInfo } from '../utils/peerUtils.js';

export function createPeerCard(container, options) {
  const { onTrust, onBlock, onUnblock } = options;
  let currentPeer = null;

  return {
    /** @param {import("../bindings.js").PeerRow} peer */
    show(peer) {
      currentPeer = peer;
      const isOnline = peer.is_online;
      const isTrusted = peer.trust_level === 'trusted';
      const isBlocked = peer.trust_level === 'blocked';
      
      const statusColor = isOnline ? 'var(--success)' : 'var(--text-muted)';
      const statusText = isOnline ? 'Online' : 'Offline';
      
      let trustHtml = '';
      let actionHtml = '';

      if (isTrusted) {
        trustHtml = `
          <div class="profile-trust profile-trust--verified">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-shield-check"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>
            Trusted
          </div>
        `;
        actionHtml = `
          <button class="profile-actions__btn profile-actions__btn--danger" id="peercard-block">Block Peer</button>
        `;
      } else if (isBlocked) {
        trustHtml = `
          <div class="profile-trust" style="background: rgba(255,59,48,0.1); color: #FF3B30;">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-ban"><circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/></svg>
            Blocked
          </div>
        `;
        actionHtml = `
          <button class="profile-actions__btn" id="peercard-unblock">Unblock</button>
        `;
      } else {
        trustHtml = `
          <div class="profile-trust profile-trust--unverified">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-shield-alert"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
            New
          </div>
        `;
        actionHtml = `
          <button class="profile-actions__btn" style="color: var(--accent); border-color: var(--accent-glow);" id="peercard-trust">Trust Peer</button>
          <button class="profile-actions__btn profile-actions__btn--danger" id="peercard-block">Block Peer</button>
        `;
      }

      // Determine avatar color and initials
      const { name, initials, color: avatarColor } = getPeerDisplayInfo(peer);

      const html = `
        <div class="profile-panel__header">
          <h2>Peer Identity</h2>
          <button class="profile-panel__close" id="peercard-close">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-x"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        <div class="profile-panel__body">
          <div>
            <div class="profile-avatar" style="background: ${avatarColor}">${initials}</div>
            <div class="profile-name">${name}</div>
            <div class="profile-status" style="color: ${statusColor}">${statusText}</div>
          </div>
          
          <div class="profile-section" style="display:flex; justify-content:center; padding-top: 8px; border-top: none;">
            ${trustHtml}
          </div>

          <div class="profile-section">
            <div class="profile-section__label">Network details</div>
            <div class="profile-row">
              <span class="profile-row__label">Hostname</span>
              <span class="profile-row__value">${peer.hostname || 'Unknown'}</span>
            </div>
            <div class="profile-row">
              <span class="profile-row__label">IP Address</span>
              <span class="profile-row__value">${peer.ip_address || 'Unknown'}</span>
            </div>
          </div>

          <div class="profile-section">
            <div class="profile-section__label">Fingerprint</div>
            <div class="profile-fingerprint">${peer.fingerprint}</div>
            <p style="font-size: 11px; color: var(--text-muted); margin-top: 8px; text-align: center;">Verify this fingerprint matches the peer's device.</p>
          </div>

          <div class="profile-actions" style="margin-top: auto;">
            ${actionHtml}
          </div>
        </div>
      `;

      container.innerHTML = html;
      container.classList.add('open');

      // Attach event listeners
      container.querySelector('#peercard-close')?.addEventListener('click', this.close);
      
      container.querySelector('#peercard-trust')?.addEventListener('click', () => {
        if (onTrust) onTrust(peer.fingerprint);
      });
      
      container.querySelector('#peercard-block')?.addEventListener('click', () => {
        if (onBlock) onBlock(peer.fingerprint);
      });
      
      container.querySelector('#peercard-unblock')?.addEventListener('click', () => {
        if (onUnblock) onUnblock(peer.fingerprint); // Internally unblocking sets them to 'untrusted'
      });
    },

    close() {
      container.classList.remove('open');
    },

    destroy() {
      container.innerHTML = '';
      container.classList.remove('open');
    }
  };
}
