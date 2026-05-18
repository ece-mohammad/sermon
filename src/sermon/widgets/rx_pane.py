from datetime import datetime

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import RichLog


class RxPane(RichLog):
    hex_mode = reactive(False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._lines: list[tuple[datetime, bytes]] = []

    def append_data(self, data: bytes, timestamp: datetime | None = None) -> None:
        if timestamp is None:
            timestamp = datetime.now()
        self._lines.append((timestamp, data))
        self._emit_line(timestamp, data)

    def _emit_line(self, timestamp: datetime, data: bytes) -> None:
        ts = timestamp.strftime("%H:%M:%S.%f")[:-3]
        if self.hex_mode:
            hex_str = data.hex(" ").upper()
            text = Text(f"[{ts}] ", style="bold dim")
            text.append(hex_str, style="bold green")
        else:
            ascii_str = data.decode("ascii", errors="replace")
            text = Text(f"[{ts}] ", style="bold dim")
            text.append(ascii_str, style="white")
        self.write(text)

    def watch_hex_mode(self, value: bool) -> None:
        self.clear()
        for ts, data in self._lines:
            self._emit_line(ts, data)
