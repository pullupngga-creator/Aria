# Aria — Technical Stack

## Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Aria Desktop Application                    │
│  ┌─────────────────┐  ┌─────────────────────────────────┐ │
│  │   Sources Vault  │  │        AI Chat Canvas            │ │
│  │   (Flet UI)      │  │        (Flet UI)                 │ │
│  └────────┬────────┘  └─────────────────┬─────────────────┘ │
│           │                             │                   │
│  ┌────────▼─────────────────────────────▼─────────────────┐ │
│  │              Aria Core Engine (Python)                │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │  Document   │  │   Context    │  │   Session    │ │ │
│  │  │  Parser     │  │   Manager    │  │   Manager    │ │ │
│  │  └─────────────┘  └──────────────┘  └──────────────┘ │ │
│  └────────────────────────┬──────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐ │
│  │              External LLM APIs (Cloud)                 │ │
│  │     Google Gemini API  |  Anthropic Claude SDK          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Choices

### UI Framework: Flet
| Aspect | Decision |
|--------|----------|
| **Framework** | Flet (`flet`) — Python-to-Flutter bridge |
| **Rendering** | Flutter C++ engine with native hardware acceleration |
| **Target** | Desktop (macOS, Windows, Linux) via `flet build` |
| **Why** | Single-language stack (Python), 60fps rendering, native window chrome, minimal bundle size |

### Package Management: uv
| Aspect | Decision |
|--------|----------|
| **Tool** | `uv` (Astral, Rust-based) |
| **Commands** | `uv venv`, `uv pip install`, `uv run` |
| **Why** | 100× faster environment creation, lockfile support (`uv.lock`), reproducible builds, no pip overhead |

### Language & Runtime
| Aspect | Decision |
|--------|----------|
| **Language** | Python 3.12+ |
| **Type Hints** | Strict `mypy` compliance, `TypedDict` for API responses |
| **Async** | `asyncio` + `aiohttp` for non-blocking API calls |

### LLM Integration
| Provider | SDK / Package | Use Case |
|----------|---------------|----------|
| **Google Gemini** | `google-generativeai` | Primary — massive context windows (1M+ tokens), fast throughput |
| **Anthropic Claude** | `anthropic` | Secondary — superior reasoning, long-form analysis |
| **OpenAI** | `openai` | Tertiary — fallback option |

### Document Processing
| Function | Library |
|----------|---------|
| **PDF text extraction** | `pymupdf` (fitz) — fast, accurate, metadata-rich |
| **DOCX parsing** | `python-docx` — structured paragraph extraction |
| **CSV/Excel** | `pandas` — robust data frame + text serialization |
| **Markdown** | `markdown` — AST parsing for structure awareness |
| **Plain text** | Native Python I/O |
| **Token counting** | `tiktoken` (OpenAI) or `google-generativeai` native counting |

### Data Persistence
| Layer | Technology |
|-------|------------|
| **Local cache** | SQLite (`sqlite3` stdlib) — document metadata, conversation history |
| **Document storage** | Local filesystem (user data dir) — raw extracted text as `.txt` |
| **Config** | `pydantic-settings` + TOML file (`~/.aria/config.toml`) |

### State Management
| Pattern | Implementation |
|---------|---------------|
| **App state** | Singleton `AppState` class with observable properties |
| **UI reactivity** | Flet's built-in `page.update()` + custom event bus |
| **Conversation state** | In-memory with SQLite persistence on mutation |

---

## Project Structure

```
aria/
├── pyproject.toml           # uv project config, dependencies
├── uv.lock                  # Reproducible lockfile
├── README.md
├── src/
│   ├── aria/
│   │   ├── __init__.py
│   │   ├── main.py           # Entry point, Flet app initialization
│   │   ├── config.py         # Pydantic settings, paths, API keys
│   │   ├── state.py          # Global app state manager
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── gemini.py     # Google Gemini client wrapper
│   │   │   ├── claude.py     # Anthropic Claude client wrapper
│   │   │   └── base.py       # Abstract LLM client interface
│   │   ├── document/
│   │   │   ├── __init__.py
│   │   │   ├── parser.py     # File type router + text extraction
│   │   │   ├── tokenizer.py  # Token counting utilities
│   │   │   └── vault.py      # Vault CRUD + search operations
│   │   ├── context/
│   │   │   ├── __init__.py
│   │   │   ├── injector.py   # System prompt builder with source injection
│   │   │   └── mention.py    # @-mention parser and resolver
│   │   ├── chat/
│   │   │   ├── __init__.py
│   │   │   ├── session.py    # Conversation thread manager
│   │   │   ├── renderer.py   # Markdown → Flet controls
│   │   │   └── history.py    # SQLite persistence for messages
│   │   └── ui/
│   │       ├── __init__.py
│   │       ├── app.py        # Root layout, two-panel shell
│   │       ├── vault_panel.py    # Sources Vault component
│   │       ├── chat_panel.py     # Chat Canvas component
│   │       ├── input_bar.py      # Prompt input with @-mention
│   │       ├── message_bubble.py # User/AI message rendering
│   │       └── components.py     # Shared UI primitives
│   └── assets/
│       ├── fonts/            # Inter/Geist font files
│       └── icons/            # Custom icon set (SVG)
├── data/                     # Runtime data (gitignored)
│   ├── vault/                # Extracted text files
│   └── aria.db               # SQLite database
└── tests/
    ├── test_parser.py
    ├── test_context.py
    └── test_mention.py
```

---

## Development Workflow

```bash
# 1. Bootstrap
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 2. Run (hot-reload)
uv run flet run src/aria/main.py

# 3. Build desktop bundle
flet build macos    # or windows, linux

# 4. Type check
uv run mypy src/

# 5. Test
uv run pytest tests/ -v
```

---

## Key Dependencies

```toml
[project]
name = "aria"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "flet>=0.25.0",
    "google-generativeai>=0.8.0",
    "anthropic>=0.40.0",
    "pymupdf>=1.25.0",
    "python-docx>=1.1.0",
    "pandas>=2.2.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "aiohttp>=3.11.0",
    "markdown>=3.7.0",
    "tiktoken>=0.8.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "mypy>=1.13", "ruff>=0.8"]
```

---

## Performance Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| Cold start | < 2s | Lazy-load LLM clients, async init |
| Document parse (10MB PDF) | < 2s | `pymupdf` parallel page extraction |
| @-mention dropdown | < 100ms | In-memory vault index, no I/O |
| API first token | < 5s | Streaming response, async HTTP |
| UI frame rate | 60fps | Flet/Flutter native rendering, virtualized lists |
| Memory footprint | < 500MB | Stream large docs, SQLite pagination |
