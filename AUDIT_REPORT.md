# Aria P2P Chat Application — Comprehensive Audit Report

**Application**: Aria — Local-first P2P chat (Tauri v2 + Vanilla JS + Rust)  
**Audit Date**: 2026-07-17  
**Auditor**: Senior Architect / Product Designer / Frontend / Backend / UX Lead

---

## Executive Summary

Aria is a **well-architected, production-viable P2P chat application** with a clean separation between Rust backend (networking, crypto, persistence) and Vanilla JS frontend (UI, state, components). The codebase demonstrates strong architectural discipline: no framework bloat, explicit event-driven communication, and a well-defined wire protocol.

**Overall Health**: **B+ / A-**  
- **Strengths**: Clean Rust architecture, solid protocol design, good type safety via `tauri-specta`, proper mDNS + TCP implementation, clean component/store patterns
- **Critical Gaps**: No test coverage, handshake rekeying incomplete, signature verification stubbed, no file/voice transfer implementation, missing error recovery, no CI/CD
- **Risk Level**: **Medium** — core architecture is sound but several "Phase 2/3" features are stubbed with TODOs

---

## 1. Architecture Review

### Project Structure Assessment

```
aria/
├── src/                          # Vanilla JS frontend (✓ clean separation)
│   ├── main.js                   # App bootstrap, DOMContentLoaded (✓ single entry)
│   ├── bindings.js/.d.ts         # tauri-specta generated (✓ committed)
│   ├── components/               # Factory functions returning { destroy, ... } (✓ pattern)
│   ├── services/                 # IIFE singletons for business logic (✓ pattern)
│   ├── stores/                   # Pub/Sub state with subscribe()/get()/set() (✓ pattern)
│   ├── protocol/                 # Wire types mirroring Rust (✓ shared contract)
│   ├── utils/                    # DOM helpers, formatters (✓)
│   └── styles/                   # Tailwind + CSS custom properties (✓)
├── src-tauri/
│   ├── src/
│   │   ├── main.rs → lib.rs::run()  # Tauri entry (✓ minimal)
│   │   ├── lib.rs                  # AppState, command registry, setup (✓ central)
│   │   ├── commands/               # One file per domain (✓ organized)
│   │   ├── network/                # mDNS, TCP server, connection manager (✓ async)
│   │   ├── protocol/               # Envelope, dispatcher, handshake, message (✓)
│   │   ├── crypto/                 # Ed25519 identity, keyring storage (✓)
│   │   ├── db/                     # SQLite schema, migrations, queries (✓)
│   │   └── transfer/               # (empty — file/voice not implemented)
│   ├── Cargo.toml                  # Dependencies (✓ modern crates)
│   └── tauri.conf.json             # Build config (✓ port 1420 fixed)
└── Documentation/                  # TECH_STACK, SPEC, DESIGN, PROTOCOL, AGENTS
```

### Separation of Concerns

| Layer | Responsibility | Quality |
|-------|----------------|---------|
| **Frontend Components** | Pure UI rendering, event binding, destroy() cleanup | ✓ Excellent — factory functions, no framework |
| **Frontend Services** | Business logic, Tauri invoke, event listeners | ✓ Good — IIFE singletons, clear boundaries |
| **Frontend Stores** | Reactive state, pub/sub, derived sorting | ✓ Good — minimal, no external deps |
| **Rust Commands** | Thin Tauri handlers → delegate to modules | ✓ Good — single responsibility |
| **Rust Network** | mDNS broadcast/listen, TCP accept/connect, heartbeat | ✓ Strong — proper Tokio patterns |
| **Rust Protocol** | Envelope framing, signing, dispatch, handshake | ✓ Strong — well-typed enums, canonical signing |
| **Rust Crypto** | Identity generation, keyring persistence, fingerprint | ✓ Good — keyring for secure storage |
| **Rust DB** | Schema, migrations, peer/message/file/voice tables | ✓ Good — manual migrations, FKs, indexes |

### Communication Flow

```
User Action (UI)
    ↓
Frontend Service (messageService.sendMessage)
    ↓
invoke("send_message", { fingerprint, content })
    ↓
Rust Command (commands::message::send_message)
    ↓
ConnectionManager.get(fingerprint) → ConnectionHandle.send_raw()
    ↓
TCP Stream (length-prefixed JSON envelope)
    ↓
Remote Peer: run_read_loop() → dispatch_envelope()
    ↓
Handler (message) → DB store + emit("message:received")
    ↓
Frontend: listen("message:received") → messageStore.addMessage()
    ↓
Component (ChatView) subscribe → re-render bubble
```

**Assessment**: Clean unidirectional flow. The only bidirectional coupling is the global `window.messageService`/`window.typingService` exposure for ChatView — a pragmatic but slightly leaky abstraction.

