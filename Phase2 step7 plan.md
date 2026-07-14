# Phase 2 Step 7: Typing Indicators Implementation Plan

## Objective
Implement real-time typing indicators that show when a peer is composing a message, using heartbeat packets and animated UI feedback.

## Current State
- Wire protocol exists with message types (message, receipt)
- Connection manager handles peer connections
- ChatView displays messages
- ThreadList shows conversation previews
- No typing indicator functionality exists

## Implementation Plan

### 1. Protocol Design
**File**: `src-tauri/src/protocol/message.rs`

Add new message type for typing indicators:
```rust
pub enum MessageType {
    Message,
    Receipt,
    Typing, // New type
}

pub struct TypingPayload {
    pub is_typing: bool,
    pub timestamp: i32,
}
```

Protocol envelope structure:
- Type: "typing"
- Payload: `{ is_typing: boolean, timestamp: number }`
- Signature: Optional (typing indicators may not need signing for MVP)

### 2. Rust Backend Implementation
**File**: `src-tauri/src/protocol/message.rs`

Add typing message serialization:
- `TypingPayload` struct with `Serialize`/`Deserialize`
- Constructor for typing messages
- Deserialization from envelope

**File**: `src-tauri/src/commands/typing.rs` (new file)

Create Tauri commands for typing:
- `send_typing(fingerprint: String, is_typing: bool)` - Send typing state to peer
- Handle sending via existing connection manager
- Emit Tauri event: `typing:received` when typing indicator received

**File**: `src-tauri/src/protocol/mod.rs`

Register typing message type in protocol handler:
- Add typing message to message router
- Forward typing events to frontend via Tauri events

### 3. Frontend State Management
**File**: `src/stores/typingStore.js` (new file)

Create typing state store:
```javascript
class TypingStore {
  constructor() {
    this.typingStates = new Map(); // Map<peerFingerprint, { isTyping, lastSeen }>
    this.subscribers = new Set();
  }

  setTyping(peerId, isTyping) {
    this.typingStates.set(peerId, {
      isTyping,
      lastSeen: Date.now()
    });
    this.notify();
  }

  isPeerTyping(peerId) {
    const state = this.typingStates.get(peerId);
    if (!state) return false;
    
    // Auto-clear after 3 seconds of no updates
    if (Date.now() - state.lastSeen > 3000) {
      this.typingStates.delete(peerId);
      this.notify();
      return false;
    }
    
    return state.isTyping;
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notify() {
    this.subscribers.forEach(cb => cb(this.typingStates));
  }
}
```

### 4. TypingIndicator UI Component
**File**: `src/components/TypingIndicator.js` (new file)

Create typing indicator component:
```javascript
export function createTypingIndicator(container) {
  let isVisible = false;

  function show() {
    if (!isVisible) {
      container.innerHTML = `
        <div class="typing-indicator">
          <div class="typing-indicator__dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span class="typing-indicator__text">typing...</span>
        </div>
      `;
      isVisible = true;
    }
  }

  function hide() {
    if (isVisible) {
      container.innerHTML = '';
      isVisible = false;
    }
  }

  return { show, hide };
}
```

### 5. Input Integration
**File**: `src/components/ChatView.js` (enhancement)

Add typing detection to message input:
- Detect when user starts typing (input event)
- Send typing heartbeat every 2 seconds while typing
- Send "not typing" when message is sent or user stops typing
- Debounce typing detection to avoid spam

```javascript
let typingTimer = null;
let isTyping = false;

function handleTyping() {
  if (!isTyping) {
    isTyping = true;
    commands.sendTyping(peerId, true);
  }
  
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => {
    isTyping = false;
    commands.sendTyping(peerId, false);
  }, 2000);
}

input.addEventListener('input', handleTyping);
```

### 6. Typing Event Handling
**File**: `src/services/typingService.js` (new file)

Create typing service to handle Tauri events:
```javascript
import { listen } from '@tauri-apps/api/event';
import { typingStore } from '../stores/typingStore.js';

export const typingService = {
  async init() {
    await listen('typing:received', (event) => {
      const { fingerprint, is_typing } = event.payload;
      typingStore.setTyping(fingerprint, is_typing);
    });
  },

  async sendTyping(fingerprint, isTyping) {
    await commands.sendTyping(fingerprint, isTyping);
  },

  destroy() {
    // Cleanup listeners
  }
};
```

### 7. ChatView Integration
**File**: `src/components/ChatView.js`

Integrate typing indicator into ChatView:
- Add typing indicator container above message list
- Subscribe to typingStore updates
- Show/hide indicator based on peer typing state
- Position indicator at bottom of message list

### 8. Styling & Animation
**File**: `src/styles/typing.css` (new file)

Create typing indicator animations:
```css
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  color: var(--text-muted);
  font-size: 13px;
}

.typing-indicator__dots {
  display: flex;
  gap: 4px;
}

.typing-indicator__dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: typing-bounce 1.4s infinite ease-in-out;
}

.typing-indicator__dots span:nth-child(1) {
  animation-delay: 0s;
}

.typing-indicator__dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator__dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing-bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-4px);
  }
}
```

### 9. Main.js Integration
**File**: `src/main.js`

Wire up typing service:
- Import typingService
- Initialize typing service on app load
- Pass typing service to ChatView components

### 10. Testing Checklist
- [ ] Typing indicator shows when peer starts typing
- [ ] Typing indicator hides after peer stops typing (3s timeout)
- [ ] Typing indicator hides when peer sends message
- [ ] Typing heartbeat sends every 2 seconds while typing
- [ ] Multiple peers can have typing states simultaneously
- [ ] Typing indicator animation is smooth
- [ ] Typing indicator respects theme variables
- [ ] No typing indicator shown for non-active conversations
- [ ] Typing state clears when peer disconnects

## Dependencies
- Existing wire protocol infrastructure
- Connection manager (for sending typing messages)
- Tauri event system (for receiving typing events)
- ChatView component (for displaying indicator)

## Success Criteria
- Typing indicator appears when peer is typing
- Indicator animates smoothly with bouncing dots
- Indicator auto-hides after typing stops
- Typing state syncs between peers in real-time
- No performance impact from typing heartbeats
- Theme support throughout

## Edge Cases to Handle
- Peer disconnects while typing - clear state
- Rapid typing start/stop - debounce appropriately
- Multiple peers typing simultaneously - show for active conversation only
- Network latency - indicator may show briefly after peer stops
- Message sent while typing - clear typing state immediately

## Performance Considerations
- Typing heartbeats should be rate-limited (max 1 per 2 seconds)
- Typing state should auto-expire to prevent memory leaks
- Animation should use CSS transforms (GPU-accelerated)
- Avoid excessive DOM updates (only show/hide when state changes)

## Estimated Time
- Protocol design & Rust backend: 3 hours
- Frontend state & service: 2 hours
- UI component & integration: 2 hours
- Styling & animation: 1 hour
- Testing & refinement: 2 hours
- **Total: ~10 hours**
