# SPEC.md — Aria (MVP)

## Overview
Aria is a lightweight, privacy-first peer-to-peer desktop application for instant communication and high-speed file sharing over local Wi-Fi. It requires zero configuration, no internet connection, and no centralized servers. Users discover peers automatically on the same network, then chat, exchange files, and send voice messages through direct device-to-device connections.

## MVP Features

### 1. Local Peer Discovery
- Auto-discover other Aria instances on the same LAN via mDNS (Bonjour/Zeroconf)
- Display a live peer list with hostname, avatar, and online status
- Manual "Refresh Discovery" button with subtle network scan animation
- Peer verification via auto-generated fingerprint (short hash of public key)

### 2. Real-Time Text Chat
- One-to-one direct messaging with any discovered peer
- Message timestamps, read receipts (local-network acknowledgment)
- Typing indicators via lightweight heartbeat packets
- Persistent chat history per peer (local SQLite)
- Markdown-lite support: bold, italic, code blocks, links

### 3. File Transfer
- Drag-and-drop or file picker to send any file type to a peer
- Direct TCP socket pipeline for ultra-fast LAN transfer
- Progress bar with live speed (MB/s) and ETA
- Auto-accept from trusted peers; prompt for untrusted
- Received files auto-saved to configurable "Downloads/Aria" folder
- Inline preview for images in chat thread

### 4. Voice Messages
- Record short audio clips (max 5 minutes) from the chat input
- Direct stream or chunked transfer to peer
- Inline playback with waveform visualization
- Pause, resume, and scrub within the chat bubble

### 5. Connection & Trust Management
- Each peer has a persistent identity (Ed25519 keypair generated on first launch)
- Trust levels: "Untrusted" → "Trusted" → "Blocked"
- Blocked peers are ignored entirely (no discovery, no connection)
- Optional "Require approval" mode for all incoming connections

### 6. Settings & Preferences
- Display name and avatar customization
- Default download directory
- Audio input device selection
- Notification preferences (OS native notifications via Tauri)
- Dark / Light / System theme toggle

## User Flow

```
┌─────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│   Launch    │────▶│  Auto-Discover LAN  │────▶│  Peer List View  │
│   Aria      │     │  (mDNS Broadcast)   │     │  (Online peers)  │
└─────────────┘     └─────────────────────┘     └──────────────────┘
                                                        │
                    ┌───────────────────────────────────┼───────────────────────────┐
                    ▼                                   ▼                           ▼
            ┌──────────────┐                  ┌──────────────┐            ┌──────────────┐
            │  Start Chat  │                  │  Send File   │            │ Send Voice   │
            │  (Text Thread)│                  │  (Drag/Drop) │            │  (Record)    │
            └──────────────┘                  └──────────────┘            └──────────────┘
                    │                                   │                           │
                    └───────────────────────────────────┼───────────────────────────┘
                                                        ▼
                                                ┌──────────────┐
                                                │  Direct P2P  │
                                                │  TCP Pipe    │
                                                └──────────────┘
                                                        │
                                                        ▼
                                                ┌──────────────┐
                                                │   Delivered  │
                                                │   (Receipt)  │
                                                └──────────────┘
```

## Key Interactions
- **Discovery**: Rust mDNS listener broadcasts Aria service → frontend receives peer list updates via Tauri events (`peer:discovered`, `peer:offline`)
- **Chat**: Frontend sends `send_message` invoke → Rust opens TCP socket to peer → delivers payload → peer Rust receives → stores in DB → emits `message:received` to peer's frontend
- **File Transfer**: Frontend sends `send_file` with path → Rust reads file in chunks → streams over TCP with progress events → peer receives → writes to disk → emits `file:received`
- **Voice**: Frontend records via Web Audio API → sends Blob to Rust → Rust packages and transmits → peer receives → stores → frontend renders waveform + audio player
- **Trust**: Frontend sends `trust_peer` / `block_peer` → Rust updates DB → filters discovery and connection attempts

## Out of Scope (Post-MVP)
- Group chats / multicast messaging
- Screen sharing or video calls
- End-to-end encryption over the internet (relay servers)
- Cross-LAN discovery (WAN / DHT)
- Mobile companion app
- File versioning or sync
