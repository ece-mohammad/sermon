from datetime import datetime
from typing import Literal

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import RichLog

Direction = Literal["RX", "TX"]


class RxPane(RichLog):
    hex_mode = reactive(False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._lines: list[tuple[datetime, bytes, Direction]] = []

    def append_data(
        self,
        data: bytes,
        timestamp: datetime | None = None,
        direction: Direction = "RX",
    ) -> None:
        if timestamp is None:
            timestamp = datetime.now()
        self._lines.append((timestamp, data, direction))
        self._emit_line(timestamp, data, direction)

    def _emit_line(
        self, timestamp: datetime, data: bytes, direction: Direction
    ) -> None:
        ts = timestamp.strftime("%H:%M:%S.%f")[:-3]
        is_rx = direction == "RX"
        tag_colour = "bold green" if is_rx else "bold yellow"
        data_colour = "bold green" if is_rx else "bold yellow"
        if self.hex_mode:
            hex_str = data.hex(" ").upper()
            text = Text(f"[{ts}] ", style="bold dim")
            text.append(f"[{direction}] ", style=tag_colour)
            text.append(hex_str, style=data_colour)
        else:
            ascii_str = data.decode("ascii", errors="replace")
            text = Text(f"[{ts}] ", style="bold dim")
            text.append(f"[{direction}] ", style=tag_colour)
            text.append(ascii_str, style=data_colour)
        self.write(text)

    def watch_hex_mode(self, value: bool) -> None:
        self.clear()
        for ts, data, direction in self._lines:
            self._emit_line(ts, data, direction)
