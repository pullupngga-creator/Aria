"""Sources Vault panel component with document upload and list."""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import flet as ft

from aria.document.vault import VaultManager
from aria.exceptions import FileSizeExceededError, UnsupportedFileTypeError, VaultError
from aria.state import app_state
from aria.ui.theme import COLORS, TYPOGRAPHY

logger = logging.getLogger(__name__)


class ToastNotification(ft.Container):
    """Toast notification for success/error feedback."""

    def __init__(
        self,
        message: str,
        notification_type: str = "success",
        on_dismiss: Callable[[], Any] | None = None,
    ) -> None:
        """Initialize toast notification."""
        super().__init__()
        self.message = message
        self.notification_type = notification_type
        self.on_dismiss = on_dismiss

        # Set border color based on type
        border_color = {
            "success": COLORS["accent_success"],
            "error": COLORS["accent_error"],
            "warning": COLORS["accent_warning"],
            "info": COLORS["accent_electric"],
        }.get(notification_type, COLORS["accent_electric"])

        self.bgcolor = COLORS["bg_elevated"]
        self.border = ft.Border(left=ft.BorderSide(3, border_color))
        self.border_radius = 8
        self.padding = 12
        self.margin = ft.Margin(left=0, top=0, right=0, bottom=8)
        self.shadow = ft.BoxShadow(
            blur_radius=24,
            spread_radius=0,
            color="#66000000",
            offset=ft.Offset(0, 8),
        )

        self.content = ft.Row(
            [
                ft.Icon(
                    icon=ft.Icons.CHECK_CIRCLE
                    if notification_type == "success"
                    else ft.Icons.ERROR,
                    color=border_color,
                    size=20,
                ),
                ft.Container(
                    width=8,
                ),
                ft.Text(
                    message,
                    color=COLORS["text_primary"],
                    size=TYPOGRAPHY["small"]["size"],
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=COLORS["text_secondary"],
                    icon_size=16,
                    on_click=self._dismiss,
                    tooltip="Dismiss",
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

    def _dismiss(self, e: Any) -> None:
        """Dismiss the toast notification."""
        if self.on_dismiss:
            self.on_dismiss()
        self.visible = False
        self.update()


class DocumentListItem(ft.Container):
    """A single document list item with toggle and delete actions."""

    def __init__(
        self,
        doc: Any,
        on_toggle: Callable[[str], None],
        on_delete: Callable[[str, str], None],
    ) -> None:
        """Initialize document list item."""
        super().__init__()
        self.doc = doc
        self.on_toggle = on_toggle
        self.on_delete = on_delete

        # Determine icon
        icon_name = (
            ft.Icons.PICTURE_AS_PDF if doc.file_type == "pdf" else ft.Icons.DESCRIPTION
        )

        # Left section: document info (clickable to toggle active)
        self.toggle_btn = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        icon_name,
                        color=COLORS["text_secondary"],
                        size=24,
                    ),
                    ft.Container(width=12),
                    ft.Column(
                        [
                            ft.Text(
                                doc.filename,
                                color=COLORS["text_primary"],
                                size=TYPOGRAPHY["body"]["size"],
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"{doc.word_count} words • {doc.token_count} tokens",
                                color=COLORS["text_secondary"],
                                size=TYPOGRAPHY["micro"]["size"],
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
            data={"doc_id": doc.id},
        )

        # Right section: status indicator + delete button
        self.status_indicator = ft.Container(
            width=8,
            height=8,
            border_radius=4,
            bgcolor=COLORS["accent_electric"] if doc.is_active else ft.Colors.TRANSPARENT,
        )

        self.delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color=COLORS["text_muted"],
            icon_size=20,
            tooltip="Delete Document",
        )

        # Main container styling
        self.padding = ft.Padding(left=12, right=4, top=8, bottom=8)
        self.bgcolor = COLORS["bg_active"] if doc.is_active else COLORS["bg_obsidian"]
        self.data = {"is_active": doc.is_active, "doc_id": doc.id}

        self.content = ft.Row(
            [
                self.toggle_btn,
                ft.Row(
                    [
                        self.status_indicator,
                        self.delete_btn,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=0,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def did_mount(self) -> None:
        """Attach event handlers after widget is mounted."""
        self.toggle_btn.on_click = lambda e: self._handle_toggle()
        self.delete_btn.on_click = lambda e: self._handle_delete()

    def _handle_toggle(self) -> None:
        """Handle toggle active state."""
        self.on_toggle(self.doc.id)

    def _handle_delete(self) -> None:
        """Handle delete document."""
        self.on_delete(self.doc.id, self.doc.filename)

    def on_hover(self, e: Any) -> None:
        """Handle hover state."""
        is_active = self.data.get("is_active", False)
        if e.data == "true":  # Hovering
            self.bgcolor = COLORS["bg_hover"]
        else:  # Not hovering
            self.bgcolor = COLORS["bg_active"] if is_active else COLORS["bg_obsidian"]
        self.update()


class UploadZone(ft.Container):
    """Upload zone for documents (button click)."""

    def __init__(self, on_upload_click: Callable[[Any], Any]) -> None:
        """Initialize upload zone."""
        super().__init__()

        self.bgcolor = COLORS["bg_obsidian"]
        border_side = ft.BorderSide(2, COLORS["border_hairline"])
        self.border = ft.Border(
            top=border_side,
            right=border_side,
            bottom=border_side,
            left=border_side,
        )
        self.border_radius = 8
        self.padding = 32
        self.alignment = ft.Alignment(0, 0)
        self.expand = True

        self.content = ft.Column(
            [
                ft.Icon(
                    icon=ft.Icons.UPLOAD_FILE,
                    color=COLORS["accent_electric"],
                    size=48,
                ),
                ft.Container(height=16),
                ft.Text(
                    "Upload Documents",
                    color=COLORS["text_primary"],
                    size=TYPOGRAPHY["h2"]["size"],
                    weight=ft.FontWeight.W_500,
                ),
                ft.Container(height=8),
                ft.Text(
                    "PDF and TXT files only (max 50MB)",
                    color=COLORS["text_secondary"],
                    size=TYPOGRAPHY["small"]["size"],
                ),
                ft.Container(height=24),
                ft.ElevatedButton(
                    "Browse Files",
                    icon=ft.Icons.FOLDER_OPEN,
                    color=COLORS["text_inverse"],
                    bgcolor=COLORS["accent_electric"],
                    on_click=on_upload_click,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )


class VaultPanel(ft.Column):
    """Sources Vault panel with document list and upload functionality."""

    def __init__(self, page: ft.Page, on_collapse_toggle: Callable[[Any], Any]) -> None:
        """Initialize vault panel."""
        super().__init__()
        self._page = page
        self.vault_manager = VaultManager()
        self.toasts: list[ToastNotification] = []

        self.expand = True
        self.spacing = 0

        collapse_btn = ft.IconButton(
            icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT_ROUNDED,
            icon_color=COLORS["text_muted"],
            icon_size=18,
            tooltip="Collapse sidebar",
            on_click=on_collapse_toggle,
        )

        # Header
        self.header = ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        "Sources Vault",
                        color=COLORS["text_primary"],
                        size=TYPOGRAPHY["h1"]["size"],
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.ADD,
                        icon_color=COLORS["accent_electric"],
                        icon_size=32,
                        tooltip="Upload Document",
                        on_click=self._on_upload_click,
                    ),
                    collapse_btn,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=16, right=8, top=12, bottom=12),
            bgcolor=COLORS["bg_obsidian"],
            border=ft.Border(bottom=ft.BorderSide(1, COLORS["border_hairline"])),
        )

        # Upload zone (shown when vault is empty)
        self.upload_zone = UploadZone(on_upload_click=self._on_upload_click)

        # Document list
        self.document_list = ft.ListView(
            expand=True,
            spacing=0,
            padding=0,
        )

        # Toast container
        self.toast_container = ft.Column(
            [],
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )

        # Stack toasts on top
        self.toast_stack = ft.Stack(
            [
                ft.Container(expand=True),
                ft.Container(
                    content=self.toast_container,
                    alignment=ft.Alignment(1, 1),
                    padding=ft.Padding(left=16, top=16, right=16, bottom=64),
                ),
            ],
            expand=True,
        )

        self.file_picker = ft.FilePicker()

        self.controls = [
            self.header,
            ft.Stack(
                [
                    ft.Container(
                        content=self.upload_zone,
                        expand=True,
                    ),
                    self.toast_stack,
                ],
                expand=True,
            ),
        ]

    def did_mount(self) -> None:
        """Called when the control is added to the page."""
        # Register FilePicker as a page service
        self._page.services.append(self.file_picker)

        # Set up state observers
        app_state.add_observer("documents_changed", self._load_documents)
        app_state.add_observer("active_documents_changed", self._load_documents)
        
        # Load initial documents
        self._load_documents()

    def _load_documents(self) -> None:
        """Load and display documents from vault."""
        try:
            documents = self.vault_manager.get_all_documents()
            if documents:
                self._show_document_list(documents)
            else:
                self._show_upload_zone()
        except Exception:
            logger.error("Failed to load documents", exc_info=True)
            self._show_error("Failed to load documents from vault")

    def _show_upload_zone(self) -> None:
        """Show the empty state upload zone."""
        self.controls = [
            self.header,
            ft.Stack(
                [
                    ft.Container(
                        content=self.upload_zone,
                        expand=True,
                    ),
                    self.toast_stack,
                ],
                expand=True,
            ),
        ]
        self.update()

    def _show_document_list(self, documents: list[Any]) -> None:
        """Display the list of documents."""
        list_items: list[DocumentListItem] = []

        for doc in documents:
            item = DocumentListItem(
                doc=doc,
                on_toggle=self._handle_document_toggle,
                on_delete=self._handle_document_delete,
            )
            item.on_hover = lambda e, i=item: i.on_hover(e)
            list_items.append(item)

<<<<<<< HEAD
=======
            # Assemble the row
            row = ft.Container(
                content=ft.Row([
                    toggle_area,
                    ft.Row([
                        # Status Dot
                        ft.Container(
                            width=8, height=8, border_radius=4,
                            bgcolor=COLORS["accent_electric"] if doc.is_active else ft.Colors.TRANSPARENT,
                        ),
                    ], alignment=ft.MainAxisAlignment.END)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.Padding(left=12, right=4, top=8, bottom=8),
                bgcolor=COLORS["bg_active"] if doc.is_active else COLORS["bg_obsidian"],
                data={"is_active": doc.is_active},  # Pass state to hover handler
                on_hover=self._on_document_hover,
            )
            list_items.append(row)

        # Update the UI efficiently
>>>>>>> 16da978 (feat(chat): implement AI chat with Gemini integration and persistence)
        self.document_list.controls = list_items
        self.controls = [
            self.header,
            ft.Stack(
                [
                    ft.Container(
                        content=self.document_list,
                        expand=True,
                    ),
                    self.toast_stack,
                ],
                expand=True,
            ),
        ]
        self.update()

    def _handle_document_toggle(self, doc_id: str) -> None:
        """Toggle document active state."""
        try:
            # Get the document to check current state
            doc = self.vault_manager.get_document(doc_id)
            if doc is None:
                self._show_error("Document not found")
                return

            # Toggle the active state in database
            new_active = not doc.is_active
            self.vault_manager.toggle_active(doc_id, new_active)

            # Update app state
            app_state.toggle_document_active(doc_id)

            # Reload UI
            self._load_documents()
        except VaultError as e:
            logger.error(f"Failed to toggle document: {e}", exc_info=True)
            self._show_error("Failed to update document")
        except Exception as e:
            logger.error(f"Unexpected error toggling document: {e}", exc_info=True)
            self._show_error("Failed to update document")

<<<<<<< HEAD
    def _handle_document_delete(self, doc_id: str, filename: str) -> None:
        """Show delete confirmation dialog."""

        def handle_confirm(e: Any) -> None:
            """Confirm and delete the document."""
            dialog.open = False
            
            try:
                # Delete from vault
                self.vault_manager.delete_document(doc_id)
                
                # Update app state
                app_state.remove_document(doc_id)
                
                # Show success message
                self._show_success(f"Deleted: {filename}")
                
                # Reload UI
                self._load_documents()
            except VaultError as ex:
                logger.error(f"Failed to delete document: {ex}", exc_info=True)
                self._show_error("Failed to delete document")
            except Exception as ex:
                logger.error(f"Unexpected error deleting document: {ex}", exc_info=True)
                self._show_error("Failed to delete document")
            finally:
                # Update page
                self._page.update()

        def handle_cancel(e: Any) -> None:
            """Cancel deletion."""
            dialog.open = False
            self._page.update()

        # Create confirmation dialog
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Document"),
            content=ft.Text(
                f"Are you sure you want to delete '{filename}'?",
                color=COLORS["text_primary"],
            ),
            actions=[
                ft.TextButton("Cancel", on_click=handle_cancel),
                ft.TextButton(
                    "Delete",
                    on_click=handle_confirm,
                    style=ft.ButtonStyle(color=COLORS["accent_error"]),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Show dialog
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

=======
>>>>>>> 16da978 (feat(chat): implement AI chat with Gemini integration and persistence)
    async def _on_upload_click(self, e: Any) -> None:
        """Handle upload button click."""
        try:
            files = await self.file_picker.pick_files(
                allowed_extensions=["pdf", "txt"],
                allow_multiple=False,
            )
            if files and files[0].path:
                file_path = Path(files[0].path)
                self._handle_upload(file_path)
        except Exception as ex:
            logger.error(f"Error picking file: {ex}", exc_info=True)
            self._show_error("Failed to open file picker")

    def _handle_upload(self, file_path: Path) -> None:
        """Handle file upload in background thread."""

        def upload_worker() -> None:
            """Perform upload in background."""
            try:
                self._show_info("Uploading document...")

                # Upload the document
                metadata = self.vault_manager.upload_document(file_path)

                # Update app state
                app_state.add_document({
                    "id": metadata.id,
                    "filename": metadata.filename,
                    "original_path": metadata.original_path,
                    "storage_path": metadata.storage_path,
                    "file_type": metadata.file_type,
                    "file_size_bytes": metadata.file_size_bytes,
                    "word_count": metadata.word_count,
                    "token_count": metadata.token_count,
                    "extracted_text": metadata.extracted_text,
                    "is_active": metadata.is_active,
                    "created_at": metadata.created_at,
                })

                # Show success
                self._show_success(f"Uploaded: {file_path.name}")

            except UnsupportedFileTypeError as e:
                self._show_error(e.message)
            except FileSizeExceededError as e:
                self._show_error(e.message)
            except VaultError as e:
                logger.error(f"Vault error during upload: {e}", exc_info=True)
                self._show_error(e.message)
            except Exception as ex:
                logger.error(f"Unexpected error during upload: {ex}", exc_info=True)
                self._show_error("Failed to upload document")

        # Run in background
        self._page.run_thread(upload_worker)

    def _show_toast(self, toast: ToastNotification) -> None:
        """Show a toast notification."""
        toast.on_dismiss = lambda: self._remove_toast(toast)
        self.toasts.append(toast)
        self.toast_container.controls.append(toast)
        self.toast_container.update()

        # Auto-dismiss after 4 seconds
        async def auto_dismiss() -> None:
            await asyncio.sleep(4)
            self._remove_toast(toast)

        self._page.run_task(auto_dismiss)

    def _remove_toast(self, toast: ToastNotification) -> None:
        """Remove a toast notification."""
        if toast in self.toasts:
            self.toasts.remove(toast)
        if toast in self.toast_container.controls:
            self.toast_container.controls.remove(toast)
            self.toast_container.update()

    def _show_success(self, message: str) -> None:
        """Show success toast."""
        toast = ToastNotification(message, notification_type="success")
        self._show_toast(toast)

    def _show_error(self, message: str) -> None:
        """Show error toast."""
        toast = ToastNotification(message, notification_type="error")
        self._show_toast(toast)

    def _show_info(self, message: str) -> None:
        """Show info toast."""
        toast = ToastNotification(message, notification_type="info")
        self._show_toast(toast)
