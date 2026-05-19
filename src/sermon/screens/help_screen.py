from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label


class HelpScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    HelpScreen {
        align: center top;
    }

    #help-content {
        width: 80;
        height: 90%;
        margin: 1;
    }

    #help-title {
        text-style: bold;
        margin-bottom: 1;
        padding: 1 0;
    }

    #help-body {
        height: 1fr;
    }

    .help-section {
        text-style: bold;
        padding: 1 0 0 0;
    }

    .help-key {
        padding: 0 0 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Label("Help — Keyboard Shortcuts", id="help-title"),
            Vertical(
                Label("Connection", classes="help-section"),
                Label(
                    "  Ctrl+O                Open port connection", classes="help-key"
                ),
                Label("  Ctrl+K                Disconnect", classes="help-key"),
                Label(""),
                Label("Display", classes="help-section"),
                Label(
                    "  Ctrl+D                Toggle HEX/ASCII mode", classes="help-key"
                ),
                Label("  Ctrl+E                Toggle TX echo", classes="help-key"),
                Label(
                    "  Ctrl+Y                Copy RX content to clipboard",
                    classes="help-key",
                ),
                Label(
                    "  Ctrl+L                Clear RX display",
                    classes="help-key",
                ),
                Label(""),
                Label("TX Input", classes="help-section"),
                Label("  Enter                 Send data", classes="help-key"),
                Label("  Up / Down             Cycle TX history", classes="help-key"),
                Label("  Ctrl+C                Clear input field", classes="help-key"),
                Label(""),
                Label("Screens", classes="help-section"),
                Label("  ?                     This help screen", classes="help-key"),
                Label("  Ctrl+T                TX history list", classes="help-key"),
                Label("  F3                    Sequence editor", classes="help-key"),
                Label("  F4                    Trigger editor", classes="help-key"),
                Label(
                    "  F5                    Overview (sequences + triggers)",
                    classes="help-key",
                ),
                Label(""),
                Label("General", classes="help-section"),
                Label(
                    "  Escape                Dismiss current screen", classes="help-key"
                ),
                Label(""),
                Label("ASCII Escape Sequences", classes="help-section"),
                Label("  \\n, \\r, \\t           Newline, CR, tab", classes="help-key"),
                Label(
                    "  \\\\                    Literal backslash", classes="help-key"
                ),
                Label(
                    "  \\xHH                  Hex byte (e.g. \\x41 = A)",
                    classes="help-key",
                ),
                id="help-body",
            ),
            id="help-content",
        )
        yield Footer()
