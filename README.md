# serial-tui

A TUI serial monitor built with Python and [Textual](https://textual.textualize.io/).

## Features

- Serial port connection management (baud, data bits, parity, stop bits)
- Live RX display with timestamps, toggle between ASCII and HEX modes
- TX input with escape sequence support (`\n`, `\r`, `\t`, `\xHH`)
- Transmit history with up/down arrow navigation (mode-preserving)
- ? help screen, Ctrl+L clear RX display
- Ctrl+O port configuration screen
- Pattern matching engine with greedy backtracking wildcards (`*`, `+`)
- Checksum verification (LRC, MOD256, CRC-8/16/32) integrated into matching

## Quick Start

```bash
pip install -e .
serial-tui
```

Or without installing:

```bash
python src/serial_tui/cli.py
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
| ? | Help |
| F3 | Sequence editor |
| F4 | Trigger editor |
| F5 | Overview |
| Up/Down | Cycle transmit history |

## Project Layout

```
src/serial_tui/
├── cli.py              — Main app & entry point
├── checksum.py         — LRC, MOD256, CRC-8/16/32
├── data_model.py       — FieldDefinition, SequenceDefinition, JSON
├── matcher.py          — Pattern matching engine
├── serial_manager.py   — pyserial wrapper
├── session.py          — Session persistence
├── screens/
│   ├── help_screen.py      — Keyboard shortcuts reference
│   ├── history_screen.py   — Transmit history modal
│   ├── overview_screen.py  — Combined sequences + triggers
│   ├── port_screen.py      — Port config modal
│   ├── sequence_screen.py  — Sequence editor
│   └── trigger_screen.py   — Trigger editor
└── widgets/
    └── rx_pane.py          — Scrollable RX display
```

## Development

```bash
pip install -e ".[dev]"
pre-commit install
pytest tests/ -v
```
