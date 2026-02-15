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


# Match: <!-- code_snippet_start:path/to/file:LINE_OR_SEARCH:LINE_OR_SEARCH -->
# The path and line specs may contain escaped colons (\:)
_SNIPPET_START_RE = re.compile(
    r"<!--\s*code_snippet_start:"
    r"(?P<path>(?:[^:\\]|\\.)+?)"
    r":"
    r"(?P<start>(?:[^:\\]|\\.)+?)"
    r":"
    r"(?P<end>(?:[^:\\]|\\.)+?)"
    r"\s*-->"
)
_SNIPPET_END_RE = re.compile(r"<!--\s*code_snippet_end\s*-->")
_FENCED_CODE_RE = re.compile(r"^(`{3,}|~{3,})")


def _resolve_path(snippet_path: str, md_dir: str) -> str:
    """Resolve a snippet file path relative to the markdown file's directory."""
    snippet_path = snippet_path.replace("\\:", ":")
    if os.path.isabs(snippet_path):
        return snippet_path
    return os.path.normpath(os.path.join(md_dir, snippet_path))


def process_markdown(in_markdown: t.TextIO, out_markdown: t.TextIO) -> None:
    """
    Process the input markdown file, updating code snippets between
    code_snippet_start and code_snippet_end comments.
    """
    in_snippet_block = False
    in_fenced_block = False
    fence_marker = ""

    md_dir = "."
    if hasattr(in_markdown, "name"):
        md_dir = os.path.dirname(os.path.abspath(in_markdown.name))

    for line in in_markdown.readlines():
        if not in_snippet_block:
            out_markdown.write(line)

            # Track fenced code blocks so we don't process snippet comments inside them
            stripped = line.strip()
            fence_match = _FENCED_CODE_RE.match(stripped)
            if fence_match:
                if not in_fenced_block:
                    in_fenced_block = True
                    fence_marker = fence_match.group(1)[0]  # ` or ~
                elif stripped.startswith(fence_marker) and stripped.rstrip(fence_marker) == "":
                    in_fenced_block = False
                continue

            if in_fenced_block:
                continue

            match = _SNIPPET_START_RE.match(stripped)
            if match:
                in_snippet_block = True
                snippet_path = match.group("path")
                start_spec = match.group("start")
                end_spec = match.group("end")

                resolved_path = _resolve_path(snippet_path, md_dir)
                with open(resolved_path) as f:
                    source_lines = f.readlines()

                start_line = _parse_line_spec(start_spec, source_lines)
                end_line = _parse_line_spec(end_spec, source_lines, start_after=start_line)

                # end line is exclusive
                snippet_lines = source_lines[start_line - 1 : end_line - 1]

                lang = _detect_language(resolved_path)
                out_markdown.write(f"\n```{lang}\n")
                for snippet_line in snippet_lines:
                    out_markdown.write(snippet_line)
                if snippet_lines and not snippet_lines[-1].endswith("\n"):
                    out_markdown.write("\n")
                out_markdown.write("```\n\n")
        else:
            match = _SNIPPET_END_RE.match(line.strip())
            if match:
                in_snippet_block = False
                out_markdown.write(line)
