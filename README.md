# code_snippet_to_doc

![PyPI - Version](https://img.shields.io/pypi/v/code_snippet_to_doc?labelColor=383838)
 [![CI](https://github.com/igrr/code_snippet_to_doc/actions/workflows/main.yml/badge.svg)](https://github.com/igrr/code_snippet_to_doc/actions/workflows/main.yml) ![Python](https://img.shields.io/badge/dynamic/yaml?url=https://raw.githubusercontent.com/igrr/code_snippet_to_doc/main/.github/workflows/main.yml&query=$.jobs['test'].strategy.matrix['python-version']&label=Python&logo=python&color=3366ff&logoColor=ffcc00&labelColor=383838)

`code_snippet_to_doc` keeps code snippets in documentation files in sync with source code. It replaces the content between special comments with the corresponding lines from source files, ensuring that code examples in documentation never go stale. It can be invoked as a pre-commit hook or as a standalone script. Documentation in Markdown and RestructuredText formats is supported.

## How it works

### Markdown

Add HTML comments to your Markdown file indicating which source file and line range to include:

**Using line numbers:**

```md
<!-- code_snippet_start:path/to/file.c:10:20 -->

<!-- code_snippet_end -->
```

**Using search patterns** (glob-style):

```md
<!-- code_snippet_start:path/to/file.c:/int main/:/return/ -->

<!-- code_snippet_end -->
```

**Using regular expressions** (prefix with `r`):

```md
<!-- code_snippet_start:path/to/file.c:r/^int main/:r/^\}/ -->

<!-- code_snippet_end -->
```

Regex patterns support the full Python `re` syntax, including anchors like `^` (start of line) and `$` (end of line).

**Including or excluding the end line** — by default, the end line is excluded from the snippet. Add a `+` suffix to include it:

```md
<!-- code_snippet_start:path/to/file.c:r/^int main/:r/^\}/+ -->

<!-- code_snippet_end -->
```

The `+` suffix works with all end line specification types: line numbers, glob patterns, and regular expressions. It is convenient for extracting complete blocks like C function bodies, where the closing `}` should be included.

Colons inside search patterns must be escaped with `\:`.

File paths are resolved relative to the document file.

### RestructuredText

Add RST comments to your `.rst` file using the same colon-separated syntax:

**Using line numbers:**

```rst
.. code_snippet_start:path/to/file.c:10:20

.. code_snippet_end
```

**Using search patterns and regular expressions:**

```rst
.. code_snippet_start:path/to/file.c:r/^int main/:r/^\}/+

.. code_snippet_end
```

The generated output uses RST's `code-block` directive with proper indentation:

```rst
.. code_snippet_start:path/to/file.c:r/^int main/:r/^\}/+

.. code-block:: c

   int main(int argc, char *argv[]) {
       printf("Hello, World!\n");
       return 0;
   }

.. code_snippet_end
```

All line specification types (line numbers, glob patterns, regex, `+` suffix) work the same way in both Markdown and RST files. The format is auto-detected from the file extension.

Then run `code_snippet_to_doc` — the area between the comments will be populated with a code block containing the specified source lines. The language for syntax highlighting is detected automatically from the file extension.

## Usage as a pre-commit hook

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
-   repo: https://github.com/igrr/code_snippet_to_doc.git
    rev: v0.1.0
    hooks:
    -   id: code_snippet_to_doc
```

To update additional files beyond `README.md`, specify them in `args:`:

```yaml
repos:
-   repo: https://github.com/igrr/code_snippet_to_doc.git
    rev: v0.1.0
    hooks:
    -   id: code_snippet_to_doc
        args: [--input=README.md, --input=docs/GUIDE.md, --input=docs/api.rst]
```

## Command-line usage

<!-- code_snippet_start:code_snippet_to_doc/__main__.py:/def get_parser/:/_FORMAT_PROCESSORS/ -->

```python
def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="code_snippet_to_doc")
    parser.add_argument(
        "-i",
        "--input",
        nargs="+",
        type=argparse.FileType("r+"),
        help="Documentation file to update (can be specified multiple times).",
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
- `-i, --input`: Documentation files to update.
- `--check`: Check if files need updating without modifying them. Returns exit code 2 if changes are needed.
- `--version`: Show version.

## Example

Given a source file `example.c`:

<!-- code_snippet_start:test/data/sample.c:r/^#include/:r/^\}/+ -->

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
<!-- code_snippet_start:example.c:r/^int main/:r/^\}/+ -->

<!-- code_snippet_end -->
```

Running `code_snippet_to_doc -i README.md` will populate the snippet block with the `main` function body from `example.c`.

## License

This tool is Copyright (c) 2026 Ivan Grokhotkov and distributed under the [MIT License](LICENSE).
