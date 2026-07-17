# AGENTS.md — Aria (Tauri v2 + Vanilla JS + Rust P2P Chat)

## Project Overview
Aria is a **local-first P2P chat application** built with:
- **Frontend**: Vanilla JS (ES2024), Tailwind CSS v4, Vite — no framework
- **Backend**: Rust (Tauri v2), Tokio, mDNS discovery, direct TCP P2P
- **Protocol**: JSON envelopes over TCP, Ed25519 signatures, file transfer with chunking
- **Data**: SQLite (rusqlite bundled) for peers, messages, settings, trust lists
- **Type Safety**: Tauri-specta generates TypeScript bindings from Rust commands

---

## Dev Commands (run from repo root)

```bash
# Frontend dev server (Vite + HMR on port 1420)
pnpm dev

# Tauri dev (runs Vite + Rust backend with hot reload)
pnpm tauri dev

# Type-check frontend (JSDoc types via tsconfig.json)
pnpm tsc --noEmit

# Build frontend for production
pnpm build

# Build Tauri app (frontend + Rust) — produces installers
pnpm tauri build

# Run Rust tests
cd src-tauri && cargo test

# Lint Rust
cd src-tauri && cargo clippy -- -D warnings

# Format Rust
cd src-tauri && cargo fmt
```

**Order for verification**: `pnpm tsc --noEmit && cd src-tauri && cargo clippy -- -D warnings && cargo test`

---

## Project Structure

```
aria/
├── src/                          # Vanilla JS frontend
│   ├── main.js                   # App entry, bootstraps all services/components
│   ├── bindings.js               # Tauri-specta generated TS bindings (commit this!)
│   ├── bindings.d.ts             # Type definitions (commit this!)
│   ├── components/               # Factory functions returning { destroy, ...methods }
│   │   ├── ChatView.js
│   │   ├── ThreadList.js
│   │   ├── PeerCard.js
│   │   ├── DiscoverModal.js
│   │   ├── MessageBubble.js
│   │   └── TypingIndicator.js
│   ├── services/                 # Business logic (singletons via IIFE)
│   │   ├── peerService.js        # Peer lifecycle, trust/block, discovery events
│   │   ├── connectionService.js  # TCP connection pool, reconnection logic
│   │   ├── handshakeService.js   # Protocol handshake, fingerprint verify
│   │   ├── messageService.js     # Send/recv, history, encryption stubs
│   │   └── typingService.js      # Typing indicators over TCP
│   ├── stores/                   # Pub/Sub state (tiny event bus)
│   │   ├── peerStore.js
│   │   ├── threadStore.js
│   │   ├── messageStore.js
│   │   └── connectionStore.js
│   ├── protocol/                 # Wire protocol types (mirrors Rust)
│   ├── utils/                    # DOM helpers, formatters
│   └── styles/                   # Tailwind entry + custom CSS
├── src-tauri/                    # Rust backend
│   ├── src/
│   │   ├── main.rs               # Tauri entry, plugin setup
│   │   ├── lib.rs                # Module exports, Tauri commands
│   │   ├── commands/             # #[tauri::command] handlers
│   │   ├── network/              # mDNS, TCP server, connection manager
│   │   ├── protocol/             # Envelope framing, message types, dispatcher
│   │   ├── crypto/               # Ed25519 keypair, fingerprint, signing
│   │   ├── db/                   # SQLite schema, migrations, queries
│   │   └── transfer/             # File chunking, progress, resume
│   ├── Cargo.toml
│   └── tauri.conf.json
├── index.html                    # Vite entry HTML
├── vite.config.ts                # Vite + Tailwind + Tauri dev config
├── tsconfig.json                 # JSDoc type-checking config
└── package.json
```

---

## Key Architectural Facts

