export function createMessageBubble(message, isOwn) {
  const bubble = document.createElement('div');
  bubble.className = `message ${isOwn ? 'message--sent' : 'message--received'}`;

  const timestamp = new Date(message.timestamp * 1000).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  });

  bubble.innerHTML = `
    <div class="message__content">${escapeHtml(message.content)}</div>
    <div class="message__meta">
      <span class="message__time">${timestamp}</span>
      ${isOwn ? `<span class="message__status message__status--${message.status}">${getStatusIcon(message.status)}</span>` : ''}
    </div>
  `;

  return bubble;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function getStatusIcon(status) {
  switch (status) {
    case 'pending': return '⏳';
    case 'delivered': return '✓';
    case 'read': return '✓✓';
    case 'failed': return '✗';
    default: return '';
  }
}
