# Code Insights

一个轻量级离线代码库分析工具，支持 macOS、Windows、Linux。

## 功能

- 基础代码行统计
  - 按语言统计总行数
  - 按语言统计有效代码行（去除空行与注释）
- 基础项目结构统计
  - 顶层目录分布
  - 最大源文件
- 终端 Rich 可视化输出（不提供 JSON/HTML 报告）

## 非目标

- Dependency graph analysis
- Project summary generation
- Directory tree visualization report
- Security scanning
- Automatic code fixing
- Cloud collaboration

## 安装

```bash
pip install -e .
```

## 使用

```bash
code-insights analyze /path/to/repo
```

可选参数：

- `--exclude "pattern"` (repeatable)
- `--no-cache`
- `--monitor` (adaptive 1-3s monitor refresh, low-frequency summary refresh, Total/Effective line deltas, 300s rhythm with 5s buckets, and 5s rolling change radar)
- `--monitor-profile balanced|agent` (alert sensitivity profile; `agent` is less noisy for high-churn AI edits)
- `--lang zh|en`（默认 `zh`）

## 输出

命令会直接在终端输出分析结果，默认中文显示。

## 测试

```bash
pytest
```
