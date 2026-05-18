Project: sermon — compact agent notes

What matters (only the non-obvious bits an agent would otherwise guess wrong)

- Python version: the project requires Python >= 3.13 (see pyproject.toml).
  - A .venv exists at the repo root. Prefer activating it: `source .venv/bin/activate` (POSIX) or use the matching Python 3.13 interpreter.

- How to run the program quickly (no install required):
  - Run the script directly: `python src/sermon/main.py` (this works out-of-the-box).
  - If you prefer module-style execution without installing the package, set the source directory on PYTHONPATH: `PYTHONPATH=src python -m sermon.main`.

- Dependencies:
  - Declared in pyproject.toml: `pyserial>=3.5` and `textual>=8.2.6`.
  - There is no requirements.txt. Install by name into the active environment (example): `pip install pyserial textual`.

- Packaging: hatchling build-system is configured. `pip install -e .` or `uv pip install -e .` works.

- Project layout and imports:
  - This repo uses a src/ layout. If you need to import sermon as a package for tests or REPL, either install the package properly or run with `PYTHONPATH=src` so `import sermon` resolves.

- Tests / tooling:
  - Unit tests use `pytest`. Run with: `PYTHONPATH=src python -m pytest tests/ -v`
  - Test files live in `tests/` and mirror `src/sermon/` package structure.
  - Always add or update tests in the same commit as the code they cover.

- Local environment notes:
  - A .venv folder is present in the repository. Treat it as a local dev environment; avoid committing or modifying it accidentally.

- When editing or adding packaging/build tooling:
  - If you add packaging support, add a [build-system] table to pyproject.toml (for example, setuptools.build_meta) so pip can build/install the project.

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

### M3 — Protocol Data Model & Checksum Library
- [ ] Implement checksum algorithms: LRC, MOD256, CRC-8, CRC-16, CRC-32
- [ ] Data model classes: `FieldDefinition` (name, field_type, value, checksum_algorithm, checksum_scope, capture_name), `SequenceDefinition` (list of fields)
- [ ] JSON serialization for sequences

### M4 — Pattern Matching Engine
- [ ] Compile `SequenceDefinition` → greedy backtracking matcher with `*` (0+) and `+` (1+) wildcards
- [ ] On match: return `MatchResult` mapping capture names → captured bytes
- [ ] Checksum verification integrated into match (reject on mismatch)
- [ ] Unit tests against known byte sequences

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
