from pathlib import Path

from code_insights.analyzer import analyze_repository


def test_analyzer_returns_basic_stats_and_structure(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    src = repo / "src"
    src.mkdir()

    (src / "main.py").write_text("x = 1\n", encoding="utf-8")
    (src / "util.py").write_text("# note\ndef f():\n    return 1\n", encoding="utf-8")
    (repo / "app.ts").write_text("const value = 1;\n", encoding="utf-8")

    analysis = analyze_repository(repo, use_cache=False)

    assert analysis["totals"]["files"] == 3
    assert analysis["totals"]["languages"] >= 2

    languages = {row["language"] for row in analysis["language_stats"]}
    assert "Python" in languages
    assert "TypeScript" in languages

    top_dirs = analysis["structure"]["top_directories"]
    assert any(row["path"] == "src" for row in top_dirs)

    largest_files = analysis["structure"]["largest_files"]
    assert len(largest_files) >= 1
    assert "path" in largest_files[0]
