import fnmatch
import os
import re
import typing as t


def _parse_line_spec(spec: str, lines: t.List[str], start_after: int = 0) -> int:
    """
    Parse a line specification, which can be either a line number or a /search/ pattern.
    Returns a 1-based line number.

    :param spec: Line number or /search/ pattern
    :param lines: All lines in the source file
    :param start_after: 1-based line number to start searching after (only for /search/ patterns)
    """
    # Try line number first
    try:
        return int(spec)
    except ValueError:
        pass

    # Check for regex pattern: r/regex/
    if spec.startswith("r/") and spec.endswith("/"):
        pattern = spec[2:-1]
        pattern = pattern.replace("\\:", ":")
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regular expression in '{spec}': {e}")

        for i, line in enumerate(lines):
            if i < start_after:
                continue
            if compiled.search(line):
                return i + 1  # 1-based

        raise ValueError(f"Regex pattern {spec} not found in file")

    # Must be a /search/ pattern (glob-style)
    if not spec.startswith("/") or not spec.endswith("/"):
        raise ValueError(f"Invalid line specification: '{spec}'. Expected a line number, /glob/ pattern, or r/regex/ pattern.")

    pattern = spec[1:-1]
    # Unescape colons
    pattern = pattern.replace("\\:", ":")

    for i, line in enumerate(lines):
        if i < start_after:
            continue
        if fnmatch.fnmatch(line, f"*{pattern}*"):
            return i + 1  # 1-based

    raise ValueError(f"Search pattern {spec} not found in file")


def _detect_language(file_path: str) -> str:
    """Detect the language identifier for a fenced code block based on file extension."""
    ext_map = {
        ".py": "python",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".cc": "cpp",
        ".hpp": "hpp",
        ".java": "java",
        ".js": "javascript",
        ".ts": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".rb": "ruby",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
        ".toml": "toml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".md": "markdown",
        ".cmake": "cmake",
        ".mk": "makefile",
    }
    _, ext = os.path.splitext(file_path)
    basename = os.path.basename(file_path)
    if basename in ("Makefile", "makefile", "GNUmakefile"):
        return "makefile"
    if basename in ("CMakeLists.txt",):
        return "cmake"
    if basename in ("Dockerfile",):
        return "dockerfile"
    if basename in ("Kconfig",) or basename.startswith("Kconfig."):
        return "kconfig"
    return ext_map.get(ext, "")


def _resolve_path(snippet_path: str, doc_dir: str) -> str:
    """Resolve a snippet file path relative to the document file's directory."""
    snippet_path = snippet_path.replace("\\:", ":")
    if os.path.isabs(snippet_path):
        return snippet_path
    return os.path.normpath(os.path.join(doc_dir, snippet_path))


# Snippet start/end comment patterns, keyed by name
_SNIPPET_FIELDS_RE = (
    r"(?P<path>(?:[^:\\]|\\.)+?)"
    r":"
    r"(?P<start>(?:[^:\\]|\\.)+?)"
    r":"
    r"(?P<end>(?:[^:\\]|\\.)+?)"
)


class DocFormat:
    """Base class defining the interface for document format handlers."""

    snippet_start_re: re.Pattern[str]
    snippet_end_re: re.Pattern[str]

    def write_code_block(self, out: t.TextIO, lang: str, lines: t.List[str]) -> None:
        raise NotImplementedError

    def is_passthrough_line(self, line: str, state: dict) -> bool:
        """Check if the line is inside a literal/fenced block where snippet markers should be ignored.
        May update state. Returns True if the line should be passed through without checking for snippets."""
        return False


