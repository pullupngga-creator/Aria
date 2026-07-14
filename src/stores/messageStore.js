/**
 * Message store - manages message history per peer
 */
class MessageStore {
  constructor() {
    this.messages = new Map(); // fingerprint -> array of messages
    this.listeners = new Set();
  }

  getMessages(fingerprint) {
    return this.messages.get(fingerprint) || [];
  }

  setMessages(fingerprint, messages) {
    this.messages.set(fingerprint, messages);
    this.notify();
  }

  addMessage(fingerprint, message) {
    if (!this.messages.has(fingerprint)) {
      this.messages.set(fingerprint, []);
    }
    this.messages.get(fingerprint).push(message);
    this.notify();
  }

  updateMessageStatus(fingerprint, messageId, status) {
    const msgs = this.messages.get(fingerprint);
    if (msgs) {
      const msg = msgs.find(m => m.message_id === messageId);
      if (msg) {
        msg.status = status;
        this.notify();
      }
    }
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notify() {
    this.listeners.forEach(listener => listener(this.messages));
  }
}

export const messageStore = new MessageStore();
