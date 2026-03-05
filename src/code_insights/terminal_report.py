from __future__ import annotations

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

WAFFLE_DEFAULT_COLUMNS = 36
WAFFLE_MIN_COLUMNS = 24
WAFFLE_MAX_COLUMNS = 56
WAFFLE_TARGET_LOGICAL_ROWS = 8
WAFFLE_CELL = "■"
WAFFLE_H_GAP = ""
WAFFLE_V_GAP_LINES = 0
TOP_PANEL_MIN_HEIGHT = 15
TOP_PANEL_MAX_HEIGHT = 18
DEFAULT_LANG = "zh"

TRANSLATIONS = {
    "zh": {
        "overview_title": "总览",
        "headline": "终端分析报告",
        "brand": "Code Insights",
        "project_title": "项目概览",
        "project_label": "项目",
        "path_label": "路径",
        "scanned_at_label": "扫描时间",
        "runtime_label": "运行环境",
        "totals_title": "统计汇总",
        "source_files": "源文件数",
        "languages": "语言数",
        "total_lines": "总行数",
        "code_lines": "有效代码行",
        "cache_hit_miss": "缓存命中/未命中",
        "metric": "指标",
        "rate": "占比",
        "bar": "图示",
        "code_density": "代码密度",
        "cache_hit_rate": "缓存命中率",
        "lang_breakdown_title": "语言分布",
        "no_source_files_detected": "未检测到源文件",
        "language_label": "语言",
        "largest_files_title": "最大源文件",
        "file_col": "文件",
        "stats_col": "统计",
        "no_source_file_data": "无源文件数据",
        "monitor_title": "实时监控",
        "mode": "模式",
        "live": "实时",
        "snapshot": "快照",
        "profile": "配置",
        "status": "状态",
        "poll": "轮询",
        "tracked_files": "跟踪文件",
        "last_scan": "上次扫描",
        "scope": "范围",
        "total_add_col": "总+",
        "total_remove_col": "总-",
        "effective_add_col": "有效+",
        "effective_remove_col": "有效-",
        "changed_col": "变更文件",
        "this_cycle": "本轮",
        "cumulative": "累计",
        "rhythm_300s": "近5min变化",
        "latest_5s_net": "最近5s净变化",
        "activity": "活动",
        "target": "目标",
        "total_delta_col": "总(+/-)",
        "effective_delta_col": "有效(+/-)",
        "note": "说明",
        "burst_active": "突发(进行中)",
        "burst_recent": "突发(最近)",
        "change": "变更",
        "no_activity": "无活动",
        "other": "其他",
        "status_running": "运行中",
        "status_idle": "空闲",
        "status_stopped": "已停止",
    },
    "en": {
        "overview_title": "Overview",
        "headline": "Terminal Analysis Report",
        "brand": "Code Insights",
        "project_title": "Project",
        "project_label": "Project",
        "path_label": "Path",
        "scanned_at_label": "Scanned At",
        "runtime_label": "Runtime",
        "totals_title": "Totals",
        "source_files": "Source Files",
        "languages": "Languages",
        "total_lines": "Total Lines",
        "code_lines": "Code Lines",
        "cache_hit_miss": "Cache Hit/Miss",
        "metric": "Metric",
        "rate": "Rate",
        "bar": "Bar",
        "code_density": "Code Density",
        "cache_hit_rate": "Cache Hit Rate",
        "lang_breakdown_title": "Language Breakdown",
        "no_source_files_detected": "No source files detected",
        "language_label": "Language",
        "largest_files_title": "Largest Source Files",
        "file_col": "File",
        "stats_col": "Stats",
        "no_source_file_data": "No source file data",
        "monitor_title": "Monitor",
        "mode": "Mode",
        "live": "Live",
        "snapshot": "Snapshot",
        "profile": "Profile",
        "status": "Status",
        "poll": "Poll",
        "tracked_files": "Tracked Files",
        "last_scan": "Last Scan",
        "scope": "Scope",
        "total_add_col": "+Total",
        "total_remove_col": "-Total",
        "effective_add_col": "+Eff",
        "effective_remove_col": "-Eff",
        "changed_col": "Changed",
        "this_cycle": "This Cycle",
        "cumulative": "Cumulative",
        "rhythm_300s": "5m Trend",
        "latest_5s_net": "Latest 5s Net",
        "activity": "Activity",
        "target": "Target",
        "total_delta_col": "T(+/-)",
        "effective_delta_col": "E(+/-)",
        "note": "Note",
        "burst_active": "Burst(Active)",
        "burst_recent": "Burst(Recent)",
        "change": "Change",
        "no_activity": "No activity",
        "other": "Other",
        "status_running": "running",
        "status_idle": "idle",
        "status_stopped": "stopped",
    },
}


