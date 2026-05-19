from datetime import datetime
from typing import Literal

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import RichLog

Direction = Literal["RX", "TX"]

_CTRL_NAMES = [
    "NUL",
    "SOH",
    "STX",
    "ETX",
    "EOT",
    "ENQ",
    "ACK",
    "BEL",
    "BS",
    "HT",
    "LF",
    "VT",
    "FF",
    "CR",
    "SO",
    "SI",
    "DLE",
    "DC1",
    "DC2",
    "DC3",
    "DC4",
    "NAK",
    "SYN",
    "ETB",
    "CAN",
    "EM",
    "SUB",
    "ESC",
    "FS",
    "GS",
    "RS",
    "US",
]


def _fmt_ascii(data: bytes) -> str:
    parts: list[str] = []
    for b in data:
        if 0x20 <= b <= 0x7E:
            parts.append(chr(b))
        elif 0x00 <= b <= 0x1F:
            parts.append(f"<{_CTRL_NAMES[b]}:{b:02X}>")
        elif b == 0x7F:
            parts.append(f"<DEL:{b:02X}>")
        else:
            parts.append(chr(b))
    return "".join(parts)


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
            text = Text(f"[{ts}] ", style="bold dim")
            text.append(f"[{direction}] ", style=tag_colour)
            text.append(_fmt_ascii(data), style=data_colour)
        self.write(text)

    def watch_hex_mode(self, value: bool) -> None:
        self.clear()
        for ts, data, direction in self._lines:
            self._emit_line(ts, data, direction)
