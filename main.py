"""
taxes-bot: CLI tool for computing federal individual income tax returns.

Usage:
    uv run python main.py <input.json>                 Compute tax return from JSON file
    uv run python main.py --schema input                Print input JSON schema
    uv run python main.py --schema output               Print output JSON schema
    uv run python main.py <input.json> --pdf <dir>      Compute and fill IRS PDF forms
    echo '{ ... }' | uv run python main.py              Compute from stdin
"""

import json
import sys
from dataclasses import asdict
from enum import Enum

from models import TaxReturnInput, TaxReturnOutput, generate_schema
from calculator import calculate, ValidationError, _deserialize_enum


def _enum_to_str(obj):
    """Recursively convert Enum values to their name strings."""
    if isinstance(obj, dict):
        return {k: _enum_to_str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_enum_to_str(v) for v in obj]
    if isinstance(obj, Enum):
        return obj.name
    return obj


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--schema":
        schema_type = sys.argv[2] if len(sys.argv) > 2 else "input"
        if schema_type == "output":
            schema = generate_schema(TaxReturnOutput, "TaxReturnOutput")
        else:
            schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        print(json.dumps(schema, indent=2))
        return

    # Parse --pdf flag from argv
    pdf_dir = None
    args = sys.argv[1:]
    if "--pdf" in args:
        idx = args.index("--pdf")
        if idx + 1 < len(args):
            pdf_dir = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        else:
            print("Error: --pdf requires an output directory", file=sys.stderr)
            sys.exit(1)

    if args and args[0] != "-":
        with open(args[0]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    _deserialize_enum(data, TaxReturnInput)
    inp = TaxReturnInput(**data)

    try:
        result = calculate(inp)
    except ValidationError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(asdict(result), indent=2, default=str))

    if pdf_dir:
        from pdf_filler import determine_required_forms, fill_return

        input_dict = _enum_to_str(asdict(inp))
        output_dict = _enum_to_str(asdict(result))

        forms = determine_required_forms(input_dict, output_dict)
        print(f"\nFilling PDF forms: {', '.join(forms)}", file=sys.stderr)
        written = fill_return(input_dict, output_dict, pdf_dir, forms)
        print(f"Wrote {len(written)} PDF(s) to {pdf_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
