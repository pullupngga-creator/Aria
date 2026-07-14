import { messageStore } from '../stores/messageStore.js';
import { typingStore } from '../stores/typingStore.js';
import { createMessageBubble } from './MessageBubble.js';
import { getPeerDisplayInfoByFingerprint } from '../utils/peerUtils.js';
import { createTypingIndicator } from './TypingIndicator.js';

export function createChatView(container, fingerprint = null) {
  const chatView = document.createElement('div');
  chatView.className = 'chat-view';
  chatView.id = 'chat-view';

  // Chat Header
  const header = document.createElement('div');
  header.className = 'chat-view__header';
  header.id = 'chat-header';
  header.style.display = fingerprint ? 'flex' : 'none';

  if (fingerprint) {
    const peerInfo = getPeerDisplayInfoByFingerprint(fingerprint);
    header.innerHTML = `
      <div class="chat-view__header-avatar" id="chat-avatar" style="background:${peerInfo.color};">${peerInfo.initial}</div>
      <div class="chat-view__header-info">
        <div class="chat-view__header-name" id="chat-name">${peerInfo.displayName}</div>
        <div class="chat-view__header-status">● Online</div>
      </div>
      <div class="chat-view__header-actions">
        <button class="chat-view__header-btn" id="btn-profile">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          Profile
        </button>
        <button class="chat-view__header-btn" id="btn-call">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
          </svg>
          Call
        </button>
      </div>
    `;
  }

  // Transfer Progress (hidden by default)
  const transferProgress = document.createElement('div');
  transferProgress.className = 'transfer-progress';
  transferProgress.id = 'transfer-progress';
  transferProgress.style.display = 'none';
  transferProgress.innerHTML = `
    <div class="transfer-progress__info">
      <span class="transfer-progress__name" id="transfer-name">design-mockups.zip</span>
      <span class="transfer-progress__speed" id="transfer-speed">12.4 MB/s</span>
    </div>
    <div class="transfer-progress__bar">
      <div class="transfer-progress__fill" id="transfer-fill" style="width:0%"></div>
    </div>
  `;

  // Messages Container
  const messagesContainer = document.createElement('div');
  messagesContainer.className = 'chat-view__messages';
  messagesContainer.id = 'chat-messages';

  // Typing Indicator Container
  const typingIndicatorContainer = document.createElement('div');
  typingIndicatorContainer.className = 'chat-view__typing';
  typingIndicatorContainer.id = 'chat-typing';
  typingIndicatorContainer.style.display = 'none';
  const typingIndicator = createTypingIndicator(typingIndicatorContainer);

  // Empty State (shown when no conversation)
  const emptyState = document.createElement('div');
  emptyState.className = 'chat-view__empty animate-in';
  emptyState.id = 'chat-empty';
  emptyState.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
    <h3>No conversation selected</h3>
    <p>Pick a chat or search for peers on your network.</p>
  `;

  if (!fingerprint) {
    messagesContainer.appendChild(emptyState);
  }

  // Input Bar
  const inputBar = document.createElement('div');
  inputBar.className = 'input-bar';
  inputBar.id = 'input-bar';
  inputBar.style.display = fingerprint ? 'flex' : 'none';
  inputBar.innerHTML = `
    <button class="input-bar__btn" id="btn-attach" aria-label="Attach file">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
      </svg>
    </button>
    <div class="input-bar__field">
      <input type="text" id="chat-input" placeholder="Write messages..." aria-label="Type a message">
    </div>
    <button class="input-bar__btn" aria-label="Add emoji">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <path d="M8 14s1.5 2 4 2 4-2 4-2"></path>
        <line x1="9" y1="9" x2="9.01" y2="9"></line>
        <line x1="15" y1="9" x2="15.01" y2="9"></line>
      </svg>
    </button>
    <button class="input-bar__btn" id="btn-record" aria-label="Record voice">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" y1="19" x2="12" y2="22"></line>
      </svg>
    </button>
    <button class="input-bar__send input-bar__btn" id="btn-send" disabled aria-label="Send message">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" y1="2" x2="11" y2="13"></line>
        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
      </svg>
    </button>
  `;

  // Call Overlay (hidden by default)
  const callOverlay = document.createElement('div');
  callOverlay.className = 'call-overlay';
  callOverlay.id = 'call-overlay';
  callOverlay.style.display = 'none';
  callOverlay.innerHTML = `
    <div class="call-overlay__peer">
      <div class="call-overlay__avatar" id="call-avatar" style="background:#34C759;">M</div>
      <div class="call-overlay__name" id="call-name">Marcus Chen</div>
      <div class="call-overlay__status" id="call-status">
        <span class="dot is-dialing"></span>
        <span id="call-status-text">Calling...</span>
      </div>
    </div>
    <div class="call-overlay__timer" id="call-timer" style="display:none;">00:00</div>
    <div class="call-overlay__controls">
      <button class="call-overlay__btn call-overlay__btn--mute" id="call-mute" aria-label="Mute">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
          <line x1="19" y1="10" x2="19" y2="12a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="22" />
        </svg>
      </button>
      <button class="call-overlay__btn call-overlay__btn--end" id="call-end" aria-label="End call">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
        </svg>
      </button>
    </div>
  `;

  chatView.appendChild(header);
  chatView.appendChild(transferProgress);
  chatView.appendChild(messagesContainer);
  chatView.appendChild(typingIndicatorContainer);
  chatView.appendChild(inputBar);
  chatView.appendChild(callOverlay);

  container.appendChild(chatView);

  // Scroll anchoring state
  let isUserScrolling = false;
  let lastScrollTop = 0;

  messagesContainer.addEventListener('scroll', () => {
    const currentScrollTop = messagesContainer.scrollTop;
    const scrollHeight = messagesContainer.scrollHeight;
    const clientHeight = messagesContainer.clientHeight;

    // Check if user is scrolling up (reading history)
    isUserScrolling = currentScrollTop < lastScrollTop && currentScrollTop < scrollHeight - clientHeight - 50;
    lastScrollTop = currentScrollTop;
  });

  // Load and render messages if fingerprint provided
  if (fingerprint) {
    loadMessages(fingerprint, messagesContainer);

    const unsubscribe = messageStore.subscribe(() => {
      renderMessages(fingerprint, messagesContainer, isUserScrolling);
    });

    // Subscribe to typing state for this peer
    const typingUnsubscribe = typingStore.subscribe((typingStates) => {
      const isTyping = typingStore.isPeerTyping(fingerprint);
      if (isTyping) {
        typingIndicatorContainer.style.display = 'flex';
        typingIndicator.show();
        // Auto-scroll to bottom to show typing indicator
        if (!isUserScrolling) {
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
      } else {
        typingIndicatorContainer.style.display = 'none';
        typingIndicator.hide();
      }
    });

    // Input handling
    const input = inputBar.querySelector('#chat-input');
    const sendBtn = inputBar.querySelector('#btn-send');

    // Typing detection
    let typingTimer = null;
    let isTyping = false;

    const handleTyping = () => {
      if (!isTyping && input.value.trim()) {
        isTyping = true;
        window.typingService?.sendTyping(fingerprint, true);
      }
      
      clearTimeout(typingTimer);
      typingTimer = setTimeout(() => {
        isTyping = false;
        window.typingService?.sendTyping(fingerprint, false);
      }, 2000);
    };

    input.addEventListener('input', () => {
      sendBtn.disabled = !input.value.trim();
      handleTyping();
    });

    const handleSend = async () => {
      const content = input.value.trim();
      if (!content) return;

      // Clear typing state when sending message
      isTyping = false;
      clearTimeout(typingTimer);
      window.typingService?.sendTyping(fingerprint, false);

      input.value = '';
      input.disabled = true;
      sendBtn.disabled = true;

      try {
        await window.messageService.sendMessage(fingerprint, content);
      } catch (err) {
        console.error('Failed to send:', err);
        input.value = content; // Restore on error
      } finally {
        input.disabled = false;
        sendBtn.disabled = !input.value.trim();
        input.focus();
      }
    };

    sendBtn.addEventListener('click', handleSend);
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleSend();
    });

    return {
      destroy: () => {
        unsubscribe();
        typingUnsubscribe();
        chatView.remove();
      },
      setFingerprint: (newFingerprint) => {
        // Update for new peer
      }
    };
  }

  return {
    destroy: () => {
      chatView.remove();
    },
    setFingerprint: (newFingerprint) => {
      // Update for new peer
    }
  };
}

function loadMessages(fingerprint, container) {
  window.messageService.loadMessages(fingerprint);
  renderMessages(fingerprint, container, false);
}

function renderMessages(fingerprint, container, isUserScrolling) {
  const messages = messageStore.getMessages(fingerprint);

  // Clear existing messages (except empty state)
  const emptyState = container.querySelector('.chat-view__empty');
  container.innerHTML = '';
  if (emptyState && messages.length === 0) {
    container.appendChild(emptyState);
    return;
  }

  messages.forEach(msg => {
    const isOwn = msg.direction === 'sent';
    const bubble = createMessageBubble(msg, isOwn);
    container.appendChild(bubble);
  });

  // Auto-scroll to bottom unless user is reading history
  if (!isUserScrolling) {
    container.scrollTop = container.scrollHeight;
  }
}
