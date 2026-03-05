from __future__ import annotations

import math
from datetime import datetime
from pathlib import PurePosixPath

from rich import box
from rich.align import Align
from rich.console import Console
from rich.console import Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

PIE_COLORS = [
    "bright_cyan",
    "bright_blue",
    "bright_green",
    "bright_magenta",
    "bright_yellow",
    "bright_red",
]

WAFFLE_MIN_CELLS = 600
WAFFLE_COLUMNS = 60
WAFFLE_CELL = "■"
WAFFLE_H_GAP = ""
WAFFLE_V_GAP_LINES = 0
TOP_PANEL_HEIGHT = 19


def render_terminal_report(analysis: dict[str, object], console: Console | None = None) -> None:
    console = console or Console()

    project = analysis["project"]
    totals = analysis["totals"]
    language_stats = analysis.get("language_stats", [])
    structure = analysis.get("structure", {})
    largest_files = structure.get("largest_files", [])
    top_directories = structure.get("top_directories", [])
    cache_meta = analysis.get("meta", {}).get("cache", {})

    dashboard = _build_dashboard(
        project=project,
        totals=totals,
        cache_meta=cache_meta,
        language_stats=language_stats,
        largest_files=largest_files,
        top_directories=top_directories,
    )

    console.print(dashboard)


def _build_dashboard(
    *,
    project: dict[str, object],
    totals: dict[str, object],
    cache_meta: dict[str, object],
    language_stats: list[dict[str, object]],
    largest_files: list[dict[str, object]],
    top_directories: list[dict[str, object]],
) -> Group:
    language_row = Table.grid(expand=True, padding=0)
    language_row.add_column(ratio=1)
    language_row.add_column(ratio=1)
    language_row.add_row(
        _build_language_panel(language_stats),
        _build_language_monitor_panel(language_stats),
    )

    structure_row = Table.grid(expand=True, padding=0)
    structure_row.add_column(ratio=1)
    structure_row.add_column(ratio=1)
    structure_row.add_row(
        _build_largest_files_panel(largest_files),
        _build_structure_monitor_panel(top_directories, largest_files),
    )

    return Group(
        _build_overview_panel(project, totals, cache_meta),
        language_row,
        structure_row,
    )


def _build_overview_panel(
    project: dict[str, object],
    totals: dict[str, object],
    cache_meta: dict[str, object],
) -> Panel:
    content = Table.grid(expand=True, padding=1)
    content.add_column(ratio=1)
    content.add_column(ratio=1)
    content.add_row(
        _build_project_summary_panel(project),
        _build_totals_panel(totals, cache_meta),
    )

    headline = Text("Terminal Analysis Report", style="bold cyan")

    return Panel(
        Group(Align.center(headline), content),
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
        title="[bold cyan]Overview[/bold cyan]",
    )


def _build_project_summary_panel(project: dict[str, object]) -> Panel:
    scanned_at = _format_scanned_at(str(project.get("scanned_at", "")))
    content = Table.grid(padding=(0, 1))
    content.add_column(style="bold")
    content.add_column()
    content.add_row("Code Insights", Text("Terminal Analysis Report", style="cyan"))
    content.add_row("Project", str(project.get("name", "-")))
    content.add_row("Path", str(project.get("path", "-")))
    content.add_row("Scanned At", scanned_at)
    content.add_row("Runtime", f"{project.get('platform', '-')} | Python {project.get('python', '-')}")

    return Panel(
        content,
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
        title="[bold cyan]Project[/bold cyan]",
    )


