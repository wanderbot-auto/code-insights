from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from pathspec import PathSpec

from code_insights.config import DEFAULT_IGNORED_DIRS, LANGUAGE_BY_EXTENSION


def load_gitignore_spec(repo_path: Path) -> PathSpec | None:
    gitignore_path = repo_path / ".gitignore"
    if not gitignore_path.exists():
        return None

    lines = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    cleaned = [line for line in lines if line and not line.strip().startswith("#")]
    if not cleaned:
        return None

    return PathSpec.from_lines("gitwildmatch", cleaned)


def _matches_excludes(relative_path: str, exclude_patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in exclude_patterns)


def _is_ignored(
    rel_posix: str,
    *,
    is_dir: bool,
    spec: PathSpec | None,
    exclude_patterns: list[str],
) -> bool:
    if _matches_excludes(rel_posix, exclude_patterns):
        return True

    if spec:
        check_value = f"{rel_posix}/" if is_dir else rel_posix
        if spec.match_file(check_value):
            return True

    return False


def collect_source_files(repo_path: Path, exclude_patterns: list[str] | None = None) -> list[Path]:
    exclude_patterns = exclude_patterns or []
    spec = load_gitignore_spec(repo_path)
    files: list[Path] = []

    for root, dirs, filenames in os.walk(repo_path):
        root_path = Path(root)

        pruned_dirs = []
        for dirname in dirs:
            if dirname in DEFAULT_IGNORED_DIRS:
                continue
            dir_path = root_path / dirname
            rel_dir = dir_path.relative_to(repo_path).as_posix()
            if _is_ignored(
                rel_dir,
                is_dir=True,
                spec=spec,
                exclude_patterns=exclude_patterns,
            ):
                continue
            pruned_dirs.append(dirname)

        dirs[:] = pruned_dirs

        for filename in filenames:
            path = root_path / filename
            ext = path.suffix.lower()
            if ext not in LANGUAGE_BY_EXTENSION:
                continue

            rel = path.relative_to(repo_path).as_posix()
            if _is_ignored(
                rel,
                is_dir=False,
                spec=spec,
                exclude_patterns=exclude_patterns,
            ):
                continue

            files.append(path)

    return sorted(files)
