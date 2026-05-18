from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Select

from sermon.serial_manager import SerialConfig


class PortScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    def __init__(self, ports: list[dict], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._ports = ports

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Label("Select Serial Port", id="port-label"),
            ListView(id="port-list"),
            Horizontal(
                Label("Baud rate:"),
                Select(
                    [
                        (str(b), b)
                        for b in [
                            9600,
                            19200,
                            38400,
                            57600,
                            115200,
                            230400,
                            460800,
                            921600,
                        ]
                    ],
                    value=115200,
                    id="baud-select",
                ),
                id="baud-row",
            ),
            Button("Connect", id="connect-btn", variant="primary"),
            id="port-content",
        )
        yield Footer()

    def on_mount(self) -> None:
        list_view = self.query_one("#port-list", ListView)
        if not self._ports:
            list_view.append(ListItem(Label("No serial ports found")))
        else:
            for p in self._ports:
                label = f"{p['device']}"
                if p["description"]:
                    label += f" — {p['description']}"
                list_view.append(ListItem(Label(label)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.query_one("#baud-select", Select).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connect-btn":
            list_view = self.query_one("#port-list", ListView)
            if list_view.index is None or list_view.highlight_child is None:
                return
            idx = list_view.index
            if idx < 0 or idx >= len(self._ports):
                return
            baud_select = self.query_one("#baud-select", Select)
            config = SerialConfig(
                port=self._ports[idx]["device"],
                baudrate=baud_select.value if baud_select.value else 115200,
            )
            self.dismiss(config)
