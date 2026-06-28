# Aria — Development Roadmap

## Phase 0: Foundation (Weeks 1–2)
**Goal**: Running desktop shell with document upload and basic chat

### Milestones
- [x] Project scaffolding with `uv` + `flet`
- [x] Two-panel layout shell (Vault + Canvas) with draggable divider
- [x] Color system and typography tokens implemented
- [x] SQLite schema initialized on first launch
- [x] Document upload (drag-and-drop + file picker) for PDF and TXT
- [x] Basic text extraction with `pymupdf`
- [x] Vault list rendering with file metadata
- [x] Source activation toggle (click to bind/unbind)
- [x] Chat input bar with send functionality
- [x] Integration with one LLM provider (Gemini) — non-streaming
- [x] Conversation persistence to SQLite

**Deliverable**: "Aria Alpha" — internal testing, single-user, single-provider

---

## Phase 1: Core Intelligence (Weeks 3–4)
**Goal**: Context-aware conversations with @-mention system

### Milestones
- [x] @-mention parser and inline dropdown (fuzzy search, keyboard nav)
- [x] Context injection engine (system prompt builder + source text assembly)
- [x] Token budget management (count, display, enforce limits)
- [x] Streaming response rendering (token-by-token display)
- [x] Multi-provider support (Gemini + Openrouter with unified interface)
- [x] Document parsing expanded: DOCX, CSV, XLSX, Markdown
- [ ] Vault search (filename + content preview)
- [ ] Message actions: copy, regenerate, delete
- [ ] Conversation management: new, rename, archive
- [ ] Settings panel: API keys, model selection, preferences

**Deliverable**: "Aria Beta" — closed user testing with researchers and writers

---

## Phase 2: Polish & Performance (Weeks 5–6)
**Goal**: Production-ready stability and refined UX

### Milestones
- [ ] Virtualized vault list (performance for 100+ documents)
- [ ] Paginated conversation history (lazy-load older messages)
- [ ] Markdown rendering: code blocks with syntax highlighting, tables, blockquotes
- [ ] Toast notification system (upload complete, errors, API status)
- [ ] Keyboard shortcuts (new chat, search, settings, send)
- [ ] Onboarding flow (first-launch welcome + guided tour)
- [ ] Export conversations to Markdown/JSON
- [ ] Auto-save and crash recovery
- [ ] Comprehensive error handling with user-friendly messages
- [ ] Unit test coverage > 80% for business logic
- [ ] Type checking with `mypy --strict` passing

**Deliverable**: "Aria v1.0 RC" — release candidate, public beta

---

## Phase 3: Distribution (Week 7)
**Goal**: Cross-platform desktop release

### Milestones
- [ ] macOS build (`.app` bundle, signed + notarized)
- [ ] Windows build (`.exe` installer, signed)
- [ ] Linux build (`.AppImage`)
- [ ] Auto-update mechanism (check GitHub releases)
- [ ] Installation documentation + quick-start guide
- [ ] GitHub repository public with README and contributing guide
- [ ] Release notes and changelog

**Deliverable**: "Aria v1.0" — public release

---

## Phase 4: Post-Launch (Months 2–3)
**Goal**: Community-driven enhancements

### Milestones
- [ ] Folder/tag organization in Sources Vault
- [ ] Conversation templates (research, analysis, summarization)
- [ ] Citation mode: AI responses include [Source: filename] references
- [ ] Dark/light theme toggle
- [ ] Custom system prompt presets
- [ ] Import from Zotero, Obsidian, Notion
- [ ] Plugin architecture (community extensions)
- [ ] Analytics: token usage dashboard, conversation insights

**Deliverable**: "Aria v1.1–1.3" — iterative improvements

---

## Phase 5: Scale (Month 4+)
**Goal**: Enterprise and team features

### Milestones
- [ ] Cloud sync option (encrypted, optional)
- [ ] Team workspaces with shared vaults
- [ ] Role-based access control
- [ ] Audit logs for compliance
- [ ] SSO integration (OAuth, SAML)
- [ ] Self-hosted deployment option
- [ ] API for third-party integrations

**Deliverable**: "Aria Teams" — enterprise tier

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Flet desktop build issues | High | Early prototype build in Week 1; fallback to PyQt if critical |
| LLM API rate limits | Medium | Implement aggressive caching; support multiple providers |
| Large PDF parse failures | Medium | Graceful degradation; extract partial text; user notification |
| Context window exceeded | Medium | Smart truncation; token counter UI; user override option |
| SQLite concurrency | Low | WAL mode; single-writer architecture |

---

## Definition of Done (Per Phase)

- [ ] All milestones complete
- [ ] `mypy --strict` passes with zero errors
- [ ] `pytest` suite passes (minimum 80% coverage)
- [ ] Manual QA on macOS, Windows, Linux
- [ ] No critical or high-severity bugs in tracker
- [ ] Documentation updated (README, CHANGELOG)
- [ ] Performance targets met (see TECH_STACK.md)
