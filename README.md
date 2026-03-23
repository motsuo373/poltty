# polltty

> **pol**tergeist + ghos**tty** — a one-liner terminal layout manager for [Ghostty](https://ghostty.org).

`polltty` splits your Ghostty window into a custom grid of panes via AppleScript — instantly, from the command line.

```
polltty 1 2 2
```

↑ Opens 3 columns: the left has 1 pane, the middle 2 stacked, the right 2 stacked — all in one shot.

---

## Requirements

| Requirement | Version |
|---|---|
| macOS | 13 Ventura or later |
| [Ghostty](https://ghostty.org) | **≥ 1.3.0** (AppleScript support) |
| Python | ≥ 3.10 |

Ghostty's AppleScript support is **enabled by default** in v1.3.0+.
To verify: `ghostty --version`.

---

## Installation

```bash
pip install git+https://github.com/canly/ghostty-multi-window-kit.git
```

Or clone and install in editable mode for development:

```bash
git clone https://github.com/canly/ghostty-multi-window-kit.git
cd ghostty-multi-window-kit
pip install -e .
```

After installation the `polltty` command is available in your `$PATH`.

---

## Usage

### Split syntax

```
polltty <col1_rows> [<col2_rows> [<col3_rows> [<col4_rows>]]]
```

Each argument is an integer **1–4** representing the number of vertical panes in that column.
Maximum **4 columns**, maximum **4 rows per column** (16 panes total).

```bash
polltty 2 2        # 2×2 grid
polltty 1 2        # left: 1 pane  |  right: 2 panes (stacked)
polltty 1 2 2      # 3 columns: 1 / 2 / 2 rows
polltty 1 2 2 1    # 4 columns: 1 / 2 / 2 / 1 rows
polltty 4 4 4 4    # 4×4 = 16 panes (maximum)
```

### Subcommands

| Command | Description |
|---|---|
| `polltty help` | Show the help message |
| `polltty config` | Open the interactive TUI to set layout and per-pane commands |
| `polltty --restore` | Re-apply the last saved layout (with its commands) |
| `polltty --dry-run <spec>` | Print the generated AppleScript without executing it |
| `polltty --version` | Show the version number |

---

## Interactive config TUI

```bash
polltty config
```

Opens a full-screen TUI where you can:

- **Add / remove columns** (up to 4)
- **Adjust row count** per column with `+` / `−` steppers
- **Set per-pane shell commands** — run automatically when the layout is applied
- **Save named presets** for quick re-use
- **Apply** the layout directly from the TUI

### Key bindings inside the TUI

| Key | Action |
|---|---|
| `Ctrl + A` | Apply layout to Ghostty now |
| `Ctrl + S` | Save layout as "last layout" |
| `Esc` | Quit without applying |

---

## Restoring the last layout

Every successful `polltty <spec>` or TUI-applied layout is auto-saved.
Bring it back with:

```bash
polltty --restore
```

This recreates the same grid and re-runs the saved per-pane commands.

---

## Per-pane commands

Use `polltty config` to assign a shell command to any pane.
For example:

| Pane | Command |
|---|---|
| C1R1 | `vim .` |
| C2R1 | `cd ~/project && npm run dev` |
| C2R2 | `cd ~/project && npm test -- --watch` |

After saving, `polltty --restore` recreates the layout **and** runs each command.

---

## How it works

`polltty` generates an AppleScript that calls the Ghostty scripting API
(introduced in Ghostty 1.3.0):

```applescript
tell application "Ghostty"
    set w to front window
    set t1 to focused terminal of selected tab of w
    set t2 to split t1 direction right   -- new column
    set t3 to split t1 direction down    -- row in col 1
    set t4 to split t2 direction down    -- row in col 2
    input text "vim .\n" to t1
end tell
```

The script is executed via `osascript` and targets the **front Ghostty window**.
Run `polltty` from inside Ghostty for best results.

> **Note:** Column widths are divided 50/50 at each split step.
> For three or more columns the proportions become unequal (50 / 25 / 25 %).
> Resize panes manually by dragging the dividers.

---

## Configuration file

Settings are stored at `~/.polltty/config.json`:

```json
{
  "last_layout": {
    "columns": [1, 2, 2],
    "commands": [
      ["vim ."],
      ["npm run dev", "npm test"],
      ["", ""]
    ]
  },
  "presets": {
    "frontend": {
      "columns": [1, 2],
      "commands": [["vim ."], ["npm run dev", "npm test"]]
    }
  }
}
```

---

## License

MIT
