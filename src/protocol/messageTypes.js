/**
 * Message type constants matching the Rust MessageType enum.
 * Used for type safety and consistency across frontend code.
 */
export const MessageType = {
  HANDSHAKE: 'handshake',
  MESSAGE: 'message',
  FILE_OFFER: 'file_offer',
  FILE_CHUNK: 'file_chunk',
  FILE_COMPLETE: 'file_complete',
  VOICE: 'voice',
  HEARTBEAT: 'heartbeat',
  TYPING: 'typing',
};

/**
 * Check if a string is a valid message type.
 * @param {string} type
 * @returns {boolean}
 */
export function isValidMessageType(type) {
  return Object.values(MessageType).includes(type);
}
