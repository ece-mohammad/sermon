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

### M5 — Sequence Editor UI
- [ ] `DataTable`-based field list widget (add/remove/reorder rows)
- [ ] Detail pane: name, type dropdown, hex input, checksum algo, scope picker, capture name
- [ ] Inline validation (hex even-length, type constraints, etc.)
- [ ] Load/save sequences to/from JSON

### M6 — Trigger / Automation Engine
- [ ] `TriggerRule(send_sequence, receive_sequence)` model
- [ ] On incoming chunk, try all active trigger patterns
- [ ] On match: instantiate send sequence with captured values, queue for TX
- [ ] Highlight matched regions in RX display
- [ ] CRUD sidebar/modal for trigger rules

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
- [x] 134 unit tests across checksum, data model, matcher, and CLI modules
- [x] Transmit history with up/down arrow navigation in TX input
- [x] History preserves HEX/ASCII mode per entry; cycling restores mode
- [x] F2 opens scrollable history list (most recent first), select to re-transmit
- [x] TX input auto-focuses on app launch
- [x] History list: alternating row colors, HEX/ASC mode labels colored differently
- [x] Ctrl+T toggles dark/light theme
