"""Command line: python -m docsum report.pdf --lang tr"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import ExtractionError, SummaryError, load_document, summarize, to_markdown


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="docsum", description="Summarize a PDF, DOCX, DOC or TXT file.")
    p.add_argument("file", type=Path)
    p.add_argument("--lang", choices=["en", "tr"], default="en", help="summary language (default: en)")
    p.add_argument("--detail", choices=["brief", "standard", "detailed"], default="standard")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default="medium",
                   help="how hard the model thinks (higher = slower, more thorough)")
    p.add_argument("-o", "--output", type=Path, help="write Markdown here instead of stdout")
    args = p.parse_args(argv)

    try:
        doc = load_document(args.file.name, args.file.read_bytes())
        summary = summarize(
            doc, language=args.lang, detail=args.detail, effort=args.effort,
            progress=lambda m: print(m, file=sys.stderr),
        )
    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        return 1
    except (ExtractionError, SummaryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    md = to_markdown(summary, args.lang)
    if args.output:
        args.output.write_text(md, encoding="utf-8")
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
