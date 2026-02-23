"""
taxes-bot: CLI tool for computing federal individual income tax returns.

Usage:
    uv run python main.py <input.json>           Compute tax return from JSON file
    uv run python main.py --schema input          Print input JSON schema
    uv run python main.py --schema output         Print output JSON schema
    echo '{ ... }' | uv run python main.py        Compute from stdin
"""

import json
import sys
from dataclasses import asdict

from models import TaxReturnInput, TaxReturnOutput, generate_schema
from calculator import calculate, ValidationError, _deserialize_enum


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--schema":
        schema_type = sys.argv[2] if len(sys.argv) > 2 else "input"
        if schema_type == "output":
            schema = generate_schema(TaxReturnOutput, "TaxReturnOutput")
        else:
            schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        print(json.dumps(schema, indent=2))
        return

    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1]) as f:
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


if __name__ == "__main__":
    main()
