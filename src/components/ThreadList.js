// ThreadList Component - Renders conversation list with last message previews
import { getPeerDisplayInfo } from '../utils/peerUtils.js';

export function createThreadList(container) {
  const threadElements = new Map(); // Map<peerId, HTMLElement>
  let onThreadClick = null;

  // Format timestamp for display
  function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'now';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    if (diffDays < 7) return `${diffDays}d`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  // Truncate message preview
  function truncatePreview(text, maxLength = 35) {
    if (!text) return 'No messages yet';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }

  // Create thread item element
  function createThreadItem(thread) {
    const { peer, lastMessage, unreadCount } = thread;
    const { name, initials, color } = getPeerDisplayInfo(peer);
    const timeStr = formatTime(lastMessage?.timestamp);
    const previewText = truncatePreview(lastMessage?.content);

    const item = document.createElement('div');
    item.className = 'thread-item';
    item.dataset.id = thread.id;

    item.innerHTML = `
      <div class="thread-item__avatar" style="background: ${color}">
        <span>${initials}</span>
        ${peer.is_online ? '<div class="status-ring"></div>' : ''}
      </div>
      <div class="thread-item__body">
        <div class="thread-item__top">
          <span class="thread-item__name">${name}</span>
          <span class="thread-item__time">${timeStr}</span>
        </div>
        <div class="thread-item__preview">${previewText}</div>
      </div>
      ${unreadCount > 0 ? `
        <div class="thread-item__meta">
          <div class="thread-item__unread">${unreadCount}</div>
        </div>
      ` : ''}
    `;

    // Click handler
    item.addEventListener('click', () => {
      if (onThreadClick) {
        onThreadClick(thread.id);
      }
    });

    return item;
  }

  // Update existing thread item
  function updateThreadItem(item, thread) {
    const { peer, lastMessage, unreadCount } = thread;
    const { name, initials, color } = getPeerDisplayInfo(peer);
    const timeStr = formatTime(lastMessage?.timestamp);
    const previewText = truncatePreview(lastMessage?.content);

    // Update avatar
    const avatar = item.querySelector('.thread-item__avatar');
    avatar.style.background = color;
    avatar.querySelector('span').textContent = initials;
    
    // Update status ring
    const existingRing = avatar.querySelector('.status-ring');
    if (peer.is_online && !existingRing) {
      avatar.innerHTML += '<div class="status-ring"></div>';
    } else if (!peer.is_online && existingRing) {
      existingRing.remove();
    }

    // Update name and time
    item.querySelector('.thread-item__name').textContent = name;
    item.querySelector('.thread-item__time').textContent = timeStr;
    item.querySelector('.thread-item__preview').textContent = previewText;

    // Update unread badge
    const meta = item.querySelector('.thread-item__meta');
    if (unreadCount > 0 && !meta) {
      const newMeta = document.createElement('div');
      newMeta.className = 'thread-item__meta';
      newMeta.innerHTML = `<div class="thread-item__unread">${unreadCount}</div>`;
      item.appendChild(newMeta);
    } else if (unreadCount > 0 && meta) {
      meta.querySelector('.thread-item__unread').textContent = unreadCount;
    } else if (unreadCount === 0 && meta) {
      meta.remove();
    }
  }

  // Render all threads
  function renderThreads(threads, activeId) {
    // Clear container
    container.innerHTML = '';

    if (threads.length === 0) {
      container.innerHTML = `
        <div class="thread-list__empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <p>No conversations yet</p>
        </div>
      `;
      return;
    }

    // Render each thread
    threads.forEach(thread => {
      const item = createThreadItem(thread);
      if (thread.id === activeId) {
        item.classList.add('active');
      }
      container.appendChild(item);
      threadElements.set(thread.id, item);
    });
  }

  // Update thread list (diff-based update)
  function updateThreads(threads, activeId) {
    const currentIds = new Set(threadElements.keys());
    const newIds = new Set(threads.map(t => t.id));

    // Remove threads that no longer exist
    currentIds.forEach(id => {
      if (!newIds.has(id)) {
        const element = threadElements.get(id);
        if (element) {
          element.remove();
          threadElements.delete(id);
        }
      }
    });

    // Add or update threads
    threads.forEach(thread => {
      const existing = threadElements.get(thread.id);
      if (existing) {
        // Update existing thread
        updateThreadItem(existing, thread);
        
        // Update active state
        if (thread.id === activeId) {
          existing.classList.add('active');
        } else {
          existing.classList.remove('active');
        }

        // Reorder if needed (move to top if most recent)
        const containerFirstChild = container.firstElementChild;
        if (containerFirstChild && containerFirstChild !== existing) {
          container.insertBefore(existing, containerFirstChild);
        }
      } else {
        // Add new thread
        const item = createThreadItem(thread);
        if (thread.id === activeId) {
          item.classList.add('active');
        }
        container.insertBefore(item, container.firstChild);
        threadElements.set(thread.id, item);
      }
    });

    // Handle empty state
    if (threads.length === 0) {
      container.innerHTML = `
        <div class="thread-list__empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <p>No conversations yet</p>
        </div>
      `;
      threadElements.clear();
    }
  }

  // Set active thread
  function setActiveThread(id) {
    threadElements.forEach((element, threadId) => {
      if (threadId === id) {
        element.classList.add('active');
      } else {
        element.classList.remove('active');
      }
    });
  }

  // Set click handler
  function setOnThreadClick(handler) {
    onThreadClick = handler;
  }

  // Destroy component
  function destroy() {
    container.innerHTML = '';
    threadElements.clear();
    onThreadClick = null;
  }

  return {
    renderThreads,
    updateThreads,
    setActiveThread,
    setOnThreadClick,
    destroy
  };
}
