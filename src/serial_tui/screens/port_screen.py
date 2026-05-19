from __future__ import annotations

import serial
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
)

from serial_tui.serial_manager import SerialConfig

BAUD_RATES = [
    300,
    600,
    1200,
    2400,
    4800,
    9600,
    19200,
    38400,
    57600,
    115200,
    230400,
    460800,
    921600,
]

BAUD_HINT = "Common: " + ", ".join(str(b) for b in BAUD_RATES)

DATA_BITS = [
    ("5", serial.FIVEBITS),
    ("6", serial.SIXBITS),
    ("7", serial.SEVENBITS),
    ("8", serial.EIGHTBITS),
]

PARITY_OPTIONS = [
    ("None", serial.PARITY_NONE),
    ("Even", serial.PARITY_EVEN),
    ("Odd", serial.PARITY_ODD),
    ("Mark", serial.PARITY_MARK),
    ("Space", serial.PARITY_SPACE),
]

STOP_BITS = [
    ("1", serial.STOPBITS_ONE),
    ("1.5", serial.STOPBITS_ONE_POINT_FIVE),
    ("2", serial.STOPBITS_TWO),
]


class PortScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    PortScreen {
        align: center top;
    }

    #port-content {
        width: 60;
        margin: 1;
    }

    #port-label {
        text-style: bold;
        margin-bottom: 1;
    }

    #port-list {
        height: 6;
        margin-bottom: 1;
    }

    .config-row {
        height: 3;
        align: left middle;
        margin-bottom: 0;
    }

    .config-row Label {
        width: 8;
        text-style: bold;
        padding: 1 0;
    }

    .config-select {
        width: 1fr;
    }

    #baud-input {
        width: 1fr;
    }

    #baud-hint {
        color: $text-disabled;
        text-style: italic;
        margin-left: 8;
        margin-bottom: 1;
    }

    #connect-btn {
        margin-top: 1;
        width: 100%;
    }
    """

    def __init__(self, ports: list[dict], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._ports = ports

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Label("Select Serial Port", id="port-label"),
            ListView(id="port-list"),
            Horizontal(
                Label("Baud:"),
                Input(value="115200", id="baud-input", type="integer"),
                classes="config-row",
            ),
            Label(BAUD_HINT, id="baud-hint"),
            Horizontal(
                Label("Data:"),
                Select(
                    DATA_BITS,
                    value=serial.EIGHTBITS,
                    id="data-select",
                    classes="config-select",
                ),
                classes="config-row",
            ),
            Horizontal(
                Label("Parity:"),
                Select(
                    PARITY_OPTIONS,
                    value=serial.PARITY_NONE,
                    id="parity-select",
                    classes="config-select",
                ),
                classes="config-row",
            ),
            Horizontal(
                Label("Stop:"),
                Select(
                    STOP_BITS,
                    value=serial.STOPBITS_ONE,
                    id="stop-select",
                    classes="config-select",
                ),
                classes="config-row",
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
        self.query_one("#baud-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connect-btn":
            list_view = self.query_one("#port-list", ListView)
            if list_view.index is None:
                return
            idx = list_view.index
            if idx < 0 or idx >= len(self._ports):
                return
            baud_input = self.query_one("#baud-input", Input)
            data = self.query_one("#data-select", Select)
            parity = self.query_one("#parity-select", Select)
            stop = self.query_one("#stop-select", Select)
            try:
                baudrate = (
                    int(baud_input.value.strip())
                    if baud_input.value.strip()
                    else 115200
                )
            except ValueError:
                self.notify("Invalid baud rate", severity="error")
                return
            config = SerialConfig(
                port=self._ports[idx]["device"],
                baudrate=baudrate,
                bytesize=data.value if data.value is not None else serial.EIGHTBITS,
                parity=parity.value if parity.value else serial.PARITY_NONE,
                stopbits=stop.value if stop.value else serial.STOPBITS_ONE,
            )
            self.dismiss(config)
