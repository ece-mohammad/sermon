from __future__ import annotations

from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from sermon.screens.port_screen import PortScreen
from sermon.serial_manager import SerialConfig, SerialError, SerialManager
from sermon.widgets.rx_pane import RxPane


class SermonApp(App):
    BINDINGS = [
        Binding("ctrl+p", "connect_port", "Port", priority=True),
        Binding("ctrl+d", "toggle_hex", "Hex", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.serial = SerialManager()
        self._reader_worker = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RxPane()
        yield Footer()

    def on_mount(self) -> None:
        self._update_title()

    def action_connect_port(self) -> None:
        if self.serial.is_connected:
            self.serial.disconnect()
            self._stop_reader()
            self._update_title()
            self.notify("Disconnected")
            return
        ports = SerialManager.list_ports()
        self.push_screen(PortScreen(ports), self._on_port_config)

    def _on_port_config(self, config: SerialConfig | None) -> None:
        if config is None:
            return
        try:
            self.serial.connect(config)
            self._start_reader()
            self._update_title()
            self.notify(f"Connected to {config.port}")
        except SerialError as e:
            self.notify(str(e), severity="error")

    def action_toggle_hex(self) -> None:
        rx_pane = self.query_one(RxPane)
        rx_pane.hex_mode = not rx_pane.hex_mode

    def _start_reader(self) -> None:
        self._reader_worker = self.run_worker(
            self._read_loop,
            name="serial-reader",
            group="serial",
            thread=True,
        )

    def _stop_reader(self) -> None:
        if self._reader_worker:
            self._reader_worker.cancel()
            self._reader_worker = None

    def _read_loop(self) -> None:
        while self.serial.is_connected:
            data = self.serial.read(1024)
            if data:
                timestamp = datetime.now()
                self.call_from_thread(self._on_serial_data, data, timestamp)

    def _on_serial_data(self, data: bytes, timestamp: datetime) -> None:
        rx_pane = self.query_one(RxPane)
        if rx_pane:
            rx_pane.append_data(data, timestamp)

    def _update_title(self) -> None:
        if self.serial.is_connected:
            cfg = self.serial.config
            self.title = f"Sermon — Connected: {cfg.port} @ {cfg.baudrate}"
        else:
            self.title = "Sermon — Not Connected"


def main() -> None:
    app = SermonApp()
    app.run()
