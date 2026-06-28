"""Unit tests for the InputBar UI component."""

from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from aria.ui.input_bar import InputBar
from aria.ui.theme import COLORS


@pytest.fixture(autouse=True)
def _mock_update() -> None:
    """Make Flet control.update() a no-op so tests don't need a live page."""
    with patch.object(ft.Control, "update", return_value=None):
        yield


class TestInputBarInit:
    """Tests for InputBar initialization."""

    def test_creates_with_callbacks(self) -> None:
        """InputBar initializes with callbacks without errors."""
        on_send = MagicMock()
        on_text_change = MagicMock()
        bar = InputBar(on_send=on_send, on_text_change=on_text_change)
        assert bar._on_send is on_send
        assert bar._on_text_change is on_text_change

    def test_starts_enabled(self) -> None:
        """InputBar starts in enabled state."""
        bar = InputBar(on_send=MagicMock())
        assert bar._enabled is True

    def test_counter_starts_at_default(self) -> None:
        """Counter label shows default values initially."""
        bar = InputBar(on_send=MagicMock())
        assert "0 chars" in bar._counter_label.value
        assert "0 / 128,000 tokens" in bar._counter_label.value

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

    def test_send_triggers_empty_text_change(self) -> None:
        """_send() fires on_text_change with empty string to reset parent counter."""
        on_text_change = MagicMock()
        bar = InputBar(on_send=MagicMock(), on_text_change=on_text_change)
        bar._text_field.value = "Some text"
        bar._send()
        on_text_change.assert_called_once_with("")

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


class TestInputBarTokenBudgetBar:
    """Tests for the token budget progress bar and usage updates."""

    def test_update_usage_label_and_progress(self) -> None:
        """update_usage correctly formats the text and sets progress value."""
        bar = InputBar(on_send=MagicMock())
        bar.update_usage(chars=12, tokens=100, limit=1000, utilization=0.1)
        assert bar._counter_label.value == "12 chars • 100 / 1,000 tokens (10.0%)"
        assert bar._token_progress.value == 0.1

    def test_update_usage_caps_progress(self) -> None:
        """update_usage caps the progress bar at 1.0."""
        bar = InputBar(on_send=MagicMock())
        bar.update_usage(chars=10, tokens=2000, limit=1000, utilization=2.0)
        assert bar._token_progress.value == 1.0

    def test_update_usage_color_coding_normal(self) -> None:
        """Below 80% utilization displays the default colors."""
        bar = InputBar(on_send=MagicMock())
        bar.update_usage(chars=10, tokens=50, limit=100, utilization=0.5)
        assert bar._token_progress.color == COLORS["accent_electric"]
        assert bar._counter_label.color == COLORS["text_muted"]

    def test_update_usage_color_coding_warning(self) -> None:
        """80% to 100% utilization displays the warning color."""
        bar = InputBar(on_send=MagicMock())
        bar.update_usage(chars=10, tokens=85, limit=100, utilization=0.85)
        assert bar._token_progress.color == COLORS["accent_warning"]
        assert bar._counter_label.color == COLORS["accent_warning"]

    def test_update_usage_color_coding_error(self) -> None:
        """Over 100% utilization displays the error color."""
        bar = InputBar(on_send=MagicMock())
        bar.update_usage(chars=10, tokens=110, limit=100, utilization=1.1)
        assert bar._token_progress.color == COLORS["accent_error"]
        assert bar._counter_label.color == COLORS["accent_error"]


class TestInputBarTextChange:
    """Tests for on_text_change callback triggering."""

    def test_handle_change_triggers_callback(self) -> None:
        """_handle_change fires the text change callback with current text."""
        on_text_change = MagicMock()
        bar = InputBar(on_send=MagicMock(), on_text_change=on_text_change)
        bar._text_field.value = "Hello"
        bar._handle_change(None)
        on_text_change.assert_called_once_with("Hello")