def build_terminal_dashboard(
    analysis: dict[str, object],
    *,
    terminal_width: int | None = None,
    lang: str = DEFAULT_LANG,
) -> Group:
    project = analysis["project"]
    totals = analysis["totals"]
    language_stats = analysis.get("language_stats", [])
    structure = analysis.get("structure", {})
    largest_files = structure.get("largest_files", [])
    cache_meta = analysis.get("meta", {}).get("cache", {})
    monitor_state = analysis.get("meta", {}).get("monitor")

    labels = _resolve_labels(lang)
    return _build_dashboard(
        project=project,
        totals=totals,
        cache_meta=cache_meta,
        language_stats=language_stats,
        largest_files=largest_files,
        monitor_state=monitor_state if isinstance(monitor_state, dict) else None,
        terminal_width=terminal_width,
        labels=labels,
    )


def render_terminal_report(
    analysis: dict[str, object],
    console: Console | None = None,
    *,
    lang: str = DEFAULT_LANG,
) -> None:
    console = console or Console()
    dashboard = build_terminal_dashboard(analysis, terminal_width=console.size.width, lang=lang)
    console.print(dashboard)


def _build_dashboard(
    *,
    project: dict[str, object],
    totals: dict[str, object],
    cache_meta: dict[str, object],
    language_stats: list[dict[str, object]],
    largest_files: list[dict[str, object]],
    monitor_state: dict[str, object] | None,
    terminal_width: int | None,
    labels: dict[str, str],
) -> Group:
    language_segments = _build_segments(
        language_stats,
        label_key="language",
        value_key="total_lines",
        limit=6,
        other_label=labels["other"],
    )
    top_panel_height = _calculate_top_panel_height(len(language_segments))

    lower_grid = Table.grid(expand=True, padding=0)
    lower_grid.add_column(ratio=1)
    lower_grid.add_column(ratio=1)
    lower_grid.add_row(
        Group(
            _build_language_panel(
                language_segments,
                terminal_width=terminal_width,
                labels=labels,
                panel_height=top_panel_height,
            ),
            _build_largest_files_panel(largest_files, labels=labels),
        ),
        _build_merged_monitor_panel(
            monitor_state=monitor_state,
            largest_files=largest_files,
            top_panel_height=top_panel_height,
            labels=labels,
        ),
    )

    return Group(
        _build_overview_panel(project, totals, cache_meta, labels=labels),
        lower_grid,
    )


def _build_overview_panel(
    project: dict[str, object],
    totals: dict[str, object],
    cache_meta: dict[str, object],
    *,
    labels: dict[str, str],
) -> Panel:
    content = Table.grid(expand=True, padding=1)
    content.add_column(ratio=1)
    content.add_column(ratio=1)
    content.add_row(
        _build_project_summary_panel(project, labels=labels),
        _build_totals_panel(totals, cache_meta, labels=labels),
    )

    headline = Text(labels["headline"], style="bold cyan")

    return Panel(
        Group(Align.center(headline), content),
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
        title=f"[bold cyan]{labels['overview_title']}[/bold cyan]",
    )


def _build_project_summary_panel(project: dict[str, object], *, labels: dict[str, str]) -> Panel:
    scanned_at = _format_scanned_at(str(project.get("scanned_at", "")))
    content = Table.grid(padding=(0, 1))
    content.add_column(style="bold")
    content.add_column()
    content.add_row(labels["brand"], Text(labels["headline"], style="cyan"))
    content.add_row(labels["project_label"], str(project.get("name", "-")))
    content.add_row(labels["path_label"], str(project.get("path", "-")))
    content.add_row(labels["scanned_at_label"], scanned_at)
    content.add_row(
        labels["runtime_label"],
        f"{project.get('platform', '-')} | Python {project.get('python', '-')}",
    )

    return Panel(
        content,
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
        title=f"[bold cyan]{labels['project_title']}[/bold cyan]",
    )


