// Thread Store - Manages conversation metadata
// Stores thread data including last message preview, unread counts, and activity timestamps

class ThreadStore {
  constructor() {
    this.threads = new Map(); // Map<peerFingerprint, Thread>
    this.subscribers = new Set();
    this.activeThreadId = null;
  }

  // Get thread by peer ID
  getThread(id) {
    return this.threads.get(id);
  }

  // Get all threads sorted by last activity (descending)
  getAllThreads() {
    return Array.from(this.threads.values()).sort((a, b) => {
      // Primary sort: last activity (most recent first)
      if (b.lastActivity !== a.lastActivity) {
        return b.lastActivity - a.lastActivity;
      }
      // Secondary sort: unread count (most unread first)
      return b.unreadCount - a.unreadCount;
    });
  }

  // Create or update a thread
  updateThread(id, updates) {
    const existing = this.threads.get(id);
    const thread = existing || {
      id,
      peer: null,
      lastMessage: null,
      unreadCount: 0,
      lastActivity: Date.now()
    };

    Object.assign(thread, updates);
    thread.lastActivity = Date.now();
    
    this.threads.set(id, thread);
    this.notify();
  }

  // Set peer data for a thread
  setPeer(id, peer) {
    const thread = this.threads.get(id);
    if (thread) {
      thread.peer = peer;
      this.notify();
    }
  }

  // Update last message preview
  updateLastMessage(id, content, timestamp, isOutgoing) {
    const thread = this.threads.get(id);
    if (thread) {
      thread.lastMessage = {
        content,
        timestamp,
        isOutgoing
      };
      thread.lastActivity = timestamp || Date.now();
      this.notify();
    }
  }

  // Increment unread count
  incrementUnread(id) {
    const thread = this.threads.get(id);
    if (thread && id !== this.activeThreadId) {
      thread.unreadCount++;
      this.notify();
    }
  }

  // Mark thread as read (clear unread count)
  markAsRead(id) {
    const thread = this.threads.get(id);
    if (thread) {
      thread.unreadCount = 0;
      this.notify();
    }
  }

  // Set active thread
  setActiveThread(id) {
    const previousActive = this.activeThreadId;
    this.activeThreadId = id;
    
    // Mark new active thread as read
    if (id) {
      this.markAsRead(id);
    }
    
    // Notify even if same thread (for UI updates)
    this.notify();
  }

  // Remove thread
  removeThread(id) {
    this.threads.delete(id);
    if (this.activeThreadId === id) {
      this.activeThreadId = null;
    }
    this.notify();
  }

  // Subscribe to thread updates
  subscribe(callback) {
    this.subscribers.add(callback);
    // Immediately call with current state
    callback(this.getAllThreads(), this.activeThreadId);
    
    // Return unsubscribe function
    return () => {
      this.subscribers.delete(callback);
    };
  }

  // Notify all subscribers
  notify() {
    const threads = this.getAllThreads();
    this.subscribers.forEach(callback => {
      try {
        callback(threads, this.activeThreadId);
      } catch (error) {
        console.error('[ThreadStore] Subscriber error:', error);
      }
    });
  }
}

// Singleton instance
export const threadStore = new ThreadStore();
