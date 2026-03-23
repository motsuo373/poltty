"""Textual TUI for polltty configuration."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from . import config as cfg_store
from .applescript import apply_layout

MAX_COLS = 4
MAX_ROWS = 4


# ── ASCII-art layout preview ────────────────────────────────────────────────


def _build_preview(columns: list[int]) -> str:
    """Return an ASCII-art representation of the pane layout."""
    if not columns:
        return "(no columns)"

    row_max = max(columns)
    cell_w = 8  # inner width of each cell

    # top border
    top = "┌" + "┬".join(["─" * cell_w] * len(columns)) + "┐"
    bottom = "└" + "┴".join(["─" * cell_w] * len(columns)) + "┘"
    mid_sep = "├" + "┼".join(["─" * cell_w] * len(columns)) + "┤"

    lines = [top]
    for row in range(row_max):
        cells = []
        for col_rows in columns:
            if row < col_rows:
                cells.append(" " * cell_w)
            else:
                cells.append("▒" * cell_w)  # inactive area
        lines.append("│" + "│".join(cells) + "│")
        if row < row_max - 1:
            # Draw separator only where this row is the last for that column
            parts = []
            for col_idx, col_rows in enumerate(columns):
                if row + 1 == col_rows:
                    parts.append("─" * cell_w)
                else:
                    parts.append(" " * cell_w)
            sep = "├" + "┼".join(parts) + "┤"
            # Use a plain ├┤ row only if at least one column ends here
            if any(row + 1 == r for r in columns):
                lines.append(sep)
            else:
                lines.append("│" + "│".join([" " * cell_w] * len(columns)) + "│")
    lines.append(bottom)

    # Column labels at the top
    header_cells = [f"  C{i + 1}:{columns[i]}r  " for i in range(len(columns))]
    header = " ".join(header_cells)
    return header + "\n" + "\n".join(lines)


# ── Widgets ─────────────────────────────────────────────────────────────────


class LayoutPreview(Static):
    """Renders the ASCII-art grid preview."""

    columns: reactive[list[int]] = reactive(list, recompose=False)

    def update_columns(self, columns: list[int]) -> None:
        self.columns = list(columns)
        self.update(_build_preview(columns))


class ColumnEditor(Vertical):
    """One column's row-count editor row."""

    def __init__(self, col_idx: int, rows: int) -> None:
        super().__init__(id=f"col-editor-{col_idx}", classes="col-editor")
        self._col_idx = col_idx
        self._rows = rows

    def compose(self) -> ComposeResult:
        with Horizontal(classes="col-editor-row"):
            yield Label(f"Col {self._col_idx + 1} rows:", classes="col-label")
            yield Button("−", id=f"dec-rows-{self._col_idx}", classes="stepper")
            yield Label(str(self._rows), id=f"rows-val-{self._col_idx}", classes="rows-val")
            yield Button("+", id=f"inc-rows-{self._col_idx}", classes="stepper")


class PaneCommandInput(Horizontal):
    """A single labelled command input for one pane."""

    def __init__(self, col_idx: int, row_idx: int, command: str = "") -> None:
        super().__init__(id=f"pane-cmd-{col_idx}-{row_idx}", classes="pane-cmd")
        self._col_idx = col_idx
        self._row_idx = row_idx
        self._command = command

    def compose(self) -> ComposeResult:
        yield Label(
            f"[bold]C{self._col_idx + 1}R{self._row_idx + 1}[/]",
            classes="pane-label",
        )
        yield Input(
            value=self._command,
            placeholder="command (e.g. vim . )",
            id=f"input-{self._col_idx}-{self._row_idx}",
            classes="pane-input",
        )


# ── Main App ─────────────────────────────────────────────────────────────────


