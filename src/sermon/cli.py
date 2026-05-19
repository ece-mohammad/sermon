from __future__ import annotations

import subprocess
from datetime import datetime

import serial as pyserial
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, Label

from sermon.data_model import SequenceDefinition, TriggerRule
from sermon.matcher import SequenceMatcher
from sermon.screens.history_screen import TxHistoryScreen
from sermon.screens.overview_screen import OverviewScreen
from sermon.screens.port_screen import PortScreen
from sermon.screens.sequence_screen import SequenceEditorScreen
from sermon.screens.trigger_screen import TriggerEditorScreen
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


class TxInput(Input):
    BINDINGS = [
        Binding("up", "history_back", "", show=False),
        Binding("down", "history_forward", "", show=False),
        Binding("ctrl+c", "clear_input", "", show=False),
    ]

    def action_history_back(self) -> None:
        app = self.app
        if hasattr(app, "_history_back"):
            app._history_back(self)

    def action_history_forward(self) -> None:
        app = self.app
        if hasattr(app, "_history_forward"):
            app._history_forward(self)

    def action_clear_input(self) -> None:
        self.clear()
        app = self.app
        if hasattr(app, "_tx_history_index"):
            app._tx_history_index = -1


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
        Binding("ctrl+o", "connect_port", "Port", priority=True),
        Binding("ctrl+k", "disconnect", "Disconnect", priority=True),
        Binding("ctrl+d", "toggle_hex", "Hex", priority=True),
        Binding("ctrl+e", "toggle_echo", "Echo", priority=True),
        Binding("f2", "show_history", "History", priority=True),
        Binding("f3", "sequence_editor", "Sequences", priority=True),
        Binding("f4", "trigger_editor", "Triggers", priority=True),
        Binding("f5", "overview", "Overview", priority=True),
        Binding("ctrl+y", "copy_rx", "Copy", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.serial = SerialManager()
        self._reader_worker = None
        self._tx_history: list[tuple[str, bool]] = []
        self._tx_history_index = -1
        self.tx_echo = True
        self._sequences: list[SequenceDefinition] = []
        self._trigger_rules: list[TriggerRule] = []
        self._trigger_buffer = b""

    def _screen_on_stack(self, screen_type: type) -> bool:
        return any(isinstance(s, screen_type) for s in self.screen_stack)

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
            TxInput(id="tx-input", placeholder="type message, Enter to send"),
            id="tx-row",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._update_status()
        self._update_mode_indicator()
        self.query_one("#tx-input", TxInput).focus()

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
            if self.tx_echo:
                rx_pane.append_data(data, datetime.now(), direction="TX")
            self.notify(f"TX: {len(data)} bytes")
        except ValueError:
            self.notify("Invalid hex characters", severity="error")
        except SerialError as e:
            self.notify(str(e), severity="error")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "tx-input":
            text = event.value.strip()
            if text:
                rx_pane = self.query_one(RxPane)
                entry = (text, rx_pane.hex_mode)
                if not self._tx_history or self._tx_history[-1] != entry:
                    self._tx_history.append(entry)
            self._tx_history_index = -1
            self.action_send_data(event.value)
            event.input.clear()

    def _history_back(self, inp: Input) -> None:
        if not self._tx_history:
            return
        if self._tx_history_index == -1:
            self._tx_history_index = len(self._tx_history) - 1
        elif self._tx_history_index > 0:
            self._tx_history_index -= 1
        text, hex_mode = self._tx_history[self._tx_history_index]
        inp.value = text
        inp.cursor_position = len(inp.value)
        self._set_mode(hex_mode)

    def _history_forward(self, inp: Input) -> None:
        if self._tx_history_index == -1:
            return
        self._tx_history_index += 1
        if self._tx_history_index >= len(self._tx_history):
            self._tx_history_index = -1
            inp.clear()
        else:
            text, hex_mode = self._tx_history[self._tx_history_index]
            inp.value = text
            inp.cursor_position = len(inp.value)
            self._set_mode(hex_mode)

    def _set_mode(self, hex_mode: bool) -> None:
        rx_pane = self.query_one(RxPane)
        if rx_pane.hex_mode != hex_mode:
            rx_pane.hex_mode = hex_mode
            self._update_mode_indicator()

    def action_show_history(self) -> None:
        if self._screen_on_stack(TxHistoryScreen):
            return
        self.push_screen(TxHistoryScreen(self._tx_history), self._on_history_selected)

    def _on_history_selected(self, result: tuple[str, bool] | None) -> None:
        if result is None:
            return
        text, hex_mode = result
        self._set_mode(hex_mode)
        self.action_send_data(text)
        self.query_one("#tx-input", TxInput).focus()

    def action_sequence_editor(self) -> None:
        if self._screen_on_stack(SequenceEditorScreen):
            return
        self.push_screen(
            SequenceEditorScreen(),
            self._on_sequence_edit,
        )

    def _on_sequence_edit(self, result: SequenceDefinition | None) -> None:
        if result is not None:
            for i, s in enumerate(self._sequences):
                if s.name == result.name:
                    self._sequences[i] = result
                    break
            else:
                self._sequences.append(result)
            self.notify(f"Sequence '{result.name}' saved")

    def action_trigger_editor(self) -> None:
        if self._screen_on_stack(TriggerEditorScreen):
            return
        self.push_screen(
            TriggerEditorScreen(self._trigger_rules, self._sequences),
            self._on_triggers_edit,
        )

    def _on_triggers_edit(self, result: list[TriggerRule] | None) -> None:
        if result is not None:
            self._trigger_rules = result
            self._trigger_buffer = b""
            n = sum(1 for r in result if r.active and r.receive_sequence is not None)
            self.notify(f"{len(result)} trigger(s) saved, {n} active")

    def action_overview(self) -> None:
        if self._screen_on_stack(OverviewScreen):
            return
        self.push_screen(
            OverviewScreen(self._sequences, self._trigger_rules),
        )

    def _process_triggers(self, data: bytes) -> None:
        self._trigger_buffer += data
        for rule in self._trigger_rules:
            if not rule.active or rule.receive_sequence is None:
                continue
            matcher = SequenceMatcher(rule.receive_sequence)
            result = matcher.match(self._trigger_buffer)
            if result is not None:
                if rule.send_sequence is not None:
                    tx_bytes = rule.send_sequence.resolve(result.captures)
                    rx_pane = self.query_one(RxPane)
                    try:
                        self.serial.write(tx_bytes)
                        if self.tx_echo:
                            rx_pane.append_data(tx_bytes, datetime.now(), "TX")
                        captures_str = ", ".join(
                            f"{k}={v.hex(' ').upper()}"
                            for k, v in result.captures.items()
                        )
                        self.notify(
                            f"Trigger '{rule.name}' fired: TX {len(tx_bytes)}B "
                            f"({captures_str})"
                        )
                    except SerialError as e:
                        self.notify(str(e), severity="error")
                self._trigger_buffer = result.remaining
                break

    def action_toggle_hex(self) -> None:
        rx_pane = self.query_one(RxPane)
        rx_pane.hex_mode = not rx_pane.hex_mode
        self._update_mode_indicator()

    def action_copy_rx(self) -> None:
        rx_pane = self.query_one(RxPane)
        text = rx_pane.get_plain_text()
        if not text:
            self.notify("Nothing to copy")
            return
        try:
            p = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
            )
            p.communicate(text.encode("utf-8"))
        except FileNotFoundError:
            self.copy_to_clipboard(text)
        self.notify(f"Copied {len(text)} characters")

    def action_toggle_echo(self) -> None:
        self.tx_echo = not self.tx_echo
        self._update_mode_indicator()
        self.notify(f"TX echo {'on' if self.tx_echo else 'off'}")

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
            rx_pane.append_data(data, timestamp, direction="RX")
        self._process_triggers(data)

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
        mode = "HEX" if rx_pane.hex_mode else "ASCII"
        if self.tx_echo:
            mode += " Echo"
        indicator.update(mode)


def main() -> None:
    app = SermonApp()
    app.run()
