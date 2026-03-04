from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from code_insights.analyzer import analyze_repository
from code_insights.terminal_report import render_terminal_report

app = typer.Typer(help="Lightweight terminal codebase analysis")


@app.command()
def analyze(
    repo_path: Path = typer.Argument(..., help="Path to local repository"),
    exclude: list[str] | None = typer.Option(
        None,
        "--exclude",
        help="Glob patterns to exclude (repeatable)",
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable analysis cache"),
) -> None:
    repo_path = repo_path.expanduser().resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise typer.BadParameter(f"Invalid repository path: {repo_path}")

    analysis = analyze_repository(
        repo_path,
        exclude_patterns=exclude or [],
        use_cache=not no_cache,
    )

    render_terminal_report(analysis, console=Console())


@app.command()
def doctor() -> None:
    """Print runtime diagnostics."""
    typer.echo("Code Insights doctor")
    typer.echo(f"Python: {sys.version.split()[0]}")
    typer.echo(f"Typer: {typer.__version__}")


if __name__ == "__main__":
    app()
