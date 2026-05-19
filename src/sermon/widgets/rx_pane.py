from datetime import datetime
from typing import Literal

from rich.style import Style
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

_MATCH_HIGHLIGHT = Style(bold=True, color="white", bgcolor="#0055aa")


class RxPane(RichLog):
    hex_mode = reactive(False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._lines: list[tuple[datetime, bytes, Direction, int]] = []
        self._stream = bytearray()
        self._matches: list[tuple[int, int, str]] = []

    @property
    def rx_total_bytes(self) -> int:
        return len(self._stream)

    def append_data(
        self,
        data: bytes,
        timestamp: datetime | None = None,
        direction: Direction = "RX",
    ) -> None:
        if timestamp is None:
            timestamp = datetime.now()
        offset = len(self._stream)
        self._stream.extend(data)
        self._lines.append((timestamp, data, direction, offset))
        self._emit_line(timestamp, data, direction, offset)

    def add_match(self, start: int, end: int, rule_name: str) -> None:
        if start >= end or start < 0 or end > len(self._stream):
            return
        self._matches.append((start, end, rule_name))
        self._re_render()

    def _re_render(self) -> None:
        self.clear()
        for ts, data, direction, offset in self._lines:
            self._emit_line(ts, data, direction, offset)

    def _emit_line(
        self,
        timestamp: datetime,
        data: bytes,
        direction: Direction,
        offset: int,
    ) -> None:
        ts = timestamp.strftime("%H:%M:%S.%f")[:-3]
        is_rx = direction == "RX"
        tag_colour = "bold green" if is_rx else "bold yellow"
        data_colour = "bold green" if is_rx else "bold yellow"
        text = Text(f"[{ts}] ", style="bold dim")
        text.append(f"[{direction}] ", style=tag_colour)
        if self.hex_mode:
            for i in range(len(data)):
                abs_pos = offset + i
                style = (
                    _MATCH_HIGHLIGHT
                    if any(s <= abs_pos < e for s, e, _ in self._matches)
                    else data_colour
                )
                text.append(data[i : i + 1].hex().upper(), style=style)
                if i < len(data) - 1:
                    text.append(" ", style=style)
        else:
            for i, b in enumerate(data):
                abs_pos = offset + i
                style = (
                    _MATCH_HIGHLIGHT
                    if any(s <= abs_pos < e for s, e, _ in self._matches)
                    else data_colour
                )
                if 0x20 <= b <= 0x7E:
                    text.append(chr(b), style=style)
                elif 0x00 <= b <= 0x1F:
                    text.append(f"<{_CTRL_NAMES[b]}:{b:02X}>", style=style)
                elif b == 0x7F:
                    text.append(f"<DEL:{b:02X}>", style=style)
                else:
                    text.append(chr(b), style=style)
        self.write(text)

    def watch_hex_mode(self, value: bool) -> None:
        self._re_render()

    def get_plain_text(self) -> str:
        lines: list[str] = []
        for ts, data, direction, _offset in self._lines:
            line_ts = ts.strftime("%H:%M:%S.%f")[:-3]
            if self.hex_mode:
                display = data.hex(" ").upper()
            else:
                display = _fmt_ascii(data)
            lines.append(f"[{line_ts}] [{direction}] {display}")
        return "\n".join(lines)


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