CSS = """
Screen {
    background: $surface;
}

#main-container {
    layout: horizontal;
    height: 1fr;
}

#left-panel {
    width: 36;
    border: solid $primary;
    padding: 1 2;
    margin: 0 1 0 0;
}

#right-panel {
    width: 1fr;
    border: solid $accent;
    padding: 1 2;
}

#preview {
    margin-bottom: 1;
    color: $text-muted;
}

.col-editor {
    margin-bottom: 1;
}

.col-editor-row {
    height: 3;
    align: left middle;
}

.col-label {
    width: 14;
    content-align: left middle;
}

.stepper {
    width: 3;
    min-width: 3;
    margin: 0 0;
}

.rows-val {
    width: 3;
    content-align: center middle;
}

#col-controls {
    height: 3;
    align: left middle;
    margin-top: 1;
}

#add-col {
    margin-right: 1;
}

.pane-cmd {
    height: 3;
    margin-bottom: 1;
    align: left middle;
}

.pane-label {
    width: 6;
    content-align: left middle;
    color: $accent;
}

.pane-input {
    width: 1fr;
}

#action-bar {
    height: 3;
    align: center middle;
    dock: bottom;
    padding: 0 2;
    border-top: solid $primary;
}

#action-bar Button {
    margin: 0 1;
}

#preset-bar {
    height: 3;
    align: left middle;
    margin-bottom: 1;
}

#preset-bar Input {
    width: 18;
    margin-right: 1;
}
"""


