# Aria — Coding Rules & Standards

## Philosophy

Write code as if the next developer is a sleep-deprived researcher at 2 AM who needs to fix a critical bug before a deadline. Clarity trumps cleverness. Explicit trumps implicit.

---

## Python Standards

### Type Safety
- **Mandatory**: All functions must have type hints (`def parse_pdf(path: Path) -> str:`)
- **Mandatory**: Return `None` explicitly, never implicit
- **Mandatory**: Use `TypedDict` for API response structures
- **Mandatory**: Enable `strict = True` in `mypy.ini`
- **Forbidden**: `Any` type except in external library wrappers with `# type: ignore` justification

### Async Patterns
- **Mandatory**: All I/O operations must be async (`async def`, `await`)
- **Mandatory**: Use `aiohttp` for HTTP, `aiosqlite` for database
- **Mandatory**: Never block the UI thread — use `page.run_thread()` for CPU-bound work
- **Forbidden**: `time.sleep()` in async code — use `asyncio.sleep()`

### Error Handling
- **Mandatory**: All exceptions must be caught at module boundaries
- **Mandatory**: Custom exceptions inherit from `AriaError` base class
- **Mandatory**: Log exceptions with context before converting to user-facing messages
- **Mandatory**: API errors must include retry logic with exponential backoff
- **Forbidden**: Bare `except:` clauses — always specify exception types

```python
# GOOD
from aria.exceptions import AriaError, DocumentParseError

try:
    text = parser.extract(file_path)
except FileNotFoundError as e:
    logger.error("Document not found", extra={"path": str(file_path)})
    raise DocumentParseError(f"File missing: {file_path}") from e

# BAD
try:
    text = parser.extract(file_path)
except:
    return None
```

### Imports
- **Mandatory**: Use `isort` (black-compatible profile)
- **Order**: stdlib → third-party → first-party → local
- **Mandatory**: Absolute imports only — no relative imports beyond `from aria import ...`

---

## Flet UI Standards

### Component Structure
- **Mandatory**: Every custom control is a class inheriting from `ft.UserControl` or `ft.Column`/`ft.Row`
- **Mandatory**: Each control class has a `build()` method that returns the control tree
- **Mandatory**: State changes trigger `self.update()` — never mutate controls directly without update

```python
# GOOD
class SourceItem(ft.Container):
    def __init__(self, document: Document) -> None:
        super().__init__()
        self.document = document
        self.bgcolor = COLORS["bg_obsidian"]

    def activate(self) -> None:
        self.document.is_active = True
        self.bgcolor = COLORS["bg_active"]
        self.border = ft.border.only(left=ft.BorderSide(3, COLORS["accent_electric"]))
        self.update()
```

### Event Handling
- **Mandatory**: All event handlers are async (`async def on_click(e: ft.ControlEvent)`)
- **Mandatory**: Debounce rapid events (search input: 150ms, resize: 100ms)
- **Mandatory**: Show loading state for all operations > 300ms
- **Forbidden**: Direct API calls from UI event handlers — delegate to service layer

### Color & Typography
- **Mandatory**: Never hardcode colors — always use `COLORS` dict from `aria.ui.theme`
- **Mandatory**: Never hardcode font sizes — use `TYPOGRAPHY` scale
- **Mandatory**: All text must use the Inter/Geist font family

---

## Architecture Rules

### Module Boundaries
```
ui/        → Only renders controls. No business logic.
state.py   → Single source of truth. Observable properties.
document/  → File I/O, parsing, vault operations.
context/   → Prompt building, @-mention resolution.
api/       → External LLM communication only.
chat/      → Conversation state, message history.
```

### State Flow
```
User Action → UI Event Handler → AppState.update() → UI Rebuild
                     ↓
              Service Layer (async)
                     ↓
              API / File System / SQLite
```

### Forbidden Patterns
- ❌ UI components importing `pymupdf` or `anthropic` directly
- ❌ Business logic in `ft.on_click` lambdas
- ❌ Global variables outside of `AppState`
- ❌ Synchronous file operations in the main thread
- ❌ Hardcoded API keys anywhere in source code
- ❌ `print()` statements — use `structlog` or `logging`
- ❌ Circular imports between `context/` and `chat/`

---

## Document Processing Rules

### File Handling
- **Mandatory**: Validate file type by extension AND magic bytes
- **Mandatory**: Copy files to `data/vault/` — never operate on original paths
- **Mandatory**: Extracted text must be sanitized (strip null bytes, normalize newlines to `\n`)
- **Mandatory**: Store extracted text as UTF-8 `.txt` with Unix line endings

### Token Counting
- **Mandatory**: Use `tiktoken` cl100k_base for OpenAI-compatible counting
- **Mandatory**: Use Gemini's native `count_tokens` API when available
- **Mandatory**: Cache token counts in SQLite — never recalculate on load

---

## API Integration Rules

### Authentication
- **Mandatory**: API keys stored in `~/.aria/config.toml` (user home, not project dir)
- **Mandatory**: Keys loaded via `pydantic-settings` with env var fallback
- **Mandatory**: Mask keys in logs (`sk-...xxxx`)

### Request Patterns
- **Mandatory**: All API calls wrapped in `async with aiohttp.ClientSession()`
- **Mandatory**: Timeout: 30s for standard requests, 120s for large context
- **Mandatory**: Retry: 3 attempts, exponential backoff (1s, 2s, 4s)
- **Mandatory**: Stream responses — never buffer full response in memory

### Response Handling
- **Mandatory**: Validate response schema with Pydantic models
- **Mandatory**: Handle empty content gracefully (return "No response generated")
- **Mandatory**: Log API errors with sanitized request context

---

## Testing Rules

### Unit Tests
- **Mandatory**: Every parser has a test with sample files in `tests/fixtures/`
- **Mandatory**: Mock all API calls — never hit real LLM endpoints in tests
- **Mandatory**: Use `pytest-asyncio` for async test functions
- **Mandatory**: Test error paths, not just happy paths

### UI Tests
- **Mandatory**: Test component initialization with all prop combinations
- **Mandatory**: Simulate user events and assert state changes
- **Mandatory**: Test keyboard navigation for @-mention dropdown

---

## Git Standards

### Commits
- Format: `type(scope): description` (Conventional Commits)
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Example: `feat(vault): add drag-and-drop upload support`

### Branches
- `main`: Production-ready
- `feat/*`: Feature development
- `fix/*`: Bug fixes
- `release/*`: Release preparation

---

## Performance Rules

- **Mandatory**: Virtualize lists with `ft.ListView` + `ft.ListTile` for vaults > 50 items
- **Mandatory**: Lazy-load conversation history (paginate at 50 messages)
- **Mandatory**: Use `ft.Image` with `cache_width` for any future image support
- **Mandatory**: Profile memory usage with `tracemalloc` before each release
- **Forbidden**: Loading full extracted text into memory for vault list display (use previews)
