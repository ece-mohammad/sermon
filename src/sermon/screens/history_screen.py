from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView


class TxHistoryScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    TxHistoryScreen {
        align: center top;
    }

    #history-content {
        width: 80;
        margin: 1;
    }

    #history-label {
        text-style: bold;
        margin-bottom: 1;
    }

    #history-list {
        height: 1fr;
    }
    """

    def __init__(self, history: list[tuple[str, bool]], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._history = history

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ListView(id="history-list")
        yield Footer()

    def on_mount(self) -> None:
        list_view = self.query_one("#history-list", ListView)
        if not self._history:
            list_view.append(ListItem(Label("(no history)")))
        else:
            for i, (text, hex_mode) in enumerate(reversed(self._history)):
                mode = "HEX" if hex_mode else "ASC"
                display = f"{mode}  {text}"
                item = ListItem(Label(display), id=f"hist-{i}")
                item._text = text
                item._hex_mode = hex_mode
                list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is None:
            return
        text = getattr(event.item, "_text", None)
        hex_mode = getattr(event.item, "_hex_mode", None)
        if text is None or hex_mode is None:
            return
        self.dismiss((text, hex_mode))
