from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label

from sermon.data_model import SequenceDefinition, TriggerRule
from sermon.screens.sequence_screen import SequenceEditorScreen
from sermon.screens.trigger_screen import TriggerEditorScreen


class OverviewScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    OverviewScreen {
        align: center top;
    }

    #overview-content {
        width: 90;
        height: 90%;
        margin: 1;
    }

    #overview-label {
        text-style: bold;
        margin-bottom: 1;
    }

    #overview-table {
        height: 1fr;
    }

    #overview-table > DataTable {
        height: 100%;
    }

    #overview-buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    #overview-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        sequences: list[SequenceDefinition],
        trigger_rules: list[TriggerRule],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._sequences = sequences
        self._trigger_rules = trigger_rules
        self._selected_type: str | None = None
        self._selected_index: int | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Label("Overview — All Sequences & Triggers", id="overview-label"),
            DataTable(id="overview-table", cursor_type="row"),
            Horizontal(
                Button("Edit", id="edit-btn", variant="primary"),
                Button("Delete", id="delete-btn", variant="error"),
                Button("Done", id="done-btn", variant="success"),
                id="overview-buttons",
            ),
            id="overview-content",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#overview-table", DataTable)
        table.add_columns("Type", "Name", "Details", "Active")
        self._refresh_table()

    def on_screen_resume(self, event: ScreenResume) -> None:
        self._refresh_table()

    def _refresh_table(self) -> None:
        table = self.query_one("#overview-table", DataTable)
        table.clear()
        for i, s in enumerate(self._sequences):
            n = len(s.fields)
            details = f"{n} field{'s' if n != 1 else ''}"
            table.add_row("Sequence", s.name, details, "—", key=f"seq:{i}")
        for i, r in enumerate(self._trigger_rules):
            send = r.send_sequence.name if r.send_sequence else "(none)"
            recv = r.receive_sequence.name if r.receive_sequence else "(none)"
            details = f"{send} → {recv}"
            active = "✓" if r.active else "✗"
            table.add_row("Trigger", r.name, details, active, key=f"trg:{i}")

    def _resolve_selection(self, key: str | None) -> None:
        if key is None:
            self._selected_type = None
            self._selected_index = None
            return
        parts = str(key).split(":", 1)
        if len(parts) != 2:
            self._selected_type = None
            self._selected_index = None
            return
        self._selected_type = parts[0]
        self._selected_index = int(parts[1])

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._resolve_selection(event.row_key.value if event.row_key else None)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._resolve_selection(event.row_key.value if event.row_key else None)
        self._do_edit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "done-btn":
            self.dismiss(None)
        elif event.button.id == "edit-btn":
            self._do_edit()
        elif event.button.id == "delete-btn":
            self._do_delete()

    def _do_edit(self) -> None:
        if self._selected_type == "Sequence" and self._selected_index is not None:
            if self._selected_index >= len(self._sequences):
                return
            seq = self._sequences[self._selected_index]
            self.app.push_screen(
                SequenceEditorScreen(sequence=seq),
                self._on_sequence_edited,
            )
        elif self._selected_type == "Trigger" and self._selected_index is not None:
            if self._selected_index >= len(self._trigger_rules):
                return
            self.app.push_screen(
                TriggerEditorScreen(self._trigger_rules, self._sequences),
                self._on_triggers_edited,
            )

    def _on_sequence_edited(self, result: SequenceDefinition | None) -> None:
        if result is None:
            return
        for i, s in enumerate(self._sequences):
            if s.name == result.name:
                self._sequences[i] = result
                break
        else:
            self._sequences.append(result)
        self._refresh_table()

    def _on_triggers_edited(self, result: list[TriggerRule] | None) -> None:
        if result is not None:
            self._trigger_rules[:] = result
        self._refresh_table()

    def _do_delete(self) -> None:
        if self._selected_type == "Sequence" and self._selected_index is not None:
            if self._selected_index >= len(self._sequences):
                return
            name = self._sequences[self._selected_index].name
            del self._sequences[self._selected_index]
            self.notify(f"Sequence '{name}' deleted")
        elif self._selected_type == "Trigger" and self._selected_index is not None:
            if self._selected_index >= len(self._trigger_rules):
                return
            name = self._trigger_rules[self._selected_index].name
            del self._trigger_rules[self._selected_index]
            self.notify(f"Trigger '{name}' deleted")
        else:
            return
        self._selected_type = None
        self._selected_index = None
        self._refresh_table()
