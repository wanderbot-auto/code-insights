from __future__ import annotations

from datetime import datetime

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def render_terminal_report(analysis: dict[str, object], console: Console | None = None) -> None:
    console = console or Console()

    project = analysis["project"]
    totals = analysis["totals"]
    language_stats = analysis.get("language_stats", [])
    structure = analysis.get("structure", {})
    top_directories = structure.get("top_directories", [])
    largest_files = structure.get("largest_files", [])
    cache_meta = analysis.get("meta", {}).get("cache", {})

    header = _build_header_panel(project)
    summary = _build_summary_cards(totals, cache_meta)
    language_table = _build_language_table(language_stats)
    directory_table = _build_directory_table(top_directories)
    file_table = _build_largest_files_table(largest_files)

    console.print()
    console.print(header)
    console.print()
    console.print(summary)
    console.print()
    console.print(language_table)
    console.print()
    console.print(directory_table)
    console.print()
    console.print(file_table)
    console.print()


def _build_header_panel(project: dict[str, object]) -> Panel:
    scanned_at = _format_scanned_at(str(project.get("scanned_at", "")))
    title = Text("Code Insights", style="bold white")
    subtitle = Text("Terminal Analysis Report", style="cyan")

    body = Table.grid(padding=(0, 1))
    body.add_column(style="bold #d4eaf7", no_wrap=True)
    body.add_column(style="#f5f4f1")
    body.add_row("Project", str(project.get("name", "-")))
    body.add_row("Path", str(project.get("path", "-")))
    body.add_row("Scanned At", scanned_at)
    body.add_row("Platform", str(project.get("platform", "-")))
    body.add_row("Python", str(project.get("python", "-")))

    content = Table.grid(padding=0)
    content.add_row(Align.left(title))
    content.add_row(Align.left(subtitle))
    content.add_row(Text())
    content.add_row(body)

    return Panel(
        content,
        border_style="#71c4ef",
        box=box.ROUNDED,
        padding=(1, 2),
        title="[bold #71c4ef]Overview[/bold #71c4ef]",
    )


def _build_summary_cards(totals: dict[str, object], cache_meta: dict[str, object]) -> Columns:
    cards = [
        _metric_card("Source Files", _fmt_int(totals.get("files", 0)), "#00668c"),
        _metric_card("Languages", _fmt_int(totals.get("languages", 0)), "#3b3c3d"),
        _metric_card("Total Lines", _fmt_int(totals.get("total_lines", 0)), "#00668c"),
        _metric_card("Code Lines", _fmt_int(totals.get("code_lines", 0)), "#3b3c3d"),
        _metric_card(
            "Cache Hit/Miss",
            f"{_fmt_int(cache_meta.get('hits', 0))}/{_fmt_int(cache_meta.get('misses', 0))}",
            "#00668c",
        ),
    ]
    return Columns(cards, equal=True, expand=True)


def _metric_card(label: str, value: str, accent_color: str) -> Panel:
    body = Table.grid(padding=0)
    body.add_row(Text(label, style="#313d44"))
    body.add_row(Text(value, style=f"bold {accent_color}"))
    return Panel(body, box=box.ROUNDED, border_style="#b6ccd8", padding=(0, 1))


def _build_language_table(language_stats: list[dict[str, object]]) -> Table:
    table = Table(
        title="Language Breakdown",
        title_style="bold #00668c",
        box=box.SIMPLE_HEAVY,
        header_style="bold #313d44",
        row_styles=["none", "dim"],
        expand=True,
    )
    table.add_column("Language", style="bold")
    table.add_column("Files", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Code", justify="right")
    table.add_column("Total %", justify="right")
    table.add_column("Code %", justify="right")
    table.add_column("Total Share")
    table.add_column("Code Share")

    if not language_stats:
        table.add_row("No source files detected", "-", "-", "-", "-", "-", "-", "-")
        return table

    for row in language_stats:
        total_percent = float(row.get("total_percent", 0.0))
        code_percent = float(row.get("code_percent", 0.0))

        table.add_row(
            str(row.get("language", "-")),
            _fmt_int(row.get("files", 0)),
            _fmt_int(row.get("total_lines", 0)),
            _fmt_int(row.get("code_lines", 0)),
            f"{total_percent:.2f}%",
            f"{code_percent:.2f}%",
            _bar(total_percent, width=18, style="#00668c"),
            _bar(code_percent, width=18, style="#71c4ef"),
        )

    return table


def _build_directory_table(top_directories: list[dict[str, object]]) -> Table:
    table = Table(
        title="Project Structure (Top-level Directories)",
        title_style="bold #00668c",
        box=box.SIMPLE_HEAVY,
        header_style="bold #313d44",
        row_styles=["none", "dim"],
        expand=True,
    )
    table.add_column("Directory")
    table.add_column("Files", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Code", justify="right")
    table.add_column("Size")

    if not top_directories:
        table.add_row("No structure data", "-", "-", "-", "-")
        return table

    max_total = max(int(item.get("total_lines", 0)) for item in top_directories) or 1
    for row in top_directories:
        total = int(row.get("total_lines", 0))
        ratio = total / max_total * 100
        table.add_row(
            str(row.get("path", "-")),
            _fmt_int(row.get("files", 0)),
            _fmt_int(total),
            _fmt_int(row.get("code_lines", 0)),
            _bar(ratio, width=20, style="#00668c"),
        )

    return table


def _build_largest_files_table(largest_files: list[dict[str, object]]) -> Table:
    table = Table(
        title="Largest Source Files",
        title_style="bold #00668c",
        box=box.SIMPLE_HEAVY,
        header_style="bold #313d44",
        row_styles=["none", "dim"],
        expand=True,
    )
    table.add_column("Path", overflow="fold")
    table.add_column("Language")
    table.add_column("Total", justify="right")
    table.add_column("Code", justify="right")

    if not largest_files:
        table.add_row("No source file data", "-", "-", "-")
        return table

    for row in largest_files:
        table.add_row(
            str(row.get("path", "-")),
            str(row.get("language", "-")),
            _fmt_int(row.get("total_lines", 0)),
            _fmt_int(row.get("code_lines", 0)),
        )

    return table


def _bar(percent: float, *, width: int, style: str) -> Text:
    normalized = max(0.0, min(100.0, percent))
    filled = int(round(width * normalized / 100))
    text = Text("█" * filled, style=style)
    text.append("░" * (width - filled), style="#b6ccd8")
    return text


def _fmt_int(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _format_scanned_at(raw_value: str) -> str:
    try:
        dt = datetime.fromisoformat(raw_value)
        return dt.strftime("%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return raw_value or "-"
