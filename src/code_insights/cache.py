from __future__ import annotations

import json
from pathlib import Path

from code_insights.config import ANALYZER_VERSION, CACHE_DIR_NAME, CACHE_FILE_NAME


class CacheManager:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.cache_dir = repo_path / CACHE_DIR_NAME
        self.cache_file = self.cache_dir / CACHE_FILE_NAME
        self.data: dict[str, object] = {
            "version": ANALYZER_VERSION,
            "files": {},
        }

    def load(self) -> None:
        if not self.cache_file.exists():
            return

        try:
            loaded = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        if loaded.get("version") != ANALYZER_VERSION:
            return

        files = loaded.get("files")
        if not isinstance(files, dict):
            return

        self.data = {
            "version": ANALYZER_VERSION,
            "files": files,
        }

    def get(self, rel_path: str) -> dict[str, object] | None:
        files = self.data.get("files", {})
        if not isinstance(files, dict):
            return None
        value = files.get(rel_path)
        return value if isinstance(value, dict) else None

    def set(self, rel_path: str, value: dict[str, object]) -> None:
        files = self.data.setdefault("files", {})
        if isinstance(files, dict):
            files[rel_path] = value

    def save(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
