"""Textual TUI for poltty configuration."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Rule,
    Static,
)

from . import config as cfg_store
from .applescript import apply_layout

MAX_COLS = 4
MAX_ROWS = 4


# ── ASCII-art layout preview ─────────────────────────────────────────────────


def _build_preview(columns: list[int]) -> str:
    """Return an ASCII-art representation of the pane layout."""
    if not columns:
        return "(no columns)"

    row_max = max(columns)
    cell_w = 8

    top = "┌" + "┬".join(["─" * cell_w] * len(columns)) + "┐"
    bottom = "└" + "┴".join(["─" * cell_w] * len(columns)) + "┘"

    lines = [top]
    for row in range(row_max):
        cells = []
        for col_rows in columns:
            if row < col_rows:
                cells.append(" " * cell_w)
            else:
                cells.append("▒" * cell_w)
        lines.append("│" + "│".join(cells) + "│")
        if row < row_max - 1:
            parts = []
            for col_idx, col_rows in enumerate(columns):
                if row + 1 == col_rows:
                    parts.append("─" * cell_w)
                else:
                    parts.append(" " * cell_w)
            if any(row + 1 == r for r in columns):
                sep = "├" + "┼".join(parts) + "┤"
                lines.append(sep)
            else:
                lines.append("│" + "│".join([" " * cell_w] * len(columns)) + "│")
    lines.append(bottom)

    header_cells = [f"  C{i + 1}:{columns[i]}r  " for i in range(len(columns))]
    return " ".join(header_cells) + "\n" + "\n".join(lines)


# ── Widgets ──────────────────────────────────────────────────────────────────


class LayoutPreview(Static):
    """Renders the ASCII-art grid preview."""

    columns: reactive[list[int]] = reactive(list, recompose=False)

    def update_columns(self, columns: list[int]) -> None:
        self.columns = list(columns)
        self.update(_build_preview(columns))


class ColumnEditor(Vertical):
    """One column's row-count editor."""

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
            placeholder="command (e.g. vim .)",
            id=f"input-{self._col_idx}-{self._row_idx}",
            classes="pane-input",
        )


class StateListItem(ListItem):
    """A saved-state entry in the sidebar."""

    def __init__(self, state_name: str, columns: list[int]) -> None:
        super().__init__()
        self.state_name = state_name
        self.state_columns = list(columns)

    def compose(self) -> ComposeResult:
        col_spec = " ".join(str(c) for c in self.state_columns)
        if "+" in self.state_name:
            date_part, word_part = self.state_name.split("+", 1)
            text = f"{date_part}\n[dim]+{word_part}  [{col_spec}][/dim]"
        else:
            text = f"[bold]{self.state_name}[/]\n[dim][{col_spec}][/dim]"
        yield Label(text)


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
Screen {
    background: $surface;
}

Header {
    dock: top;
}

Footer {
    dock: bottom;
}

#main-container {
    layout: horizontal;
    height: 1fr;
}

/* ── Sidebar ── */

#sidebar {
    width: 28;
    border-right: solid $primary;
    background: $surface-darken-1;
}

#sidebar-title {
    background: $primary;
    color: $background;
    padding: 0 1;
    height: 1;
    text-style: bold;
}

#new-state-btn {
    width: 1fr;
    height: 3;
    margin: 0;
}

#state-list {
    height: 1fr;
}

#state-list > ListItem {
    padding: 0 1;
    border-bottom: dashed $surface-lighten-1;
}

/* ── Editor panel ── */

#editor-panel {
    width: 1fr;
    padding: 1 2;
    height: 1fr;
}

#editor-header {
    height: 1;
    margin-bottom: 1;
}

.section-label {
    text-style: bold;
    color: $text;
    margin-top: 1;
    margin-bottom: 0;
}

#preview {
    margin-top: 1;
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
    margin: 0;
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