class MarkdownFormat(DocFormat):
    # Match: <!-- code_snippet_start:path/to/file:LINE_OR_SEARCH:LINE_OR_SEARCH -->
    snippet_start_re = re.compile(r"<!--\s*code_snippet_start:" + _SNIPPET_FIELDS_RE + r"\s*-->")
    snippet_end_re = re.compile(r"<!--\s*code_snippet_end\s*-->")
    _fenced_code_re = re.compile(r"^(`{3,}|~{3,})")

    def write_code_block(self, out: t.TextIO, lang: str, lines: t.List[str]) -> None:
        out.write(f"\n```{lang}\n")
        for line in lines:
            out.write(line)
        if lines and not lines[-1].endswith("\n"):
            out.write("\n")
        out.write("```\n\n")

    def is_passthrough_line(self, line: str, state: dict) -> bool:
        stripped = line.strip()
        fence_match = self._fenced_code_re.match(stripped)
        if fence_match:
            if not state.get("in_fenced_block"):
                state["in_fenced_block"] = True
                state["fence_marker"] = fence_match.group(1)[0]  # ` or ~
            elif stripped.startswith(state["fence_marker"]) and stripped.rstrip(state["fence_marker"]) == "":
                state["in_fenced_block"] = False
            return True
        return state.get("in_fenced_block", False)


class RstFormat(DocFormat):
    # Match: .. code_snippet_start:path/to/file:LINE_OR_SEARCH:LINE_OR_SEARCH
    snippet_start_re = re.compile(r"\.\.\s+code_snippet_start:" + _SNIPPET_FIELDS_RE + r"\s*$")
    snippet_end_re = re.compile(r"\.\.\s+code_snippet_end\s*$")

    def write_code_block(self, out: t.TextIO, lang: str, lines: t.List[str]) -> None:
        out.write(f"\n.. code-block:: {lang}\n\n")
        for line in lines:
            if line.strip():
                out.write("   " + line)
            else:
                out.write("\n")
        if lines and not lines[-1].endswith("\n"):
            out.write("\n")
        out.write("\n")


_MARKDOWN_FORMAT = MarkdownFormat()
_RST_FORMAT = RstFormat()


def _process_document(in_doc: t.TextIO, out_doc: t.TextIO, fmt: DocFormat) -> None:
    """
    Process the input document file, updating code snippets between
    code_snippet_start and code_snippet_end comments.
    """
    in_snippet_block = False
    passthrough_state: dict = {}

    doc_dir = "."
    if hasattr(in_doc, "name"):
        doc_dir = os.path.dirname(os.path.abspath(in_doc.name))

    for line in in_doc.readlines():
        if not in_snippet_block:
            out_doc.write(line)

            if fmt.is_passthrough_line(line, passthrough_state):
                continue

            stripped = line.strip()
            match = fmt.snippet_start_re.match(stripped)
            if match:
                in_snippet_block = True
                snippet_path = match.group("path")
                start_spec = match.group("start")
                end_spec = match.group("end")

                resolved_path = _resolve_path(snippet_path, doc_dir)
                with open(resolved_path) as f:
                    source_lines = f.readlines()

                start_line = _parse_line_spec(start_spec, source_lines)

                # A '+' suffix on the end spec makes the end line inclusive
                end_inclusive = end_spec.endswith("/+") or end_spec.endswith("+")
                if end_inclusive:
                    end_spec = end_spec[:-1]  # strip the '+'

                end_line = _parse_line_spec(end_spec, source_lines, start_after=start_line)

                # end line is exclusive by default; '+' suffix makes it inclusive
                if end_inclusive:
                    snippet_lines = source_lines[start_line - 1 : end_line]
                else:
                    snippet_lines = source_lines[start_line - 1 : end_line - 1]

                lang = _detect_language(resolved_path)
                fmt.write_code_block(out_doc, lang, snippet_lines)
        else:
            match = fmt.snippet_end_re.match(line.strip())
            if match:
                in_snippet_block = False
                out_doc.write(line)


def process_markdown(in_markdown: t.TextIO, out_markdown: t.TextIO) -> None:
    """
    Process the input markdown file, updating code snippets between
    code_snippet_start and code_snippet_end comments.
    """
    _process_document(in_markdown, out_markdown, _MARKDOWN_FORMAT)


def process_rst(in_rst: t.TextIO, out_rst: t.TextIO) -> None:
    """
    Process the input RST file, updating code snippets between
    code_snippet_start and code_snippet_end comments.
    """
    _process_document(in_rst, out_rst, _RST_FORMAT)
