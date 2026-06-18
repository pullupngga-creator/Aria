# Chat Input Bar and Gemini Integration

## Context

The existing codebase has a working two-panel shell (`TwoPanelShell` in `src/aria/ui/app.py`) with a fully functional Sources Vault on the left and a placeholder "Welcome to Aria" chat canvas on the right. The SQLite schema already defines `conversations` and `messages` tables (see `src/aria/db/migrations.py`). The `AppState` singleton (`src/aria/state.py`) already has `messages`, `current_conversation_id`, `add_message()`, and `clear_messages()`. The `APIError` exception already exists in `src/aria/exceptions.py`.

Dependencies already declared in `pyproject.toml`: `google-generativeai>=0.8.0`, `aiohttp>=3.11.0`, `pydantic>=2.10.0`, `tiktoken>=0.8.0`.

---

## Task 1: Create the API layer (`src/aria/api/`)

**New files:**

### `src/aria/api/__init__.py`
Empty package init. Exports `LLMClient` and `GeminiClient`.

### `src/aria/api/base.py`
Abstract base class `LLMClient` defining the contract for all LLM providers:
```python
class LLMClient(ABC):
    @abstractmethod
    async def send_message(self, messages: list[dict[str, str]], system_prompt: str | None = None) -> str:
        """Send conversation history and return the assistant's response text."""
        ...

    @abstractmethod
    async def validate_key(self) -> bool:
        """Check if the configured API key is valid."""
        ...
```
Use `abc.ABC` + `abc.abstractmethod`. Return plain `str` for Phase 0 (non-streaming).

### `src/aria/api/gemini.py`
Concrete `GeminiClient(LLMClient)` wrapping `google-generativeai`:
- Constructor takes `api_key: str` and `model_name: str = "gemini-1.5-pro"`.
- Initializes `genai.configure(api_key=...)` and creates `GenerativeModel(model_name)`.
- `send_message()` converts the message list into a `genai` chat session (`model.start_chat(history=...)`), sends the last user message with `chat.send_message_async()`, and returns `response.text`.
- `validate_key()` calls `genai.list_models()` inside a try/except.
- All `google-generativeai` calls wrapped with retry logic (3 attempts, exponential backoff 1s/2s/4s) per RULES.md.
- Raises `APIError` (from `aria.exceptions`) on failure with user-friendly messages.
- Timeout: 30s default via `asyncio.wait_for()`.

---

## Task 2: Create the chat persistence layer (`src/aria/chat/`)

**New files:**

### `src/aria/chat/__init__.py`
Empty package init.

### `src/aria/chat/history.py`
SQLite CRUD for conversations and messages, following the same pattern as `vault.py`:
- `create_conversation(model_provider: str, model_name: str) -> str` -- inserts row, returns UUID.
- `save_message(conversation_id: str, role: str, content: str, sources_used: str | None, token_count: int, model_provider: str | None, model_name: str | None) -> str` -- inserts row, returns UUID.
- `get_messages(conversation_id: str) -> list[sqlite3.Row]` -- returns messages ordered by `created_at ASC`.
- `get_conversations() -> list[sqlite3.Row]` -- returns all non-archived conversations ordered by `updated_at DESC`.
- `update_conversation_title(conversation_id: str, title: str) -> None`.
- All functions use `get_connection()` from `aria.db.connection`.

---

## Task 3: Extend AppState for chat operations

**Modify `src/aria/state.py`:**

Add new state fields and methods:
- `is_sending: bool = False` -- tracks whether an API call is in progress (prevents double-send).
- `set_sending(value: bool) -> None` -- sets `is_sending` and notifies `"sending_state_changed"` observers.
- `set_current_conversation(conversation_id: str | None) -> None` -- updates `current_conversation_id`, clears messages, notifies `"conversation_changed"`.
- `load_messages(messages: list[dict[str, Any]]) -> None` -- replaces `self.messages` and notifies `"messages_changed"`.

The existing `add_message()` and `clear_messages()` are already sufficient for appending and clearing.

---

## Task 4: Build the ChatPanel UI component

**New file: `src/aria/ui/chat_panel.py`**

