# Sermon

A TUI serial monitor built with Python and [Textual](https://textual.textualize.io/).

## Features

- Serial port connection management (baud, data bits, parity, stop bits)
- Live RX display with timestamps, toggle between ASCII and HEX modes
- TX input with escape sequence support (`\n`, `\r`, `\t`, `\xHH`)
- Transmit history with up/down arrow navigation (mode-preserving)
- F2 history list with alternating row colors and color-coded mode labels
- Ctrl+T dark/light theme toggle
- Ctrl+P port configuration screen
- Pattern matching engine with greedy backtracking wildcards (`*`, `+`)
- Checksum verification (LRC, MOD256, CRC-8/16/32) integrated into matching

## Quick Start

```bash
pip install -e .
sermon
```

Or without installing:

```bash
python src/sermon/cli.py
```

## Keybindings

| Key | Action |
|-----|--------|
| Ctrl+P | Configure serial port |
| Ctrl+K | Disconnect |
| Ctrl+D | Toggle HEX/ASCII display |
| Ctrl+T | Toggle dark/light theme |
| Ctrl+C | Quit |
| F2 | Show transmit history |
| Up/Down | Cycle transmit history |

## Project Layout

```
src/sermon/
├── cli.py              — Main app & entry point
├── checksum.py         — LRC, MOD256, CRC-8/16/32
├── data_model.py       — FieldDefinition, SequenceDefinition, JSON
├── matcher.py          — Pattern matching engine
├── serial_manager.py   — pyserial wrapper
├── screens/
│   ├── port_screen.py      — Port config modal
│   └── history_screen.py   — Transmit history modal
└── widgets/
    └── rx_pane.py          — Scrollable RX display
```

## Development

```bash
pip install -e ".[dev]"
pre-commit install
pytest tests/ -v
```
