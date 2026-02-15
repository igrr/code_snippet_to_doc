import io
from pathlib import Path

import pytest

from code_snippet_to_md.snippet_processor import _detect_language, _parse_line_spec, process_markdown


DATA_DIR = Path(__file__).parent / "data"


class TestParseLineSpec:
    def test_line_number(self):
        assert _parse_line_spec("5", []) == 5

    def test_search_pattern_found(self):
        lines = ["line one\n", "line two\n", "target line\n", "line four\n"]
        assert _parse_line_spec("/target/", lines) == 3

    def test_search_pattern_not_found(self):
        lines = ["line one\n", "line two\n"]
        with pytest.raises(ValueError, match="not found"):
            _parse_line_spec("/missing/", lines)

    def test_search_glob_pattern(self):
        lines = ["int foo(void) {\n", "    return 0;\n", "}\n"]
        assert _parse_line_spec("/int foo*/", lines) == 1

    def test_search_with_escaped_colon(self):
        lines = ["key: value\n", "other: stuff\n"]
        assert _parse_line_spec("/key\\: value/", lines) == 1

    def test_invalid_spec(self):
        with pytest.raises(ValueError, match="Invalid line specification"):
            _parse_line_spec("notanumber", [])

    def test_search_with_start_after(self):
        lines = ["def foo():\n", "    pass\n", "def bar():\n", "    pass\n"]
        # Without start_after, finds first 'def' on line 1
        assert _parse_line_spec("/def /", lines) == 1
        # With start_after=1, skips line 1 and finds 'def' on line 3
        assert _parse_line_spec("/def /", lines, start_after=1) == 3

    def test_search_with_start_after_not_found(self):
        lines = ["def foo():\n", "    pass\n"]
        with pytest.raises(ValueError, match="not found"):
            _parse_line_spec("/def /", lines, start_after=1)

    def test_regex_pattern(self):
        lines = ["int foo(void) {\n", "    return 0;\n", "}\n"]
        assert _parse_line_spec(r"r/^int\s+foo/", lines) == 1

    def test_regex_pattern_anchors(self):
        lines = ["  indented line\n", "start of line\n", "another line\n"]
        # ^ anchor should match only lines starting with "start"
        assert _parse_line_spec(r"r/^start/", lines) == 2

    def test_regex_pattern_end_anchor(self):
        lines = ["foo bar\n", "bar baz\n", "hello world\n"]
        assert _parse_line_spec(r"r/world$/", lines) == 3

    def test_regex_pattern_with_escaped_colon(self):
        lines = ["key: value\n", "other: stuff\n"]
        assert _parse_line_spec(r"r/key\: value/", lines) == 1

    def test_regex_pattern_not_found(self):
        lines = ["line one\n", "line two\n"]
        with pytest.raises(ValueError, match="not found"):
            _parse_line_spec(r"r/missing/", lines)

    def test_regex_invalid_pattern(self):
        with pytest.raises(ValueError, match="Invalid regular expression"):
            _parse_line_spec(r"r/[invalid/", ["line\n"])

    def test_regex_with_start_after(self):
        lines = ["def foo():\n", "    pass\n", "def bar():\n", "    pass\n"]
        assert _parse_line_spec(r"r/^def /", lines) == 1
        assert _parse_line_spec(r"r/^def /", lines, start_after=1) == 3


class TestDetectLanguage:
    def test_c_file(self):
        assert _detect_language("foo.c") == "c"

    def test_python_file(self):
        assert _detect_language("bar.py") == "python"

    def test_header_file(self):
        assert _detect_language("baz.h") == "c"

    def test_makefile(self):
        assert _detect_language("Makefile") == "makefile"

    def test_cmake(self):
        assert _detect_language("CMakeLists.txt") == "cmake"

    def test_unknown_extension(self):
        assert _detect_language("file.xyz") == ""

    def test_yaml(self):
        assert _detect_language("config.yml") == "yaml"