### Scalability & Maintainability

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Adding new message types** | ✅ Easy | Add enum variant, payload struct, dispatcher arm |
| **Adding new Tauri commands** | ✅ Easy | New file in `commands/`, register in `lib.rs`, `cargo build` regenerates bindings |
| **Frontend component reuse** | ✅ Easy | Factory pattern, `destroy()` for cleanup |
| **State scaling** | ⚠️ Moderate | In-memory Maps; no pagination/virtualization for large histories |
| **Network scaling** | ⚠️ Moderate | Single TCP connection per peer; no connection pooling for groups |
| **Database scaling** | ⚠️ Moderate | Single SQLite file; OK for local-first but no WAL mode enabled |

---

## 2. Database Design Review

### Schema Analysis (from `schema.rs`)

```sql
settings (1 row)           — app config, theme, port, trust_mode
peers (discovered + manual) — fingerprint PK, trust_level, online status
conversations (1:1 with peers) — unread count, last_activity
messages (per conversation) — direction, content, status, signature, reply_to
file_transfers (per message) — progress, checksum, resume support
voice_messages (per message) — duration, waveform JSON, playback position
typing_indicators (per conv) — ephemeral, unique constraint
```

### Strengths

1. **Proper normalization** — conversations separate from peers, messages reference conversations
2. **Foreign keys with CASCADE** — `ON DELETE CASCADE` on conversations→messages, peers→conversations
3. **Indexes on query paths** — `conversation_id`, `timestamp`, `trust_level`, `is_online`, `status`
4. **Migration system** — `PRAGMA user_version` with incremental ALTER TABLE (v1→v4)
5. **Trust model in DB** — `trust_level` enum ('untrusted'|'trusted'|'blocked') enforced at storage layer
6. **File transfer resumability** — `bytes_transferred`, `checksum`, `status` enum supports pause/resume

### Critical Issues

| Issue | Severity | Impact |
|-------|----------|--------|
| **No WAL mode** | 🔴 High | SQLite default rollback journal causes lock contention under concurrent read/write (Tauri commands + heartbeat + network monitor all hit DB) |
| **`messages` table has dual schema** | 🔴 High | `schema.rs` defines `messages` with `conversation_id` FK, but `messages.rs::init_schema` creates a **different table** with `peer_fingerprint` TEXT FK — **these conflict** |
| **No `updated_at` triggers** | 🟡 Medium | `settings.updated_at`, `peers.last_seen` updated manually; easy to forget |
| **`conversations.last_message_id`** | 🟡 Medium | No FK to `messages.id`; orphan risk if message deleted |
| **`file_transfers.checksum` not verified on complete** | 🟡 Medium | Checksum stored but no verification logic implemented |
| **No soft-delete for peers** | 🟢 Low | `blocked` trust level exists but peers never purged; DB grows unbounded |
| **`typing_indicators` table persistent** | 🟢 Low | Should be ephemeral (memory-only); current schema writes to disk on every keystroke |

### Schema Conflict Detail

**In `schema.rs` (v1, canonical):**
```sql
CREATE TABLE messages (
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    sender_peer_id INTEGER REFERENCES peers(id),
    ...
);
```

**In `messages.rs::init_schema()` (v4 migration):**
```sql
CREATE TABLE messages (
    peer_fingerprint TEXT REFERENCES peers(fingerprint),
    ...
);
```

**Result**: If migration v4 runs, it creates a **second `messages` table** with different columns. The v1 table persists. Queries in `messages.rs` use the v4 schema; queries in `dispatcher.rs` (handshake path) use `crate::db::messages::store_message` which calls the v4 function. But any direct SQL referencing the v1 schema will hit the wrong table.

**Fix**: Consolidate to one schema. Use the v4 design (simpler, fingerprint-based) and drop the v1 `conversations` table entirely, or fully implement the v1 normalized design.

---

## 3. Rust Backend Review

### Command Organization

| Command File | Commands | Assessment |
|--------------|----------|------------|
| `peers.rs` | `list_peers`, `trust_peer`, `block_peer`, `untrust_peer` | ✓ Thin, delegates to `db::peers` |
| `tcp.rs` | `connect_to_peer`, `get_connection_status`, `disconnect_peer` | ✓ Good timeout handling, idempotent connect |
| `handshake.rs` | `send_handshake` | ⚠️ Exists but not wired in dispatcher rekey |
| `message.rs` | `send_message`, `get_messages` | ✓ Proper envelope creation, status tracking |
| `typing.rs` | `send_typing` | ✓ Minimal |

### Business Logic Distribution

**Well-placed**:
- Peer upsert/trust logic → `db::peers`
- Message storage → `db::messages`
- Envelope signing/verification → `protocol::Envelope`
- Handshake payload → `protocol::handshake`
- mDNS broadcast/listen → `network::discovery`
- TCP server/read loop → `network::tcp_server`
- Connection registry → `network::connection_manager`
- Heartbeat monitoring → `network::heartbeat`
- Network interface monitoring → `network::monitor`

**Misplaced / Missing**:
- **Handshake rekey logic** — `tcp_server.rs` calls `conn_mgr.rekey()` but `dispatcher.rs` (inbound path) has `TODO: Rekey connection manager` — **inconsistent**
- **Signature verification** — `dispatcher.rs:189` has `// TODO: Verify signature` with dummy public key — **security hole**
- **File/Voice transfer** — `transfer/` module empty; commands stubbed in dispatcher
- **Delivery receipts** — `dispatcher.rs:134` has `// TODO: Send delivery receipt`

