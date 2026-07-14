import { peerStore } from '../stores/peerStore.js';
import { commands } from '../bindings.js';
import { getPeerDisplayInfo } from '../utils/peerUtils.js';

/**
 * DiscoverModal — "Discover Peers" modal opened by the + button.
 * Renders all known peers from peerStore with live search filtering
 * and a manual refresh button that triggers mDNS re-scan.
 *
 * @param {object} options
 * @param {function(string): void} options.onSelectPeer  — called with fingerprint when user clicks "Start Chat"
 */
export function createDiscoverModal(options) {
  const { onSelectPeer } = options;

  const backdrop  = document.getElementById('person-backdrop');
  const modal     = document.getElementById('person-modal');
  const closeBtn  = document.getElementById('person-modal-close');
  const searchInput = document.getElementById('person-search');
  const refreshBtn  = document.getElementById('person-refresh');
  const listEl      = document.getElementById('person-list');

  let _query = '';
  let _unsubscribe = null;
  let _currentPeers = [];
  let _activeId = null;

  function _renderPeerRow(peer, activeId) {
    const { name, initials, color } = getPeerDisplayInfo(peer);
    
    const statusClass = peer.is_online ? 'online' : 'offline';
    const hostLine = peer.ip_address ? `${peer.ip_address}:${peer.port}` : (peer.hostname || 'Unknown Host');
    
    let actionBtnHtml;
    if (activeId === peer.fingerprint) {
      actionBtnHtml = `<button class="person-modal__peer-action connected" disabled>Chatting</button>`;
    } else {
      actionBtnHtml = `<button class="person-modal__peer-action connect" data-fp="${peer.fingerprint}">Start Chat</button>`;
    }

    return `
      <div class="person-modal__peer">
        <div class="person-modal__peer-avatar" style="background: ${color}">
          ${initials}
          <span class="status-dot ${statusClass}"></span>
        </div>
        <div class="person-modal__peer-body">
          <div class="person-modal__peer-name">${name}</div>
          <div class="person-modal__peer-host">${hostLine}</div>
        </div>
        ${actionBtnHtml}
      </div>
    `;
  }

  function _renderList(peers, activeId) {
    const filtered = peers.filter(p => {
      const haystack = [
        p.display_name, p.hostname, p.ip_address, p.fingerprint
      ].filter(Boolean).join(' ').toLowerCase();
      return haystack.includes(_query);
    });

    if (filtered.length === 0) {
      listEl.innerHTML = `
        <div class="person-modal__empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 2l20 20"></path><path d="M8.53 8.53A10.96 10.96 0 0112 8c2.69 0 5.14.96 7.07 2.56L23 6.64A14.93 14.93 0 0012 4c-1.8 0-3.52.3-5.1.86"></path><path d="M12 12c1.78 0 3.4.63 4.67 1.67l3.92-3.92A10.95 10.95 0 0012 8c-.68 0-1.34.06-2 .18"></path><path d="M12 16a4 4 0 012.38.79l2.81-2.81A7.95 7.95 0 0012 12c-.52 0-1.02.05-1.5.14"></path><path d="M12 20c.34 0 .67-.04 1-.1l2.5 2.5a14.88 14.88 0 01-3.5.6c-4.14 0-7.9-1.68-10.6-4.4L5.3 14.7c1.73 1.73 4.12 2.8 6.7 2.8z"></path></svg>
          <div>${_query ? "No peers match your search." : "No peers found on this network.<br>Make sure you're on the same Wi-Fi."}</div>
        </div>`;
      return;
    }

    listEl.innerHTML = filtered.map(p => _renderPeerRow(p, activeId)).join('');

    // Attach click handlers via event delegation
    listEl.addEventListener('click', _handleListClick, { once: true });
  }

  function _handleListClick(e) {
    const btn = e.target.closest('.person-modal__peer-action.connect');
    if (btn) {
      const fp = btn.dataset.fp;
      close();
      if (onSelectPeer) onSelectPeer(fp);
    } else {
        // Re-attach if they clicked elsewhere
        listEl.addEventListener('click', _handleListClick, { once: true });
    }
  }

  function open(currentActiveId) {
    _activeId = currentActiveId;
    
    // 1. Subscribe to peerStore for live updates
    _unsubscribe = peerStore.subscribe(peers => {
      _currentPeers = peers;
      _renderList(peers, _activeId);
    });

    // 2. Reset search
    if (searchInput) {
        searchInput.value = '';
    }
    _query = '';

    // 3. Show modal
    if (modal && backdrop) {
        modal.classList.add('open');
        backdrop.classList.add('open');
        if (searchInput) {
            setTimeout(() => searchInput.focus(), 50); // slight delay to focus after transition
        }
    }
  }

  function close() {
    if (modal && backdrop) {
        modal.classList.remove('open');
        backdrop.classList.remove('open');
    }
    if (_unsubscribe) { _unsubscribe(); _unsubscribe = null; }
    if (listEl) {
        listEl.innerHTML = '';
        listEl.removeEventListener('click', _handleListClick);
    }
  }

  // ── Event Listeners ──────────────────────────────

  if (closeBtn) closeBtn.addEventListener('click', close);
  if (backdrop) backdrop.addEventListener('click', close);
  
  document.addEventListener('keydown', e => { 
      if (e.key === 'Escape' && modal && modal.classList.contains('open')) close(); 
  });

  let _debounceTimer = null;
  if (searchInput) {
      searchInput.addEventListener('input', () => {
        clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(() => {
          _query = searchInput.value.trim().toLowerCase();
          _renderList(_currentPeers, _activeId); // re-filter
        }, 150);
      });
  }

  if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        refreshBtn.classList.add('is-loading');
        try {
          await commands.startDiscovery();
        } finally {
          setTimeout(() => refreshBtn.classList.remove('is-loading'), 2000);
        }
      });
  }

  // ── Manual Connect ──────────────────────────────
  let _manualExpanded = false;
  const _manualContainer = document.createElement('div');
  _manualContainer.style.cssText = 'padding: 8px 22px 16px; border-top: 1px solid var(--border); flex-shrink: 0;';
  _manualContainer.innerHTML = `
    <button id="manual-toggle" style="width:100%;padding:8px;border:none;border-radius:var(--radius);background:transparent;color:var(--text-secondary);font:510 12px/1 var(--font);cursor:pointer;transition:all 0.12s;">
      + Connect Manually
    </button>
    <div id="manual-form" style="display:none;margin-top:8px;">
      <div style="display:flex;gap:8px;margin-bottom:8px;">
        <input type="text" id="manual-ip" placeholder="IP address" style="flex:1;height:36px;padding:0 12px;border:1px solid var(--border);border-radius:20px;background:var(--bg);color:var(--text-primary);font:400 13px/1 var(--font);outline:none;">
        <input type="number" id="manual-port" value="9473" style="width:80px;height:36px;padding:0 10px;border:1px solid var(--border);border-radius:20px;background:var(--bg);color:var(--text-primary);font:400 13px/1 var(--font);outline:none;text-align:center;">
      </div>
      <button id="manual-connect-btn" style="width:100%;height:36px;border:none;border-radius:20px;background:var(--accent);color:#fff;font:510 13px/1 var(--font);cursor:pointer;transition:background 0.12s;">
        Connect
      </button>
      <div id="manual-status" style="font-size:11px;color:var(--text-muted);margin-top:6px;text-align:center;"></div>
    </div>
  `;
  modal.appendChild(_manualContainer);

  const manualToggle = _manualContainer.querySelector('#manual-toggle');
  const manualForm = _manualContainer.querySelector('#manual-form');
  const manualIp = _manualContainer.querySelector('#manual-ip');
  const manualPort = _manualContainer.querySelector('#manual-port');
  const manualConnectBtn = _manualContainer.querySelector('#manual-connect-btn');
  const manualStatus = _manualContainer.querySelector('#manual-status');

  manualToggle.addEventListener('click', () => {
    _manualExpanded = !_manualExpanded;
    manualForm.style.display = _manualExpanded ? 'block' : 'none';
    manualToggle.textContent = _manualExpanded ? '− Hide Manual Connect' : '+ Connect Manually';
    if (_manualExpanded) setTimeout(() => manualIp.focus(), 50);
  });

  manualConnectBtn.addEventListener('click', async () => {
    const ip = manualIp.value.trim();
    const port = parseInt(manualPort.value, 10) || 9473;
    if (!ip) {
      manualStatus.textContent = 'Please enter an IP address.';
      return;
    }
    manualStatus.textContent = 'Connecting...';
    manualConnectBtn.disabled = true;
    manualConnectBtn.style.opacity = '0.5';
    try {
      const result = await commands.connectManual(ip, port);
      if (result.status === 'ok') {
        manualStatus.textContent = 'Connected!';
        setTimeout(() => {
          close();
          if (onSelectPeer) onSelectPeer(result.data.fingerprint);
        }, 500);
      } else {
        manualStatus.textContent = result.error || 'Connection failed.';
      }
    } catch (e) {
      manualStatus.textContent = 'Connection failed: ' + (e.message || e);
    } finally {
      manualConnectBtn.disabled = false;
      manualConnectBtn.style.opacity = '1';
    }
  });

  // Allow Enter key in IP field
  manualIp.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') manualConnectBtn.click();
  });
  manualPort.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') manualConnectBtn.click();
  });

  return {
    open,
    close,
    destroy() {
      close();
      if (closeBtn) closeBtn.removeEventListener('click', close);
      if (backdrop) backdrop.removeEventListener('click', close);
      if (listEl) listEl.innerHTML = '';
      if (_manualContainer.parentNode) _manualContainer.parentNode.removeChild(_manualContainer);
    }
  };
}
