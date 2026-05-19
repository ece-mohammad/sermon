from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Select

from sermon.checksum import list_algorithms
from sermon.data_model import FieldDefinition, SequenceDefinition

FIELD_TYPES = [
    ("const", "const"),
    ("wildcard", "wildcard"),
    ("checksum", "checksum"),
]

CHECKSUM_OPTIONS = [("None", "")] + [(a, a) for a in list_algorithms()]


def _validate_hex(value: str) -> bool:
    raw = value.replace(" ", "").replace("\t", "")
    if not raw:
        return True
    if len(raw) % 2 != 0:
        return False
    try:
        bytes.fromhex(raw)
        return True
    except ValueError:
        return False


def _validate_scope(value: str) -> bool:
    if not value.strip():
        return True
    parts = value.replace(",", " ").split()
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if "-" in p:
            try:
                a, b = p.split("-", 1)
                int(a.strip())
                int(b.strip())
            except ValueError:
                return False
        else:
            try:
                int(p)
            except ValueError:
                return False
    return True


def _parse_scope(value: str) -> list[int]:
    indices: list[int] = []
    parts = value.replace(",", " ").split()
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if "-" in p:
            a, b = p.split("-", 1)
            if a.strip() and b.strip():
                indices.extend(range(int(a.strip()), int(b.strip()) + 1))
        else:
            indices.append(int(p))
    return indices


def _format_scope(scope: list[int]) -> str:
    if not scope:
        return ""
    groups: list[str] = []
    i = 0
    while i < len(scope):
        start = scope[i]
        end = start
        while i + 1 < len(scope) and scope[i + 1] == end + 1:
            end = scope[i + 1]
            i += 1
        if start == end:
            groups.append(str(start))
        else:
            groups.append(f"{start}-{end}")
        i += 1
    return ",".join(groups)


class SequenceEditorScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
        Binding("ctrl+n", "focus_name", "Name", show=False),
        Binding("ctrl+r", "focus_fields", "Fields", show=False),
        Binding("ctrl+g", "focus_buttons", "Buttons", show=False),
    ]

    CSS = """
    SequenceEditorScreen {
        align: center top;
    }

    #seq-content {
        width: 100%;
        height: 100%;
        margin: 0 1;
    }

    #seq-name-row {
        height: 3;
        align: left middle;
        margin-bottom: 1;
    }

    #seq-name-row Label {
        width: 16;
        text-style: bold;
        padding: 1 0;
    }

    #seq-name-input {
        width: 1fr;
    }

    #field-table {
        height: 1fr;
        margin-bottom: 1;
    }

    #detail-pane {
        height: auto;
        border: solid $primary;
        padding: 0 1;
        margin-bottom: 1;
    }

    #detail-title {
        text-style: bold;
        padding: 1 0;
    }

    .detail-row {
        height: 3;
        align: left middle;
    }

    .detail-row Label {
        width: 12;
        text-style: bold;
        padding: 1 0;
    }

    .detail-input {
        width: 1fr;
    }

    .detail-select {
        width: 1fr;
    }

    .detail-inner-row {
        height: 3;
        align: left middle;
    }

    .detail-inner-row Label {
        width: 12;
        text-style: bold;
        padding: 1 0;
    }

    #button-row {
        height: 3;
        align: center middle;
        margin-bottom: 1;
    }

    #button-row Button {
        margin: 0 1;
    }

    #validation-msg {
        color: $error;
        text-style: bold;
        height: 1;
        padding: 0 1;
    }

    .empty-detail {
        height: 5;
        align: center middle;
        color: $text-disabled;
    }
    """

    def __init__(
        self, sequence: SequenceDefinition | None = None, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._sequence = sequence or SequenceDefinition(name="NewSequence")
        self._selected_index: int | None = None
        self._updating_detail = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Horizontal(
                Label("Sequence Name:"),
                Input(
                    value=self._sequence.name,
                    id="seq-name-input",
                    placeholder="enter sequence name",
                ),
                id="seq-name-row",
            ),
            DataTable(id="field-table"),
            self._render_detail_pane(),
            Label(id="validation-msg"),
            Horizontal(
                Button("Add Field", id="btn-add", variant="default"),
                Button("Remove", id="btn-remove", variant="error"),
                Button("▲ Up", id="btn-up"),
                Button("▼ Down", id="btn-down"),
                Button("Save...", id="btn-save"),
                Button("Load...", id="btn-load"),
                Button("Done", id="btn-done", variant="primary"),
                id="button-row",
            ),
            id="seq-content",
        )
        yield Footer()

    def _render_detail_pane(self) -> Vertical:
        return Vertical(
            Label("Field Detail", id="detail-title"),
            Horizontal(
                Label("Name:"),
                Input(id="detail-name", placeholder="field name"),
                classes="detail-row",
            ),
            Horizontal(
                Label("Type:"),
                Select(
                    FIELD_TYPES,
                    value="const",
                    id="detail-type",
                    classes="detail-select",
                ),
                classes="detail-row",
            ),
            Horizontal(
                Label("Value (hex):"),
                Input(id="detail-value", placeholder="e.g. 7E 01"),
                classes="detail-row",
            ),
            Horizontal(
                Label("Checksum:"),
                Select(
                    CHECKSUM_OPTIONS,
                    id="detail-checksum",
                    classes="detail-select",
                ),
                classes="detail-row",
            ),
            Horizontal(
                Label("Scope:"),
                Input(id="detail-scope", placeholder="e.g. 0-2 or 0,1,2"),
                classes="detail-row",
            ),
            Horizontal(
                Label("Capture:"),
                Input(id="detail-capture", placeholder="capture name"),
                classes="detail-row",
            ),
            id="detail-pane",
        )

    def on_mount(self) -> None:
        table = self.query_one("#field-table", DataTable)
        table.add_column("#", width=3)
        table.add_column("Name", width=14)
        table.add_column("Type", width=10)
        table.add_column("Value", width=20)
        table.add_column("Checksum", width=10)
        table.add_column("Scope", width=12)
        table.add_column("Capture", width=10)
        self._refresh_table()
        self._update_detail_state()

    def _refresh_table(self) -> None:
        table = self.query_one("#field-table", DataTable)
        table.clear()
        for i, f in enumerate(self._sequence.fields):
            val_display = f.value if f.field_type == "const" else ""
            cs_display = f.checksum_algorithm if f.field_type == "checksum" else ""
            scope_display = (
                _format_scope(f.checksum_scope) if f.field_type == "checksum" else ""
            )
            cap_display = (
                f.capture_name if f.field_type in ("wildcard", "checksum") else ""
            )
            table.add_row(
                str(i),
                f.name,
                f.field_type,
                val_display,
                cs_display,
                scope_display,
                cap_display,
                key=str(i),
            )

    def _update_detail_state(self) -> None:
        detail_name = self.query_one("#detail-name", Input)
        detail_type = self.query_one("#detail-type", Select)
        detail_value = self.query_one("#detail-value", Input)
        detail_checksum = self.query_one("#detail-checksum", Select)
        detail_scope = self.query_one("#detail-scope", Input)
        detail_capture = self.query_one("#detail-capture", Input)
        val_msg = self.query_one("#validation-msg", Label)

        if self._selected_index is None or self._selected_index >= len(
            self._sequence.fields
        ):
            detail_name.disabled = True
            detail_type.disabled = True
            detail_value.disabled = True
            detail_checksum.disabled = True
            detail_scope.disabled = True
            detail_capture.disabled = True
            val_msg.update("")
            return

        f = self._sequence.fields[self._selected_index]
        self._updating_detail = True
        detail_name.disabled = False
        detail_type.disabled = False
        detail_type.value = f.field_type
        detail_name.value = f.name

        if f.field_type == "const":
            detail_value.disabled = False
            detail_checksum.disabled = True
            detail_scope.disabled = True
            detail_capture.disabled = True
            detail_value.value = f.value
            detail_checksum.value = ""
            detail_scope.value = ""
            detail_capture.value = ""
            val_msg.update("")
            if not _validate_hex(f.value):
                val_msg.update("Invalid hex value (must be even-length)")
        elif f.field_type == "checksum":
            detail_value.disabled = True
            detail_value.value = ""
            detail_checksum.disabled = False
            detail_checksum.value = f.checksum_algorithm
            detail_scope.disabled = False
            if not detail_scope.value:
                detail_scope.value = _format_scope(f.checksum_scope)
            detail_capture.disabled = False
            detail_capture.value = f.capture_name
            val_msg.update("")
            if not _validate_scope(detail_scope.value):
                val_msg.update("Invalid scope format")
        elif f.field_type == "wildcard":
            detail_value.disabled = True
            detail_value.value = ""
            detail_checksum.disabled = True
            detail_checksum.value = ""
            detail_scope.disabled = True
            detail_scope.value = ""
            detail_capture.disabled = False
            detail_capture.value = f.capture_name
            val_msg.update("")

        self._updating_detail = False

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is not None:
            self._selected_index = int(str(event.row_key.value))
            self._update_detail_state()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key is not None:
            self._selected_index = int(str(event.row_key.value))
            self._update_detail_state()
            self.query_one("#detail-name", Input).focus()

    def _on_detail_changed(self) -> None:
        if self._updating_detail:
            return
        if self._selected_index is None or self._selected_index >= len(
            self._sequence.fields
        ):
            return

        f = self._sequence.fields[self._selected_index]
        detail_name = self.query_one("#detail-name", Input)
        detail_type = self.query_one("#detail-type", Select)
        detail_value = self.query_one("#detail-value", Input)
        detail_checksum = self.query_one("#detail-checksum", Select)
        detail_scope = self.query_one("#detail-scope", Input)
        detail_capture = self.query_one("#detail-capture", Input)

        f.name = detail_name.value
        new_type = str(detail_type.value) if detail_type.value is not None else "const"

        if new_type != f.field_type:
            f.field_type = new_type  # type: ignore[assignment]
            if new_type == "const":
                f.checksum_algorithm = ""
                f.checksum_scope.clear()
                f.capture_name = ""
            elif new_type == "wildcard":
                f.value = ""
                f.checksum_algorithm = ""
                f.checksum_scope.clear()
            elif new_type == "checksum":
                f.value = ""

        if f.field_type == "const":
            f.value = detail_value.value
        elif f.field_type == "checksum":
            algo = str(detail_checksum.value) if detail_checksum.value else ""
            f.checksum_algorithm = algo
            if _validate_scope(detail_scope.value):
                f.checksum_scope = _parse_scope(detail_scope.value)
            f.capture_name = detail_capture.value
        elif f.field_type == "wildcard":
            f.capture_name = detail_capture.value

        self._refresh_table()
        self._update_detail_state()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id in (
            "detail-name",
            "detail-value",
            "detail-scope",
            "detail-capture",
        ):
            self._on_detail_changed()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in ("detail-type", "detail-checksum"):
            self._on_detail_changed()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id
        if btn == "btn-add":
            self._add_field()
        elif btn == "btn-remove":
            self._remove_field()
        elif btn == "btn-up":
            self._move_field(-1)
        elif btn == "btn-down":
            self._move_field(1)
        elif btn == "btn-save":
            self._save_sequence()
        elif btn == "btn-load":
            self._load_sequence()
        elif btn == "btn-done":
            self._finish()

    def action_focus_name(self) -> None:
        self.query_one("#seq-name-input", Input).focus()

    def action_focus_fields(self) -> None:
        self.query_one("#field-table", DataTable).focus()

    def action_focus_detail(self) -> None:
        for wid in (
            self.query_one("#detail-name", Input),
            self.query_one("#detail-type", Select),
            self.query_one("#detail-value", Input),
            self.query_one("#detail-checksum", Select),
            self.query_one("#detail-scope", Input),
            self.query_one("#detail-capture", Input),
        ):
            if not wid.disabled:
                wid.focus()
                return

    def action_focus_buttons(self) -> None:
        self.query_one("#btn-add", Button).focus()

    def _add_field(self) -> None:
        self._sequence.fields.append(
            FieldDefinition(name=f"field{len(self._sequence.fields)}")
        )
        self._refresh_table()
        self._selected_index = len(self._sequence.fields) - 1
        self._update_detail_state()

    def _remove_field(self) -> None:
        if self._selected_index is None or self._selected_index >= len(
            self._sequence.fields
        ):
            return
        del self._sequence.fields[self._selected_index]
        if self._selected_index >= len(self._sequence.fields):
            self._selected_index = (
                max(0, len(self._sequence.fields) - 1)
                if self._sequence.fields
                else None
            )
        self._refresh_table()
        self._update_detail_state()

    def _move_field(self, direction: int) -> None:
        if self._selected_index is None:
            return
        idx = self._selected_index
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self._sequence.fields):
            return
        fields = self._sequence.fields
        fields[idx], fields[new_idx] = fields[new_idx], fields[idx]
        self._selected_index = new_idx
        self._refresh_table()
        self._update_detail_state()

    def _save_sequence(self) -> None:
        def on_path(path: str) -> None:
            path = path.strip()
            if not path:
                return
            try:
                from sermon.data_model import sequence_to_file

                self._sequence.name = self.query_one("#seq-name-input", Input).value
                sequence_to_file(self._sequence, path)
                self.notify(f"Saved to {path}")
            except OSError as e:
                self.notify(f"Save failed: {e}", severity="error")

        self.app.push_screen(_get_path_screen("Save sequence to:", ".json"), on_path)

    def _load_sequence(self) -> None:
        def on_path(path: str) -> None:
            path = path.strip()
            if not path:
                return
            try:
                from sermon.data_model import sequence_from_file

                seq = sequence_from_file(path)
                self._sequence = seq
                self.query_one("#seq-name-input", Input).value = seq.name
                self._selected_index = None
                self._refresh_table()
                self._update_detail_state()
                self.notify(f"Loaded from {path}")
            except (OSError, json.JSONDecodeError) as e:
                self.notify(f"Load failed: {e}", severity="error")

        self.app.push_screen(_get_path_screen("Load sequence from:", ".json"), on_path)

    def _finish(self) -> None:
        self._sequence.name = self.query_one("#seq-name-input", Input).value
        self.dismiss(self._sequence)

    def on_screen_dismissed(self, event: Screen.Dismissed) -> None:
        pass


class _PathInputScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    _PathInputScreen {
        align: center middle;
    }

    #path-content {
        width: 60;
        padding: 1;
        border: solid $primary;
    }

    #path-label {
        text-style: bold;
        margin-bottom: 1;
    }

    #path-input {
        width: 1fr;
        margin-bottom: 1;
    }

    #path-buttons {
        height: 3;
        align: center middle;
    }

    #path-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, label: str, extension: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._label = label
        self._extension = extension

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self._label, id="path-label"),
            Input(
                placeholder=f"path to {self._extension} file",
                id="path-input",
            ),
            Horizontal(
                Button("OK", id="path-ok", variant="primary"),
                Button("Cancel", id="path-cancel", variant="default"),
                id="path-buttons",
            ),
            id="path-content",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "path-ok":
            value = self.query_one("#path-input", Input).value.strip()
            if value:
                self.dismiss(value)
        elif event.button.id == "path-cancel":
            self.dismiss("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "path-input":
            value = event.value.strip()
            if value:
                self.dismiss(value)


def _get_path_screen(label: str, extension: str) -> _PathInputScreen:
    return _PathInputScreen(label, extension)
