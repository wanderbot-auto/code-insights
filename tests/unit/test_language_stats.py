from code_insights.language_stats import count_code_lines, count_total_lines, detect_language


def test_detect_language() -> None:
    assert detect_language(".py") == "Python"
    assert detect_language(".unknown") is None


def test_count_total_and_effective_python_lines() -> None:
    source = """\
# comment

x = 1

# comment 2
def foo():
    return x
"""
    assert count_total_lines(source) == 7
    assert count_code_lines("Python", source) == 3


def test_count_effective_js_lines_with_block_comment() -> None:
    source = """\
// comment
const x = 1;
/* block
line */
const y = 2; // inline
"""
    assert count_code_lines("JavaScript", source) == 2
