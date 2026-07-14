// TypingIndicator Component - Shows when a peer is typing
export function createTypingIndicator(container) {
  let isVisible = false;

  function show() {
    if (!isVisible) {
      container.innerHTML = `
        <div class="typing-indicator">
          <div class="typing-circle"></div>
          <div class="typing-circle"></div>
          <div class="typing-circle"></div>
          <div class="typing-shadow"></div>
          <div class="typing-shadow"></div>
          <div class="typing-shadow"></div>
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
