"""Unit tests for the InputBar UI component."""

from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from aria.ui.input_bar import InputBar


@pytest.fixture(autouse=True)
def _mock_update() -> None:
    """Make Flet control.update() a no-op so tests don't need a live page."""
    with patch.object(ft.Control, "update", return_value=None):
        yield


class TestInputBarInit:
    """Tests for InputBar initialization."""

    def test_creates_with_callback(self) -> None:
        """InputBar initializes with a send callback without errors."""
        callback = MagicMock()
        bar = InputBar(on_send=callback)
        assert bar._on_send is callback

    def test_starts_enabled(self) -> None:
        """InputBar starts in enabled state."""
        bar = InputBar(on_send=MagicMock())
        assert bar._enabled is True

    def test_char_counter_starts_at_zero(self) -> None:
        """Character counter displays '0 chars' initially."""
        bar = InputBar(on_send=MagicMock())
        assert bar._char_counter.value == "0 chars"

    def test_text_field_starts_empty(self) -> None:
        """Text field value is empty on init."""
        bar = InputBar(on_send=MagicMock())
        assert bar._text_field.value is None or bar._text_field.value == ""


class TestInputBarSend:
    """Tests for InputBar send behavior."""

    def test_send_calls_callback_with_trimmed_text(self) -> None:
        """_send() fires the callback with the trimmed input text."""
        callback = MagicMock()
        bar = InputBar(on_send=callback)
        bar._text_field.value = "  Hello Aria!  "
        bar._send()
        callback.assert_called_once_with("Hello Aria!")

    def test_send_clears_field(self) -> None:
        """_send() clears the text field after sending."""
        callback = MagicMock()
        bar = InputBar(on_send=callback)
        bar._text_field.value = "Some text"
        bar._send()
        assert bar._text_field.value == ""

    def test_send_resets_counter(self) -> None:
        """_send() resets the character counter to '0 chars'."""
        callback = MagicMock()
        bar = InputBar(on_send=callback)
        bar._text_field.value = "Some text"
        bar._send()
        assert bar._char_counter.value == "0 chars"

    def test_send_ignores_empty_input(self) -> None:
        """_send() does not fire the callback when input is empty or whitespace."""
        callback = MagicMock()
        bar = InputBar(on_send=callback)
        bar._text_field.value = "   "
        bar._send()
        callback.assert_not_called()

    def test_send_ignores_none_value(self) -> None:
        """_send() does not fire when text field value is None."""
        callback = MagicMock()
        bar = InputBar(on_send=callback)
        bar._text_field.value = None
        bar._send()
        callback.assert_not_called()

    def test_send_blocked_when_disabled(self) -> None:
        """_send() does not fire when the bar is disabled."""
        callback = MagicMock()
        bar = InputBar(on_send=callback)
        bar.set_enabled(False)
        bar._text_field.value = "Hello"
        bar._send()
        callback.assert_not_called()


class TestInputBarSetEnabled:
    """Tests for InputBar.set_enabled()."""

    def test_disable_sets_read_only(self) -> None:
        """set_enabled(False) sets the text field to read-only."""
        bar = InputBar(on_send=MagicMock())
        bar.set_enabled(False)
        assert bar._text_field.read_only is True
        assert bar._enabled is False

    def test_enable_removes_read_only(self) -> None:
        """set_enabled(True) restores the text field from read-only."""
        bar = InputBar(on_send=MagicMock())
        bar.set_enabled(False)
        bar.set_enabled(True)
        assert bar._text_field.read_only is False
        assert bar._enabled is True


class TestInputBarCharCounter:
    """Tests for the character counter behavior."""

    def test_change_updates_counter(self) -> None:
        """_handle_change updates the counter to reflect current length."""
        bar = InputBar(on_send=MagicMock())
        bar._text_field.value = "Hello"
        bar._handle_change(None)
        assert bar._char_counter.value == "5 chars"

    def test_empty_updates_to_zero(self) -> None:
        """_handle_change shows '0 chars' when field is emptied."""
        bar = InputBar(on_send=MagicMock())
        bar._text_field.value = ""
        bar._handle_change(None)
        assert bar._char_counter.value == "0 chars"
