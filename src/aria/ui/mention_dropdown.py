"""Floating dropdown for @-mention document selection."""

from collections.abc import Callable
from typing import Any

import flet as ft

from aria.ui.theme import COLORS, TYPOGRAPHY

# Maximum characters to show in the content preview column.
_PREVIEW_MAX_CHARS: int = 40


class MentionDropdown(ft.Container):
    """Floating dropdown that appears above the input bar during @-mentions.

    Rendered inside a Stack (positioned above the input bar by ChatPanel).
    Supports keyboard navigation (arrow keys + Enter) and mouse selection.

    Styling follows DESIGN.md:
    - bg_elevated background, 8px border-radius
    - 0 8px 24px rgba(0,0,0,0.4) shadow
    - Max-height 240px
    """

    def __init__(
        self,
        on_select: Callable[[dict[str, Any]], None],
        on_dismiss: Callable[[], None],
    ) -> None:
        """Initialize the mention dropdown.

        Args:
            on_select: Called with the selected document dict when the user
                picks a document (via Enter, click, or tap).
            on_dismiss: Called when the dropdown should close (Escape, empty
                results, or external dismissal).
        """
        super().__init__()
        self._on_select = on_select
        self._on_dismiss = on_dismiss

        # Navigation state
        self._selected_index: int = 0
        self._results: list[dict[str, Any]] = []

        # Scrollable list of document rows
        self._list_view = ft.ListView(
            expand=True,
            spacing=0,
            auto_scroll=True,
        )

        # Container styling (per DESIGN.md)
        self.bgcolor = COLORS["bg_elevated"]
        self.border_radius = 8
        # Positioned attributes — used by the parent Stack for absolute placement
        self.left = 16
        self.right = 16
        self.bottom = 0
        self.border = ft.Border(
            top=ft.BorderSide(1, COLORS["border_subtle"]),
            bottom=ft.BorderSide(1, COLORS["border_subtle"]),
            left=ft.BorderSide(1, COLORS["border_subtle"]),
            right=ft.BorderSide(1, COLORS["border_subtle"]),
        )
        self.max_height = 240
        self.padding = 0
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE
        self.ink = True
        self.visible = False
        self.content = self._list_view
        self.box_shadow = ft.BoxShadow(
            blur_radius=24,
            color="rgba(0,0,0,0.4)",
            offset=ft.Offset(0, -8),
        )

    # ── Public API ──────────────────────────────────────────────────────────────

    def show(self, documents: list[dict[str, Any]], query: str) -> None:
        """Display the dropdown with filtered results.

        If *documents* is empty, the dropdown is hidden and *on_dismiss* fires.

        Args:
            documents: Sorted list of document dicts from search_documents().
            query: The current @-mention query (used to highlight matches).
        """
        if not documents:
            self.hide()
            self._on_dismiss()
            return

        self._results = documents
        self._selected_index = 0

        rows: list[ft.Control] = []
        for i, doc in enumerate(documents):
            rows.append(self._build_row(doc, query, i))

        self._list_view.controls = rows
        self.visible = True
        self.update()

    def hide(self) -> None:
        """Hide the dropdown and clear results."""
        self.visible = False
        self._results = []
        self._selected_index = 0
        self.update()

    @property
    def is_visible(self) -> bool:
        """Whether the dropdown is currently shown."""
        return self.visible

    def navigate(self, direction: int) -> None:
        """Move the highlight up (-1) or down (+1), wrapping at bounds."""
        if not self._results:
            return
        n = len(self._results)
        self._selected_index = (self._selected_index + direction) % n
        self._refresh_highlight()

    def select_current(self) -> None:
        """Fire on_select with the currently highlighted document."""
        if not self._results:
            return
        doc = self._results[self._selected_index]
        self._on_select(doc)

    def dismiss(self) -> None:
        """Hide the dropdown and fire on_dismiss."""
        self.hide()
        self._on_dismiss()

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _build_row(
        self,
        doc: dict[str, Any],
        query: str,
        index: int,
    ) -> ft.Container:
        """Build a single clickable document row."""
        filename = doc.get("filename", "unknown")
        file_type = doc.get("file_type", "txt")
        preview_text = doc.get("extracted_text") or ""

        # File type icon
        icon_name = ft.Icons.PICTURE_AS_PDF if file_type == "pdf" else ft.Icons.DESCRIPTION
        icon = ft.Icon(icon_name, color=COLORS["text_muted"], size=20)

        # Filename with highlighted match
        filename_text = self._build_filename_text(filename, query)

        # Content preview (truncated)
        if len(preview_text) > _PREVIEW_MAX_CHARS:
            preview_text = preview_text[:_PREVIEW_MAX_CHARS] + "…"
        preview_text = preview_text.replace("\n", " ").strip()

        preview = ft.Text(
            preview_text,
            color=COLORS["text_muted"],
            size=TYPOGRAPHY["micro"]["size"],
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )

        # Row layout: icon | filename + preview (stacked) | spacer
        info_col = ft.Column(
            [filename_text, preview],
            spacing=2,
            expand=True,
        )

        row_content = ft.Row(
            [icon, info_col],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Highlight background for the currently selected row
        is_selected = index == self._selected_index
        bg = COLORS["bg_active"] if is_selected else None

        row = ft.Container(
            content=row_content,
            padding=ft.Padding(left=12, right=12, top=8, bottom=8),
            bgcolor=bg,
            on_click=lambda _e, d=doc: self._on_select(d),
            on_hover=lambda e: self._on_row_hover(e, index),
            ink=True,
        )
        return row

    def _build_filename_text(self, filename: str, query: str) -> ft.Text:
        """Build a Text control with the matching portion of filename highlighted."""
        if not query:
            return ft.Text(
                filename,
                color=COLORS["text_primary"],
                size=TYPOGRAPHY["body"]["size"],
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )

        lower_fn = filename.lower()
        lower_query = query.lower()
        idx = lower_fn.find(lower_query)

        if idx < 0:
            return ft.Text(
                filename,
                color=COLORS["text_primary"],
                size=TYPOGRAPHY["body"]["size"],
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )

        # Split into before / match / after and bold the match
        before = filename[:idx]
        match = filename[idx : idx + len(query)]
        after = filename[idx + len(query) :]

        return ft.Text(
            spans=[
                ft.TextSpan(before, style=ft.TextStyle(color=COLORS["text_primary"])),
                ft.TextSpan(
                    match,
                    style=ft.TextStyle(
                        color=COLORS["accent_electric"],
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
                ft.TextSpan(after, style=ft.TextStyle(color=COLORS["text_primary"])),
            ],
            size=TYPOGRAPHY["body"]["size"],
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    def _refresh_highlight(self) -> None:
        """Update the background colour of each row to reflect selection."""
        for i, row in enumerate(self._list_view.controls):
            if isinstance(row, ft.Container):
                row.bgcolor = COLORS["bg_active"] if i == self._selected_index else None
                row.update()

    def _on_row_hover(self, e: Any, index: int) -> None:
        """Update selection on mouse hover for immediate visual feedback."""
        if hasattr(e, "data") and e.data == "true":
            self._selected_index = index
            self._refresh_highlight()
