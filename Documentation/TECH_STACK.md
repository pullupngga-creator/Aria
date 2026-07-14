# TECH_STACK.md — Aria Architecture

## Core Framework: Tauri v2
- **Why**: Ultra-lightweight desktop runtime (< 15MB), native OS WebView, secure Rust backend, cross-platform (Windows, macOS, Linux). Perfect for a local-only utility that must feel native.
- **Version**: Tauri v2 (stable) for latest plugin system, notification APIs, and OS integration.

## Frontend Layer

| Technology | Role | Rationale |
|------------|------|-----------|
| **Vanilla JavaScript (ES2024)** | UI logic | Zero framework overhead, maximum control, direct DOM manipulation for high-performance chat rendering, minimal bundle size |
| **Tailwind CSS v4** | Styling | Utility-first, rapid UI development, design token integration via CSS variables, minimal CSS bundle |
| **Vite** | Build tool & dev server | Fast HMR, native ESM, simple config, handles Tailwind compilation and asset bundling |
| **TypeScript (JSDoc / `.d.ts`)** | Type safety | JSDoc annotations for vanilla JS + generated `.d.ts` from Rust bindings via `tauri-specta`; no TS compilation step required |
| **lucide** | Icons | Lightweight SVG icon set, vanilla JS compatible |
| **CSS Custom Properties** | Theming | Native dark/light mode switching without JS framework re-renders |

## Backend / Core (Rust)

| Crate | Role |
|-------|------|
| **tauri** | App runtime, command system, window management, OS notifications |
| **tokio** | Async runtime for all network I/O, peer handling, and file streaming |
| **mdns-sd** | mDNS service discovery (Zeroconf/Bonjour) for LAN peer auto-discovery |
| **tokio::net** | TCP listeners and sockets for direct P2P connections and file transfers |
| **tokio::sync** | Channels for cross-thread communication between network layer and Tauri commands |
| **serde + serde_json** | Serialization for frontend ↔ backend communication and wire protocol |
| **tauri-specta** | Auto-generate TypeScript bindings from Rust commands |
| **rusqlite** | Embedded SQLite for chat history, peer metadata, and settings |
| **ed25519-dalek** | Peer identity: keypair generation, signing, fingerprint verification |
| **ring** | Cryptographic primitives (if adding encryption layer post-MVP) |
| **hound** | WAV audio encoding/decoding for voice messages |
| **anyhow / thiserror** | Error handling |
| **directories** | OS-appropriate paths for config, data, and downloads |

## Network Protocol Stack

### Discovery: mDNS (Zeroconf)
- Aria broadcasts `_aria._tcp.local` service on startup
- Rust `mdns-sd` listener scans for matching services
- Peer metadata (display name, fingerprint, port) encoded in TXT records
- Frontend receives live peer list updates via Tauri events

### Transport: Direct TCP
- Each peer opens a persistent TCP listener on a configurable port (default: 9473)
- Connection handshake: fingerprint exchange + trust verification
- Message framing: length-prefixed JSON envelopes (`{ type, payload, signature }`)
- File transfer: dedicated TCP stream or chunked over main socket with progress callbacks
- Heartbeat: 30-second ping/pong for online status detection

### Wire Protocol (JSON Envelope)
```json
{
  "version": 1,
  "type": "message" | "file_offer" | "file_chunk" | "file_complete" | "voice" | "heartbeat" | "typing",
  "sender": "<ed25519_public_key_fingerprint>",
  "payload": { ... },
  "timestamp": 1752082800,
  "signature": "<base64_signature>"
}
```

## Build & DevOps

| Tool | Purpose |
|------|---------|
| **Cargo** | Rust package manager & build |
| **pnpm** | JS package manager (Tailwind, Vite, dev dependencies) |
| **Vite** | Frontend bundling, HMR, static asset handling |
| **GitHub Actions** | CI/CD: build, test, sign, release for all platforms |
| **Tauri CLI** | `tauri build`, `tauri dev`, bundling, updater |

## Database (Local SQLite)
- **rusqlite** with `bundled` feature (zero external dependency)
- Stores: peer identities, chat messages, file transfer metadata, settings, trust lists
- Migration: manual SQL scripts executed on startup version check

## Security
- **Peer Identity**: Ed25519 keypair generated on first launch; public key fingerprint shown to users for manual verification
- **Trust Model**: Explicit trust required before auto-accepting files (configurable)
- **Local Only**: All traffic stays on LAN; no external servers, no cloud relay
- **Tauri CSP**: Strict Content Security Policy preventing external resource loading
- **File Validation**: Sanitize received filenames; write to sandboxed downloads directory

## Project Structure

```
aria/
├── src/                          # Vanilla JS frontend source
│   ├── main.js                   # Vite entry point, app bootstrap
│   ├── index.html                # HTML shell
│   ├── app.js                    # Root app controller, pane management
│   ├── components/               # ES6 class/factory components
│   │   ├── Sidebar.js
│   │   ├── ThreadList.js
│   │   ├── ChatView.js
│   │   ├── MessageBubble.js
│   │   ├── FileTransfer.js
│   │   ├── VoiceRecorder.js
│   │   ├── InputBar.js
│   │   ├── PeerCard.js
│   │   ├── Modal.js
│   │   └── Toast.js
│   ├── services/                 # Business logic modules
│   │   ├── peerService.js        # Peer list state, discovery event handling
│   │   ├── chatService.js        # Message send/receive, history loading
│   │   ├── fileService.js        # File transfer orchestration
│   │   └── voiceService.js       # Audio recording and playback
│   ├── stores/                   # Lightweight state modules (Pub/Sub pattern)
│   │   ├── peerStore.js
│   │   ├── messageStore.js
│   │   └── settingsStore.js
│   ├── utils/                    # DOM helpers, formatters, event bus
│   ├── styles/                   # Tailwind entry + custom CSS
│   │   ├── main.css
│   │   └── theme.css             # CSS custom properties (light/dark)
│   └── types/                    # Generated + manual JSDoc types
├── src-tauri/                    # Rust backend
│   ├── src/
│   │   ├── main.rs               # Entry point, Tauri setup
│   │   ├── commands/             # Tauri invoke handlers
│   │   ├── network/              # mDNS discovery, TCP server, peer connections
│   │   ├── protocol/             # Wire protocol: framing, envelope parsing
│   │   ├── crypto/               # Keypair, fingerprint, signing
│   │   ├── transfer/             # File send/receive, chunking, progress
│   │   ├── voice/                # Audio encoding, chunk streaming
│   │   ├── db/                   # SQLite schema & queries
│   │   └── models/               # Rust data structures
│   ├── Cargo.toml
│   └── tauri.conf.json
├── public/                       # Static assets (fonts, illustrations)
├── vite.config.js
├── tailwind.config.js
└── package.json
```

## Scalability Path
- Tauri v2 plugins allow packaging shared Rust networking logic for future Aria utilities
- The vanilla JS frontend can be incrementally migrated to a framework if complexity demands it
- Rust protocol and network layers are decoupled from Tauri and can be exposed as a standalone daemon or library
- Post-MVP: WebRTC data channels for NAT traversal; DHT for cross-LAN discovery
