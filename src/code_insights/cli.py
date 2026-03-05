from __future__ import annotations

import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live

from code_insights.analyzer import analyze_repository
from code_insights.monitor import (
    FileChangeMonitor,
    build_monitor_settings,
    build_static_monitor_state,
)
from code_insights.terminal_report import DEFAULT_LANG, build_terminal_dashboard, render_terminal_report

app = typer.Typer(help="轻量级终端代码分析工具")

MONITOR_FAST_INTERVAL_SECONDS = 1
MONITOR_MEDIUM_INTERVAL_SECONDS = 2
MONITOR_SLOW_INTERVAL_SECONDS = 3
MONITOR_IDLE_TO_MEDIUM_ROUNDS = 5
MONITOR_IDLE_TO_SLOW_ROUNDS = 12
MONITOR_ANALYZE_REFRESH_SECONDS = 12


def _compute_monitor_interval(idle_rounds: int) -> int:
    if idle_rounds >= MONITOR_IDLE_TO_SLOW_ROUNDS:
        return MONITOR_SLOW_INTERVAL_SECONDS
    if idle_rounds >= MONITOR_IDLE_TO_MEDIUM_ROUNDS:
        return MONITOR_MEDIUM_INTERVAL_SECONDS
    return MONITOR_FAST_INTERVAL_SECONDS


@app.command()
def analyze(
    repo_path: Path = typer.Argument(..., help="本地仓库路径"),
    exclude: list[str] | None = typer.Option(
        None,
        "--exclude",
        help="排除的 glob 模式（可重复）",
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="禁用分析缓存"),
    monitor: bool = typer.Option(
        False,
        "--monitor",
        help="启用实时文件变更监控（自适应 1-3s 刷新）",
    ),
    monitor_profile: str = typer.Option(
        "balanced",
        "--monitor-profile",
        help="监控配置: balanced | agent",
    ),
    lang: str = typer.Option(
        DEFAULT_LANG,
        "--lang",
        help="输出语言: zh | en（默认 zh）",
    ),
) -> None:
    repo_path = repo_path.expanduser().resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise typer.BadParameter(f"无效的仓库路径: {repo_path}")

    exclude_patterns = exclude or []
    normalized_profile = monitor_profile.strip().lower()
    if normalized_profile not in {"balanced", "agent"}:
        raise typer.BadParameter("无效的 --monitor-profile，请使用: balanced 或 agent")
    normalized_lang = lang.strip().lower()
    if normalized_lang not in {"zh", "en"}:
        raise typer.BadParameter("无效的 --lang，请使用: zh 或 en")

    console = Console()

    if not monitor:
        analysis = analyze_repository(
            repo_path,
            exclude_patterns=exclude_patterns,
            use_cache=not no_cache,
        )
        analysis.setdefault("meta", {})["monitor"] = build_static_monitor_state(
            tracked_files=int(analysis.get("totals", {}).get("files", 0) or 0),
            interval_seconds=MONITOR_SLOW_INTERVAL_SECONDS,
            last_scan_at=str(analysis.get("project", {}).get("scanned_at", "")),
            profile=normalized_profile,
        )
        render_terminal_report(analysis, console=console, lang=normalized_lang)
        return

    change_monitor = FileChangeMonitor(
        repo_path,
        exclude_patterns=exclude_patterns,
        interval_seconds=MONITOR_FAST_INTERVAL_SECONDS,
        settings=build_monitor_settings(normalized_profile),
    )
    analysis = analyze_repository(
        repo_path,
        exclude_patterns=exclude_patterns,
        use_cache=not no_cache,
    )
    idle_rounds = 0
    current_monitor_interval = MONITOR_FAST_INTERVAL_SECONDS
    next_analysis_at = time.monotonic() + MONITOR_ANALYZE_REFRESH_SECONDS

    monitor_state = change_monitor.initialize()
    monitor_state["interval_seconds"] = current_monitor_interval
    analysis.setdefault("meta", {})["monitor"] = monitor_state
    dashboard = build_terminal_dashboard(analysis, terminal_width=console.size.width, lang=normalized_lang)

    try:
        with Live(
            dashboard,
            console=console,
            refresh_per_second=4,
            screen=True,
            auto_refresh=False,
        ) as live:
            live.refresh()
            while True:
                cycle_started_at = time.monotonic()
                monitor_state = change_monitor.poll()
                interval_data = monitor_state.get("interval", {})
                interval = interval_data if isinstance(interval_data, dict) else {}
                files_changed = int(interval.get("files_changed", 0) or 0)
                if files_changed > 0:
                    idle_rounds = 0
                else:
                    idle_rounds += 1
                current_monitor_interval = _compute_monitor_interval(idle_rounds)
                now = time.monotonic()
                if now >= next_analysis_at:
                    analysis = analyze_repository(
                        repo_path,
                        exclude_patterns=exclude_patterns,
                        use_cache=not no_cache,
                    )
                    next_analysis_at = now + MONITOR_ANALYZE_REFRESH_SECONDS
                monitor_state["interval_seconds"] = current_monitor_interval
                analysis.setdefault("meta", {})["monitor"] = monitor_state
                dashboard = build_terminal_dashboard(
                    analysis,
                    terminal_width=console.size.width,
                    lang=normalized_lang,
                )
                live.update(dashboard, refresh=True)
                elapsed = time.monotonic() - cycle_started_at
                sleep_seconds = max(0.0, float(current_monitor_interval) - elapsed)
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        return


@app.command()
def doctor() -> None:
    """Print runtime diagnostics."""
    typer.echo("Code Insights 诊断")
    typer.echo(f"Python: {sys.version.split()[0]}")
    typer.echo(f"Typer: {typer.__version__}")


if __name__ == "__main__":
    app()
