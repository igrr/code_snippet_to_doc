import argparse
import difflib
import io
import os
import sys

from . import __version__
from .snippet_processor import process_markdown, process_rst


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


_FORMAT_PROCESSORS = {
    "rst": process_rst,
    "md": process_markdown,
}


def _get_processor(filename: str):
    """Return the appropriate processor function based on file extension."""
    parts = os.path.basename(filename).lower().split(".")
    for part in reversed(parts):
        if part in _FORMAT_PROCESSORS:
            return _FORMAT_PROCESSORS[part]
    return process_markdown


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()

    if not args.input:
        raise SystemExit("No input files specified")

    changes_required = False
    for in_file in args.input:
        in_file_str = in_file.read()
        in_file.seek(0)
        out_file = io.StringIO()
        processor = _get_processor(in_file.name)
        processor(in_file, out_file)
        out_file_str = out_file.getvalue()

        if in_file_str != out_file_str:
            if args.check:
                print(f"Changes required in {in_file.name}:", file=sys.stderr)
                for line in difflib.unified_diff(
                    in_file_str.splitlines(), out_file_str.splitlines(), lineterm=""
                ):
                    print(line, file=sys.stderr)
                changes_required = True
            else:
                print(f"Updating {in_file.name}...", file=sys.stderr)
                in_file.seek(0)
                in_file.truncate()
                in_file.write(out_file.getvalue())
                in_file.close()

    if args.check and changes_required:
        raise SystemExit(2)


main()