/* ── Action bar ── */

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
"""


# ── Main App ──────────────────────────────────────────────────────────────────


class PolttyConfigApp(App):
    """Interactive configuration TUI for poltty."""

    TITLE = "poltty config"
    SUB_TITLE = "Configure Ghostty window layout"
    CSS = CSS

    BINDINGS = [
        Binding("ctrl+a", "apply_layout", "Apply"),
        Binding("ctrl+s", "save_state", "Save State"),
        Binding("ctrl+n", "new_state", "New"),
        Binding("escape", "quit", "Quit"),
    ]

    def __init__(self, initial_columns: list[int] | None = None) -> None:
        super().__init__()
        if initial_columns:
            self._columns = list(initial_columns)
        else:
            last = cfg_store.get_last_layout()
            self._columns = list(last["columns"]) if last else [1, 1]
        self._commands: list[list[str]] = self._load_commands_from_last()
        self._current_state_name: str | None = None

    def _load_commands_from_last(self) -> list[list[str]]:
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

    def _sync_commands_to_columns(self) -> None:
        """Resize _commands to match current _columns."""
        new_cmds: list[list[str]] = []
        for col_idx, rows in enumerate(self._columns):
            if col_idx < len(self._commands):
                old = self._commands[col_idx]
                new_cmds.append([old[r] if r < len(old) else "" for r in range(rows)])
            else:
                new_cmds.append([""] * rows)
        self._commands = new_cmds

    def _collect_commands_from_inputs(self) -> list[list[str]]:
        """Read current values from all Input widgets."""
        result: list[list[str]] = []
        for col_idx, rows in enumerate(self._columns):
            col_cmds: list[str] = []
            for row_idx in range(rows):
                try:
                    inp = self.query_one(f"#input-{col_idx}-{row_idx}", Input)
                    col_cmds.append(inp.value)
                except Exception:
                    col_cmds.append("")
            result.append(col_cmds)
        return result

    def _refresh_editor(self) -> None:
        """Rebuild column editors and pane command inputs after layout change."""
        self._sync_commands_to_columns()

        try:
            self.query_one("#preview", LayoutPreview).update_columns(self._columns)
        except Exception:
            pass

        col_editors = self.query_one("#col-editors")
        col_editors.remove_children()
        for col_idx, rows in enumerate(self._columns):
            col_editors.mount(ColumnEditor(col_idx, rows))

        pane_list = self.query_one("#pane-list")
        pane_list.remove_children()
        for col_idx, rows in enumerate(self._columns):
            for row_idx in range(rows):
                cmd = ""
                if col_idx < len(self._commands) and row_idx < len(self._commands[col_idx]):
                    cmd = self._commands[col_idx][row_idx]
                pane_list.mount(PaneCommandInput(col_idx, row_idx, cmd))

    def _refresh_sidebar(self) -> None:
        """Rebuild the state list in the sidebar."""
        state_list = self.query_one("#state-list", ListView)
        state_list.remove_children()
        for state in cfg_store.list_states():
            state_list.mount(StateListItem(state["name"], state["columns"]))

    def _update_editor_header(self) -> None:
        try:
            label = self.query_one("#editor-header", Label)
            if self._current_state_name:
                label.update(
                    f"[bold $accent]▶[/]  [bold]{self._current_state_name}[/]"
                )
            else:
                label.update("[dim]New Layout  (unsaved)[/dim]")
        except Exception:
            pass

    # ── Compose ──────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main-container"):

            # ── Left sidebar ────────────────────────────────────────────────
            with Vertical(id="sidebar"):
                yield Label(" STATES", id="sidebar-title")
                yield Button("＋  New State", id="new-state-btn", variant="success")
                with ListView(id="state-list"):
                    for state in cfg_store.list_states():
                        yield StateListItem(state["name"], state["columns"])

            # ── Right editor panel ──────────────────────────────────────────
            with ScrollableContainer(id="editor-panel"):
                yield Label("[dim]New Layout  (unsaved)[/dim]", id="editor-header")

                yield Rule()

                yield Label("[bold]Layout Preview[/bold]", classes="section-label")
                preview = LayoutPreview(id="preview")
                preview.update(_build_preview(self._columns))
                yield preview

                yield Label("[bold]Column Settings[/bold]", classes="section-label")
                with Vertical(id="col-editors"):
                    for col_idx, rows in enumerate(self._columns):
                        yield ColumnEditor(col_idx, rows)

                with Horizontal(id="col-controls"):
                    yield Button("＋ Add Column", id="add-col", variant="success")
                    yield Button("－ Remove Column", id="remove-col", variant="error")

                yield Rule()

                yield Label("[bold]Pane Initial Commands[/bold]", classes="section-label")
                with Vertical(id="pane-list"):
                    for col_idx, rows in enumerate(self._columns):
                        for row_idx in range(rows):
                            cmd = ""
                            if col_idx < len(self._commands):
                                if row_idx < len(self._commands[col_idx]):
                                    cmd = self._commands[col_idx][row_idx]
                            yield PaneCommandInput(col_idx, row_idx, cmd)

        with Horizontal(id="action-bar"):
            yield Button("▶ Apply  [ctrl+a]", id="apply-btn", variant="success")
            yield Button("💾 Save State  [ctrl+s]", id="save-btn", variant="primary")
            yield Button("🗑 Delete State", id="delete-btn", variant="error")
            yield Button("Quit  [esc]", id="quit-btn", variant="default")

        yield Footer()

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Load the selected state into the editor."""
        if not isinstance(event.item, StateListItem):
            return
        state = cfg_store.get_state(event.item.state_name)
        if not state:
            return

        self._current_state_name = event.item.state_name
        self._columns = list(state["columns"])
        raw_cmds = state.get("commands", [])
        self._commands = []
        for col_idx, rows in enumerate(self._columns):
            if col_idx < len(raw_cmds):
                col = raw_cmds[col_idx]
                self._commands.append(
                    [col[r] if r < len(col) else "" for r in range(rows)]
                )
            else:
                self._commands.append([""] * rows)

        self._refresh_editor()
        self._update_editor_header()

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: C901
        btn_id = event.button.id or ""

        # ── Sidebar ──────────────────────────────────────────────────────
        if btn_id == "new-state-btn":
            self.action_new_state()
            return

        # ── Column controls ──────────────────────────────────────────────
        if btn_id == "add-col":
            if len(self._columns) < MAX_COLS:
                self._commands = self._collect_commands_from_inputs()
                self._columns.append(1)
                self._refresh_editor()
            else:
                self.notify("Maximum 4 columns reached.", severity="warning")
            return

        if btn_id == "remove-col":
            if len(self._columns) > 1:
                self._commands = self._collect_commands_from_inputs()
                self._columns.pop()
                self._refresh_editor()
            else:
                self.notify("At least 1 column required.", severity="warning")
            return

        # ── Row steppers ──────────────────────────────────────────────────
        if btn_id.startswith("inc-rows-"):
            col_idx = int(btn_id.split("-")[-1])
            if self._columns[col_idx] < MAX_ROWS:
                self._commands = self._collect_commands_from_inputs()
                self._columns[col_idx] += 1
                self._refresh_editor()
            else:
                self.notify("Maximum 4 rows per column.", severity="warning")
            return

        if btn_id.startswith("dec-rows-"):
            col_idx = int(btn_id.split("-")[-1])
            if self._columns[col_idx] > 1:
                self._commands = self._collect_commands_from_inputs()
                self._columns[col_idx] -= 1
                self._refresh_editor()
            else:
                self.notify("Minimum 1 row per column.", severity="warning")
            return

        # ── Action bar ────────────────────────────────────────────────────
        if btn_id == "apply-btn":
            self.action_apply_layout()
            return

        if btn_id == "save-btn":
            self.action_save_state()
            return

        if btn_id == "delete-btn":
            self._delete_current_state()
            return

        if btn_id == "quit-btn":
            self.action_quit()
            return

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_new_state(self) -> None:
        """Reset the editor to a blank new layout."""
        self._current_state_name = None
        last = cfg_store.get_last_layout()
        self._columns = list(last["columns"]) if last else [1, 1]
        self._commands = self._load_commands_from_last()
        self._refresh_editor()
        self._update_editor_header()
        # Deselect sidebar
        try:
            self.query_one("#state-list", ListView).index = None
        except Exception:
            pass

    def action_save_state(self) -> None:
        """Save the current editor layout as a new named state."""
        cmds = self._collect_commands_from_inputs()
        name = cfg_store.generate_state_name()
        cfg_store.save_state(name, self._columns, cmds)
        cfg_store.save_last_layout(self._columns, cmds)
        self._current_state_name = name
        self._refresh_sidebar()
        self._update_editor_header()
        self.notify(f"Saved: {name}", severity="information")

    def action_apply_layout(self) -> None:
        """Apply the current editor layout to Ghostty."""
        cmds = self._collect_commands_from_inputs()
        cfg_store.save_last_layout(self._columns, cmds)
        ok, msg = apply_layout(self._columns, cmds or None)
        if ok:
            self.notify("Layout applied to Ghostty!", severity="information")
        else:
            self.notify(f"AppleScript error: {msg}", severity="error")

    def action_quit(self) -> None:
        self.exit()

    def _delete_current_state(self) -> None:
        if not self._current_state_name:
            self.notify("No state selected to delete.", severity="warning")
            return
        name = self._current_state_name
        if cfg_store.delete_state(name):
            self._current_state_name = None
            self._update_editor_header()
            self._refresh_sidebar()
            self.notify(f"Deleted: {name}", severity="information")
        else:
            self.notify("Failed to delete state.", severity="error")


# ── Entry point ───────────────────────────────────────────────────────────────


def run_config_tui(initial_columns: list[int] | None = None) -> None:
    """Launch the interactive config TUI."""
    app = PolttyConfigApp(initial_columns=initial_columns)
    app.run()