| Aspect | Detail |
|--------|--------|
| **Entry point (JS)** | `src/main.js` — bootstraps stores, services, components on `DOMContentLoaded` |
| **Entry point (Rust)** | `src-tauri/src/main.rs` → `tauri::Builder::default().invoke_handler(...)` |
| **Type generation** | `tauri-specta` emits `src/bindings.js` + `src/bindings.d.ts` from `#[specta::type]` Rust types |
| **IPC** | `invoke("command_name", args)` from JS → `#[tauri::command]` in Rust; events via `tauri::Emitter` |
| **State (JS)** | Each store = `{ subscribe(fn), get(key), set(key, val), ... }` — plain objects, no framework |
| **Components (JS)** | Factory functions: `createChatView(container, peerId)` returns `{ destroy(), ... }` |
| **Network** | mDNS (`_aria._tcp.local`) for discovery → direct TCP (port 9473) for chat/file/voice |
| **Identity** | Ed25519 keypair generated on first run; fingerprint = `sha256(pubkey)[:16]` hex |
| **Trust** | Explicit trust required before auto-accepting files; stored in SQLite |

---

## Conventions Agents Must Follow

### Frontend (Vanilla JS)
- **No framework imports** — use native DOM APIs, `document.querySelector`, `classList`, `addEventListener`
- **Components = factories** — return plain objects with `destroy()` for cleanup
- **Stores = pub/sub** — `store.subscribe(fn)` returns unsubscribe; never mutate store directly
- **Services = IIFE singletons** — `const service = (() => { ... return { init, ... } })();`
- **Global exposure only for ChatView** — `window.messageService`, `window.typingService` (legacy compat)
- **Types via JSDoc** — `@typedef`, `@param`, `@returns`; `tauri-specta` types in `bindings.d.ts`
- **CSS via Tailwind utilities** — custom properties in `styles/main.css` for theming

### Backend (Rust)
- **Commands in `commands/`** — one file per domain (`peers.rs`, `message.rs`, `tcp.rs`, etc.)
- **Async everywhere** — `tokio::spawn` for background tasks; channels for cross-thread comms
- **Errors via `anyhow::Result`** — propagate to Tauri; frontend catches via `try { await invoke() } catch`
- **Events to frontend** — `app.emit("event-name", payload).unwrap()` from Tauri `AppHandle`
- **Specta types** — `#[derive(specta::Type)]` on all command args/returns; run `cargo build` to regenerate bindings

### Protocol
- **Envelope** — `{ version, type, sender, payload, timestamp, signature }`
- **Types**: `message`, `file_offer`, `file_chunk`, `file_complete`, `voice`, `heartbeat`, `typing`
- **Signing** — Ed25519 over `version|type|sender|payload|timestamp` (see `src-tauri/src/protocol/envelope.rs`)

---

## Testing & Verification

| Target | Command |
|--------|---------|
| Frontend type-check | `pnpm tsc --noEmit` |
| Rust unit tests | `cd src-tauri && cargo test` |
| Rust clippy | `cd src-tauri && cargo clippy -- -D warnings` |
| Full Tauri build | `pnpm tauri build` (slow — runs full Rust compile + Vite build) |

**No frontend unit tests exist yet** — manual testing via `pnpm tauri dev` on multiple machines.

---

## Reference Docs (in `Documentation/`)

| File | Purpose |
|------|---------|
| `TECH_STACK.md` | Full architecture, dependencies, protocol spec |
| `AGENTS.md` | Agent role definitions (Architect, Frontend, Rust-Core, Protocol, DevOps, Product, QA, Writer) |
| `SPEC.md` | Product spec & feature breakdown |
| `DESIGN.md` | UI/UX specs, component library |
| `PROTOCOL.md` | Wire protocol deep-dive |

---

## Common Pitfalls

- **Don't edit `bindings.js`/`bindings.d.ts` manually** — regenerate via `cd src-tauri && cargo build` (tauri-specta build.rs hook)
- **Don't import Rust types directly in JS** — use `commands` from `bindings.js`
- **Tauri dev port is fixed at 1420** (see `vite.config.ts`) — don't change without updating `tauri.conf.json`
- **SQLite migrations** — manual SQL in `src-tauri/src/db/schema.rs`; run on startup via version check
- **mDNS requires network permissions** — test on real LAN, not localhost loopback
- **File transfers > 1GB** — chunked streaming; check `transfer/` module for resume logic

---

## Git / CI Notes

- **No CI workflow yet** — GitHub Actions config needed for multi-platform builds
- **Commit generated bindings** — `src/bindings.js` and `src/bindings.d.ts` are tracked
- **Branch/PR conventions** — not documented; follow conventional commits if adding