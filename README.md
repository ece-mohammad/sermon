# serial-tui

> Version 1.1.0 — A feature-rich serial monitor TUI built with Python and [Textual](https://textual.textualize.io/).

## Features

**Serial Communication**
- Full port configuration: baud rate (custom free-text), data bits (5–8), parity (None/Even/Odd/Mark/Space), stop bits (1/1.5/2)
- Device description display in port list, empty-port handling
- Connection-loss detection with error notification
- Auto-save/restore session on exit/launch

**Live Display**
- Scrollable RX pane with real-time timestamping (`[HH:MM:SS.mmm]`)
- Toggle between ASCII (with control-character names like `<NUL>`, `<LF>`, `<DEL>`) and HEX dump modes
- Per-byte match highlighting (blue background) in both modes
- Re-render preserves all data on mode toggle

**Transmit**
- TX input with escape sequence support (`\n`, `\r`, `\t`, `\\`, `\xHH`)
- HEX mode parses hex string input
- TX echo toggle (Ctrl+E) with on/off indicator
- Transmit history with up/down arrow navigation (mode-preserving per entry)
- Ctrl+T opens scrollable history list (most recent first, alternating colors)
- Duplicate consecutive entry prevention
- Ctrl+C clears input field

**Protocol Testing**
- Pattern matching engine with greedy backtracking wildcards (`*` 0+, `+` 1+)
- Checksum verification (LRC, MOD256, CRC-8/16/32) integrated into matching
- Capture groups with named fields
- Sequence editor (F3) with DataTable field list, detail pane, inline validation
- Trigger automation (F4): on RX pattern match, resolve and transmit send sequence

**UX & Convenience**
- F5 overview screen — combined table of all sequences and triggers
- ? help screen listing all keybindings
- Ctrl+Y copies RX content to clipboard
- Ctrl+L clears RX display
- Notification toasts on mode/echo toggle
- Session persistence to `~/.local/share/serial-tui/session.json`
- File logging to `~/.local/share/serial-tui/serial-tui.log`

## Quick Start

```bash
pip install -e .
serial-tui
```

Or without installing:

```bash
PYTHONPATH=src python -m serial_tui.cli
```

## Keybindings

| Key | Action |
|-----|--------|
| Ctrl+O | Configure serial port |
| Ctrl+K | Disconnect |
| Ctrl+D | Toggle HEX/ASCII display |
| Ctrl+L | Clear RX display |
| Ctrl+E | Toggle TX echo |
| Ctrl+Y | Copy RX log |
| Ctrl+T | TX history list |
| Ctrl+C | Clear TX input |
| ? | Help |
| F3 | Sequence editor |
| F4 | Trigger editor |
| F5 | Overview |
| Up/Down | Cycle TX history |
| Escape | Dismiss current screen |

## Project Layout

```
src/serial_tui/
├── cli.py              — Main app & entry point
├── checksum.py         — LRC, MOD256, CRC-8/16/32
├── data_model.py       — FieldDefinition, SequenceDefinition, TriggerRule
├── matcher.py          — Pattern matching engine with wildcards
├── serial_manager.py   — pyserial wrapper
├── session.py          — Session persistence (JSON)
├── screens/
│   ├── help_screen.py      — Keyboard shortcuts reference
│   ├── history_screen.py   — Transmit history modal
│   ├── overview_screen.py  — Combined sequences + triggers
│   ├── port_screen.py      — Port config modal
│   ├── sequence_screen.py  — Sequence editor with field list & validation
│   └── trigger_screen.py   — Trigger rule editor
└── widgets/
    └── rx_pane.py          — Scrollable RX display with match highlighting
```

## Development

```bash
pip install -e ".[dev]"
pre-commit install
pytest tests/ -v
```