def _build_totals_panel(totals: dict[str, object], cache_meta: dict[str, object]) -> Panel:
    total_lines = int(totals.get("total_lines", 0) or 0)
    code_lines = int(totals.get("code_lines", 0) or 0)
    cache_hits = int(cache_meta.get("hits", 0) or 0)
    cache_misses = int(cache_meta.get("misses", 0) or 0)
    cache_total = cache_hits + cache_misses
    code_ratio = (code_lines / total_lines * 100.0) if total_lines else 0.0
    cache_ratio = (cache_hits / cache_total * 100.0) if cache_total else 0.0

    metrics = Table.grid(expand=True, padding=(0, 1))
    metrics.add_column(style="bold")
    metrics.add_column(justify="right")
    metrics.add_row("Source Files", _fmt_int(totals.get("files", 0)))
    metrics.add_row("Languages", _fmt_int(totals.get("languages", 0)))
    metrics.add_row("Total Lines", _fmt_int(total_lines))
    metrics.add_row("Code Lines", _fmt_int(code_lines))
    metrics.add_row("Cache Hit/Miss", f"{_fmt_int(cache_hits)}/{_fmt_int(cache_misses)}")

    ratios = Table(
        box=box.SIMPLE,
        expand=True,
        show_header=True,
        padding=(0, 1),
        collapse_padding=True,
    )
    ratios.add_column("Metric", style="bold")
    ratios.add_column("Rate", justify="right")
    ratios.add_column("Bar")
    ratios.add_row("Code Density", f"{code_ratio:.2f}%", _bar(code_ratio, width=16, style="bright_cyan"))
    ratios.add_row("Cache Hit Rate", f"{cache_ratio:.2f}%", _bar(cache_ratio, width=16, style="bright_blue"))

    return Panel(
        Group(metrics, ratios),
        title="[bold cyan]Totals[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
    )


def _build_language_panel(language_stats: list[dict[str, object]]) -> Panel:
    segments = _build_segments(language_stats, label_key="language", value_key="total_lines", limit=6)
    if not segments:
        return Panel(
            "No source files detected",
            title="[bold cyan]Language Breakdown[/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 1),
            height=TOP_PANEL_HEIGHT,
        )

    waffle_rows = math.ceil(WAFFLE_MIN_CELLS / WAFFLE_COLUMNS)
    if waffle_rows % 2 != 0:
        waffle_rows += 1
    content = Group(
        Padding(
            Align.center(
                _waffle_chart(
                    segments,
                    rows=waffle_rows,
                    cols=WAFFLE_COLUMNS,
                )
            ),
            (1, 0, 0, 0),
        ),
        _build_legend_table(segments, label_title="Language"),
    )

    return Panel(
        content,
        title="[bold cyan]Language Breakdown[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        height=TOP_PANEL_HEIGHT,
    )


def _build_language_monitor_panel(language_stats: list[dict[str, object]]) -> Panel:
    if not language_stats:
        return Panel(
            "No language metrics",
            title="[bold cyan]monitor[/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 1),
            height=TOP_PANEL_HEIGHT,
        )

    ordered = sorted(
        language_stats,
        key=lambda row: (-int(row.get("total_lines", 0)), str(row.get("language", ""))),
    )
    total_lines = sum(int(row.get("total_lines", 0) or 0) for row in ordered)
    top = ordered[0]
    top_lines = int(top.get("total_lines", 0) or 0)
    top_pct = (top_lines / total_lines * 100.0) if total_lines else 0.0

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(style="bold")
    table.add_column(justify="right")
    table.add_row("Dominant", str(top.get("language", "-")))
    table.add_row("Top Share", f"{top_pct:.2f}%")
    table.add_row("Languages", _fmt_int(len(ordered)))

    density_table = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 1), collapse_padding=True)
    density_table.add_column("Language", style="bold")
    density_table.add_column("Density", justify="right")
    density_table.add_column("Bar")

    for row in ordered[:4]:
        lines = int(row.get("total_lines", 0) or 0)
        code = int(row.get("code_lines", 0) or 0)
        density = (code / lines * 100.0) if lines else 0.0
        density_table.add_row(
            str(row.get("language", "-")),
            f"{density:.1f}%",
            _bar(density, width=10, style="bright_green"),
        )

    return Panel(
        Group(table, density_table),
        title="[bold cyan]monitor[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        height=TOP_PANEL_HEIGHT,
    )


