Project: sermon — compact agent notes

What matters (only the non-obvious bits an agent would otherwise guess wrong)

- Python version: the project requires Python >= 3.13 (see pyproject.toml).
  - A .venv exists at the repo root. Prefer activating it: `source .venv/bin/activate` (POSIX) or use the matching Python 3.13 interpreter.

- How to run the program quickly (no install required):
  - Run the script directly: `python src/sermon/cli.py`
  - If you prefer module-style execution without installing the package, use: `PYTHONPATH=src python -m sermon.cli`.

- Dependencies:
  - Declared in pyproject.toml: `crccheck>=1.3`, `pyserial>=3.5`, `textual>=8.2.6`.
  - Dev dependencies: `pytest>=9.0` (optional, install with `pip install -e ".[dev]"`).
  - Install by name into the active environment: `uv pip install crccheck pyserial textual`

- Packaging: hatchling build-system is configured. `pip install -e .` or `uv pip install -e .` works.

- Project layout and imports:
  - This repo uses a src/ layout. If you need to import sermon as a package for tests or REPL, either install the package properly or run with `PYTHONPATH=src` so `import sermon` resolves.
  - Pre-commit hooks: isort, black, flake8, pytest. Run `pre-commit install` if hooks are missing.

- Tests / tooling:
  - Unit tests use `pytest`. Run with: `.venv/bin/python -m pytest tests/ -v` (no `PYTHONPATH` needed — it's configured in `pyproject.toml`).
  - Test files live in `tests/` and mirror `src/sermon/` package structure.
  - Always add or update tests in the same commit as the code they cover.

- Local environment notes:
  - A .venv folder is present in the repository. Treat it as a local dev environment; avoid committing or modifying it accidentally.

If something here looks stale, prefer executable sources (pyproject.toml, src/ files) over prose.

---

## Milestone Tasks (in priority order)

### M1 — Foundation ✓
- [x] Add hatchling `[build-system]` to `pyproject.toml`
- [x] Create `src/sermon/__init__.py` and `src/sermon/cli.py` with `def main():`
- [x] Add `[project.scripts]` entry_point → `sermon.cli:main`
- [x] Basic textual `App` skeleton rendering a placeholder screen
- [x] Verify `pip install -e .` works and `sermon` launches

### M2 — Serial Layer + Live Display ✓
- [x] `SerialManager` class wrapping pyserial (port enumerate, connect/disconnect, baud/parity/stopbits config)
- [x] Threaded read task pumping bytes into textual via `call_from_thread`
- [x] Port connection/disconnection screen (ListView + baud Select + Connect button)
- [x] Scrollable RX pane (RichLog-based) with ASCII/hex dump toggle via `^d`
- [x] Live timestamping (`[HH:MM:SS.mmm]` prefix on each line)
- [x] Fix: clean shutdown on Ctrl+C when serial connected
- [x] Display mode indicator (ASCII/HEX badge in status row)
- [x] Spaced connection status format (`8 N 1` instead of `8N1`)

### M3 — Protocol Data Model & Checksum Library ✓
- [x] Implement checksum algorithms: LRC, MOD256, CRC-8, CRC-16, CRC-32 (via `crccheck` library)
- [x] Data model classes: `FieldDefinition` (name, field_type, value, checksum_algorithm, checksum_scope, capture_name, quantifier), `SequenceDefinition` (list of fields)
- [x] JSON serialization for sequences
- [x] Tests: checksum verification against known vectors, data model roundtrip, edge cases

### M4 — Pattern Matching Engine ✓
- [x] Compile `SequenceDefinition` → greedy backtracking matcher with `*` (0+) and `+` (1+) wildcards
- [x] On match: return `MatchResult` mapping capture names → captured bytes
- [x] Checksum verification integrated into match (reject on mismatch)
- [x] `match_all()` for non-overlapping matches
- [x] Tests: const, wildcard, checksum (all 5 algos), greedy backtracking, match_all, edge cases

### M5 — Sequence Editor UI ✓
- [x] `DataTable`-based field list widget (add/remove/reorder rows)
- [x] Detail pane: name, type dropdown, hex input, checksum algo, scope picker, capture name
- [x] Inline validation (hex even-length, type constraints, etc.)
- [x] Load/save sequences to/from JSON

### M6 — Trigger / Automation Engine ✓
- [x] `TriggerRule(send_sequence, receive_sequence)` model + JSON serialization
- [x] On incoming chunk, try all active trigger patterns via `SequenceMatcher`
- [x] On match: instantiate send sequence with captured values, queue for TX
- [x] CRUD editor screen for trigger rules (F4, DataTable + detail pane)
- [ ] Highlight matched regions in RX display

### M7 — Session Persistence
- [ ] Save/load full session to JSON (port config, sequences, triggers, display mode)
- [ ] Auto-save on exit, auto-restore on launch (opt-in)

### M8 — Polish
- [ ] F1/? help screen listing all keybindings
- [ ] Connection-loss detection and recovery/notification
- [ ] File logging for debugging
- [ ] Final verification: `pip install .` works and `sermon` launches

### Extra Features (ad-hoc, not in original plan)
- [x] TX input field (text entry at bottom, Enter to send)
- [x] ASCII mode supports escape sequences: `\n`, `\r`, `\t`, `\\`, `\xHH`
- [x] HEX mode in TX parses hex string from input
- [x] Pytest pre-commit hook, pyproject.toml pytest config, dev dependencies
- [x] 148 unit tests across checksum, data model, matcher, CLI, and trigger modules
- [x] Transmit history with up/down arrow navigation in TX input
- [x] History preserves HEX/ASCII mode per entry; cycling restores mode
- [x] F2 opens scrollable history list (most recent first), select to re-transmit
- [x] TX input auto-focuses on app launch
- [x] History list: alternating row colors, HEX/ASC mode labels colored differently
- [x] F3 opens sequence editor (DataTable field list, detail pane, load/save JSON)
- [x] Sequence editor section shortcuts: ctrl+n (name), ctrl+r (fields), ctrl+g (buttons)
- [x] Port binding moved to ctrl+o (avoids conflict with Textual command palette on ctrl+p)
- [x] RX/TX direction tags with color-coded display (green=RX, yellow=TX)
- [x] TX echo toggle (ctrl+e) with on/off indicator in mode bar
- [x] Control character names in ASCII mode (`<NUL>`, `<LF>`, `<DEL>`, etc.)
- [x] Re-render all existing data on hex/ASCII toggle (no data loss)
- [x] Combined mode+echo indicator badge (`"ASCII Echo"` / `"HEX"`)
- [x] Ctrl+K disconnect hotkey
- [x] Escape key dismisses all modal screens
- [x] Header with live clock on all screens
- [x] Footer with auto-populated keybinding hints
- [x] Connected/disconnected status bar visual styling (green/muted)
- [x] Custom free-text baud rate input (with common-rate hint)
- [x] Full serial config: data bits (5/6/7/8), parity (incl. Mark/Space), stop bits (1/1.5/2)
- [x] Port list shows device descriptions; empty ports state handled
- [x] Auto-focus baud input after port selection
- [x] Sequence editor: Up/Down field reorder buttons
- [x] Sequence editor: File path input modal for Save/Load
- [x] Sequence editor: Auto-disable irrelevant detail fields by type
- [x] Sequence editor: Inline validation error messages
- [x] Sequence editor: Scope format with range syntax (`0-2,5,7-9`)
- [x] Graceful connection-loss handling on serial read error
- [x] Duplicate consecutive TX entry prevention
- [x] TX history restores cursor position to end on cycle
- [x] "Not connected" error notification on TX attempt
- [x] Example `sequence.json` in repo root
- [x] TriggerRule model + JSON serialization for trigger automation
- [x] F4 trigger editor screen (DataTable + detail pane, add/remove/toggle)
- [x] Trigger rules: on RX match, resolve send sequence with captures and transmit
- [x] Automatic trigger buffer management with matched-byte removal
- [x] Ctrl+Y copies RX log content to clipboard (via xclip)
- [x] Ctrl+C clears TX input field
- [x] Sequence editor loads field details on row highlight (up/down arrows)
- [x] Sequence editor scope input: no crash on incomplete range, partial input preserved