### Error Handling

| Pattern | Usage | Quality |
|---------|-------|---------|
| `anyhow::Result` in library code | ✅ Consistent | Good — context with `.context()` |
| `Result<T, String>` in Tauri commands | ✅ Consistent | OK — but loses error chain; consider `tauri::Error` |
| `map_err(|e| e.to_string())` | ⚠️ Frequent | Loses context; use `.context()` then `.map_err(|e| e.to_string())` |
| `unwrap()` in hot paths | ❌ Several | `tcp_server.rs:195` `VerifyingKey::from_bytes(&[0u8; 32]).unwrap()` — **panic risk** |

### Async Usage

- ✅ `tokio::spawn` for all background tasks (mDNS, TCP accept, read loops, heartbeat, network monitor)
- ✅ Channels (`mpsc::unbounded_channel`) for cross-task communication (heartbeat actions)
- ✅ `RwLock` for connection registry, `Mutex` for DB (coarse but correct)
- ⚠️ **DB lock contention** — single `Mutex<Connection>` shared by all commands + heartbeat + network monitor + dispatcher. Under load, commands block on heartbeat's 30s tick.

### Security

| Area | Status | Notes |
|------|--------|-------|
| **Identity storage** | ✅ Keyring | `keyring` crate — secure OS credential store |
| **Fingerprint** | ✅ SHA-256 truncated | 4 bytes (8 hex chars) — **collision risk** (~1 in 4B; acceptable for LAN) |
| **Envelope signing** | ✅ Ed25519 | Canonical JSON signing data (version\|type\|sender\|payload\|timestamp) |
| **Timestamp validation** | ✅ 5 min drift | Handshake: 30s; Envelope: 300s |
| **Signature verification** | ❌ Stubbed | `dispatcher.rs:189` uses dummy key — **critical** |
| **Trust enforcement** | ⚠️ Partial | Handshake checks `blocked` but not `trusted` for file auto-accept |
| **Input validation** | ⚠️ Minimal | No message size limits beyond 64MB envelope; no sanitization |
| **SQL injection** | ✅ Parameterized | All queries use `params![]` or `?` placeholders |

### Performance

- **DB**: Single connection, no WAL, no connection pool — bottleneck at ~100 concurrent commands
- **Network**: One TCP connection per peer; read loop per connection; OK for <50 peers
- **Memory**: `HashMap<String, ConnectionHandle>` — keys are fingerprints (8 chars), fine
- **Event emission**: `app.emit()` on every message/heartbeat — Tauri serializes to JSON; OK for chat volume

---

## 4. Frontend Architecture Review

### Component Pattern

```js
// Factory function returning { destroy(), ...methods }
export function createChatView(container, fingerprint) {
  // ... create DOM, bind events, subscribe to stores
  return { destroy, setFingerprint };
}
```

**Assessment**: ✅ **Excellent**. No framework, explicit lifecycle, testable, composable.

### Store Pattern (Pub/Sub)

```js
// peerStore.js
const _peers = new Map();
const _listeners = new Set();
export const peerStore = {
  upsert(peer) { _peers.set(...); _notify(); },
  subscribe(fn) { _listeners.add(fn); fn(getAll()); return () => _listeners.delete(fn); },
  // ...
};
```

**Assessment**: ✅ **Good**. Minimal, no dependencies, derived sorting in `getAll()`.

**Issues**:
- `threadStore` duplicates peer data (`thread.peer = peer`) — **denormalized**
- `messageStore` stores full message objects per fingerprint — **no pagination**, memory grows unbounded
- `typingStore` and `connectionStore` are simple Sets/Maps — ✅ appropriate

### Service Pattern (IIFE Singletons)

```js
export const messageService = {
  async init() { _unlistenSent = await listen(...); },
  async sendMessage(fp, content) { await commands.sendMessage(fp, content); },
  destroy() { _unlistenSent?.(); }
};
```

**Assessment**: ✅ **Good**. Clear `init()`/`destroy()` lifecycle, event listener management.

**Issues**:
- `window.messageService` / `window.typingService` global exposure — breaks encapsulation for ChatView convenience
- `peerService.init()` called before stores fully ready — race condition risk (mitigated by `subscribe` immediate callback)

### State Flow Example: Send Message

```
User types → ChatView input handler
    → window.messageService.sendMessage(fp, content)
        → invoke("send_message", { fingerprint: fp, content })
            → Rust: commands::message::send_message
                → DB store (status: 'pending')
                → Envelope::new(Message, fp, payload, identity)
                → ConnectionHandle.send_raw(bytes)
                    → TCP write
    → Rust: dispatcher receives envelope (remote)
        → DB store (status: 'received')
        → emit("message:received", { fingerprint, content, ... })
    → Frontend: messageService._unlistenReceived callback
        → messageStore.addMessage(fp, { ...direction: 'received' })
            → messageStore.notify()
                → ChatView subscribe callback → renderMessages()
                    → createMessageBubble() → DOM append
```