def _build_totals_panel(
    totals: dict[str, object],
    cache_meta: dict[str, object],
    *,
    labels: dict[str, str],
) -> Panel:
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
    metrics.add_row(labels["source_files"], _fmt_int(totals.get("files", 0)))
    metrics.add_row(labels["languages"], _fmt_int(totals.get("languages", 0)))
    metrics.add_row(labels["total_lines"], _fmt_int(total_lines))
    metrics.add_row(labels["code_lines"], _fmt_int(code_lines))
    metrics.add_row(labels["cache_hit_miss"], f"{_fmt_int(cache_hits)}/{_fmt_int(cache_misses)}")

    ratios = Table(
        box=box.SIMPLE,
        expand=True,
        show_header=True,
        padding=(0, 1),
        collapse_padding=True,
    )
    ratios.add_column(labels["metric"], style="bold")
    ratios.add_column(labels["rate"], justify="right")
    ratios.add_column(labels["bar"])
    ratios.add_row(labels["code_density"], f"{code_ratio:.2f}%", _bar(code_ratio, width=16, style="bright_cyan"))
    ratios.add_row(labels["cache_hit_rate"], f"{cache_ratio:.2f}%", _bar(cache_ratio, width=16, style="bright_blue"))

    return Panel(
        Group(metrics, ratios),
        title=f"[bold cyan]{labels['totals_title']}[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
    )


def _build_language_panel(
    segments: list[dict[str, object]],
    *,
    terminal_width: int | None,
    labels: dict[str, str],
    panel_height: int,
) -> Panel:
    if not segments:
        return Panel(
            labels["no_source_files_detected"],
            title=f"[bold cyan]{labels['lang_breakdown_title']}[/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 1),
            height=panel_height,
        )

    waffle_cols, waffle_rows = _waffle_geometry(terminal_width)
    content = Group(
        Padding(
            Align.center(
                _waffle_chart(
                    segments,
                    rows=waffle_rows,
                    cols=waffle_cols,
                )
            ),
            (1, 0, 0, 0),
        ),
        _build_legend_table(segments, label_title=labels["language_label"]),
    )

    return Panel(
        content,
        title=f"[bold cyan]{labels['lang_breakdown_title']}[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        height=panel_height,
    )


def _waffle_geometry(terminal_width: int | None) -> tuple[int, int]:
    if terminal_width is None or terminal_width <= 0:
        cols = WAFFLE_DEFAULT_COLUMNS
    else:
        # Dashboard is two equal-width columns. Reserve borders/padding and keep
        # a conservative chart width for narrow terminals.
        estimated_left_panel = max(32, (terminal_width // 2) - 8)
        cols = estimated_left_panel - 8
        cols = max(WAFFLE_MIN_COLUMNS, min(WAFFLE_MAX_COLUMNS, cols))

    rows = WAFFLE_TARGET_LOGICAL_ROWS
    if rows % 2 != 0:
        rows += 1
    return cols, rows


def _build_largest_files_panel(largest_files: list[dict[str, object]], *, labels: dict[str, str]) -> Panel:
    table = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 1), collapse_padding=True)
    table.add_column(labels["file_col"], no_wrap=True, overflow="ellipsis")
    table.add_column(labels["stats_col"], no_wrap=True, width=14, overflow="ellipsis")

    if not largest_files:
        table.add_row(labels["no_source_file_data"], "-")
        return Panel(
            table,
            title=f"[bold cyan]{labels['largest_files_title']}[/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 1),
            height=_largest_files_panel_height(largest_files),
        )

    for row in largest_files[:10]:
        total = int(row.get("total_lines", 0))
        stats = _format_stats_cell(str(row.get("language", "-")), total)
        table.add_row(
            _format_path_cell(str(row.get("path", "-")), max_total_len=34, parent_max_len=22, name_max_len=16),
            stats,
        )

    return Panel(
        table,
        title=f"[bold cyan]{labels['largest_files_title']}[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        height=_largest_files_panel_height(largest_files),
    )


def _largest_files_panel_height(largest_files: list[dict[str, object]]) -> int:
    visible_rows = max(1, min(10, len(largest_files)))
    return visible_rows + 6


def _build_merged_monitor_panel(
    *,
    monitor_state: dict[str, object] | None,
    largest_files: list[dict[str, object]],
    top_panel_height: int,
    labels: dict[str, str],
) -> Panel:
    content = _build_file_monitor_content(monitor_state, labels=labels)

    return Panel(
        content,
        title=f"[bold cyan]{labels['monitor_title']}[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        height=top_panel_height + _largest_files_panel_height(largest_files),
    )


