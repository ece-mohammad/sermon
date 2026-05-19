from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from serial_tui.cli import _unescape_ascii
from serial_tui.serial_manager import SerialError


def _parse_tx_input(text: str, hex_mode: bool) -> bytes:
    text = text.strip()
    if not text:
        return b""
    if hex_mode:
        raw = text.replace(" ", "").replace("\t", "")
        if len(raw) % 2 != 0:
            raise ValueError("Hex string must have even length")
        return bytes.fromhex(raw)
    return _unescape_ascii(text)


class TestParseTxInput:
    def test_ascii_simple(self) -> None:
        assert _parse_tx_input("hello", hex_mode=False) == b"hello"

    def test_ascii_empty(self) -> None:
        assert _parse_tx_input("", hex_mode=False) == b""

    def test_ascii_whitespace(self) -> None:
        assert _parse_tx_input("  ", hex_mode=False) == b""

    def test_ascii_newline(self) -> None:
        assert _parse_tx_input("line1\\nline2", hex_mode=False) == b"line1\nline2"

    def test_ascii_carriage_return(self) -> None:
        assert _parse_tx_input("hello\\rworld", hex_mode=False) == b"hello\rworld"

    def test_ascii_tab(self) -> None:
        assert _parse_tx_input("a\\tb", hex_mode=False) == b"a\tb"

    def test_ascii_backslash(self) -> None:
        assert (
            _parse_tx_input("path\\\\to\\\\file", hex_mode=False) == b"path\\to\\file"
        )

    def test_ascii_hex_escape(self) -> None:
        assert _parse_tx_input("\\x41\\x42", hex_mode=False) == b"AB"

    def test_ascii_mixed_escapes(self) -> None:
        assert _parse_tx_input("\\r\\n", hex_mode=False) == b"\r\n"

    def test_ascii_combined(self) -> None:
        assert _parse_tx_input("AT\\r\\n", hex_mode=False) == b"AT\r\n"

    def test_ascii_no_escapes_passthrough(self) -> None:
        assert _parse_tx_input("hello world", hex_mode=False) == b"hello world"

    def test_ascii_bare_backslash_passthrough(self) -> None:
        assert _parse_tx_input("test\\", hex_mode=False) == b"test\\"

    def test_ascii_unknown_escape_passthrough(self) -> None:
        assert _parse_tx_input("\\q\\z", hex_mode=False) == b"\\q\\z"

    def test_ascii_non_ascii_replaced(self) -> None:
        result = _parse_tx_input("héllo", hex_mode=False)
        assert isinstance(result, bytes)

    def test_hex_simple(self) -> None:
        assert _parse_tx_input("AABB", hex_mode=True) == bytes([0xAA, 0xBB])

    def test_hex_with_spaces(self) -> None:
        assert _parse_tx_input("AA BB", hex_mode=True) == bytes([0xAA, 0xBB])

    def test_hex_lowercase(self) -> None:
        assert _parse_tx_input("aabb", hex_mode=True) == bytes([0xAA, 0xBB])

    def test_hex_odd_length_raises(self) -> None:
        with pytest.raises(ValueError, match="even length"):
            _parse_tx_input("A", hex_mode=True)

    def test_hex_invalid_chars_raises(self) -> None:
        with pytest.raises(ValueError, match="non-hexadecimal"):
            _parse_tx_input("XX", hex_mode=True)

    def test_hex_empty(self) -> None:
        assert _parse_tx_input("", hex_mode=True) == b""

    def test_ascii_null_byte(self) -> None:
        assert _unescape_ascii("\\x00") == b"\x00"

    def test_ascii_hex_at_end_of_string(self) -> None:
        assert _unescape_ascii("prefix\\x41") == b"prefixA"

    def test_ascii_consecutive_hex(self) -> None:
        result = _unescape_ascii("\\x48\\x65\\x6C\\x6C\\x6F")
        assert result == b"Hello"

    def test_ascii_escape_only(self) -> None:
        assert _unescape_ascii("\\n") == b"\n"
        assert _unescape_ascii("\\r") == b"\r"
        assert _unescape_ascii("\\t") == b"\t"

    def test_ascii_incomplete_hex_at_end(self) -> None:
        assert _unescape_ascii("\\x") == b"\\x"
        assert _unescape_ascii("\\x0") == b"\\x0"

    def test_ascii_invalid_hex_passthrough(self) -> None:
        assert _unescape_ascii("\\xGH") == b"\\xGH"

    def test_ascii_escaped_backslash_before_hex(self) -> None:
        assert _unescape_ascii("\\\\x41") == b"\\x41"

    def test_ascii_hex_sends_correct_bytes(self) -> None:
        result = _unescape_ascii("foo\\x0A\\x0D")
        assert result == b"foo\n\r"
        assert result.hex() == "666f6f0a0d"


class TestSerialManagerWrite:
    def test_write_success(self) -> None:
        from serial_tui.serial_manager import SerialManager

        sm = SerialManager()
        sm._serial = MagicMock()
        sm._serial.is_open = True
        sm._serial.write = MagicMock()

        sm.write(b"hello")
        sm._serial.write.assert_called_once_with(b"hello")

    def test_write_not_connected(self) -> None:
        from serial_tui.serial_manager import SerialManager

        sm = SerialManager()
        sm._serial = None

        with pytest.raises(SerialError, match="Not connected"):
            sm.write(b"data")

    def test_write_serial_error(self) -> None:
        import serial

        from serial_tui.serial_manager import SerialManager

        sm = SerialManager()
        sm._serial = MagicMock()
        sm._serial.is_open = True
        sm._serial.write = MagicMock(side_effect=serial.SerialException("port error"))

        with pytest.raises(SerialError, match="port error"):
            sm.write(b"data")