class PollttyConfigApp(App):
    """Interactive configuration TUI for polltty."""

    TITLE = "polltty config"
    SUB_TITLE = "Configure Ghostty window layout"
    CSS = CSS

    BINDINGS = [
        Binding("ctrl+s", "save_layout", "Save"),
        Binding("ctrl+a", "apply_layout", "Apply"),
        Binding("escape", "quit", "Quit"),
    ]

    def __init__(self, initial_columns: list[int] | None = None) -> None:
        super().__init__()
        if initial_columns:
            self._columns = list(initial_columns)
        else:
            last = cfg_store.get_last_layout()
            self._columns = list(last["columns"]) if last else [1, 1]
        self._commands: list[list[str]] = self._load_commands()

    def _load_commands(self) -> list[list[str]]:
        last = cfg_store.get_last_layout()
        if last and last.get("commands"):
            saved = last["commands"]
            result = []
            for col_idx, col_rows in enumerate(self._columns):
                if col_idx < len(saved):
                    col_cmds = saved[col_idx]
                    result.append(
                        [col_cmds[r] if r < len(col_cmds) else "" for r in range(col_rows)]
                    )
                else:
                    result.append([""] * col_rows)
            return result
        return [[""] * r for r in self._columns]

    # ── Layout helpers ──────────────────────────────────────────────────────

    def _sync_commands_to_columns(self) -> None:
        """Resize _commands to match current _columns."""
        new_cmds: list[list[str]] = []
        for col_idx, rows in enumerate(self._columns):
            if col_idx < len(self._commands):
                old = self._commands[col_idx]
                new_cmds.append(
                    [old[r] if r < len(old) else "" for r in range(rows)]
                )
            else:
                new_cmds.append([""] * rows)
        self._commands = new_cmds

    def _collect_commands_from_inputs(self) -> list[list[str]]:
        """Read current values from all Input widgets."""
        result: list[list[str]] = []
        for col_idx, rows in enumerate(self._columns):
            col_cmds: list[str] = []
            for row_idx in range(rows):
                widget_id = f"input-{col_idx}-{row_idx}"
                try:
                    inp = self.query_one(f"#{widget_id}", Input)
                    col_cmds.append(inp.value)
                except Exception:
                    col_cmds.append("")
            result.append(col_cmds)
        return result

    def _refresh_ui(self) -> None:
        """Rebuild the dynamic parts of the UI after columns change."""
        self._sync_commands_to_columns()

        # Update preview
        try:
            self.query_one("#preview", LayoutPreview).update_columns(self._columns)
        except Exception:
            pass

        # Rebuild column editors
        left = self.query_one("#col-editors")
        left.remove_children()
        for col_idx, rows in enumerate(self._columns):
            left.mount(ColumnEditor(col_idx, rows))

        # Rebuild pane command inputs
        pane_list = self.query_one("#pane-list")
        pane_list.remove_children()
        for col_idx, rows in enumerate(self._columns):
            for row_idx in range(rows):
                cmd = ""
                if col_idx < len(self._commands) and row_idx < len(self._commands[col_idx]):
                    cmd = self._commands[col_idx][row_idx]
                pane_list.mount(PaneCommandInput(col_idx, row_idx, cmd))

    # ── Compose ─────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main-container"):
            # Left: layout editor
            with Vertical(id="left-panel"):
                yield Label("[bold]Layout Preview[/]")
                preview = LayoutPreview(id="preview")
                preview.update(_build_preview(self._columns))
                yield preview

                yield Label("[bold]Column Settings[/]")
                with Vertical(id="col-editors"):
                    for col_idx, rows in enumerate(self._columns):
                        yield ColumnEditor(col_idx, rows)

                with Horizontal(id="col-controls"):
                    yield Button("＋ Add Column", id="add-col", variant="success")
                    yield Button("－ Remove Column", id="remove-col", variant="error")

            # Right: pane command editor
            with Vertical(id="right-panel"):
                yield Label("[bold]Pane Initial Commands[/]")
                with Horizontal(id="preset-bar"):
                    yield Input(placeholder="preset name", id="preset-name")
                    yield Button("Save Preset", id="save-preset", variant="primary")
                with ScrollableContainer(id="pane-list"):
                    for col_idx, rows in enumerate(self._columns):
                        for row_idx in range(rows):
                            cmd = ""
                            if col_idx < len(self._commands):
                                if row_idx < len(self._commands[col_idx]):
                                    cmd = self._commands[col_idx][row_idx]
                            yield PaneCommandInput(col_idx, row_idx, cmd)

        with Horizontal(id="action-bar"):
            yield Button("Apply Now  [ctrl+a]", id="apply-btn", variant="success")
            yield Button("Save Layout  [ctrl+s]", id="save-btn", variant="primary")
            yield Button("Quit  [esc]", id="quit-btn", variant="default")

        yield Footer()

    # ── Event handlers ──────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: C901
        btn_id = event.button.id or ""

        # ── Column controls ──────────────────────────────────────────────
        if btn_id == "add-col":
            if len(self._columns) < MAX_COLS:
                self._columns.append(1)
                self._refresh_ui()
            else:
                self.notify("Maximum 4 columns reached.", severity="warning")
            return

        if btn_id == "remove-col":
            if len(self._columns) > 1:
                self._columns.pop()
                self._commands = self._collect_commands_from_inputs()
                self._refresh_ui()
            else:
                self.notify("At least 1 column required.", severity="warning")
            return

        # ── Row steppers ──────────────────────────────────────────────────
        if btn_id.startswith("inc-rows-"):
            col_idx = int(btn_id.split("-")[-1])
            if self._columns[col_idx] < MAX_ROWS:
                self._commands = self._collect_commands_from_inputs()
                self._columns[col_idx] += 1
                self._refresh_ui()
            else:
                self.notify("Maximum 4 rows per column.", severity="warning")
            return

        if btn_id.startswith("dec-rows-"):
            col_idx = int(btn_id.split("-")[-1])
            if self._columns[col_idx] > 1:
                self._commands = self._collect_commands_from_inputs()
                self._columns[col_idx] -= 1
                self._refresh_ui()
            else:
                self.notify("Minimum 1 row per column.", severity="warning")
            return

        # ── Action buttons ────────────────────────────────────────────────
        if btn_id in ("apply-btn",):
            self.action_apply_layout()
            return

        if btn_id in ("save-btn",):
            self.action_save_layout()
            return

        if btn_id == "quit-btn":
            self.action_quit()
            return

        if btn_id == "save-preset":
            self._save_preset()
            return

    def _save_preset(self) -> None:
        try:
            inp = self.query_one("#preset-name", Input)
            name = inp.value.strip()
        except Exception:
            name = ""
        if not name:
            self.notify("Enter a preset name first.", severity="warning")
            return
        cmds = self._collect_commands_from_inputs()
        cfg_store.save_preset(name, self._columns, cmds)
        self.notify(f"Preset '{name}' saved!", severity="information")

    def action_save_layout(self) -> None:
        cmds = self._collect_commands_from_inputs()
        cfg_store.save_last_layout(self._columns, cmds)
        self.notify("Layout saved as last layout.", severity="information")

    def action_apply_layout(self) -> None:
        cmds = self._collect_commands_from_inputs()
        cfg_store.save_last_layout(self._columns, cmds)
        ok, msg = apply_layout(self._columns, cmds or None)
        if ok:
            self.notify("Layout applied to Ghostty!", severity="information")
        else:
            self.notify(f"AppleScript error: {msg}", severity="error")

    def action_quit(self) -> None:
        self.exit()


# ── Entry point ───────────────────────────────────────────────────────────────


def run_config_tui(initial_columns: list[int] | None = None) -> None:
    """Launch the interactive config TUI."""
    app = PollttyConfigApp(initial_columns=initial_columns)
    app.run()