def _build_largest_files_panel(largest_files: list[dict[str, object]]) -> Panel:
    table = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 1), collapse_padding=True)
    table.add_column("File", no_wrap=True, overflow="ellipsis")
    table.add_column("Stats", no_wrap=True, width=16, overflow="ellipsis")

    if not largest_files:
        table.add_row("No source file data", "-")
        return Panel(
            table,
            title="[bold cyan]Largest Source Files[/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 1),
        )

    for row in largest_files[:10]:
        total = int(row.get("total_lines", 0))
        stats = _format_stats_cell(str(row.get("language", "-")), total)
        table.add_row(
            _format_path_cell(str(row.get("path", "-")), max_total_len=26, parent_max_len=14, name_max_len=11),
            stats,
        )

    return Panel(
        table,
        title="[bold cyan]Largest Source Files[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
    )


def _build_structure_monitor_panel(
    top_directories: list[dict[str, object]],
    largest_files: list[dict[str, object]],
) -> Panel:
    total_lines = sum(int(item.get("total_lines", 0) or 0) for item in top_directories)
    top_dir = top_directories[0] if top_directories else {}
    top_dir_lines = int(top_dir.get("total_lines", 0) or 0)
    top_dir_share = (top_dir_lines / total_lines * 100.0) if total_lines else 0.0

    largest = largest_files[0] if largest_files else {}

    summary = Table.grid(expand=True, padding=(0, 1))
    summary.add_column(style="bold")
    summary.add_column(justify="right")
    summary.add_row("Top Dir", str(top_dir.get("path", "-")))
    summary.add_row("Dir Share", f"{top_dir_share:.2f}%")
    summary.add_row("Largest", _shorten_path(str(largest.get("path", "-")), max_len=22))
    summary.add_row("Lines", _fmt_int(largest.get("total_lines", 0)))

    directory_table = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 1), collapse_padding=True)
    directory_table.add_column("Directory", style="bold")
    directory_table.add_column("Files", justify="right")
    directory_table.add_column("Share", justify="right")

    for row in top_directories[:4]:
        lines = int(row.get("total_lines", 0) or 0)
        share = (lines / total_lines * 100.0) if total_lines else 0.0
        directory_table.add_row(
            str(row.get("path", "-")),
            _fmt_int(row.get("files", 0)),
            f"{share:.1f}%",
        )

    if not top_directories:
        directory_table.add_row("-", "0", "0.0%")

    return Panel(
        Group(summary, directory_table),
        title="[bold cyan]monitor[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
    )


def _build_segments(
    rows: list[dict[str, object]],
    *,
    label_key: str,
    value_key: str,
    limit: int,
) -> list[dict[str, object]]:
    ranked: list[tuple[str, int]] = []
    for row in rows:
        label = str(row.get(label_key, "-"))
        value = int(row.get(value_key, 0) or 0)
        if value > 0:
            ranked.append((label, value))

    ranked.sort(key=lambda item: (-item[1], item[0]))
    if not ranked:
        return []

    if len(ranked) > limit:
        kept = ranked[: limit - 1]
        other = sum(value for _, value in ranked[limit - 1 :])
        kept.append(("Other", other))
        ranked = kept

    total = sum(value for _, value in ranked) or 1
    segments: list[dict[str, object]] = []
    for index, (label, value) in enumerate(ranked):
        segments.append(
            {
                "label": label,
                "value": value,
                "percent": value / total * 100.0,
                "style": PIE_COLORS[index % len(PIE_COLORS)],
            }
        )
    return segments


