# AGENTS.md - Code Insights Execution Guide

## Mission
Build and maintain a lightweight cross-platform terminal analyzer with only two capabilities:

1. Basic code line statistics
2. Basic project structure statistics

## Hard scope constraints

- Offline local processing only.
- Input source: local directory path only.
- Output must be terminal text only.
- No JSON or HTML report output.
- Keep logic simple and deterministic.
- Terminal presentation should prioritize readability and aesthetics using Rich.

## Explicitly out of scope

- Dependency analysis and dependency graphs
- Project narrative summary generation
- Directory tree report visualization
- Security scanning
- Automatic code fixes
- Cloud services, accounts, collaboration features
- Plugin system

## Required CLI behavior

- Main command: `code-insights analyze <repo_path>`
- Output is printed directly to terminal.
- Support options:
  - `--exclude <glob>` (repeatable)
  - `--no-cache`

## Required analysis output sections

1. Totals
  - source files
  - language count
  - total lines
  - effective code lines
2. Language breakdown
  - files, total lines, effective lines, percentages
3. Project structure summary
  - top-level directories (file/line aggregation)
  - largest source files

## Cross-platform expectations

- Must run on macOS, Windows, Linux.
- Use `pathlib` and avoid OS-specific path assumptions.

## Quality bar

- Unit tests for statistics logic.
- End-to-end CLI smoke test for terminal output.
- Keep CLI stable and minimal.

## Implementation priorities

1. Correctness and clarity
2. Terminal readability
3. Simplicity over feature breadth
4. Performance improvements via file-hash cache
