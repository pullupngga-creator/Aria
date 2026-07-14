# RULES.md / .cursorrules — Aria Coding Standards

## Philosophy
Write code that is correct, readable, and minimal — in that order. Prefer explicit over clever. Every line must justify its existence. Aria is a vanilla JS app: no frameworks, no abstractions that obscure the DOM.

---

## Rust Rules

### 1. Error Handling
- Use `thiserror` for structured error types in library code
- Use `anyhow` for application-level error propagation
- Never use `.unwrap()` or `.expect()` in production code paths
- Return `Result<T, AriaError>` from all Tauri commands
- Include context with `.context("message")` when chaining errors

### 2. Async Patterns
- Use `tokio` for all async runtime needs
- Prefer `async fn` over callback-based APIs
- Use `tokio::spawn` for background tasks (network listeners, file transfers)
- Never block the async runtime with synchronous I/O
- Use `tokio::sync::mpsc` channels for communication between network tasks and Tauri commands

### 3. Tauri Commands
- All commands must be strongly typed: `#[tauri::command] async fn my_command(payload: MyStruct) -> Result<MyResponse, AriaError>`
- Use `tauri-specta` to auto-generate TypeScript bindings
- Keep commands thin; delegate to `network/` and `protocol/` modules
- Validate all inputs at the command boundary
- Emit events to frontend using `app_handle.emit()` for real-time updates (peer discovery, messages, progress)

### 4. Network & Protocol
- Implement mDNS discovery with graceful degradation (handle networks with mDNS disabled)
- Use length-prefixed framing for all TCP messages to prevent stream desynchronization
- Implement connection timeouts and retry logic with exponential backoff (max 3 retries)
- Validate all received protocol envelopes: version, signature, timestamp drift (< 5 minutes)
- Sanitize all received filenames before writing to disk

### 5. Memory & Performance
- Stream file transfers in chunks (64KB buffers) — never load entire files into memory
- Use `tokio::io::copy` or `tokio::fs::File` for async file I/O
- Release buffers and drop connections explicitly when transfers complete or fail
- Profile with `cargo flamegraph` before optimizing

### 6. Security
- Store Ed25519 private key in OS keychain, never in SQLite or plain text
- Validate peer fingerprints before establishing trust
- Use `ring` or `ed25519-dalek` for all cryptographic operations
- Sanitize all user-provided paths and filenames
- Never trust peer-provided file paths — always write to configured download directory

### 7. Testing
- Write unit tests for all `protocol/` and `crypto/` functions
- Use `tokio::test` for async tests
- Mock TCP connections for protocol testing
- Aim for >70% coverage on Rust core

---

## JavaScript / Frontend Rules

### 1. Vanilla JS Only
- No React, Vue, Angular, or Svelte. Pure ES2024 JavaScript.
- Use ES6 classes or factory functions for component encapsulation
- Use native DOM APIs: `document.querySelector`, `addEventListener`, `classList`, `dataset`
- No jQuery or utility libraries that wrap DOM APIs

### 2. Component Pattern
```javascript
// Factory pattern (preferred for simple components)
export function createSidebar(container, options) {
  const element = document.createElement('div');
  // ... build DOM, attach listeners
  return {
    element,
    updatePeers(peers) { /* ... */ },
    destroy() { /* cleanup listeners */ }
  };
}

// Class pattern (preferred for complex stateful components)
export class ChatView {
  constructor(container, options) {
    this.container = container;
    this.messages = [];
    this.render();
  }
  addMessage(msg) { /* ... */ }
  destroy() { /* cleanup */ }
}
```
- Every component must have a `destroy()` method that removes all event listeners and DOM references
- Never leak DOM nodes or listeners on navigation/re-mount

### 3. State Management
- Use lightweight Pub/Sub pattern or `EventTarget` for cross-component communication
- No Redux, MobX, or global state libraries
- Store state in module-level constants or simple classes
- Example:
```javascript
const peerStore = new Map(); // peer_id -> peer_data
const listeners = new Set();
export const peerStore = {
  get(id) { return peers.get(id); },
  set(id, data) { peers.set(id, data); listeners.forEach(fn => fn(id, data)); },
  subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }
};
```

### 4. Styling
- Use Tailwind CSS utility classes exclusively. No inline styles except for dynamic values (progress widths, waveform bars).
- Use CSS Custom Properties for all theme tokens. Toggle dark mode by setting `data-theme="dark"` on `<html>`.
- Use BEM-like naming for component-specific styles: `.aria-chat__bubble`, `.aria-sidebar__peer--online`
- Never use `!important` in custom CSS

### 5. Event Handling
- Use event delegation for lists (peers, messages) to minimize listener count
- Debounce scroll handlers (16ms / 1 frame)
- Debounce input handlers (150ms for search)
- Always remove event listeners in `destroy()` methods

### 6. Performance
- Use `DocumentFragment` for batch DOM insertions (message history loading)
- Use `requestAnimationFrame` for animations and scroll anchoring
- Lazy load message history (virtual scroll or pagination)
- Use `IntersectionObserver` for lazy image previews in chat
- Avoid `innerHTML` for user-generated content — use `textContent` or `createElement`

### 7. Accessibility
- All interactive elements must be keyboard accessible (`tabindex`, `keydown` handlers)
- Use semantic HTML: `<nav>`, `<main>`, `<section>`, `<button>`, `<input>`
- Include `aria-label` for icon-only buttons
- Ensure 4.5:1 contrast ratio for all text (verified in both light and dark modes)
- Announce dynamic updates with `aria-live` regions (new messages, peer online/offline)

### 8. Audio / Voice
- Use Web Audio API (`MediaRecorder` + `AudioContext`) for recording
- Use `<audio>` element for playback (native controls, accessible)
- Generate waveform data from decoded audio buffer (Canvas 2D)
- Request microphone permission gracefully with user-initiated action only

---

## General Rules

### 1. File Naming
- Rust: `snake_case.rs` for files, `PascalCase` for structs/enums
- JS: `camelCase.js` for modules, `PascalCase.js` for class-based components
- CSS: `kebab-case.css` for stylesheets
- Constants: `SCREAMING_SNAKE_CASE`

### 2. Imports
- Group imports: Native APIs → Third-party → Absolute (`@/`) → Relative (`./`)
- Use path aliases (`@/components`, `@/services`, `@/stores`) via Vite resolve config
- No circular dependencies

### 3. Comments
- Explain *why*, not *what*. Code should be self-documenting.
- Use `// TODO(agent): description` for temporary workarounds
- Use `///` doc comments for all public Rust functions
- Use JSDoc for all public JS functions and component constructors

### 4. Git
- Commit messages: `type(scope): description` (Conventional Commits)
- Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`
- Example: `feat(network): add mDNS peer discovery`
- Keep commits atomic; one logical change per commit

### 5. AI-Readable Code
- Add JSDoc / Rust doc comments to all public APIs
- Keep functions under 40 lines when possible
- Avoid deep nesting; use early returns
- Name variables descriptively: `peerConnection` not `pc`, `messageBuffer` not `mb`
- Prefer `const` over `let`; never use `var`
