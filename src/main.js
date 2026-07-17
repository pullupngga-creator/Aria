import './styles/main.css';
import './styles/chat.css';
import { commands } from './bindings.js';
import { peerStore } from './stores/peerStore.js';
import { threadStore } from './stores/threadStore.js';
import { peerService } from './services/peerService.js';
import { connectionService } from './services/connectionService.js';
import { handshakeService } from './services/handshakeService.js';
import { messageService } from './services/messageService.js';
import { typingService } from './services/typingService.js';
import { createPeerCard } from './components/PeerCard.js';
import { createDiscoverModal } from './components/DiscoverModal.js';
import { createChatView } from './components/ChatView.js';
import { createThreadList } from './components/ThreadList.js';
import { getPeerDisplayInfo } from './utils/peerUtils.js';

const state = { activeId: null, currentChatView: null };

document.addEventListener('DOMContentLoaded', async () => {
  const loadingScreen = document.getElementById('loading-screen');
  const app = document.querySelector('.app');
  
  // Hide loading screen and show app after initialization
  const hideLoadingScreen = () => {
    if (loadingScreen) {
      loadingScreen.classList.add('hidden');
      loadingScreen.addEventListener('transitionend', () => {
        loadingScreen.style.display = 'none';
      }, { once: true });
    }
    if (app) {
      app.style.opacity = '1';
    }
  };

  const sectionsEl = document.getElementById('thread-sections');
  const chatContainer = document.getElementById('chat-container');
  
  // Initialize ThreadList component
  let threadList = null;
  if (sectionsEl) {
    threadList = createThreadList(sectionsEl);
    threadList.setOnThreadClick((peerId) => {
      state.activeId = peerId;
      threadStore.setActiveThread(peerId);
      
      const peer = peerStore.get(peerId);
      if (peer) {
        // Destroy existing chat view and create new one with selected peer
        if (state.currentChatView) {
          state.currentChatView.destroy();
        }
        
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
          state.currentChatView = createChatView(chatContainer, peerId);
        }

        if (peerCard) peerCard.show(peer);

        // Initiate TCP connection to peer (non-blocking)
        connectionService.connectToPeer(peerId).catch(err => {
          console.warn('[Connection] Could not connect to peer:', err);
        });
      }
    });
  }
  
  // Initialize chat view with no peer (shows empty state)
  if (chatContainer) {
    state.currentChatView = createChatView(chatContainer, null);
  }
  
  let peerCard = null;
  const profilePanel = document.querySelector('.profile-panel');
  if (profilePanel) {
      peerCard = createPeerCard(profilePanel, {
          onTrust: async (fp) => await peerService.trust(fp),
          onBlock: async (fp) => await peerService.block(fp),
          onUnblock: async (fp) => await peerService.unblock(fp)
      });
  }

  const discoverModal = createDiscoverModal({
    onSelectPeer: (fingerprint) => {
      state.activeId = fingerprint;
      threadStore.setActiveThread(fingerprint);
      
      const peer = peerStore.get(fingerprint);
      if (peer) {
        // Destroy existing chat view and create new one with selected peer
        if (state.currentChatView) {
          state.currentChatView.destroy();
        }
        
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
          state.currentChatView = createChatView(chatContainer, fingerprint);
        }

        if (peerCard) peerCard.show(peer);

        // Initiate TCP connection to peer (non-blocking)
        connectionService.connectToPeer(fingerprint).catch(err => {
          console.warn('[Connection] Could not connect to peer:', err);
        });
      }
    }
  });

  // Subscribe to threadStore updates and render ThreadList
  threadStore.subscribe((threads, activeId) => {
    if (threadList) {
      threadList.updateThreads(threads, activeId);
    }
  });

  // Subscribe to peerStore to create/update threads
  peerStore.subscribe((peers) => {
    peers.forEach(peer => {
      const existingThread = threadStore.getThread(peer.fingerprint);
      if (existingThread) {
        // Update peer data in existing thread
        threadStore.setPeer(peer.fingerprint, peer);
      } else {
        // Create new thread for peer
        threadStore.updateThread(peer.fingerprint, {
          peer: peer,
          lastMessage: null,
          unreadCount: 0,
          lastActivity: peer.last_seen || Date.now()
        });
      }
    });
  });
  
  // Initialize peer service before starting discovery so no discovery events
  // are emitted before the frontend has subscribed to them.
  try {
    await peerService.init();
  } catch (err) {
    console.error('[PeerService] Failed to initialize:', err);
  }

  // Initialize connection service
  connectionService.init();

  // Initialize handshake service
  handshakeService.init();

  // Initialize message service
  messageService.init();

  // Initialize typing service
  typingService.init();

  // Expose globally for ChatView
  window.messageService = messageService;
  window.typingService = typingService;

  // Start discovery after all frontend listeners are ready. The backend only
  // starts the TCP server during setup; discovery is owned by the webview so
  // its first peer events cannot be lost during startup.
  try {
    const discoveryResult = await commands.startDiscovery();
    if (discoveryResult.status === 'error') {
      console.error('[Discovery] Failed to start:', discoveryResult.error);
    }
  } catch (err) {
    console.error('[Discovery] Failed to start:', err);
  }

  // Theme Toggle
  const themeToggle = document.getElementById('theme-toggle');
  themeToggle?.addEventListener('click', () => {
    const html = document.documentElement;
    if (html.getAttribute('data-theme') === 'dark') {
      html.removeAttribute('data-theme');
      localStorage.setItem('theme', 'light');
    } else {
      html.setAttribute('data-theme', 'dark');
      localStorage.setItem('theme', 'dark');
    }
  });

  // Load saved theme
  if (localStorage.getItem('theme') === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  }

  // Load Identity for the Profile Button using Specta bindings
  async function loadIdentity() {
    try {
      const identity = await commands.getMyIdentity();
      // Use fingerprint or default ME
      const meBtn = document.querySelector('.sidebar__profile');
      if(meBtn) {
        meBtn.textContent = 'ME'; 
        meBtn.title = identity.fingerprint;
        
        // Self-identity modal logic
        const selfModal = document.querySelector('.self-modal');
        const modalBackdrop = document.querySelector('.modal-backdrop');
        
        if (selfModal && modalBackdrop) {
            meBtn.addEventListener('click', () => {
                // Populate modal
                const fpEl = selfModal.querySelector('.profile-fingerprint');
                if (fpEl) fpEl.textContent = identity.fingerprint;
                
                // Show modal
                selfModal.classList.add('open');
                modalBackdrop.classList.add('open');
            });
            
            const closeModal = () => {
                selfModal.classList.remove('open');
                modalBackdrop.classList.remove('open');
            };
            
            const closeBtn = selfModal.querySelector('.self-modal__close');
            if (closeBtn) closeBtn.addEventListener('click', closeModal);
            modalBackdrop.addEventListener('click', closeModal);
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') closeModal();
            });
        }
      }
    } catch (e) {
      console.error('Failed to load identity', e);
    }
  }
  loadIdentity();

  // Show Discover Peers Modal
  const addBtn = document.querySelector('.thread-list__add');
  if (addBtn) {
    addBtn.addEventListener('click', () => {
      commands.startDiscovery().catch(() => {}); // Auto-start background discovery silently
      discoverModal.open(state.activeId);
    });
  }

  // Basic Chat switching logic
  if(sectionsEl) {
    sectionsEl.addEventListener('click', (e) => {
      const item = e.target.closest('.thread-item');
      if (item) {
        // Update active class
        document.querySelectorAll('.thread-item.active').forEach(el => el.classList.remove('active'));
        item.classList.add('active');
        state.activeId = item.dataset.id;

        // Show chat view headers
        document.getElementById('chat-empty').style.display = 'none';
        document.getElementById('chat-header').style.display = 'flex';
        document.getElementById('input-bar').style.display = 'flex';

        const peer = peerStore.get(state.activeId);
        if(peer) {
          const { name, initials, color } = getPeerDisplayInfo(peer);

          document.getElementById('chat-name').textContent = name;
          const av = document.getElementById('chat-avatar');
          if (av) {
            av.textContent = initials;
            av.style.background = color;
          }

          // Show PeerCard
          if (peerCard) {
              peerCard.show(peer);
          }

          // Initiate TCP connection to peer (non-blocking)
          connectionService.connectToPeer(state.activeId).catch(err => {
            console.warn('[Connection] Could not connect to peer:', err);
          });
        }
      }
    });
  }

  // Hide loading screen after all initialization is complete
  setTimeout(hideLoadingScreen, 100);
});
