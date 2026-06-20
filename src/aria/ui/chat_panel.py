"""AI Chat Canvas panel with message list and send orchestration (async)."""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import flet as ft

from aria.api.base import LLMClient
from aria.chat import history as chat_history
from aria.config import settings
from aria.context.injector import ContextInjector
from aria.context.mention import search_documents
from aria.document.vault import VaultManager
from aria.exceptions import APIError
from aria.state import app_state
from aria.ui.input_bar import InputBar
from aria.ui.mention_dropdown import MentionDropdown
from aria.ui.message_bubble import LoadingIndicator, MessageBubble
from aria.ui.theme import COLORS, TYPOGRAPHY
from aria.ui.vault_panel import ToastNotification

logger = logging.getLogger(__name__)

# Maximum characters to use when auto-titling a conversation from the first user message.
_AUTO_TITLE_MAX_CHARS: int = 40


class ChatPanel(ft.Column):
    """Right-hand chat canvas: header + scrollable messages + input bar.

    Orchestrates the send flow between the UI, AppState, persistence, and the LLM client.
    """

    def __init__(
        self,
        page: ft.Page,
        on_collapse_toggle: Callable[[Any], Any],
        llm_client_factory: Callable[[], LLMClient],
    ) -> None:
        """Initialize the chat panel.

        Args:
            page: The Flet page (used for run_task).
            on_collapse_toggle: Callback to toggle the vault sidebar.
            llm_client_factory: Callable that returns a fresh LLMClient instance.
                                Called lazily on first send to defer key validation.
        """
        super().__init__()
        self._page = page
        self._on_collapse_toggle = on_collapse_toggle
        self._llm_client_factory = llm_client_factory
        self._llm_client: LLMClient | None = None
        self._vault_manager = VaultManager()
        self._context_injector = ContextInjector(
            self._vault_manager,
            context_limit=settings.context_token_limit,
            reserved_for_response=settings.reserved_response_tokens,
            per_document_cap=settings.per_document_token_cap,
        )
        self.toasts: list[ToastNotification] = []

        self.expand = True
        self.spacing = 0

        # ── Header ──────────────────────────────────────────────────────────────
        self._expand_btn = ft.IconButton(
            icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT_ROUNDED,
            icon_color=COLORS["text_muted"],
            icon_size=18,
            tooltip="Expand sidebar",
            visible=app_state.vault_collapsed,
            on_click=self._on_collapse_toggle,
        )

        # Conversation switcher dropdown
        self._conversation_dropdown = ft.Dropdown(
            expand=True,
            hint_text="Select a conversation",
            text_size=TYPOGRAPHY["body"]["size"],
            color=COLORS["text_primary"],
            bgcolor=COLORS["bg_elevated"],
            border_color=COLORS["border_subtle"],
            focused_border_color=COLORS["border_focus"],
            border_radius=6,
            content_padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            height=36,
            on_select=self._on_conversation_selected,
        )

        self._header = ft.Container(
            content=ft.Row(
                controls=[
                    self._expand_btn,
                    ft.Text(
                        "AI Chat Canvas",
                        size=TYPOGRAPHY["h1"]["size"],
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text_primary"],
                    ),
                    ft.Container(width=12),
                    self._conversation_dropdown,
                    ft.Container(width=4),
                    ft.IconButton(
                        icon=ft.Icons.ADD_COMMENT_OUTLINED,
                        icon_color=COLORS["text_secondary"],
                        icon_size=20,
                        tooltip="New chat",
                        on_click=self._on_new_chat,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.Padding(left=8, right=16, top=12, bottom=12),
            border=ft.Border(bottom=ft.BorderSide(1, COLORS["border_hairline"])),
        )

        # ── Empty state ─────────────────────────────────────────────────────────
        self._empty_state = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                        color=COLORS["accent_electric"],
                        size=56,
                    ),
                    ft.Container(height=16),
                    ft.Text(
                        "Welcome to Aria",
                        size=TYPOGRAPHY["display"]["size"],
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text_primary"],
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Upload documents to the vault, activate sources, and ask anything.",
                        size=TYPOGRAPHY["body"]["size"],
                        color=COLORS["text_secondary"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment(0, -0.5),
            expand=True,
            padding=48,
            visible=True,
        )

        # ── Message list ────────────────────────────────────────────────────────
        self._message_list = ft.ListView(
            expand=True,
            spacing=0,
            padding=ft.Padding(left=0, right=0, top=8, bottom=8),
            auto_scroll=True,
        )

        self._loading_indicator = LoadingIndicator()

        # Message area container (stacks messages + loading indicator)
        self._message_area = ft.Container(
            content=ft.Column(
                [
                    self._message_list,
                    self._loading_indicator,
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
            visible=False,  # Hidden until there are messages
        )

        # ── Toast container (overlaid on the content area) ────────────────────
        self._toast_container = ft.Column(
            [],
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )
        self._toast_stack = ft.Container(
            content=self._toast_container,
            alignment=ft.Alignment(1, 1),
            padding=ft.Padding(left=16, top=16, right=16, bottom=16),
        )

        # ── Mention dropdown (hosted in the content Stack, not InputBar) ────────
        self._mention_dropdown = MentionDropdown(
            on_select=self._on_mention_selected,
            on_dismiss=self._on_mention_dismissed,
        )

        # ── Input bar ───────────────────────────────────────────────────────────
        # InputBar takes sync callbacks; we bridge to async where needed.
        self._input_bar = InputBar(
            on_send=self._on_send_callback,
            on_mention_trigger=self._on_mention_trigger,
            on_mention_dismiss=self._on_mention_dismiss,
        )

        # ── Assemble main content ───────────────────────────────────────────────
        # MentionDropdown is positioned at the bottom of the Stack so it floats
        # just above the InputBar without being clipped by the window edge.
        self._content_area = ft.Stack(
            [
                ft.Column(
                    [
                        self._empty_state,
                        self._message_area,
                    ],
                    spacing=0,
                    expand=True,
                ),
                self._toast_stack,
                self._mention_dropdown,
            ],
            expand=True,
        )

        self.controls = [
            self._header,
            self._content_area,
            self._input_bar,
        ]

        # ── State observers ─────────────────────────────────────────────────────
        app_state.add_observer("vault_collapsed_changed", self._sync_expand_btn)
        app_state.add_observer("messages_changed", self._rebuild_messages)
        app_state.add_observer("sending_state_changed", self._on_sending_state_changed)
        app_state.add_observer("conversations_changed", self._rebuild_conversation_dropdown)
        app_state.add_observer("conversation_changed", self._sync_dropdown_selection)

        # Initial dropdown population (conversations may already be loaded from startup)
        self._rebuild_conversation_dropdown()

    # ── Observer callbacks (sync — invoked by AppState on the UI thread) ────────

    def _sync_expand_btn(self) -> None:
        """Show/hide expand button based on vault collapse state."""
        self._expand_btn.visible = app_state.vault_collapsed
        self._expand_btn.update()

    def _rebuild_messages(self) -> None:
        """Rebuild the message list from app_state.messages."""
        messages = app_state.messages
        has_messages = len(messages) > 0

        self._empty_state.visible = not has_messages
        self._message_area.visible = has_messages

        if has_messages:
            bubbles: list[ft.Control] = []
            for msg in messages:
                bubbles.append(MessageBubble(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    created_at=msg.get("created_at", ""),
                ))
            self._message_list.controls = bubbles

        self._content_area.update()

    def _on_sending_state_changed(self) -> None:
        """Update loading indicator and input bar based on sending state."""
        is_sending = app_state.is_sending
        self._loading_indicator.visible = is_sending
        self._input_bar.set_enabled(not is_sending)
        self._loading_indicator.update()
        self._input_bar.update()

    def _rebuild_conversation_dropdown(self) -> None:
        """Rebuild dropdown options from app_state.conversations."""
        options: list[ft.dropdown.Option] = []
        for conv in app_state.conversations:
            conv_id = str(conv.get("id", ""))
            title = str(conv.get("title", "New Chat"))
            options.append(ft.dropdown.Option(key=conv_id, text=title))

        self._conversation_dropdown.options = options
        # Sync current selection
        self._conversation_dropdown.value = app_state.current_conversation_id or ""
        try:
            self._conversation_dropdown.update()
        except (AssertionError, RuntimeError):
            # Control not yet mounted on the page; safe to ignore during init.
            pass

    def _sync_dropdown_selection(self) -> None:
        """Sync the dropdown value when current_conversation_id changes externally."""
        self._conversation_dropdown.value = app_state.current_conversation_id or ""
        try:
            self._conversation_dropdown.update()
        except (AssertionError, RuntimeError):
            pass

    # ── @-Mention handlers (sync — called by InputBar / page keyboard) ──────────

    def _on_mention_trigger(self, query: str) -> None:
        """Called by InputBar whenever an active @-mention is detected.

        Opens the mention dropdown with fuzzy-searched vault documents and
        registers a page-level keyboard handler for arrow-key navigation.
        """
        results = search_documents(query, app_state.documents)
        self._mention_dropdown.show(results, query)
        # Gate InputBar submit so Enter selects from the dropdown
        self._input_bar.is_mention_dropdown_open = self._mention_dropdown.is_visible
        # Register page-level keyboard handler for navigation
        self._page.on_keyboard_event = self._on_mention_key

    def _on_mention_dismiss(self) -> None:
        """Called by InputBar when the @-mention trigger ends."""
        self._mention_dropdown.hide()
        self._input_bar.is_mention_dropdown_open = False
        self._page.on_keyboard_event = None

    def _on_mention_key(self, e: Any) -> None:
        """Handle keyboard navigation when the mention dropdown is open.

        Intercepts arrow keys, Enter, and Escape; suppresses them so they
        don't propagate to the TextField.
        """
        key = getattr(e, "key", None) or ""
        if key == "ArrowUp":
            self._mention_dropdown.navigate(-1)
            if hasattr(e, "prevent_default"):
                e.prevent_default = True
        elif key == "ArrowDown":
            self._mention_dropdown.navigate(1)
            if hasattr(e, "prevent_default"):
                e.prevent_default = True
        elif key == "Enter":
            self._mention_dropdown.select_current()
            if hasattr(e, "prevent_default"):
                e.prevent_default = True
        elif key == "Escape":
            self._mention_dropdown.dismiss()
            if hasattr(e, "prevent_default"):
                e.prevent_default = True

    def _on_mention_selected(self, document: dict[str, Any]) -> None:
        """Called when the user picks a document from the dropdown."""
        self._input_bar.add_mention(document)
        self._mention_dropdown.hide()
        self._input_bar.is_mention_dropdown_open = False
        self._page.on_keyboard_event = None

    def _on_mention_dismissed(self) -> None:
        """Called by MentionDropdown.on_dismiss (Escape / empty results)."""
        self._input_bar.is_mention_dropdown_open = False
        self._page.on_keyboard_event = None

    # ── Chat actions (async — run on Flet's event loop) ─────────────────────────

    def _on_send_callback(self, text: str) -> None:
        """Sync bridge from InputBar to async send handler.

        InputBar fires this synchronously from on_submit / on_click.
        We schedule the async handler on Flet's event loop.
        """
        asyncio.create_task(self._handle_send(text))

    async def _on_new_chat(self, e: Any) -> None:
        """Start a new conversation, clearing current messages."""
        app_state.set_current_conversation(None)
        # Dropdown selection is cleared via the conversation_changed observer

    async def _on_conversation_selected(self, e: Any) -> None:
        """Handle selection change in the conversation dropdown."""
        selected_id: str | None = self._conversation_dropdown.value or None
        if not selected_id:
            return
        if selected_id == app_state.current_conversation_id:
            return  # Already viewing this conversation

        await self._switch_conversation(selected_id)

    async def _switch_conversation(self, conversation_id: str) -> None:
        """Load a different conversation from the database into the UI."""
        try:
            messages = await chat_history.get_messages(conversation_id)
            app_state.set_current_conversation(conversation_id)
            app_state.load_messages(messages)
            logger.info(
                "Switched to conversation %s (%d messages)",
                conversation_id,
                len(messages),
            )
        except Exception:
            logger.error("Failed to switch conversation", exc_info=True)
            self._show_error("Failed to load conversation. Please try again.")

    # ── Send flow ───────────────────────────────────────────────────────────────

    async def _handle_send(self, text: str) -> None:
        """Handle a send action from the InputBar.

        Runs the full send flow (DB write + API call) as native async code
        on Flet's event loop, keeping the UI responsive via aiosqlite and
        the async Gemini client.
        """
        if app_state.is_sending:
            return
        if not text.strip():
            return

        try:
            app_state.set_sending(True)

            # Create conversation on first message
            if app_state.current_conversation_id is None:
                conv_id = await chat_history.create_conversation(
                    model_provider="gemini",
                    model_name="gemini-1.5-pro",
                )
                app_state.current_conversation_id = conv_id
                # Add to in-memory list so it appears in the dropdown
                app_state.add_conversation({
                    "id": conv_id,
                    "title": "New Chat",
                    "model_provider": "gemini",
                    "model_name": "gemini-1.5-pro",
                    "system_prompt": None,
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                    "is_archived": False,
                })

            conv_id = app_state.current_conversation_id
            assert conv_id is not None  # Guaranteed by create above

            # Save user message to DB (returns id + timestamp)
            msg_id, msg_ts = await chat_history.save_message(
                conversation_id=conv_id,
                role="user",
                content=text,
                token_count=len(text.split()),  # rough estimate
            )

            # Add to in-memory state (triggers UI rebuild)
            app_state.add_message({
                "id": msg_id,
                "role": "user",
                "content": text,
                "created_at": msg_ts,
            })

            # Build system prompt with active sources + @-mentioned sources
            mentioned_ids = self._input_bar.mentioned_document_ids
            system_prompt = await self._context_injector.build(
                active_ids=app_state.active_document_ids,
                mentioned_ids=set(mentioned_ids) if mentioned_ids else None,
                user_message=text,
            )

            # Build message history for API
            api_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in app_state.messages
                if m.get("role") in ("user", "assistant")
            ]

            # Lazy-init LLM client
            if self._llm_client is None:
                self._llm_client = self._llm_client_factory()

            # Call the LLM (native async, no asyncio.run needed)
            response_text = await self._llm_client.send_message(api_messages, system_prompt)

            if not response_text:
                response_text = "No response generated."

            # Save assistant message to DB (returns id + timestamp)
            asst_id, asst_ts = await chat_history.save_message(
                conversation_id=conv_id,
                role="assistant",
                content=response_text,
                token_count=len(response_text.split()),
                model_provider="gemini",
                model_name="gemini-1.5-pro",
            )

            # Add to in-memory state (triggers UI rebuild)
            app_state.add_message({
                "id": asst_id,
                "role": "assistant",
                "content": response_text,
                "created_at": asst_ts,
            })

            # ── Auto-title: derive a title from the first user message ──
            # Only re-title if the conversation still has the default name.
            conv = await chat_history.get_conversation(conv_id)
            if conv and conv.get("title") == "New Chat":
                auto_title = text[:_AUTO_TITLE_MAX_CHARS].strip()
                if len(text) > _AUTO_TITLE_MAX_CHARS:
                    auto_title += "…"
                await chat_history.update_conversation_title(conv_id, auto_title)
                app_state.update_conversation_title(conv_id, auto_title)

        except APIError as e:
            logger.error("API error during send", exc_info=True)
            self._show_error(e.message)
        except Exception:
            logger.error("Unexpected error during send", exc_info=True)
            self._show_error("An unexpected error occurred. Please try again.")
        finally:
            app_state.set_sending(False)

    # ── Toast helpers ───────────────────────────────────────────────────────────

    def _show_toast(self, toast: ToastNotification) -> None:
        """Show a toast notification on the chat panel."""
        toast.on_dismiss = lambda: self._remove_toast(toast)
        self.toasts.append(toast)
        self._toast_container.controls.append(toast)
        self._toast_container.update()

        async def auto_dismiss() -> None:
            await asyncio.sleep(4)
            self._remove_toast(toast)

        asyncio.create_task(auto_dismiss())

    def _remove_toast(self, toast: ToastNotification) -> None:
        """Remove a toast from the panel."""
        if toast in self.toasts:
            self.toasts.remove(toast)
        if toast in self._toast_container.controls:
            self._toast_container.controls.remove(toast)
            self._toast_container.update()

    def _show_error(self, message: str) -> None:
        """Show an error toast."""
        toast = ToastNotification(message, notification_type="error")
        self._show_toast(toast)
