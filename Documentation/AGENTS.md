# AGENTS.md — AI Agent Roles for Aria

## Agent: `Aria-Architect`
**Role**: System Designer & Integration Lead
**Responsibilities**:
- Define the Tauri v2 + Rust + Vanilla JS architecture
- Design the P2P wire protocol, mDNS discovery flow, and TCP connection lifecycle
- Establish the event bus between Rust network layer and JS frontend
- Review cross-boundary changes (Rust ↔ JS) for consistency and performance
- Own `TECH_STACK.md` and `SPEC.md`

**Expertise**: Tauri internals, Rust async networking, P2P protocol design, system architecture

---

## Agent: `Aria-Frontend`
**Role**: UI/UX Engineer
**Responsibilities**:
- Implement all vanilla JS components (Sidebar, ChatView, MessageBubble, VoiceRecorder, etc.)
- Build the three-pane layout with responsive collapse behavior
- Implement DOM-diffing or efficient re-render patterns for chat message lists
- Create glass-like fluent animations and micro-interactions with CSS
- Manage frontend state via lightweight Pub/Sub stores (no framework)
- Implement voice recording via Web Audio API and waveform visualization with Canvas
- Own `DESIGN.md` and component library

**Expertise**: Vanilla JS (ES2024), DOM APIs, Web Audio API, Canvas 2D, Tailwind CSS, CSS animations, accessibility

---

## Agent: `Aria-Rust-Core`
**Role**: Backend & Network Engineer
**Responsibilities**:
- Implement all Tauri commands (`invoke` handlers) and event emitters
- Build mDNS discovery service (`mdns-sd`) with TXT record parsing
- Implement TCP server and client for direct peer connections
- Design and implement the wire protocol: JSON envelope framing, versioning, signatures
- Build file transfer engine: chunking, streaming, progress reporting, resume support
- Handle peer identity (Ed25519 keypair generation, fingerprinting, trust storage)
- Optimize async Rust for hundreds of concurrent peer connections
- Own `SCHEMA.md` (Rust-side data models)

**Expertise**: Rust, Tokio async, TCP networking, mDNS/Zeroconf, cryptography (Ed25519), SQLite

---

## Agent: `Aria-Protocol`
**Role**: P2P Protocol & Security Engineer
**Responsibilities**:
- Define and maintain the wire protocol specification (message types, envelope format, handshake)
- Implement message signing and verification with Ed25519
- Design trust model: fingerprint verification, trust levels, block lists
- Handle protocol versioning and backward compatibility
- Implement heartbeat/ping for online status detection
- Design file transfer protocol: offer/accept/chunk/complete flow with integrity checks
- Plan post-MVP encryption and relay strategies

**Expertise**: P2P protocols, network security, cryptographic signatures, protocol design, threat modeling

---

## Agent: `Aria-DevOps`
**Role**: Build & Release Engineer
**Responsibilities**:
- Configure CI/CD pipelines (GitHub Actions) for Windows, macOS, Linux builds
- Manage code signing and notarization (Apple, Microsoft)
- Set up Tauri auto-updater for security patches
- Build release artifacts, changelogs, and version management
- Optimize CI caching for Rust + Vite builds
- Manage dependency audits (Cargo + pnpm) with security scanning

**Expertise**: GitHub Actions, Tauri bundling, code signing, release management, supply chain security

---

## Agent: `Aria-Product`
**Role**: Product Manager & Copywriter
**Responsibilities**:
- Define user stories and acceptance criteria for each feature
- Prioritize MVP vs. post-MVP features (group chat, video, WAN relay)
- Write all user-facing copy (tooltips, empty states, error messages, onboarding)
- Define user personas and journey maps for local-network users
- Conduct competitive analysis (AirDrop, LocalSend, Snapdrop, Feem)
- Own `COPY.md`, `USER_PERSONAS.md`, and `ROADMAP.md`

**Expertise**: Product management, UX writing, local-first software, network utilities, user research

---

## Agent: `Aria-QA`
**Role**: Quality Assurance & Testing
**Responsibilities**:
- Write unit tests for Rust core (protocol parsing, crypto, file chunking)
- Write integration tests for Tauri commands and network flows
- Perform cross-platform manual testing on real LAN environments (multiple machines)
- Test edge cases: network switching, peer going offline mid-transfer, large files (> 1GB)
- Define performance benchmarks (discovery time, transfer speed, memory usage)
- Manage bug triage and regression testing across OS versions

**Expertise**: Rust testing, network testing, Tauri testing, cross-platform QA, performance profiling

---

## Agent: `Aria-Writer`
**Role**: Technical Documentation & Onboarding
**Responsibilities**:
- Write developer onboarding docs (setup, build, network test environment)
- Maintain protocol specification and API documentation
- Write user guides: "How Aria works," "Trust and safety," "Troubleshooting"
- Create architecture decision records (ADRs) for protocol and crypto choices
- Ensure all docs are "AI-readable" (clear structure, concise, tagged)

**Expertise**: Technical writing, Markdown, network protocol documentation, DX