class TestProcessMarkdown:
    def test_line_numbers(self):
        """Test snippet extraction using line numbers."""
        out_md = io.StringIO()
        with open(DATA_DIR / "test1.md.in") as in_md:
            process_markdown(in_md, out_md)

        expected = (DATA_DIR / "test1.md.expected").read_text()
        assert out_md.getvalue() == expected

    def test_search_patterns(self):
        """Test snippet extraction using /search/ patterns."""
        out_md = io.StringIO()
        with open(DATA_DIR / "test2.md.in") as in_md:
            process_markdown(in_md, out_md)

        expected = (DATA_DIR / "test2.md.expected").read_text()
        assert out_md.getvalue() == expected

    def test_update_existing(self):
        """Test that existing (outdated) snippets are replaced."""
        out_md = io.StringIO()
        with open(DATA_DIR / "test3.md.in") as in_md:
            process_markdown(in_md, out_md)

        expected = (DATA_DIR / "test3.md.expected").read_text()
        assert out_md.getvalue() == expected

    def test_no_snippets(self):
        """Test that markdown without snippets passes through unchanged."""
        input_text = "# Title\n\nSome regular text.\n"
        in_md = io.StringIO(input_text)
        out_md = io.StringIO()
        process_markdown(in_md, out_md)
        assert out_md.getvalue() == input_text

    def test_multiple_snippets(self):
        """Test that multiple snippet blocks in one file are all processed."""
        out_md = io.StringIO()
        with open(DATA_DIR / "test2.md.in") as in_md:
            process_markdown(in_md, out_md)

        result = out_md.getvalue()
        assert result.count("```python") == 2
        assert result.count("```") == 4  # 2 opening + 2 closing

    def test_end_pattern_searches_after_start(self):
        """Test that end pattern search begins after the start line, not from the top."""
        out_md = io.StringIO()
        with open(DATA_DIR / "test4.md.in") as in_md:
            process_markdown(in_md, out_md)

        expected = (DATA_DIR / "test4.md.expected").read_text()
        assert out_md.getvalue() == expected

    def test_regex_patterns(self):
        """Test snippet extraction using r/regex/ patterns."""
        out_md = io.StringIO()
        with open(DATA_DIR / "test5.md.in") as in_md:
            process_markdown(in_md, out_md)

        expected = (DATA_DIR / "test5.md.expected").read_text()
        assert out_md.getvalue() == expected

    def test_inclusive_end_line(self):
        """Test snippet extraction with '+' suffix for inclusive end line."""
        out_md = io.StringIO()
        with open(DATA_DIR / "test6.md.in") as in_md:
            process_markdown(in_md, out_md)

        expected = (DATA_DIR / "test6.md.expected").read_text()
        assert out_md.getvalue() == expected

    def test_snippet_inside_fenced_block_is_ignored(self):
        """Test that snippet comments inside fenced code blocks are not processed."""
        input_text = (
            "# Example\n\n"
            "```md\n"
            "<!-- code_snippet_start:nonexistent.c:1:5 -->\n"
            "\n"
            "<!-- code_snippet_end -->\n"
            "```\n"
        )
        in_md = io.StringIO(input_text)
        out_md = io.StringIO()
        process_markdown(in_md, out_md)
        assert out_md.getvalue() == input_text


class TestCLI:
    def test_check_mode_detects_changes(self):
        """Test that --check returns exit code 2 when changes are needed."""
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_snippet_to_md",
                "--check",
                "-i",
                str(DATA_DIR / "test1.md.in"),
            ],
            text=True,
            capture_output=True,
        )
        assert result.returncode == 2
        assert "Changes required in" in result.stderr

    def test_check_mode_no_changes(self):
        """Test that --check returns exit code 0 when no changes are needed."""
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_snippet_to_md",
                "--check",
                "-i",
                str(DATA_DIR / "test1.md.expected"),
            ],
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0
        assert result.stderr == ""