**Fragility Points**:
1. **Dual write** — message stored in Rust DB AND frontend store; no reconciliation if one fails
2. **No optimistic UI** — input disabled during send; no local echo before server ack
3. **No delivery receipt handling** — `message:delivered` listener exists but Rust never emits it
4. **Race: `loadMessages` + subscribe** — `loadMessages` calls `renderMessages` then subscribes; messages arriving between load and subscribe render twice

### Code Quality

| Metric | Assessment |
|--------|------------|
| **Naming** | ✅ Consistent (`peerStore`, `createChatView`, `sendMessage`) |
| **JSDoc Types** | ✅ Good coverage on stores/services |
| **Dead Code** | ⚠️ `chat.css` imports unused in some components; `components2.css`, `components3.css` likely stale |
| **Commented Code** | ✅ Minimal |
| **Hardcoded Values** | ⚠️ Port 9473 in 3+ places; 64MB max envelope; 30s handshake timeout |

---

## 5. State Management Review

### Store Inventory

| Store | State | Subscribers | Derived? | Issues |
|-------|-------|-------------|----------|--------|
| `peerStore` | `Map<fp, PeerRow>` | Components, DiscoverModal | `getAll()` sorts online→offline→time | ✅ Clean |
| `threadStore` | `Map<fp, Thread>` | ThreadList, ChatView | `getAllThreads()` sorts by activity | ⚠️ Duplicates peer data |
| `messageStore` | `Map<fp, Message[]>` | ChatView | None | ❌ No pagination, unbounded growth |
| `connectionStore` | `Set<fp>` | ChatView (connect btn) | None | ✅ Simple |
| `typingStore` | `Map<fp, {isTyping, timestamp}>` | ChatView | `isPeerTyping(fp)` | ✅ Ephemeral |

### Critical State Issues

1. **Thread Store Denormalization**
   - `threadStore.setPeer(fp, peer)` copies entire `PeerRow` into thread
   - `peerStore.upsert()` → `main.js` subscribes → calls `threadStore.setPeer()` → `threadStore.updateThread()`
   - **Two sources of truth** for peer display name/avatar/online status
   - **Fix**: Thread store should only hold `{ fp, lastMessage, unreadCount, lastActivity }`; derive peer info from `peerStore.get(fp)` at render time

2. **Message Store Unbounded**
   - No limit on messages per conversation
   - No virtualization in ChatView — renders all messages as DOM nodes
   - **Fix**: Add pagination (load 50, prepend on scroll), virtualize with `IntersectionObserver`

3. **Typing Store Persistence**
   - `typingStore` in memory only — correct (ephemeral)
   - But Rust `typing_indicators` table writes to disk on every keystroke — **remove table or make it in-memory**

4. **Network State in Peer Store**
   - `peerStore.setNetworkState({ ips, changed, mdnsDegraded })` — mixes peer data with network metadata
   - **Fix**: Separate `networkStore` or keep in `peerStore` but rename namespace

---

## 6. Data Flow Review

### Trace: Create Message (Send)

```
UI: ChatView input → handleSend()
    → messageService.sendMessage(fp, content)
        → invoke("send_message", { fingerprint, content, replyTo })
            → Rust: send_message command
                → DB: store_message(..., status='pending')
                → Envelope::new(Message, my_fp, payload, identity)
                → ConnectionManager.get(fp) → send_raw()
                    → TCP write (length-prefixed)
    → UI: input disabled, re-enabled on catch/finally
    → (async) Remote peer receives → dispatcher → DB store → emit("message:received")
        → Frontend: listen("message:received") → messageStore.addMessage()
            → ChatView subscribe → renderMessages()
```

