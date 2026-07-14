# ROADMAP.md — Aria Build Plan

## Phase 0: Foundation (Weeks 1–2)
**Goal**: Working development environment and project skeleton

- [x] Initialize Tauri v2 + Vite + Vanilla JS project scaffold
- [x] Configure Tailwind CSS v4 with Aria design tokens (light/dark modes)
- [x] Set up Rust toolchain, `tauri-specta` for JS bindings
- [x] Configure SQLite with `rusqlite` + migration system
- [x] Implement Ed25519 keypair generation and fingerprinting (`ed25519-dalek`)
- [x] Set up CI/CD pipeline (GitHub Actions) for build matrix
- [x] Establish folder structure and coding standards (`RULES.md`)
- [x] **Milestone**: `cargo tauri dev` launches a styled empty window with theme toggle

---

## Phase 1: Discovery & Identity (Weeks 3–4)
**Goal**: Peers can find each other automatically on the same LAN

- [x] Implement mDNS service broadcast (`mdns-sd`) — Aria announces itself
- [x] Implement mDNS listener — scans for other Aria instances
- [x] Build peer identity system: keypair generation, fingerprint display, persistent storage
- [x] Create peer list UI with online/offline status
- [x] Implement Tauri events: `peer:discovered`, `peer:offline`, `peer:updated`
- [x] Add peer search/filter and manual refresh
- [x] Handle edge cases: multiple network interfaces, mDNS disabled, IP changes
- [x] **Milestone**: Two instances on the same Wi-Fi see each other in the peer list
=======
---

## Phase 2: Direct Messaging (Weeks 5–7)
**Goal**: Real-time one-to-one text chat between peers

- [x] Implement TCP server (persistent listener) and client connection manager
- [x] Design and implement wire protocol: JSON envelope with type, payload, signature
- [x] Build connection handshake: fingerprint exchange + trust check
- [x] Implement message send/receive pipeline with delivery receipts
- [x] Build ChatView component with message bubbles, timestamps, scroll anchoring
- [x] Implement conversation list (ThreadList) with last message preview
- [ ] Add typing indicators (heartbeat packets + UI animation)
- [ ] Persist all messages to SQLite with conversation threading
- [ ] Implement unread counters and conversation sorting
- [ ] **Milestone**: Two users can send text messages back and forth with delivery confirmation

---

## Phase 3: File Transfer (Weeks 8–9)
**Goal**: Fast, reliable P2P file sharing

- [ ] Implement file offer/accept protocol over TCP
- [ ] Build file chunking and streaming engine (64KB buffers, async I/O)
- [ ] Add progress tracking with real-time events to frontend
- [ ] Build drag-and-drop UI and file picker integration
- [ ] Implement inline image previews in chat bubbles
- [ ] Add "Open file" and "Show in folder" actions for received files
- [ ] Handle trust-based auto-accept vs. manual approval prompt
- [ ] Implement transfer resume for interrupted connections (post-MVP: basic retry)
- [ ] Test with large files (100MB, 1GB, 5GB)
- [ ] **Milestone**: Users can send and receive files at full LAN speed with progress UI

---

## Phase 4: Voice Messages (Weeks 10–11)
**Goal**: Record and send voice messages inline

- [ ] Implement Web Audio API recording in frontend (`MediaRecorder`)
- [ ] Encode audio to WAV in Rust (`hound` crate) or send raw PCM
- [ ] Build VoiceRecorder component: record button, timer, waveform preview
- [ ] Transmit voice chunks over TCP (or small files)
- [ ] Build inline audio player with waveform visualization (Canvas 2D)
- [ ] Add playback controls: play/pause, scrub, speed toggle
- [ ] Persist voice metadata (duration, waveform data) in SQLite
- [ ] Handle microphone permission gracefully across platforms
- [ ] **Milestone**: Users can record, send, and play voice messages in chat

---

## Phase 5: Trust, Settings & Polish (Weeks 12–13)
**Goal**: Production-ready security, preferences, and UX refinement

- [ ] Implement trust model: trust/untrust/block with UI actions
- [ ] Add peer fingerprint verification modal
- [ ] Build Settings panel: name, avatar, theme, download folder, audio device, port
- [ ] Implement OS-native notifications via Tauri
- [ ] Add keyboard shortcuts (search, settings, send)
- [ ] Implement dark mode with full CSS custom property toggle
- [ ] Optimize startup time (< 2 seconds cold start)
- [ ] Memory profiling and leak fixes (especially for long-running network tasks)
- [ ] Cross-platform testing: Windows, macOS, Linux on real LAN
- [ ] **Milestone**: App feels stable, secure, and native on all platforms

---

## Phase 6: Distribution & Launch (Weeks 14–15)
**Goal**: Public release and community feedback

- [ ] Code signing and notarization (Apple, Microsoft)
- [ ] Tauri auto-updater configuration
- [ ] Write user documentation: "How Aria works," "Trust & Safety," "Troubleshooting"
- [ ] Create landing page / website for Aria
- [ ] Beta testing with 15–30 users across target personas
- [ ] Bug fixes and stability patches based on feedback
- [ ] Prepare GitHub release with binaries for all platforms
- [ ] **Milestone**: v1.0 public release of Aria

---

## Phase 7: Ecosystem Expansion (Post-v1.0)
**Goal**: Scale from utility to local communication platform

- [ ] **Group Chat**: Multicast messaging to multiple peers (UDP or mesh TCP)
- [ ] **Screen Share**: Capture and stream screen region to peer (WebRTC or custom)
- [ ] **Cross-LAN Discovery**: DHT or relay for WAN peer finding (optional, privacy-preserving)
- [ ] **Mobile Companion**: Tauri mobile or Flutter wrapper for iOS/Android
- [ ] **Plugin System**: Allow third-party integrations (whiteboard, code editor sync)
- [ ] **Milestone**: Aria v2.0 with group chat and screen sharing

---

## Risk Mitigation
| Risk | Mitigation |
|------|------------|
| mDNS blocked on corporate networks | Fallback to manual IP entry + TCP direct connect; document clearly |
| Cross-platform network quirks | Test on real hardware weekly; use `tokio` abstractions, not raw sockets |
| Large file transfer memory pressure | Stream in 64KB chunks; never buffer entire file; test with 5GB+ files |
| Firewall blocking listen port | Auto-detect blocked port; suggest alternative; allow user override in settings |
| Scope creep (group chat, video) | Strict MVP gate at end of Phase 4; post-MVP features go to Phase 7 backlog |
