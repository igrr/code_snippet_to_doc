# code_snippet_to_md

`code_snippet_to_md` keeps code snippets in Markdown files in sync with source code. It replaces the content between special HTML comments with the corresponding lines from source files, ensuring that code examples in documentation never go stale. It can be invoked as a pre-commit hook or as a standalone script.

## How it works

Add HTML comments to your Markdown file indicating which source file and line range to include:

**Using line numbers** (end line is exclusive):

```md
<!-- code_snippet_start:path/to/file.c:10:20 -->

<!-- code_snippet_end -->
```

**Using search patterns** (glob-style, end pattern line is exclusive):

```md
<!-- code_snippet_start:path/to/file.c:/int main/:/return/ -->

<!-- code_snippet_end -->
```

Colons inside search patterns must be escaped with `\:`.

File paths are resolved relative to the Markdown file.

Then run `code_snippet_to_md` — the area between the comments will be populated with a fenced code block containing the specified source lines. The language for syntax highlighting is detected automatically from the file extension.

## Usage as a pre-commit hook

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
-   repo: https://github.com/igrr/code_snippet_to_md.git
    rev: v0.1.0
    hooks:
    -   id: code_snippet_to_md
```

To update additional files beyond `README.md`, specify them in `args:`:

```yaml
repos:
-   repo: https://github.com/igrr/code_snippet_to_md.git
    rev: v0.1.0
    hooks:
    -   id: code_snippet_to_md
        args: [--input=README.md, --input=docs/GUIDE.md]
```

## Command-line usage

<!-- code_snippet_start:code_snippet_to_md/__main__.py:/def get_parser/:/def main/ -->

```python
def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="code_snippet_to_md")
    parser.add_argument(
        "-i",
        "--input",
        nargs="+",
        type=argparse.FileType("r+"),
        help="Markdown file to update (can be specified multiple times).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if the files need to be updated, but don't modify them. "
        "Non-zero exit code is returned if any file needs to be updated.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


```

<!-- code_snippet_end -->

Options:
- `-i, --input`: Markdown files to update.
- `--check`: Check if files need updating without modifying them. Returns exit code 2 if changes are needed.
- `--version`: Show version.

## Example

Given a source file `example.c`:

<!-- code_snippet_start:test/data/sample.c:1:8 -->

```c
#include <stdio.h>

// Main function
int main(int argc, char *argv[]) {
    printf("Hello, World!\n");
    return 0;
}
```

<!-- code_snippet_end -->

And a Markdown file containing:

```md
<!-- code_snippet_start:example.c:4:8 -->

<!-- code_snippet_end -->
```

Running `code_snippet_to_md -i README.md` will populate the snippet block with lines 4-7 of `example.c`.

## License

This tool is Copyright (c) 2026 Ivan Grokhotkov and distributed under the [MIT License](LICENSE).
