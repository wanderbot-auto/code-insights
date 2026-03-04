# Code Insights

A lightweight offline codebase analyzer for macOS, Windows, and Linux.

## What it does

- Basic code line statistics
  - Total lines by language
  - Effective code lines by language (blank/comment lines removed)
- Basic project structure analysis
  - Top-level directory distribution
  - Largest source files
- Terminal-first output with Rich UI (no JSON/HTML reports)
  - Styled overview panel
  - Colorful summary cards
  - Bar-chart-like columns for language and directory shares

## What it does not do

- Dependency graph analysis
- Project summary generation
- Directory tree visualization report
- Security scanning
- Automatic code fixing
- Cloud collaboration

## Install

```bash
pip install -e .
```

## Usage

```bash
code-insights analyze /path/to/repo
```

Optional flags:

- `--exclude "pattern"` (repeatable)
- `--no-cache`

## Output

The command prints all analysis results directly in terminal with styled Rich tables/panels.

## Test

```bash
pytest
```
