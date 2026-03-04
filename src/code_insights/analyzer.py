from __future__ import annotations

import hashlib
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from code_insights import __version__
from code_insights.cache import CacheManager
from code_insights.language_stats import count_code_lines, count_total_lines, detect_language
from code_insights.scanner import collect_source_files


def analyze_repository(
    repo_path: Path,
    *,
    exclude_patterns: list[str] | None = None,
    use_cache: bool = True,
) -> dict[str, object]:
    exclude_patterns = exclude_patterns or []

    cache = CacheManager(repo_path)
    if use_cache:
        cache.load()

    files = collect_source_files(repo_path, exclude_patterns)

    language_rollup: dict[str, dict[str, int]] = {}
    top_directory_rollup: dict[str, dict[str, int]] = {}
    largest_files: list[dict[str, object]] = []

    cache_hits = 0
    cache_misses = 0

    for path in files:
        rel_path = path.relative_to(repo_path).as_posix()
        file_bytes = path.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        language = detect_language(path.suffix)
        if language is None:
            continue

        cached = cache.get(rel_path) if use_cache else None
        cache_entry = (
            cached
            if cached
            and cached.get("hash") == file_hash
            and isinstance(cached.get("data"), dict)
            else None
        )

        if cache_entry:
            cache_hits += 1
            file_data = cache_entry["data"]
        else:
            cache_misses += 1
            source = file_bytes.decode("utf-8", errors="ignore")
            file_data = {
                "language": language,
                "total_lines": count_total_lines(source),
                "code_lines": count_code_lines(language, source),
            }
            if use_cache:
                cache.set(rel_path, {"hash": file_hash, "data": file_data})

        lang_stats = language_rollup.setdefault(
            str(file_data["language"]),
            {"files": 0, "total_lines": 0, "code_lines": 0},
        )
        lang_stats["files"] += 1
        lang_stats["total_lines"] += int(file_data["total_lines"])
        lang_stats["code_lines"] += int(file_data["code_lines"])

        top_dir = _top_level_dir(path, repo_path)
        dir_stats = top_directory_rollup.setdefault(
            top_dir,
            {"files": 0, "total_lines": 0, "code_lines": 0},
        )
        dir_stats["files"] += 1
        dir_stats["total_lines"] += int(file_data["total_lines"])
        dir_stats["code_lines"] += int(file_data["code_lines"])

        largest_files.append(
            {
                "path": rel_path,
                "language": str(file_data["language"]),
                "total_lines": int(file_data["total_lines"]),
                "code_lines": int(file_data["code_lines"]),
            }
        )

    total_lines_sum = sum(int(v["total_lines"]) for v in language_rollup.values())
    code_lines_sum = sum(int(v["code_lines"]) for v in language_rollup.values())

    language_stats = _build_language_rows(language_rollup, total_lines_sum, code_lines_sum)
    top_directories = _build_top_directory_rows(top_directory_rollup)
    top_files = sorted(largest_files, key=lambda x: (-int(x["total_lines"]), str(x["path"])))[:15]

    analysis = {
        "project": {
            "name": repo_path.name,
            "path": str(repo_path.resolve()),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
        },
        "totals": {
            "files": len(files),
            "languages": len(language_rollup),
            "total_lines": total_lines_sum,
            "code_lines": code_lines_sum,
        },
        "language_stats": language_stats,
        "structure": {
            "top_directories": top_directories,
            "largest_files": top_files,
        },
        "meta": {
            "version": __version__,
            "options": {
                "exclude": exclude_patterns,
                "use_cache": use_cache,
            },
            "cache": {
                "hits": cache_hits,
                "misses": cache_misses,
            },
        },
    }

    if use_cache:
        cache.save()

    return analysis


def _top_level_dir(path: Path, repo_path: Path) -> str:
    rel_parts = path.relative_to(repo_path).parts
    if len(rel_parts) <= 1:
        return "."
    return rel_parts[0]


def _build_language_rows(
    language_rollup: dict[str, dict[str, int]],
    total_lines_sum: int,
    code_lines_sum: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for language, values in sorted(language_rollup.items(), key=lambda x: (-x[1]["total_lines"], x[0])):
        total_lines = int(values["total_lines"])
        code_lines = int(values["code_lines"])
        rows.append(
            {
                "language": language,
                "files": int(values["files"]),
                "total_lines": total_lines,
                "code_lines": code_lines,
                "total_percent": round((total_lines / total_lines_sum * 100), 2) if total_lines_sum else 0.0,
                "code_percent": round((code_lines / code_lines_sum * 100), 2) if code_lines_sum else 0.0,
            }
        )

    return rows


def _build_top_directory_rows(top_directory_rollup: dict[str, dict[str, int]]) -> list[dict[str, object]]:
    rows = [
        {
            "path": path,
            "files": int(values["files"]),
            "total_lines": int(values["total_lines"]),
            "code_lines": int(values["code_lines"]),
        }
        for path, values in top_directory_rollup.items()
    ]

    rows.sort(key=lambda row: (-int(row["files"]), -int(row["total_lines"]), str(row["path"])))
    return rows[:12]
