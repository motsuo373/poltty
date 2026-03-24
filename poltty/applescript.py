"""AppleScript generation and execution for Ghostty layout management."""

import subprocess
from typing import Optional


def generate_layout_script(
    columns: list[int],
    commands: Optional[list[list[str]]] = None,
) -> str:
    """
    Generate an AppleScript that splits the front Ghostty window.

    Parameters
    ----------
    columns : list[int]
        Number of rows in each column, e.g. [1, 2, 2] → 3 columns.
        Maximum 4 columns, each value 1–4.
    commands : list[list[str]] | None
        commands[col][row] — shell command to run in that pane.
        Passed as initial input text (with newline).

    Returns
    -------
    str
        Complete AppleScript source code.
    """
    if not columns:
        raise ValueError("columns must not be empty")
    if len(columns) > 4:
        raise ValueError("Maximum 4 columns allowed")
    for v in columns:
        if not (1 <= v <= 4):
            raise ValueError(f"Row count must be 1–4, got {v}")

    lines: list[str] = []
    lines.append('tell application "Ghostty"')
    lines.append("    -- Obtain the top-level terminal of the front window's focused tab")
    lines.append("    set w to front window")
    lines.append("    set t1 to focused terminal of selected tab of w")

    counter = [1]  # mutable counter

    def new_var() -> str:
        counter[0] += 1
        return f"t{counter[0]}"

    num_cols = len(columns)

    # all_terminals[col_idx][row_idx] = AppleScript variable name
    all_terminals: list[list[Optional[str]]] = []

    # Column 0 already exists as t1
    col_tops: list[str] = ["t1"]
    all_terminals.append(["t1"] + [None] * (columns[0] - 1))

    # ── Create additional columns ──────────────────────────────────────────
    # Each new column is created by splitting the previous column's top terminal to the right.
    # After all splits are created, equalize_splits is called to distribute widths evenly.
    for i in range(1, num_cols):
        var = new_var()
        col_tops.append(var)
        all_terminals.append([var] + [None] * (columns[i] - 1))
        lines.append(f"    set {var} to split {col_tops[i - 1]} direction right")

    # ── Create rows inside each column ────────────────────────────────────
    for col_idx in range(num_cols):
        prev_var = col_tops[col_idx]
        for row_idx in range(1, columns[col_idx]):
            var = new_var()
            all_terminals[col_idx][row_idx] = var
            lines.append(f"    set {var} to split {prev_var} direction down")
            prev_var = var

    # ── Equalize split sizes ───────────────────────────────────────────────
    lines.append('    perform action "equalize_splits" on t1')

    # ── Send initial commands ──────────────────────────────────────────────
    if commands:
        lines.append("    -- Send initial commands to each pane")
        for col_idx, col_cmds in enumerate(commands):
            if col_idx >= len(all_terminals):
                break
            for row_idx, cmd in enumerate(col_cmds):
                cmd = (cmd or "").strip()
                if not cmd:
                    continue
                if row_idx >= len(all_terminals[col_idx]):
                    break
                term_var = all_terminals[col_idx][row_idx]
                if term_var is None:
                    continue
                # Escape for AppleScript double-quoted string
                escaped = cmd.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'    input text "{escaped}\\n" to {term_var}')

    lines.append("end tell")
    return "\n".join(lines)


def run_applescript(script: str) -> tuple[bool, str]:
    """Execute an AppleScript string via osascript.

    Returns (success, message).
    """
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()
    return True, result.stdout.strip()


def apply_layout(
    columns: list[int],
    commands: Optional[list[list[str]]] = None,
) -> tuple[bool, str]:
    """Generate and execute the layout AppleScript."""
    script = generate_layout_script(columns, commands)
    return run_applescript(script)
