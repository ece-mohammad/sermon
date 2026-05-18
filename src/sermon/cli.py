from __future__ import annotations

from datetime import datetime

import serial as pyserial
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, Label

from sermon.screens.port_screen import PortScreen
from sermon.serial_manager import SerialConfig, SerialError, SerialManager
from sermon.widgets.rx_pane import RxPane

_BYTESIZE_LABELS = {
    pyserial.FIVEBITS: "5",
    pyserial.SIXBITS: "6",
    pyserial.SEVENBITS: "7",
    pyserial.EIGHTBITS: "8",
}

_PARITY_LABELS = {
    pyserial.PARITY_NONE: "None",
    pyserial.PARITY_EVEN: "Even",
    pyserial.PARITY_ODD: "Odd",
    pyserial.PARITY_MARK: "Mark",
    pyserial.PARITY_SPACE: "Space",
}

_STOPBITS_LABELS = {
    pyserial.STOPBITS_ONE: "1",
    pyserial.STOPBITS_ONE_POINT_FIVE: "1.5",
    pyserial.STOPBITS_TWO: "2",
}


def _unescape_ascii(text: str) -> bytes:
    result = bytearray()
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == "n":
                result.append(0x0A)
                i += 2
                continue
            if nxt == "r":
                result.append(0x0D)
                i += 2
                continue
            if nxt == "t":
                result.append(0x09)
                i += 2
                continue
            if nxt == "\\":
                result.append(0x5C)
                i += 2
                continue
            if nxt == "x" and i + 3 < len(text):
                try:
                    val = int(text[i + 2 : i + 4], 16)
                    result.append(val)
                    i += 4
                    continue
                except ValueError:
                    pass
        result.append(ord(ch))
        i += 1
    return bytes(result)


def _fmt_config(cfg: SerialConfig) -> str:
    data = _BYTESIZE_LABELS.get(cfg.bytesize, str(cfg.bytesize))
    parity = _PARITY_LABELS.get(cfg.parity, cfg.parity)
    stop = _STOPBITS_LABELS.get(cfg.stopbits, str(cfg.stopbits))
    return f"{cfg.port} {cfg.baudrate} {data} {parity} {stop}"


class SermonApp(App):
    TITLE = "Sermon — Serial Monitor"
    CSS = """
    #status-row {
        height: 1;
        dock: top;
    }
    #status-bar {
        padding: 0 1;
        width: 1fr;
        background: $surface;
        color: $text;
    }
    #status-bar.connected {
        background: $success;
        color: $text;
    }
    #status-bar.disconnected {
        background: $surface;
        color: $text-muted;
    }
    #mode-indicator {
        padding: 0 1;
        width: auto;
        background: $accent;
        color: $text;
        text-style: bold;
    }
    #tx-row {
        height: 3;
        dock: bottom;
        layout: horizontal;
    }
    #tx-label {
        padding: 0 1;
        width: 4;
        background: $panel;
        color: $text;
        text-style: bold;
        content-align: center middle;
    }
    #tx-input {
        width: 1fr;
    }
    """
    BINDINGS = [
        Binding("ctrl+p", "connect_port", "Port", priority=True),
        Binding("ctrl+k", "disconnect", "Disconnect", priority=True),
        Binding("ctrl+d", "toggle_hex", "Hex", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.serial = SerialManager()
        self._reader_worker = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            Label("Not connected", id="status-bar"),
            Label("ASCII", id="mode-indicator"),
            id="status-row",
        )
        yield RxPane()
        yield Horizontal(
            Label("TX>", id="tx-label"),
            Input(id="tx-input", placeholder="type message, Enter to send"),
            id="tx-row",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._update_status()
        self._update_mode_indicator()

    def action_connect_port(self) -> None:
        ports = SerialManager.list_ports()
        self.push_screen(PortScreen(ports), self._on_port_config)

    def action_disconnect(self) -> None:
        if not self.serial.is_connected:
            self.notify("Not connected")
            return
        self.serial.disconnect()
        self._stop_reader()
        self._update_status()
        self.notify("Disconnected")

    def action_quit(self) -> None:
        self.action_disconnect()
        return super().action_quit()

    def _on_port_config(self, config: SerialConfig | None) -> None:
        if config is None:
            return
        try:
            self.serial.connect(config)
            self._start_reader()
            self._update_status()
            self.notify(f"Connected to {config.port}")
        except SerialError as e:
            self.notify(str(e), severity="error")

    def action_send_data(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        if not self.serial.is_connected:
            self.notify("Not connected", severity="error")
            return
        rx_pane = self.query_one(RxPane)
        try:
            if rx_pane.hex_mode:
                raw = text.replace(" ", "").replace("\t", "")
                if len(raw) % 2 != 0:
                    self.notify("Hex string must have even length", severity="error")
                    return
                data = bytes.fromhex(raw)
            else:
                data = _unescape_ascii(text)
            self.serial.write(data)
            self.notify(f"TX: {len(data)} bytes")
        except ValueError:
            self.notify("Invalid hex characters", severity="error")
        except SerialError as e:
            self.notify(str(e), severity="error")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "tx-input":
            self.action_send_data(event.value)
            event.input.clear()

    def action_toggle_hex(self) -> None:
        rx_pane = self.query_one(RxPane)
        rx_pane.hex_mode = not rx_pane.hex_mode
        self._update_mode_indicator()

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
            try:
                data = self.serial.read(1024)
            except Exception:
                break
            if data:
                timestamp = datetime.now()
                try:
                    self.call_from_thread(self._on_serial_data, data, timestamp)
                except Exception:
                    break

    def _on_serial_data(self, data: bytes, timestamp: datetime) -> None:
        rx_pane = self.query_one(RxPane)
        if rx_pane:
            rx_pane.append_data(data, timestamp)

    def _update_status(self) -> None:
        label = self.query_one("#status-bar", Label)
        if self.serial.is_connected:
            cfg = self.serial.config
            label.update(f"Connected: {_fmt_config(cfg)}")
            label.remove_class("disconnected")
            label.add_class("connected")
        else:
            label.update("Not connected")
            label.remove_class("connected")
            label.add_class("disconnected")

    def _update_mode_indicator(self) -> None:
        rx_pane = self.query_one(RxPane)
        indicator = self.query_one("#mode-indicator", Label)
        indicator.update("HEX" if rx_pane.hex_mode else "ASCII")


def main() -> None:
    app = SermonApp()
    app.run()