`ChatPanel(ft.Column)` -- the right-hand panel that replaces the current placeholder in `main.py`:
- **Header**: Reuse the existing header logic from `main.py` (expand button + "AI Chat Canvas" title). Move it into this class for encapsulation.
- **Message area**: `ft.ListView(expand=True, spacing=0, auto_scroll=True)` wrapped in a `ft.Container` with `bgcolor=COLORS["bg_anthracite"]`. Renders `MessageBubble` controls.
- **Empty state**: When no messages, show the centered "Welcome to Aria" text with tagline (moved from `main.py`).
- **Input bar**: `InputBar` control docked at the bottom (see Task 5).
- Observes `"messages_changed"` on `app_state` to rebuild the message list.
- Observes `"sending_state_changed"` to show/hide a loading indicator (pulsing dot or `ft.ProgressRing`) and disable/enable the input bar.

### `src/aria/ui/message_bubble.py`
`MessageBubble(ft.Container)` -- renders a single message:
- **User message**: Right-aligned, `bg_elevated` background, max-width 80%, body-sized text.
- **Assistant message**: Left-aligned, full-width, body-sized text. For Phase 0, render as plain `ft.Text` (Markdown rendering is Phase 2).
- **Timestamp**: Micro-sized muted text below each message.
- Follows design tokens from `DESIGN.md` (spacing, border-radius, colors).

---

## Task 5: Build the InputBar component

**New file: `src/aria/ui/input_bar.py`**

`InputBar(ft.Container)` -- fixed at the bottom of the chat panel:
- **Layout**: `ft.Row` containing:
  - `ft.TextField` with `multiline=True`, `min_lines=1`, `max_lines=6` (auto-expanding), `border_radius=8`, `bgcolor=COLORS["bg_elevated"]`, `hint_text="Ask Aria anything..."`.
  - Send button: `ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color=COLORS["accent_electric"], icon_size=24)` in a 36px circular container.
- **Keyboard handling**: The `TextField` `on_submit` event fires on Enter. The send button `on_click` also triggers send. Shift+Enter inserts newline (native `multiline` behavior in Flet).
- **Send callback**: Constructor takes `on_send: Callable[[str], None]`. When send is triggered, calls `on_send(text)` with the trimmed input, then clears the field.
- **Disabled state**: `set_enabled(enabled: bool)` method to disable input during API calls (greys out field and send button).
- **Token counter**: Small muted text showing character count below the input (e.g., "142 chars"). Updates on `on_change`.
- **Styling**: `bgcolor=COLORS["bg_elevated"]`, top border `border_hairline`, padding 12px, min-height 56px per DESIGN.md.

---

## Task 6: Wire everything together in `main.py`

**Modify `src/aria/main.py`:**

Replace the current placeholder chat panel (lines 68-120) with:
1. Import `ChatPanel` from `aria.ui.chat_panel`.
2. Import `GeminiClient` from `aria.api.gemini`.
3. Instantiate `GeminiClient` using `settings.gemini_api_key` (lazy -- only create when first message is sent, to avoid startup failure if key is missing).
4. Create `ChatPanel(page=page, on_collapse_toggle=_on_toggle, llm_client_factory=lambda: GeminiClient(api_key=settings.gemini_api_key or ""))`.
5. Pass it to `TwoPanelShell(vault_panel, chat_panel)`.

The `llm_client_factory` pattern defers client creation so the app starts even without an API key configured. The key is validated at send-time.

---

## Task 7: Implement the send flow (orchestration)

The send flow lives in `ChatPanel` (the orchestrator between UI, state, and API):

```
User types message -> presses Enter / clicks Send
  -> InputBar.on_send callback fires with text
  -> ChatPanel._handle_send(text):
     1. Guard: if app_state.is_sending or text is empty, return
     2. app_state.set_sending(True)
     3. If no current conversation: create one via history.create_conversation()
     4. Save user message to DB via history.save_message()
     5. app_state.add_message({"role": "user", "content": text, ...})
     6. Gather active document text from vault (read storage_path files for active doc IDs)
     7. Build system prompt: "You are Aria, a research assistant..." + active source text
     8. Build message history list from app_state.messages
     9. Call llm_client.send_message(messages, system_prompt) in background thread
    10. On success: save assistant message to DB, app_state.add_message()
    11. On failure: show error toast via ToastNotification
    12. Finally: app_state.set_sending(False)
```

