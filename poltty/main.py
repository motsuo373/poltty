"""poltty — CLI entry point."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .applescript import apply_layout, generate_layout_script
from . import config as cfg_store

console = Console()

HELP_TEXT = """
[bold cyan]poltty[/bold cyan] — Ghostty terminal layout manager  (poltergeist + ghostty)

[bold]USAGE[/bold]
  poltty [COLUMN_SPEC...] [OPTIONS]
  poltty config
  poltty help

[bold]COLUMN SPEC[/bold]
  One to four integers (1–4), each representing the number of rows in that column.

  [cyan]poltty 2 2[/cyan]       →  2×2 grid  (left: 2 panes / right: 2 panes)
  [cyan]poltty 1 2[/cyan]       →  2 columns  (left: 1 pane / right: 2 panes stacked)
  [cyan]poltty 1 2 2[/cyan]     →  3 columns  (1 / 2 / 2)
  [cyan]poltty 1 2 2 1[/cyan]   →  4 columns  (1 / 2 / 2 / 1)
  [cyan]poltty 4 4 4 4[/cyan]   →  16 panes   (4×4 maximum)

[bold]SUBCOMMANDS[/bold]
  [cyan]config[/cyan]            Open the TUI to configure layout and per-pane commands.
  [cyan]help[/cyan]              Show this help message.

[bold]OPTIONS[/bold]
  [cyan]--restore / -r[/cyan]    Re-apply the last saved layout (with its commands).
  [cyan]--dry-run[/cyan]         Print the generated AppleScript without executing it.
  [cyan]--version[/cyan]         Show the version.
  [cyan]--help / -h[/cyan]       Show this help message.

[bold]NOTES[/bold]
  • Requires Ghostty ≥ 1.3.0 with AppleScript support enabled (default).
  • Run from within Ghostty — the front window is used as the target.
  • Column widths are equalized automatically after layout is applied.
  • Layout + commands are auto-saved after each successful apply.
"""


def _print_help() -> None:
    console.print(Panel(HELP_TEXT.strip(), title="poltty help", border_style="cyan"))


def _validate_columns(raw: tuple[str, ...]) -> list[int]:
    columns: list[int] = []
    for token in raw:
        try:
            v = int(token)
        except ValueError:
            console.print(f"[red]Error:[/red] '{token}' is not an integer.", highlight=False)
            sys.exit(1)
        if not (1 <= v <= 4):
            console.print(f"[red]Error:[/red] Row count must be 1–4 (got {v}).", highlight=False)
            sys.exit(1)
        columns.append(v)
    if len(columns) > 4:
        console.print("[red]Error:[/red] Maximum 4 columns allowed.", highlight=False)
        sys.exit(1)
    return columns


# ── CLI ──────────────────────────────────────────────────────────────────────


@click.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
        help_option_names=["-h", "--help"],
    ),
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--restore", "-r", is_flag=True, default=False, help="Re-apply the last saved layout.")
@click.option("--dry-run", is_flag=True, default=False, help="Print generated AppleScript instead of running it.")
@click.option("--version", is_flag=True, default=False, help="Show the version number.")
def main(
    args: tuple[str, ...],
    restore: bool,
    dry_run: bool,
    version: bool,
) -> None:
    """poltty — Ghostty terminal layout manager.

    Pass one to four integers (1-4) as COLUMN_SPEC, each representing
    the number of rows in that column.  Use 'config' to open the TUI.

    \b
    Examples:
      poltty 2 2        2x2 grid
      poltty 1 2        left:1 pane / right:2 panes
      poltty 1 2 2      3 columns
      poltty config     open interactive TUI
      poltty --restore  re-apply last saved layout
    """

    if version:
        console.print(f"poltty {__version__}")
        return

    if not args and not restore:
        _print_help()
        return

    # ── Subcommands ──────────────────────────────────────────────────────
    if args and args[0] == "help":
        _print_help()
        return

    if args and args[0] == "config":
        from .tui import run_config_tui
        initial = None
        if len(args) > 1:
            try:
                initial = _validate_columns(args[1:])
            except SystemExit:
                pass
        run_config_tui(initial_columns=initial)
        return

    # ── --restore ────────────────────────────────────────────────────────
    if restore:
        layout = cfg_store.get_last_layout()
        if not layout:
            console.print(
                "[yellow]No saved layout found.[/yellow] "
                "Run [cyan]poltty config[/cyan] to create one."
            )
            sys.exit(1)
        columns = layout["columns"]
        commands = layout.get("commands") or None
        _execute(columns, commands, dry_run)
        return

    # ── Column spec ──────────────────────────────────────────────────────
    columns = _validate_columns(args)
    _execute(columns, None, dry_run)


def _execute(
    columns: list[int],
    commands: list[list[str]] | None,
    dry_run: bool,
) -> None:
    """Generate and optionally run the AppleScript layout."""
    script = generate_layout_script(columns, commands)

    if dry_run:
        console.rule("[bold]Generated AppleScript[/bold]")
        console.print(script)
        console.rule()
        return

    spec = " ".join(str(c) for c in columns)
    console.print(f"Applying layout [cyan]{spec}[/cyan] to Ghostty…")

    from .applescript import run_applescript
    ok, msg = run_applescript(script)

    if ok:
        cfg_store.save_last_layout(columns, commands)
        console.print("[green]✓ Layout applied.[/green]")
    else:
        console.print(f"[red]✗ AppleScript error:[/red] {msg}")
        sys.exit(1)