def _build_file_monitor_content(monitor_state: dict[str, object] | None, *, labels: dict[str, str]) -> Group:
    state = monitor_state or {}
    status = str(state.get("status", "idle"))
    interval_seconds = int(state.get("interval_seconds", 3) or 3)
    tracked_files = int(state.get("tracked_files", 0) or 0)
    profile = str(state.get("profile", "balanced"))
    last_scan = _format_monitor_time(str(state.get("last_scan_at", "")))
    enabled = bool(state.get("enabled", False))

    interval_data = state.get("interval", {})
    interval = interval_data if isinstance(interval_data, dict) else {}
    cumulative_data = state.get("cumulative", {})
    cumulative = cumulative_data if isinstance(cumulative_data, dict) else {}
    radar_data = state.get("radar", {})
    radar = radar_data if isinstance(radar_data, dict) else {}
    interval_total = interval.get("total", {})
    interval_total_metrics = interval_total if isinstance(interval_total, dict) else {}
    interval_effective = interval.get("effective", {})
    interval_effective_metrics = interval_effective if isinstance(interval_effective, dict) else {}
    cumulative_total = cumulative.get("total", {})
    cumulative_total_metrics = cumulative_total if isinstance(cumulative_total, dict) else {}
    cumulative_effective = cumulative.get("effective", {})
    cumulative_effective_metrics = cumulative_effective if isinstance(cumulative_effective, dict) else {}

    header = Table.grid(expand=False, padding=(0, 1))
    header.add_column(style="bold cyan", no_wrap=True, width=13)
    header.add_column(style="white", no_wrap=True)
    header.add_row(labels["mode"], labels["live"] if enabled else labels["snapshot"])
    header.add_row(labels["profile"], _localize_profile(profile, labels))
    header.add_row(labels["status"], _localize_status(status, labels))
    header.add_row(labels["poll"], f"{interval_seconds}s")
    header.add_row(labels["tracked_files"], _fmt_int(tracked_files))
    header.add_row(labels["last_scan"], last_scan)

    delta_table = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 1), collapse_padding=True)
    delta_table.add_column(labels["scope"], style="bold")
    delta_table.add_column(labels["total_delta_col"], justify="right")
    delta_table.add_column(labels["effective_delta_col"], justify="right")
    delta_table.add_column(labels["changed_col"], justify="right")
    delta_table.add_row(
        labels["this_cycle"],
        _fmt_add_remove(
            int(interval_total_metrics.get("added_lines", 0) or 0),
            int(interval_total_metrics.get("removed_lines", 0) or 0),
        ),
        _fmt_add_remove(
            int(interval_effective_metrics.get("added_lines", 0) or 0),
            int(interval_effective_metrics.get("removed_lines", 0) or 0),
        ),
        _fmt_int(interval.get("files_changed", 0)),
    )
    delta_table.add_row(
        labels["cumulative"],
        _fmt_add_remove(
            int(cumulative_total_metrics.get("added_lines", 0) or 0),
            int(cumulative_total_metrics.get("removed_lines", 0) or 0),
        ),
        _fmt_add_remove(
            int(cumulative_effective_metrics.get("added_lines", 0) or 0),
            int(cumulative_effective_metrics.get("removed_lines", 0) or 0),
        ),
        _fmt_int(cumulative.get("files_changed", 0)),
    )

    rhythm_panel = _build_rhythm_panel(radar, labels=labels)
    activity_table = _build_activity_table(radar, labels=labels)

    return Group(
        Padding(header, (0, 1, 1, 1)),
        rhythm_panel,
        delta_table,
        activity_table,
    )


def _build_rhythm_panel(radar: dict[str, object], *, labels: dict[str, str]) -> Table:
    rhythm_data = radar.get("rhythm", [])
    rhythm_values = rhythm_data if isinstance(rhythm_data, list) else []
    values: list[int] = []
    for item in rhythm_values[-40:]:
        try:
            values.append(int(item))
        except (TypeError, ValueError):
            continue

    sparkline = _trendline(values, width=28)
    net = values[-1] if values else 0
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(style="bold cyan", width=13)
    table.add_column()
    table.add_row(labels["rhythm_300s"], sparkline)
    table.add_row(labels["latest_5s_net"], _fmt_delta(net))
    return table


def _build_activity_table(radar: dict[str, object], *, labels: dict[str, str]) -> Table:
    table = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 1), collapse_padding=True)
    recent_window = int(radar.get("recent_window_seconds", 5) or 5)
    repeat_threshold = int(radar.get("recent_repeat_threshold", 2) or 2)
    table.add_column(labels["activity"], style="bold")
    table.add_column(labels["target"], overflow="ellipsis")
    table.add_column(labels["total_delta_col"], justify="right")
    table.add_column(labels["effective_delta_col"], justify="right")

    changes_data = radar.get("recent_changes", [])
    changes = changes_data if isinstance(changes_data, list) else []

    shown = 0

    for row in changes:
        if not isinstance(row, dict):
            continue
        added_total = int(row.get("added_total", 0) or 0)
        removed_total = int(row.get("removed_total", 0) or 0)
        added_effective = int(row.get("added_effective", 0) or 0)
        removed_effective = int(row.get("removed_effective", 0) or 0)
        repeat_count = int(row.get("repeat_count", 1) or 1)
        target_time = _format_monitor_time(str(row.get("at", "")))
        target_path = _shorten_path(str(row.get("path", "-")), max_len=14)
        if repeat_count > repeat_threshold:
            target_path = f"{target_path} x{repeat_count}"
        table.add_row(
            labels["change"],
            f"{target_time} {target_path}",
            _fmt_add_remove(added_total, removed_total),
            _fmt_add_remove(added_effective, removed_effective),
        )
        shown += 1
        if shown >= 6:
            break

    if shown == 0:
        table.add_row(
            f"{labels['no_activity']} ({recent_window}s)",
            "-",
            "+0/-0",
            "+0/-0",
        )
    return table


