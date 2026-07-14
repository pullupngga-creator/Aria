// Typing Store - Manages typing indicator state for peers
class TypingStore {
  constructor() {
    this.typingStates = new Map(); // Map<peerFingerprint, { isTyping, lastSeen }>
    this.subscribers = new Set();
    this.cleanupInterval = null;
    
    // Start cleanup interval to expire old typing states
    this.startCleanup();
  }

  // Set typing state for a peer
  setTyping(peerId, isTyping) {
    this.typingStates.set(peerId, {
      isTyping,
      lastSeen: Date.now()
    });
    this.notify();
  }

  // Check if a peer is currently typing
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

  // Get all typing states
  getAllTypingStates() {
    return new Map(this.typingStates);
  }

  // Subscribe to typing state changes
  subscribe(callback) {
    this.subscribers.add(callback);
    // Immediately call with current state
    callback(this.getAllTypingStates());
    
    // Return unsubscribe function
    return () => {
      this.subscribers.delete(callback);
    };
  }

  // Notify all subscribers
  notify() {
    const states = this.getAllTypingStates();
    this.subscribers.forEach(callback => {
      try {
        callback(states);
      } catch (error) {
        console.error('[TypingStore] Subscriber error:', error);
      }
    });
  }

  // Start cleanup interval to expire old typing states
  startCleanup() {
    this.cleanupInterval = setInterval(() => {
      let changed = false;
      const now = Date.now();
      
      this.typingStates.forEach((state, peerId) => {
        if (now - state.lastSeen > 3000) {
          this.typingStates.delete(peerId);
          changed = true;
        }
      });
      
      if (changed) {
        this.notify();
      }
    }, 1000); // Check every second
  }

  // Stop cleanup interval
  stopCleanup() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }

  // Clear all typing states
  clear() {
    this.typingStates.clear();
    this.notify();
  }
}

// Singleton instance
export const typingStore = new TypingStore();
