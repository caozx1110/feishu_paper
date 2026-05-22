"""Rich-powered terminal output helpers used across AutoPaper."""

from __future__ import annotations

import builtins
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console(highlight=False)
_VERBOSE = False
_QUIET = False

_PREFIX_STYLES = {
    "✅": "green",
    "❌": "bold red",
    "⚠️": "yellow",
    "ℹ️": "blue",
    "🚀": "bold cyan",
    "🔍": "cyan",
    "📅": "cyan",
    "📄": "cyan",
    "📊": "bold cyan",
    "📋": "cyan",
    "📢": "magenta",
    "🔄": "cyan",
    "⏳": "yellow",
    "🧪": "magenta",
    "💾": "green",
    "🎉": "bold green",
    "🆕": "green",
    "🗑️": "yellow",
}


def set_output_mode(*, verbose: bool | None = None, quiet: bool | None = None) -> None:
    """Configure global terminal verbosity for CLI commands."""
    global _VERBOSE, _QUIET
    if verbose is not None:
        _VERBOSE = bool(verbose)
    if quiet is not None:
        _QUIET = bool(quiet)


def is_verbose() -> bool:
    return _VERBOSE and not _QUIET


def is_quiet() -> bool:
    return _QUIET


def print(*objects: Any, sep: str = " ", end: str = "\n", file: Any = None, flush: bool = False) -> None:
    """Drop-in replacement for ``print`` that styles common AutoPaper status lines."""
    if file is not None:
        builtins.print(*objects, sep=sep, end=end, file=file, flush=flush)
        return

    message = sep.join(str(obj) for obj in objects)
    if _should_suppress_message(message):
        return
    _rich_print_message(message, end=end)
    if flush:
        console.file.flush()


def section(title: str, subtitle: str | None = None) -> None:
    """Render a section heading."""
    if _QUIET:
        return
    text = Text(title, style="bold cyan")
    if subtitle:
        text.append(f"  {subtitle}", style="dim")
    console.print(Rule(text, style="cyan"))


def panel(title: str, body: str | RenderableType, *, style: str = "cyan") -> None:
    """Render body content in a compact panel."""
    if _QUIET:
        return
    console.print(Panel(body, title=title, border_style=style, box=box.ROUNDED))


def key_values(title: str, values: Mapping[str, Any] | Sequence[tuple[str, Any]], *, style: str = "cyan") -> None:
    """Render key/value pairs in a small panel."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column()
    items = values.items() if isinstance(values, Mapping) else values
    for key, value in items:
        grid.add_row(str(key), _stringify(value))
    panel(title, grid, style=style)


def table(
    title: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    *,
    styles: Sequence[str] | None = None,
    show_lines: bool = False,
) -> None:
    """Render a readable table."""
    if _QUIET:
        return
    rich_table = Table(
        title=title,
        header_style="bold cyan",
        box=box.SIMPLE_HEAVY,
        show_lines=show_lines,
        expand=False,
    )
    for index, column in enumerate(columns):
        style = styles[index] if styles and index < len(styles) else ""
        rich_table.add_column(column, style=style, overflow="fold")
    for row in rows:
        rich_table.add_row(*(_stringify(value) for value in row))
    console.print(rich_table)


def bullet_list(title: str, items: Iterable[Any], *, style: str = "cyan") -> None:
    """Render a compact bullet list."""
    if _QUIET:
        return
    lines = [Text(f"- {_stringify(item)}") for item in items]
    panel(title, Group(*lines) if lines else Text("(empty)", style="dim"), style=style)


def success(message: str) -> None:
    console.print(Text(f"✅ {message}", style="green"))


def warning(message: str) -> None:
    console.print(Text(f"⚠️ {message}", style="yellow"))


def error(message: str) -> None:
    console.print(Text(f"❌ {message}", style="bold red"))


def info(message: str) -> None:
    if _QUIET:
        return
    console.print(Text(f"ℹ️ {message}", style="blue"))


def debug(*objects: Any, sep: str = " ") -> None:
    """Print verbose diagnostic output only when ``--verbose`` is active."""
    if not is_verbose():
        return
    print(*objects, sep=sep)


def debug_table(
    title: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    *,
    styles: Sequence[str] | None = None,
    show_lines: bool = False,
) -> None:
    """Render a table only in verbose mode."""
    if not is_verbose():
        return
    table(title, columns, rows, styles=styles, show_lines=show_lines)


def _rich_print_message(message: str, *, end: str) -> None:
    leading_newlines = len(message) - len(message.lstrip("\n"))
    for _ in range(leading_newlines):
        console.print()
    message = message.lstrip("\n")

    if not message:
        if end and end != "\n":
            console.print("", end=end)
        return

    stripped = message.strip()
    if len(stripped) >= 10 and set(stripped) <= {"=", "-", "─"}:
        console.print(Rule(style="dim"), end=end)
        return

    style = _style_for_message(stripped)
    console.print(Text(message, style=style), end=end)


def _should_suppress_message(message: str) -> bool:
    if not _QUIET:
        return False

    stripped = message.strip()
    if not stripped:
        return True

    essential_prefixes = ("✅", "❌", "⚠️", "🎉")
    return not stripped.startswith(essential_prefixes)


def _style_for_message(message: str) -> str | None:
    for prefix, style in _PREFIX_STYLES.items():
        if message.startswith(prefix):
            return style
    if message.startswith(("•", "-", "   -", "     •")):
        return "dim"
    return None


def _stringify(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