Steps 9-12 run via `page.run_thread()` to avoid blocking the UI thread (per RULES.md).

---

## Task 8: Error handling

| Scenario | Handling |
|----------|----------|
| No API key configured | Show toast: "Set your Gemini API key in environment variable GEMINI_API_KEY" |
| Invalid API key | Catch `google.generativeai` auth errors, show toast: "Invalid API key" |
| Network timeout (30s) | Show toast: "Request timed out. Please try again." |
| Rate limit (429) | Retry with backoff, then show toast: "Rate limited. Please wait a moment." |
| Empty response | Display "No response generated" as assistant message |
| Empty user input | Ignore send (no API call) |
| Double-send prevention | `is_sending` flag disables input bar during API call |
| Database errors | Catch, log, show generic toast |

---

## Task 9: Testing

**New file: `tests/test_gemini_client.py`**
- Mock `google-generativeai` calls using `unittest.mock.patch`.
- Test `send_message()` returns string response.
- Test retry logic on simulated 503 errors.
- Test `APIError` raised on persistent failure.
- Test `validate_key()` with valid/invalid keys.
- Test timeout handling.

**New file: `tests/test_chat_history.py`**
- Test `create_conversation()` inserts and returns UUID.
- Test `save_message()` and `get_messages()` round-trip.
- Test `get_conversations()` ordering.
- Test foreign key cascade (delete conversation deletes messages).
- Use in-memory SQLite (`:memory:`) for test isolation.

**New file: `tests/test_input_bar.py`**
- Test InputBar initialization with correct styling.
- Test send callback fires with trimmed text.
- Test empty input does not trigger send.
- Test disabled state prevents send.

---

## Task 10: Dependencies and package setup

No new `pyproject.toml` dependencies needed -- `google-generativeai`, `aiohttp`, `pydantic`, and `tiktoken` are already declared.

New packages to create (with `__init__.py`):
- `src/aria/api/`
- `src/aria/chat/`

---

## File Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/aria/api/__init__.py` | Create | Package init |
| `src/aria/api/base.py` | Create | Abstract `LLMClient` |
| `src/aria/api/gemini.py` | Create | `GeminiClient` implementation |
| `src/aria/chat/__init__.py` | Create | Package init |
| `src/aria/chat/history.py` | Create | Conversation/message SQLite CRUD |
| `src/aria/state.py` | Modify | Add `is_sending`, `set_sending`, `set_current_conversation`, `load_messages` |
| `src/aria/ui/chat_panel.py` | Create | Chat canvas with message list + send orchestration |
| `src/aria/ui/input_bar.py` | Create | Auto-expanding input with send button |
| `src/aria/ui/message_bubble.py` | Create | User/assistant message rendering |
| `src/aria/main.py` | Modify | Replace placeholder chat panel with `ChatPanel` |
| `tests/test_gemini_client.py` | Create | Gemini client unit tests |
| `tests/test_chat_history.py` | Create | Chat persistence unit tests |
| `tests/test_input_bar.py` | Create | Input bar unit tests |

---

## Estimated Timeline

| Task | Estimated Time |
|------|---------------|
| Task 1: API layer (base + gemini) | 1-2 hours |
| Task 2: Chat persistence | 1 hour |
| Task 3: AppState extensions | 30 minutes |
| Task 4: ChatPanel + MessageBubble | 2 hours |
| Task 5: InputBar | 1 hour |
| Task 6: Wire into main.py | 30 minutes |
| Task 7: Send flow orchestration | 1-2 hours |
| Task 8: Error handling (integrated) | included above |
| Task 9: Tests | 1-2 hours |
| **Total** | **8-11 hours** |

---

## Implementation Order

Execute tasks in this sequence to maintain a buildable state at each step:

1. Task 10 (create packages) -- trivial, enables imports
2. Task 1 (API layer) -- standalone, no UI dependency
3. Task 2 (chat persistence) -- standalone, no UI dependency
4. Task 3 (AppState) -- small, needed by UI
5. Task 5 (InputBar) -- standalone UI component
6. Task 4 (ChatPanel + MessageBubble) -- depends on InputBar + state
7. Task 6 (wire main.py) -- depends on ChatPanel
8. Task 7 (send flow) -- depends on all above
9. Task 9 (tests) -- can be written incrementally alongside each task