**Issues**:
- No optimistic UI — user waits for round-trip (LAN: ~5-20ms, acceptable)
- No local echo — message appears only after `message:received` event (which comes from *remote* peer's dispatcher, not local)
- **Critical**: Local message never appears in UI unless remote peer echoes back! The `message:sent` event emits but `messageService` only logs it — doesn't add to store.

### Trace: Receive Message

```
Remote: TCP read_loop → Envelope::from_bytes → dispatch_envelope(Message)
    → DB: store_message(..., direction='received', status='received')
    → emit("message:received", { fingerprint, message_id, content, timestamp, reply_to })
Frontend: listen("message:received") → messageStore.addMessage(fp, { direction: 'received' })
    → ChatView subscribe → renderMessages()
```

**Issue**: `message:received` payload in dispatcher includes `message_id` but frontend `MessageRow` expects `message_id` — OK. But `reply_to` not handled in UI.

### Trace: Peer Discovery

```
Rust: mDNS browse → ServiceResolved → upsert_peer() → heartbeat.Seen() → emit("peer:discovered")
Frontend: listen("peer:discovered") → peerStore.upsert()
    → main.js subscribe → threadStore.updateThread(fp, { peer })
        → ThreadList subscribe → updateThreads()
            → DOM update
```

**Issue**: `threadStore.updateThread` called for *every* peer discovery, creating thread for peers never messaged. OK for "recent" list but inflates thread count.

### Trace: Network Change (Wi-Fi switch)

```
Rust: network_monitor tick (10s) → get_local_ips() → changed?
    → peers::clear_stale_peers(old_ips) → set offline
    → rebroadcast_mdns()
    → emit("network:changed", { ips, changed: true, mdns_degraded })
Frontend: listen("network:changed") → peerStore.setNetworkState()
    → (no UI reaction currently)
```

**Missing**: Frontend should show "Network changed, rediscovering..." toast; auto-refresh DiscoverModal.

---

## 7. UI Review

### Visual Design System (from `theme.css`)

| Token | Light | Dark | Assessment |
|-------|-------|------|------------|
| `--bg` | `#F5F6FA` | `#0C0E17` | ✅ Good contrast |
| `--surface` | `#FFFFFF` | `#141729` | ✅ Card backgrounds |
| `--border` | `#E5E7EB` | `rgba(255,255,255,0.06)` | ✅ Subtle |
| `--text-primary` | `#111111` | `#E8E8ED` | ✅ WCAG AA |
| `--text-secondary` | `#6B7280` | `#8B8FA3` | ✅ |
| `--accent` | `#E86A33` (orange) | Same | ✅ Distinctive brand color |
| `--radius` | `10px` | Same | ✅ Consistent |
| `--font` | Inter + system fallback | Same | ✅ Modern |

### Component Consistency

| Component | Visual Quality | Issues |
|-----------|----------------|--------|
| **Sidebar** | ✅ Clean, compact (72px), active indicator animation | Profile button "ME" hardcoded; no avatar support |
| **ThreadList** | ✅ Good avatar/status ring, unread badge, time formatting | Empty state SVG inline (duplicated in ChatView) |
| **ChatView** | ✅ Message bubbles, typing indicator, input bar | Header actions (Profile/Call) non-functional; transfer progress UI orphaned |
| **DiscoverModal** | ✅ Search, refresh, manual connect, status dots | Manual connect form inline (not a sub-modal); IP validation missing |
| **PeerCard** | ✅ Trust/Block/Unblock actions, fingerprint display | Close button only way to dismiss; no click-outside |
| **MessageBubble** | ✅ Sent/received styling, status icons, timestamp | No reply preview; no file/voice bubble variants |
| **TypingIndicator** | ✅ Animated 3-dot | Container always in DOM (display:none) — minor |

### CSS Architecture

- **7 CSS files** imported in `main.css` — `components.css`, `components2.css`, `components3.css`, `chat.css`, `loader.css`, `typing.css`, `theme.css`
- **Likely duplication** — `components2/3.css` suggest iterative additions without consolidation
- **No design token centralization** beyond `theme.css` — spacing, shadows, transitions scattered

### Accessibility

| Check | Status |
|-------|--------|
| Semantic HTML | ⚠️ Mixed — `<main>`, `<aside>`, `<button>` used but some `<div>` click handlers |
| ARIA labels | ✅ Present on icon-only buttons (`aria-label`) |
| Focus management | ❌ None — modals don't trap focus, no visible focus rings in CSS |
| Color contrast | ✅ Light/dark tokens meet WCAG AA |
| Keyboard nav | ⚠️ Enter to send works; Tab through modal? Escape closes? Partial |
| Screen reader | ❌ No `aria-live` for new messages, typing indicator |

---

## 8. UX Review

### Onboarding & First Run

| Step | Current | Gap |
|------|---------|-----|
| **First launch** | Loading screen (5.5s!) → empty sidebar | No welcome screen, no identity explanation, no "how to connect" guide |
| **Identity** | "ME" button shows fingerprint modal | Fingerprint shown but no QR code, no copy button, no "verify with peer" flow |
| **Discover peers** | + button → Discover Modal → "No peers found" | No explanation of mDNS requirements (same subnet, firewall) |

### Core Workflows

| Workflow | Steps | Friction |
|----------|-------|----------|
| **Start chat (mDNS)** | Click + → Wait for scan → Click "Start Chat" → ChatView loads | ✅ Good if peers online |
| **Start chat (manual IP)** | Click + → Expand "Connect Manually" → Enter IP:Port → Connect | ⚠️ No validation, no "recent manual connections" history |
| **Send message** | Type → Enter | ✅ Smooth |
| **Trust peer** | Open PeerCard (click avatar) → "Trust Peer" | ✅ Clear |
| **Send file** | ❌ Not implemented | — |
| **Voice message** | ❌ Not implemented | — |
| **Search messages** | ❌ Not implemented | — |

### Empty States

| State | Current | Quality |
|-------|---------|---------|
| No conversations | "No conversations yet" + chat icon | ✅ Good |
| No peers discovered | "No peers found on this network. Make sure you're on the same Wi-Fi." | ✅ Helpful |
| No messages in chat | "No conversation selected" | ✅ Clear |
| mDNS failed | Toast: "mDNS discovery failed: [error]" | ⚠️ Technical error shown to user |

### Error Handling UX

- **Connection timeout**: Console warn only — user sees nothing
- **Handshake rejected**: Console warn + `peer:handshake_rejected` event — no UI
- **Message send failure**: Input restored, no toast — user may not notice
- **Database error**: `console.error` only

**Recommendation**: Add a global toast/notification system (simple `div` stack) for all user-facing errors.

### Keyboard Shortcuts

| Shortcut | Action | Implemented? |
|----------|--------|--------------|
| `Enter` | Send message | ✅ |
| `Escape` | Close modals | ✅ (Discover, Self) |
| `Ctrl/Cmd + K` | Focus search | ❌ |
| `Ctrl/Cmd + N` | New chat | ❌ |
| `↑/↓` | Navigate threads | ❌ |

---

## 9. Feature Consistency

| Feature | Status | Consistency Issues |
|---------|--------|-------------------|
| **Trust/Block** | ✅ PeerCard + commands | `untrust_peer` sets "untrusted" but UI says "Unblock" — label mismatch |
| **Online status** | ✅ mDNS + heartbeat | Green dot in ThreadList, "Online" text in ChatView — consistent |
| **Unread count** | ✅ ThreadList badge | Increments on receive; clears on thread click — ✅ |
| **Typing indicator** | ✅ Events + store + UI | Shows "X is typing..." but no "X stopped typing" animation |
| **Message status** | ⚠️ Partial | `pending`→`sent` local; `delivered`/`read` never sent by Rust |
| **Timestamps** | ✅ Relative formatting | Consistent across ThreadList (short) and ChatView (time only) |
| **Avatars** | ✅ Initials + color hash | Consistent in ThreadList, ChatView, PeerCard, DiscoverModal |
| **Theme** | ✅ Light/Dark + System | Persisted in localStorage + Tauri settings — ✅ |

---

## 10. Performance Review

### Frontend

| Area | Current | Risk |
|------|---------|------|
| **Message rendering** | Full re-render on every message (`container.innerHTML = ''` + loop) | 🔴 High — O(n) DOM ops per message; degrades >500 messages |
| **Thread list updates** | Diff-based (add/update/remove/reorder) | ✅ Good |
| **Store subscriptions** | Synchronous notify on every mutation | 🟡 Medium — batched in event loop but no debounce |
| **Scroll anchoring** | Manual `isUserScrolling` flag | ✅ Works |
| **Memory** | All messages in `messageStore` Map forever | 🔴 High — no eviction |

### Backend

| Area | Current | Risk |
|------|---------|------|
| **DB lock contention** | Single `Mutex<Connection>` for all commands + background tasks | 🔴 High — heartbeat (30s), network monitor (10s), mDNS events all lock DB |
| **WAL mode** | Not enabled | 🔴 High — readers block writers |
| **Connection per peer** | One TCP stream, one read loop | 🟡 Medium — OK for <50 peers |
| **Envelope size limit** | 64MB hardcoded | 🟡 Medium — no per-message-type limits |
| **Heartbeat interval** | 30s tick, 3 misses = offline | ✅ Reasonable |

### Startup Time

- **Frontend**: Vite HMR ~200ms
- **Rust**: `cargo build` ~15-30s (incremental ~3s)
- **Tauri dev**: `pnpm tauri dev` ~5-8s (Rust compile + Vite)
- **Loading screen**: Hardcoded 5.5s in `main.js:27` — **fake delay, remove**

---

## 11. Code Quality Review

### Rust

| File | Lines | Issues |
|------|-------|--------|
| `tcp_server.rs` | 215 | `unwrap()` on dummy VerifyingKey (line 195); handshake timeout hardcoded |
| `dispatcher.rs` | 178 | Signature verification stubbed; handshake rekey TODO; delivery receipt TODO |
| `discovery.rs` | 236 | `rebroadcast_mdns` re-registers without unregister (mdns-sd limitation); IP filtering IPv4-only |
| `connection_manager.rs` | 84 | ✅ Clean |
| `heartbeat.rs` | 120 | ✅ Clean |
| `monitor.rs` | 146 | Rebcasts mDNS on every IP change — could spam |
| `db/mod.rs` | 162 | Global `OnceLock<Mutex<Connection>>` duplicates connection — two pools! |
| `db/messages.rs` | 132 | Schema conflict with `schema.rs`; `timestamp: i32` for Specta (lossy > 2038) |
| `db/peers.rs` | 153 | `clear_stale_peers` loads all peers → N+1 subnet check |
| `crypto/mod.rs` | 66 | ✅ Clean |
| `protocol/envelope.rs` | 142 | ✅ Good tests |

### Frontend

| File | Lines | Issues |
|------|-------|--------|
| `main.js` | 269 | Bootstraps everything; 5.5s fake loading delay; global `window.*` exposure |
| `ChatView.js` | 306 | Full re-render on message; inline SVG; `setFingerprint` stub |
| `ThreadList.js` | 230 | ✅ Good diffing |
| `DiscoverModal.js` | 242 | Inline manual connect form; `listEl` undefined in `destroy()` (line 123) |
| `PeerCard.js` | 127 | ✅ Clean |
| `MessageBubble.js` | 35 | ✅ Minimal |
| `peerStore.js` | 107 | Network state mixed in |
| `threadStore.js` | 136 | Denormalized peer data |
| `messageStore.js` | 48 | No pagination |
| `peerUtils.js` | (not read) | Color hash for avatars — likely deterministic |

### Dead Code / Stale Files

- `src/styles/components2.css`, `components3.css` — likely superseded by `components.css` + `chat.css`
- `src/components/TypingIndicator.js` imported but also defined in `ChatView.js` inline styles
- `src-tauri/src/transfer/` directory exists but empty
- `commands::handshake::send_handshake` exists but not used (handshake auto-sent on connect)

---

## 12. Design System Assessment

### Current State

| Element | Status |
|---------|--------|
| **Color palette** | ✅ Defined in `theme.css` (light/dark) |
| **Spacing scale** | ❌ Ad-hoc (`padding: 0.5rem 1rem`, `gap: 0.5rem`, `margin: 24px`) |
| **Typography scale** | ❌ Ad-hoc (`font-size: 0.875rem`, `1rem`, `1.25rem`, `2rem`) |
| **Border radius** | ✅ `--radius`, `--radius-sm`, `--radius-full` |
| **Shadows** | ❌ Ad-hoc (`box-shadow: 0 4px 12px...`) |
| **Transitions** | ❌ Ad-hoc (`transition: all 0.15s`, `0.2s`, `0.3s`) |
| **Component variants** | ❌ No systematic Button/Input/Card variants |
| **Icons** | ✅ Lucide SVG inline (consistent style) |

### Recommendation

Extract a **`design-tokens.css`** with:
```css
:root {
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-5: 24px; --space-6: 32px;
  --text-xs: 0.75rem; --text-sm: 0.875rem; --text-base: 1rem; --text-lg: 1.125rem; --text-xl: 1.25rem; --text-2xl: 1.5rem;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05); --shadow-md: 0 4px 6px rgba(0,0,0,0.07); --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
  --transition-fast: 100ms; --transition-base: 200ms; --transition-slow: 300ms;
}
```

Then refactor all CSS to use tokens.

---

## 13. Security & Reliability

### Threat Model: Local Network P2P Chat

| Threat | Mitigation | Status |
|--------|------------|--------|
| **MITM on LAN** | Ed25519 signatures on every envelope | ✅ Protocol designed |
| **Signature verification** | Verify sender public key matches fingerprint | ❌ **Stubbed** — critical |
| **Replay attacks** | Timestamp + 5min window | ✅ Envelope + handshake |
| **Impersonation** | Fingerprint verification (manual) | ⚠️ UI shows fingerprint but no QR/verification flow |
| **File transfer integrity** | SHA-256 checksum in `file_transfers` | ⚠️ Stored but not verified on complete |
| **DoS via large messages** | 64MB envelope limit | 🟡 High — should be per-type (text: 64KB, file: chunked) |
| **SQL injection** | Parameterized queries | ✅ |
| **Key compromise** | Keyring storage; no rotation UI | 🟡 Medium — no key rotation/revocation |
| **mDNS spoofing** | TXT record includes public key; verify on handshake | ✅ Protocol supports |

### Reliability

| Scenario | Current Behavior | Gap |
|----------|------------------|-----|
| Peer goes offline mid-transfer | `file_transfers` status = 'transferring' | No resume logic; no timeout cleanup |
| Network interface change | `network_monitor` clears stale peers, rebroadcasts | ✅ Good |
| App crash during write | SQLite rollback journal (no WAL) | 🔴 Risk of corruption |
| Duplicate peer discovery | `ON CONFLICT(public_key) DO UPDATE` | ✅ Handled |
| Clock skew >5min | Envelope rejected | ✅ Handled |
| Handshake race (both connect) | Both initiate; temp IP keys → rekey on handshake | ⚠️ `rekey` only in inbound path |

---

## 14. Future Scalability Assessment

| Future Feature | Current Architecture Support | Blockers |
|----------------|------------------------------|----------|
| **Group chat** | ❌ No | 1:1 only; `conversations` tied to single peer; no group key agreement |
| **End-to-end encryption** | ⚠️ Partial | Ed25519 signing only; no encryption layer; would need Noise/X3DH/Double Ratchet |
| **WAN relay / TURN** | ❌ No | Direct TCP only; no NAT traversal (STUN/ICE/relay) |
| **Message sync across devices** | ❌ No | Identity tied to keyring (per-device); no account system |
| **Plugins / Extensions** | ❌ No | No plugin architecture; Tauri plugins possible but not designed |
| **AI features (summarize, reply)** | ⚠️ Possible | Local DB accessible; would need local LLM or cloud API (breaks local-first) |
| **Attachments (images, docs)** | ⚠️ Schema ready | `file_transfers` table exists; UI + transfer protocol missing |
| **Message reactions / threads** | ❌ No | Schema would need `reactions` table, `reply_to` already in messages |
| **Search (full-text)** | ❌ No | SQLite FTS5 not enabled; would need migration |
| **Multi-platform (mobile)** | ⚠️ Tauri mobile alpha | Vanilla JS works; but no touch-optimized UI, no push notifications |

### Architectural Limitations

1. **Identity = Device** — No multi-device sync; keyring per OS user
2. **No Protocol Version Negotiation** — `version: 1` hardcoded; breaking changes require full fleet upgrade
3. **Single SQLite File** — Not suitable for concurrent multi-process access (e.g., future background service)
4. **No Event Sourcing** — State derived from DB; hard to add audit log / undo
5. **Frontend State = Source of Truth for UI** — No server-driven UI; OK for chat but limits dynamic features

---

## Prioritized Improvement Roadmap

### Phase 1 — Critical Fixes (Week 1-2) 🔴

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | **Enable WAL mode** in `db::init()` (`PRAGMA journal_mode=WAL;`) | 1h | Eliminates DB lock contention |
| 2 | **Fix signature verification** in `dispatcher.rs` — lookup peer public key, verify envelope | 4h | Security: prevents spoofing |
| 3 | **Resolve `messages` schema conflict** — pick v4 (fingerprint-based) or v1 (normalized); drop other | 2h | Data integrity |
| 4 | **Remove 5.5s fake loading delay** in `main.js` | 5min | UX: instant startup |
| 5 | **Implement delivery receipts** — Rust emit `message:delivered` on handshake ack; frontend update status | 4h | UX: message status accuracy |
| 6 | **Fix `DiscoverModal.destroy()`** — `listEl` undefined reference | 15min | Bug: memory leak |
| 7 | **Remove dummy `VerifyingKey::from_bytes(&[0u8;32]).unwrap()`** in `tcp_server.rs:195` | 15min | Crash risk |

### Phase 2 — Architecture Improvements (Week 3-4) 🟡

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 8 | **Add pagination + virtualization** to `messageStore` / `ChatView` | 8h | Performance: handle 10k+ messages |
| 9 | **Denormalization cleanup** — `threadStore` derives peer from `peerStore` | 4h | Consistency |
| 10 | **Add toast notification system** for errors, connection status, file transfers | 6h | UX: visibility |
| 11 | **Implement handshake rekey** in `dispatcher.rs` (inbound path) | 4h | Reliability: inbound connections work |
| 12 | **Consolidate CSS** — merge `components*.css`, extract design tokens | 4h | Maintainability |
| 13 | **Add WAL + busy_timeout** to SQLite connection | 2h | Reliability |
| 14 | **Message size limits per type** (text 64KB, file chunk 1MB) | 2h | DoS prevention |

### Phase 3 — UI/UX Polish (Week 5-6) 🟢

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 15 | **Onboarding flow** — welcome screen, identity explanation, QR code for fingerprint | 8h | UX: first-run success |
| 16 | **Focus management** in modals (trap, restore) | 4h | Accessibility |
| 17 | **Keyboard shortcuts** (Cmd+K search, Cmd+N new chat, ↑/↓ navigate) | 4h | Power users |
| 18 | **File transfer UI** — drag-drop, progress, resume (using existing `file_transfers` table) | 16h | Core feature |
| 19 | **Voice message UI** — record/playback, waveform (using `voice_messages` table) | 16h | Core feature |
| 20 | **Message search** (FTS5 virtual table) | 8h | Power users |
| 21 | **Copy fingerprint button** + QR code in self-modal | 2h | UX: verification |

### Phase 4 — Performance & Scale (Week 7-8) 🔵

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 22 | **Connection pool for DB** (rusqlite `Connection` not thread-safe; use `r2d2` or `sqlx` with `SqlitePool`) | 12h | Throughput |
| 23 | **Background sync service** (Tauri background task) for message delivery when app closed | 16h | Reliability |
| 24 | **NAT traversal** — STUN + TURN relay for WAN | 40h+ | Reachability |
| 25 | **Group chat protocol** — MLS or double-ratchet per group | 40h+ | Major feature |

### Phase 5 — Future-Proofing (Ongoing) 🟣

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 26 | **CI/CD pipeline** (GitHub Actions: test, build, sign, release) | 16h | Release velocity |
| 27 | **Automated tests** — Rust unit (protocol, crypto), integration (Tauri commands), E2E (Playwright) | 40h | Confidence |
| 28 | **Protocol version negotiation** — `version` field + capability flags | 8h | Upgradability |
| 29 | **Key rotation / revocation** — key packages, trust-on-first-use with verification | 24h | Security |
| 30 | **Multi-device identity** — sync encrypted key via QR/backup phrase | 40h | User retention |

---

## Summary Verdict

**Aria is a remarkably clean, well-architected P2P chat application for its stage.** The Rust backend demonstrates senior-level async/ Tokio patterns, the protocol is thoughtfully designed with signing and framing, and the Vanilla JS frontend avoids framework bloat while maintaining component discipline.

**The critical path to production is short**: fix the 7 Phase 1 items (mostly signature verification, schema conflict, WAL mode), and you have a secure, working 1:1 LAN messenger.

**The medium-term investment** should focus on the missing core features (file/voice transfer) and the pagination/virtualization needed for real-world message volumes.

**The long-term vision** (groups, E2EE, WAN, multi-device) will require significant protocol evolution — but the current foundation (Ed25519 identity, envelope framing, mDNS discovery, SQLite persistence) is the right starting point.

---

*End of Audit Report*