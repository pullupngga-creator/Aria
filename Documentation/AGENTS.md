# Aria — AI Agent Roles

## Agent Architecture

Aria is built by a coordinated team of specialized AI agents, each owning a distinct domain. Agents communicate through structured outputs (code, schemas, specs) and operate under strict interface contracts.

---

## Agent: `ARCHITECT`

**Role**: System Designer & Integration Coordinator

**Responsibilities**:
- Define module boundaries and public APIs
- Enforce the two-panel layout contract (Vault + Canvas)
- Design the event bus for cross-panel communication
- Review all inter-module dependencies for circular references
- Own `src/aria/state.py` — the single source of truth for reactive state
- Define the `LLMClient` abstract base class in `src/aria/api/base.py`

**Output Format**:
- Python abstract classes and protocols
- Module dependency graphs (Mermaid or text)
- Interface specifications (input/output types)

**Constraints**:
- No UI code in this agent's output
- All state mutations must go through the central `AppState` singleton
- Must document async boundaries explicitly

---

## Agent: `UI_ENGINEER`

**Role**: Flet Interface Implementer

**Responsibilities**:
- Implement all Flet controls in `src/aria/ui/`
- Enforce the Design System (colors, typography, spacing)
- Build the two-panel shell with draggable divider
- Implement the Sources Vault list with virtualization
- Build the Chat Canvas with markdown rendering
- Create the @-mention dropdown with keyboard navigation
- Implement all micro-interactions (hover states, transitions, glows)

**Output Format**:
- Flet Python code (`ft.Column`, `ft.Row`, `ft.Container`, etc.)
- Custom control classes with `build()` methods
- Event handler wiring

**Constraints**:
- Must use only the color tokens from `DESIGN.md`
- No business logic in UI files — delegate to `state.py` or service modules
- All async operations must use `page.run_thread()` or `asyncio.create_task()`
- Support minimum window size: 1024×768

---

## Agent: `DOCUMENT_ENGINEER`

**Role**: Document Processing & Vault Specialist

**Responsibilities**:
- Implement file type detection and routing in `src/aria/document/parser.py`
- Build text extraction pipelines for PDF, DOCX, CSV, XLSX, MD, TXT
- Implement token counting with `tiktoken` and Gemini native counters
- Build the vault index (in-memory + SQLite) in `src/aria/document/vault.py`
- Implement vault search (filename + content preview fuzzy matching)
- Handle file system operations (copy to data dir, cleanup on delete)

**Output Format**:
- Python modules with pure functions for parsing
- SQLite schema for vault metadata
- Unit tests for each file type parser

**Constraints**:
- Must handle corrupted files gracefully (catch + toast error)
- Extracted text must be stored as UTF-8 `.txt` in `data/vault/`
- Token counts must be cached in SQLite, not recalculated
- Max file size: 50MB (reject with clear error message)

---

## Agent: `CONTEXT_ENGINEER`

**Role**: LLM Prompt Engineering & Context Injection

**Responsibilities**:
- Implement the system prompt builder in `src/aria/context/injector.py`
- Build the @-mention parser and resolver in `src/aria/context/mention.py`
- Design the context assembly protocol (user message + active sources → API payload)
- Implement token budget management (reserve space for system prompt + sources + user message)
- Build the streaming response handler with token-by-token UI updates
- Implement conversation summarization for long threads (context window management)

**Output Format**:
- Python functions for prompt assembly
- Jinja2 or f-string templates for system prompts
- Token budget calculation algorithms

**Constraints**:
- Must support both Gemini and Claude with provider-specific payload formats
- System prompt must include: "You are Aria, a research assistant. The following documents are attached as context..."
- Must truncate sources intelligently if they exceed token budget (priority: active sources > mentioned sources)
- All API calls must be async with timeout handling (30s default)

---

## Agent: `API_ENGINEER`

**Role**: External LLM Client Implementer

**Responsibilities**:
- Implement `GeminiClient` in `src/aria/api/gemini.py`
- Implement `ClaudeClient` in `src/aria/api/claude.py`
- Build the provider router (fallback logic, model selection)
- Handle API authentication (env vars, config file, key validation)
- Implement retry logic with exponential backoff (503/429 errors)
- Build response streaming adapters (unify Gemini and Claude streaming formats)

**Output Format**:
- Python async client classes inheriting from `LLMClient`
- Pydantic models for API request/response schemas
- Error handling utilities

**Constraints**:
- Must use `aiohttp` for all HTTP operations
- API keys must never be logged or committed
- Must support model switching mid-conversation (with clear UX warning)
- Implement rate limit tracking (tokens per minute, requests per minute)

---

## Agent: `QA_ENGINEER`

**Role**: Testing & Quality Assurance

**Responsibilities**:
- Write unit tests for all parser modules (`tests/test_parser.py`)
- Write integration tests for context injection (`tests/test_context.py`)
- Write UI interaction tests for @-mention system (`tests/test_mention.py`)
- Build a mock LLM server for offline testing
- Define performance benchmarks (parse time, API latency, memory usage)
- Validate color contrast and accessibility (WCAG 2.1 AA for text)

**Output Format**:
- `pytest` test suites
- Mock fixtures and factories
- Performance benchmark scripts

**Constraints**:
- Minimum 80% code coverage for business logic
- All async code must be tested with `pytest-asyncio`
- UI tests must use Flet's built-in test utilities

---

## Agent: `DEVOPS_ENGINEER`

**Role**: Build, Release & Distribution

**Responsibilities**:
- Configure `pyproject.toml` for `uv` and `flet build`
- Set up GitHub Actions for CI (type check, test, lint)
- Build desktop installers for macOS (`.app`), Windows (`.exe`), Linux (`.AppImage`)
- Manage code signing and notarization for macOS
- Build auto-update mechanism (check GitHub releases)
- Write installation documentation

**Output Format**:
- GitHub Actions YAML
- Build scripts (`scripts/build.sh`, `scripts/build.ps1`)
- Release notes templates

**Constraints**:
- All builds must be reproducible (lockfile committed)
- macOS build must be notarized for Gatekeeper compliance
- Windows build must be signed with EV certificate (or self-signed with clear warning)
