from pathlib import Path

from typer.testing import CliRunner

from code_insights.cli import app


runner = CliRunner()


def test_cli_analyze_prints_terminal_report(tmp_path: Path) -> None:
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "main.py").write_text("import os\n\n\ndef run():\n    return os.name\n", encoding="utf-8")
    (repo / "web.js").write_text("const x = 1;\n", encoding="utf-8")

    result = runner.invoke(app, ["analyze", str(repo), "--no-cache"])

    assert result.exit_code == 0, result.stdout
    assert "Code Insights" in result.stdout
    assert "终端分析报告" in result.stdout
    assert "总览" in result.stdout
    assert "语言分布" in result.stdout
    assert "最大源文件" in result.stdout
    assert "Python" in result.stdout
    assert "JavaScript" in result.stdout
