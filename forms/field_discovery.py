"""Discover AcroForm field names in IRS fillable PDF forms.

Uses pypdf to extract field names, types, and metadata from each PDF.
Output is used to build the mapping files in forms/mappings/.

Usage:
    uv run --group pdf python forms/field_discovery.py --all
    uv run --group pdf python forms/field_discovery.py --form f1040
    uv run --group pdf python forms/field_discovery.py --form f1040 --json
"""

import json
import os
import sys

try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf is required: uv sync --group pdf")
    sys.exit(1)

BLANKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blanks")

# Import form list from download script
from download_forms import FORMS


def get_field_type(field: dict) -> str:
    """Determine field type from its AcroForm attributes."""
    ft = field.get("/FT", "")
    if ft == "/Tx":
        return "text"
    elif ft == "/Btn":
        return "checkbox"
    elif ft == "/Ch":
        return "choice"
    return str(ft) if ft else "unknown"


def discover_fields(pdf_path: str) -> list[dict]:
    """Extract all AcroForm fields from a PDF file."""
    reader = PdfReader(pdf_path)
    fields = []

    if reader.get_fields() is None:
        return fields

    for name, field_obj in reader.get_fields().items():
        field_info = {
            "name": name,
            "type": get_field_type(field_obj),
            "value": field_obj.get("/V", ""),
        }

        # Get tooltip/alternate name if available
        tu = field_obj.get("/TU", "")
        if tu:
            field_info["tooltip"] = str(tu)

        # Get default value
        dv = field_obj.get("/DV", "")
        if dv:
            field_info["default"] = str(dv)

        fields.append(field_info)

    return fields


def discover_form(form_id: str, as_json: bool = False) -> list[dict]:
    """Discover fields for a single form."""
    if form_id not in FORMS:
        print(f"Unknown form: {form_id}. Available: {', '.join(sorted(FORMS))}")
        sys.exit(1)

    filename = FORMS[form_id][0]
    pdf_path = os.path.join(BLANKS_DIR, filename)

    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        print("Run: uv run python forms/download_forms.py")
        sys.exit(1)

    fields = discover_fields(pdf_path)

    if as_json:
        print(json.dumps({"form_id": form_id, "fields": fields}, indent=2))
    else:
        print(f"\n{FORMS[form_id][1]}")
        print(f"File: {filename}")
        print(f"Fields: {len(fields)}")
        print("-" * 80)
        for f in fields:
            tooltip = f" ({f['tooltip']})" if "tooltip" in f else ""
            print(f"  [{f['type']:8s}] {f['name']}{tooltip}")

    return fields


def main():
    as_json = "--json" in sys.argv

    if "--all" in sys.argv:
        all_results = {}
        for form_id in FORMS:
            filename = FORMS[form_id][0]
            pdf_path = os.path.join(BLANKS_DIR, filename)
            if not os.path.exists(pdf_path):
                print(f"Skipping {form_id}: PDF not found")
                continue
            fields = discover_fields(pdf_path)
            all_results[form_id] = fields

            if not as_json:
                print(f"\n{FORMS[form_id][1]}")
                print(f"File: {filename} | Fields: {len(fields)}")
                print("-" * 80)
                for f in fields:
                    tooltip = f" ({f['tooltip']})" if "tooltip" in f else ""
                    print(f"  [{f['type']:8s}] {f['name']}{tooltip}")

        if as_json:
            print(json.dumps(all_results, indent=2))

    elif "--form" in sys.argv:
        idx = sys.argv.index("--form")
        form_id = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        if not form_id:
            print("Usage: python forms/field_discovery.py --form <form_id>")
            sys.exit(1)
        discover_form(form_id, as_json)

    else:
        print("Usage:")
        print("  python forms/field_discovery.py --all              Discover all forms")
        print("  python forms/field_discovery.py --form <form_id>   Discover one form")
        print("  python forms/field_discovery.py --form f1040 --json  Output as JSON")
        print(f"\nAvailable forms: {', '.join(sorted(FORMS))}")


if __name__ == "__main__":
    main()
