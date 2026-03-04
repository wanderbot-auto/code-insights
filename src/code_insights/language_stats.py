from __future__ import annotations

from code_insights.config import LANGUAGE_BY_EXTENSION

LINE_COMMENT_PREFIXES = {
    "Python": ["#"],
    "Shell": ["#"],
    "YAML": ["#"],
    "Ruby": ["#"],
    "TOML": ["#"],
    "JavaScript": ["//"],
    "TypeScript": ["//"],
    "Go": ["//"],
    "Rust": ["//"],
    "Java": ["//"],
    "Kotlin": ["//"],
    "C": ["//"],
    "C++": ["//"],
    "C#": ["//"],
    "PHP": ["//", "#"],
    "Swift": ["//"],
    "Scala": ["//"],
    "SQL": ["--"],
    "HTML": [],
    "CSS": [],
    "SCSS": ["//"],
    "Markdown": [],
    "JSON": [],
    "XML": [],
}

BLOCK_COMMENT_MARKERS = {
    "JavaScript": ("/*", "*/"),
    "TypeScript": ("/*", "*/"),
    "Go": ("/*", "*/"),
    "Rust": ("/*", "*/"),
    "Java": ("/*", "*/"),
    "Kotlin": ("/*", "*/"),
    "C": ("/*", "*/"),
    "C++": ("/*", "*/"),
    "C#": ("/*", "*/"),
    "PHP": ("/*", "*/"),
    "Swift": ("/*", "*/"),
    "Scala": ("/*", "*/"),
    "CSS": ("/*", "*/"),
    "SCSS": ("/*", "*/"),
    "HTML": ("<!--", "-->"),
    "XML": ("<!--", "-->"),
}


def detect_language(extension: str) -> str | None:
    return LANGUAGE_BY_EXTENSION.get(extension.lower())


def count_total_lines(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def count_code_lines(language: str, text: str) -> int:
    if not text:
        return 0

    line_prefixes = LINE_COMMENT_PREFIXES.get(language, [])
    block_markers = BLOCK_COMMENT_MARKERS.get(language)
    in_block_comment = False
    code_lines = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if block_markers:
            start_marker, end_marker = block_markers
            if in_block_comment:
                if end_marker in line:
                    _, _, after = line.partition(end_marker)
                    in_block_comment = False
                    line = after.strip()
                    if not line:
                        continue
                else:
                    continue

            if start_marker in line:
                before, _, after = line.partition(start_marker)
                if end_marker in after:
                    after_block = after.split(end_marker, 1)[1].strip()
                    line = (before + " " + after_block).strip()
                    if not line:
                        continue
                else:
                    line = before.strip()
                    in_block_comment = True
                    if not line:
                        continue

        if any(line.startswith(prefix) for prefix in line_prefixes):
            continue

        code_lines += 1

    return code_lines