def _waffle_chart(segments: list[dict[str, object]], *, rows: int = 10, cols: int = 10) -> Text:
    if not segments:
        return Text("No data")

    total_cells = rows * cols
    raw_cells = [float(segment["percent"]) / 100.0 * total_cells for segment in segments]
    base_cells = [int(value) for value in raw_cells]
    remaining = total_cells - sum(base_cells)

    remainders = sorted(
        enumerate(raw_cells),
        key=lambda item: (item[1] - int(item[1]), -item[0]),
        reverse=True,
    )
    for index, _ in remainders[:remaining]:
        base_cells[index] += 1

    style_cells: list[str] = []
    for index, count in enumerate(base_cells):
        style_cells.extend([str(segments[index]["style"])] * count)
    if len(style_cells) < total_cells:
        style_cells.extend(["grey37"] * (total_cells - len(style_cells)))
    style_cells = style_cells[:total_cells]

    chart = Text(style="none")
    row_width = cols * len(WAFFLE_CELL) + max(0, cols - 1) * len(WAFFLE_H_GAP)
    style_rows = [style_cells[row * cols : (row + 1) * cols] for row in range(rows)]

    # Render two logical rows per terminal row to reduce vertical sparsity.
    for row in range(0, rows, 2):
        top_styles = style_rows[row]
        bottom_styles = style_rows[row + 1] if row + 1 < rows else top_styles
        for index, (top_style, bottom_style) in enumerate(zip(top_styles, bottom_styles)):
            if index > 0 and WAFFLE_H_GAP:
                chart.append(WAFFLE_H_GAP)
            if top_style == bottom_style:
                chart.append("█", style=top_style)
            else:
                chart.append("▀", style=f"{top_style} on {bottom_style}")
        if row + 2 < rows:
            chart.append("\n")
            for _ in range(WAFFLE_V_GAP_LINES):
                chart.append(" " * row_width)
                chart.append("\n")
    return chart


def _build_legend_table(segments: list[dict[str, object]], *, label_title: str) -> Table:
    table = Table(
        box=box.SIMPLE,
        expand=True,
        show_header=True,
        padding=(0, 1),
        collapse_padding=True,
    )
    table.add_column("", width=1, no_wrap=True)
    table.add_column(label_title, style="bold")
    table.add_column("Percent", justify="right")
    for segment in segments:
        table.add_row(
            Text("■", style=str(segment["style"])),
            str(segment["label"]),
            f"{float(segment['percent']):.2f}%",
        )
    return table


def _fmt_int(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _shorten_path(path: str, max_len: int = 40) -> str:
    if len(path) <= max_len:
        return path
    keep = max_len - 3
    return f"...{path[-keep:]}"


def _shorten_middle(text: str, max_len: int) -> str:
    if max_len <= 3:
        return text[:max_len]
    if len(text) <= max_len:
        return text
    head = max(2, (max_len - 3) // 2)
    tail = max_len - 3 - head
    return f"{text[:head]}...{text[-tail:]}"


def _format_path_cell(path: str, max_total_len: int = 40, parent_max_len: int = 22, name_max_len: int = 16) -> Text:
    normalized = path.replace("\\", "/")
    parsed = PurePosixPath(normalized)
    name = parsed.name or normalized
    parent = "" if str(parsed.parent) == "." else str(parsed.parent)

    name_display = _shorten_middle(name, name_max_len)
    if not parent:
        return Text(name_display, style="bold")

    parent_limit = max(6, min(parent_max_len, max_total_len - len(name_display) - 1))
    parent_display = _shorten_middle(parent, parent_limit)

    cell = Text()
    cell.append(f"{parent_display}/", style="dim")
    cell.append(name_display, style="bold")
    return cell


def _format_stats_cell(language: str, total_lines: int) -> Table:
    stats = Table.grid(expand=True, padding=0)
    stats.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
    stats.add_column(justify="right", no_wrap=True)
    stats.add_row(Text(language, style="cyan"), Text(_fmt_int(total_lines), style="bold"))
    return stats


def _bar(percent: float, *, width: int, style: str) -> Text:
    normalized = max(0.0, min(100.0, percent))
    filled = int(round(width * normalized / 100))
    text = Text("█" * filled, style=style)
    text.append("░" * (width - filled), style="grey37")
    return text


def _format_scanned_at(raw_value: str) -> str:
    try:
        dt = datetime.fromisoformat(raw_value)
        return dt.strftime("%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return raw_value or "-"