def _build_segments(
    rows: list[dict[str, object]],
    *,
    label_key: str,
    value_key: str,
    limit: int,
    other_label: str,
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
        kept.append((other_label, other))
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


def _calculate_top_panel_height(segment_count: int) -> int:
    clamped_segment_count = max(1, segment_count)
    target_height = 12 + clamped_segment_count
    return max(TOP_PANEL_MIN_HEIGHT, min(TOP_PANEL_MAX_HEIGHT, target_height))


def _resolve_labels(lang: str | None) -> dict[str, str]:
    normalized = (lang or DEFAULT_LANG).strip().lower()
    return TRANSLATIONS.get(normalized, TRANSLATIONS[DEFAULT_LANG])


def _localize_status(status: str, labels: dict[str, str]) -> str:
    status_map = {
        "running": labels["status_running"],
        "idle": labels["status_idle"],
        "stopped": labels["status_stopped"],
    }
    return status_map.get(status, status)


def _localize_profile(profile: str, labels: dict[str, str]) -> str:
    if labels is TRANSLATIONS["zh"]:
        if profile == "balanced":
            return "均衡"
        if profile == "agent":
            return "智能体"
    return profile


def _fmt_int(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _fmt_delta(value: int) -> str:
    if value > 0:
        return f"[green]+{_fmt_int(value)}[/green]"
    if value < 0:
        return f"[red]-{_fmt_int(abs(value))}[/red]"
    return "0"


def _fmt_add_remove(added: int, removed: int) -> Text:
    text = Text()
    text.append(f"+{_fmt_int(added)}", style="green")
    text.append("/")
    text.append(f"-{_fmt_int(removed)}", style="red")
    return text


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


def _trendline(values: list[int], *, width: int) -> Text:
    blocks = "▁▂▃▄▅▆▇█"
    if width <= 0:
        return Text("")
    if not values:
        return Text("·" * width, style="grey37")

    sampled = _resample_series(values, width=width)
    smoothed = _smooth_series(sampled, radius=1)

    max_abs = max(abs(v) for v in smoothed) or 1
    text = Text()
    for value in smoothed:
        level = int(round((abs(value) / max_abs) * (len(blocks) - 1)))
        char = blocks[level]
        if level == 0:
            style = "grey50"
        elif value < 0:
            style = "red3" if level <= 3 else "red"
        elif value > 0:
            style = "cyan3" if level <= 3 else "bright_cyan"
        else:
            style = "grey50"
        text.append(char, style=style)
    return text


def _resample_series(values: list[int], *, width: int) -> list[int]:
    if width <= 0:
        return []
    if not values:
        return [0] * width
    if len(values) == width:
        return list(values)
    if len(values) < width:
        return [0] * (width - len(values)) + list(values)

    result: list[int] = []
    n = len(values)
    for idx in range(width):
        start = (idx * n) // width
        end = ((idx + 1) * n) // width
        bucket = values[start:end] or [values[min(start, n - 1)]]
        avg = sum(bucket) / len(bucket)
        result.append(int(round(avg)))
    return result


def _smooth_series(values: list[int], *, radius: int = 1) -> list[int]:
    if not values:
        return []
    if radius <= 0:
        return list(values)

    smoothed: list[int] = []
    n = len(values)
    for idx in range(n):
        lo = max(0, idx - radius)
        hi = min(n, idx + radius + 1)
        window = values[lo:hi]
        smoothed.append(int(round(sum(window) / len(window))))
    return smoothed


def _format_scanned_at(raw_value: str) -> str:
    try:
        dt = datetime.fromisoformat(raw_value)
        return dt.strftime("%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return raw_value or "-"


def _format_monitor_time(raw_value: str) -> str:
    try:
        dt = datetime.fromisoformat(raw_value)
        return dt.strftime("%H:%M:%S")
    except ValueError:
        return raw_value or "-"
