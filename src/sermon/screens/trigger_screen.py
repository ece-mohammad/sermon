from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Select

from sermon.data_model import SequenceDefinition, TriggerRule


class TriggerEditorScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
        Binding("f2", "toggle_active", "Toggle", priority=True),
        Binding("delete", "remove_trigger", "Remove", priority=True),
    ]

    CSS = """
    TriggerEditorScreen {
        align: center top;
    }

    #trigger-content {
        width: 90;
        height: 90%;
        margin: 1;
    }

    #trigger-table {
        height: 1fr;
    }

    #trigger-table > DataTable {
        height: 100%;
    }

    #trigger-detail {
        height: auto;
        margin-top: 1;
    }

    .detail-row {
        height: 3;
        align: left middle;
    }

    .detail-row Label {
        width: 14;
        text-style: bold;
        padding: 1 0;
    }

    .detail-input {
        width: 1fr;
    }

    .detail-select {
        width: 1fr;
    }

    #trigger-buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    #trigger-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        rules: list[TriggerRule],
        sequences: list[SequenceDefinition],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._rules = rules
        self._sequences = sequences
        self._selected_idx: int | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Label("Trigger Rules", id="trigger-label"),
            DataTable(id="trigger-table", cursor_type="row"),
            self._detail_pane(),
            Horizontal(
                Button("Add", id="add-btn", variant="primary"),
                Button("Remove", id="remove-btn", variant="error"),
                Button("Toggle", id="toggle-btn"),
                Button("Done", id="done-btn", variant="success"),
                id="trigger-buttons",
            ),
            id="trigger-content",
        )
        yield Footer()

    def _detail_pane(self) -> Vertical:
        return Vertical(
            Horizontal(
                Label("Name:"),
                Input(id="rule-name", classes="detail-input"),
                classes="detail-row",
            ),
            Horizontal(
                Label("Send Seq:"),
                Select([], id="send-seq-select", classes="detail-select"),
                classes="detail-row",
            ),
            Horizontal(
                Label("Receive Seq:"),
                Select([], id="recv-seq-select", classes="detail-select"),
                classes="detail-row",
            ),
            id="trigger-detail",
        )

    def on_mount(self) -> None:
        table = self.query_one("#trigger-table", DataTable)
        table.add_columns("Name", "Active", "Send Sequence", "Receive Sequence")
        self._refresh_table()
        self._rebuild_selects()
        self._update_detail()

    def on_screen_resume(self, event: ScreenResume) -> None:
        self._rebuild_selects()

    def _rebuild_selects(self) -> None:
        choices = [("(none)", "")]
        for s in self._sequences:
            choices.append((s.name, s.name))
        self.query_one("#send-seq-select", Select).set_options(choices)
        self.query_one("#recv-seq-select", Select).set_options(choices)

    def _refresh_table(self) -> None:
        table = self.query_one("#trigger-table", DataTable)
        table.clear()
        for r in self._rules:
            active = "✓" if r.active else "✗"
            send = r.send_sequence.name if r.send_sequence else ""
            recv = r.receive_sequence.name if r.receive_sequence else ""
            table.add_row(r.name, active, send, recv)

    def _update_detail(self) -> None:
        idx = self._selected_idx
        if idx is not None and 0 <= idx < len(self._rules):
            rule = self._rules[idx]
            self.query_one("#rule-name", Input).value = rule.name
            self.query_one("#send-seq-select", Select).value = (
                rule.send_sequence.name if rule.send_sequence else ""
            )
            self.query_one("#recv-seq-select", Select).value = (
                rule.receive_sequence.name if rule.receive_sequence else ""
            )
        else:
            self.query_one("#rule-name", Input).value = ""

    def _find_sequence(self, name: str) -> SequenceDefinition | None:
        for s in self._sequences:
            if s.name == name:
                return s
        return None

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.cursor_row is not None:
            self._selected_idx = event.cursor_row
            self._update_detail()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "done-btn":
            self.dismiss(self._rules)
        elif event.button.id == "add-btn":
            self._rules.append(TriggerRule(name=f"Rule {len(self._rules) + 1}"))
            self._selected_idx = len(self._rules) - 1
            self._refresh_table()
            table = self.query_one("#trigger-table", DataTable)
            table.focus()
            table.move_cursor(row=self._selected_idx)
            self._update_detail()
        elif event.button.id == "remove-btn":
            self.action_remove_trigger()
        elif event.button.id == "toggle-btn":
            self.action_toggle_active()

    def action_remove_trigger(self) -> None:
        if self._selected_idx is not None and 0 <= self._selected_idx < len(
            self._rules
        ):
            del self._rules[self._selected_idx]
            self._selected_idx = min(self._selected_idx, len(self._rules) - 1)
            if len(self._rules) == 0:
                self._selected_idx = None
            self._refresh_table()
            self._update_detail()

    def action_toggle_active(self) -> None:
        if self._selected_idx is not None and 0 <= self._selected_idx < len(
            self._rules
        ):
            self._rules[self._selected_idx].active = not self._rules[
                self._selected_idx
            ].active
            self._refresh_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "rule-name" and self._selected_idx is not None:
            if 0 <= self._selected_idx < len(self._rules):
                self._rules[self._selected_idx].name = event.value
                self._refresh_table()

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._selected_idx is None or not (
            0 <= self._selected_idx < len(self._rules)
        ):
            return
        rule = self._rules[self._selected_idx]
        if event.select.id == "send-seq-select":
            seq = self._find_sequence(str(event.value)) if event.value else None
            rule.send_sequence = seq
        elif event.select.id == "recv-seq-select":
            seq = self._find_sequence(str(event.value)) if event.value else None
            rule.receive_sequence = seq
        self._refresh_table()
