#!/usr/bin/env python3
"""Strip HTML tags, CSS/pandoc class selectors, #id attributes, control characters,
and other non-content markup from a markdown file converted from HTML (e.g. via pandoc).

Focuses on maximizing readable information while producing clean markdown that
reads well even without a markdown parser.
"""

import re
import sys
from pathlib import Path


def strip_markup(text: str) -> str:
    # 1. Remove HTML tags (<div>, </div>, <span ...>, etc.)
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)

    # 2. Remove pandoc attribute blocks: {#id .class ...} including when
    #    attached to headings or inline elements
    text = re.sub(r"\s*\{[#.][^}]*\}", "", text)

    # 3. Remove pandoc fenced div markers  ::: class-name  and bare :::
    text = re.sub(r"^:{3,}\s*\{[^}]*\}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:{3,}.*$", "", text, flags=re.MULTILINE)

    # 4. Remove pandoc/markdown footnote-style anchors:
    #    ^[1](#target){#id}^  or  [text](#anchor){#id}
    text = re.sub(r"\^\[\d+\]\(#[^)]*\)\^", "", text)
    text = re.sub(r"\[([^\]]*)\]\(#[^)]*\)", r"\1", text)

    # 5. Remove standalone backslashes used as line breaks
    text = re.sub(r"^\\\s*$", "", text, flags=re.MULTILINE)

    # 6. Remove markdown grid-table border lines:
    #    +---+---+  or  +===+===+
    text = re.sub(r"^\+[-=+]+\+\s*$", "", text, flags=re.MULTILINE)

    # 7. Remove leading/trailing pipe characters from table rows
    #    (leftover from grid tables after border removal)
    text = re.sub(r"^\|\s*(.*?)\s*\|\s*$", r"\1", text, flags=re.MULTILINE)

    # 8. Remove control characters (keep \n, \r, \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # 9. Remove escaped markdown punctuation that adds no value:
    #    1\.  becomes  1.   (numbered list escapes)
    text = re.sub(r"(\d+)\\(\.\s)", r"\1\2", text)

    # 10. Remove non-breaking spaces and other unicode whitespace oddities
    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")  # zero-width space
    text = text.replace("\u200c", "")  # zero-width non-joiner
    text = text.replace("\u200d", "")  # zero-width joiner
    text = text.replace("\ufeff", "")  # BOM

    # 11. Collapse 3+ consecutive blank lines into 2 (one visual blank line)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 12. Strip trailing whitespace from each line
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

    return text.strip() + "\n"


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.md> [output.md]", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path

    text = input_path.read_text(encoding="utf-8")
    input_size = len(text.encode("utf-8"))
    cleaned = strip_markup(text)
    output_path.write_text(cleaned, encoding="utf-8")
    output_size = len(cleaned.encode("utf-8"))
    print(f"Processed {input_path} -> {output_path}")
    print(f"  Input:  {input_size:,} bytes")
    print(f"  Output: {output_size:,} bytes")
    print(f"  Saved:  {input_size - output_size:,} bytes ({(1 - output_size / input_size) * 100:.1f}%)")


if __name__ == "__main__":
    main()
