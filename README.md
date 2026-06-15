# Aria — Desktop-first Cognitive Workspace

Aria is a premium, desktop-first cognitive workspace that transforms static document storage into a real-time contextual intelligence environment. It bridges the gap between file management and AI-assisted thinking through an interactive two-panel laboratory interface.

## Development Status

**Phase 0: Foundation** (Weeks 1–2) - In Progress

## Quick Start

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run the app
uv run flet run src/aria/main.py
```

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

## Development Workflow

```bash
# Run with hot-reload
uv run flet run src/aria/main.py

# Type check
uv run mypy src/

# Test
uv run pytest tests/ -v

# Build desktop bundle
flet build macos    # or windows, linux
```

## Documentation

- [Product Specification](Documentation/SPEC.md)
- [Design System](Documentation/DESIGN.md)
- [Technical Stack](Documentation/TECH_STACK.md)
- [Development Roadmap](Documentation/ROADMAP.md)
- [Coding Rules](Documentation/RULES.md)

## License

TBD
