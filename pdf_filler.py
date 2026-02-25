"""Fill IRS PDF forms with computed tax return data.

Reads field mapping files from forms/mappings/ and uses pypdf to populate
the corresponding blank PDF forms in forms/blanks/.

Requires pypdf: uv sync --group pdf

Usage:
    uv run --group pdf python pdf_filler.py <input.json> <output_dir>
"""

import json
import os
import sys
from dataclasses import asdict
from enum import Enum

FORMS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forms")
BLANKS_DIR = os.path.join(FORMS_DIR, "blanks")
MAPPINGS_DIR = os.path.join(FORMS_DIR, "mappings")


def _import_pypdf():
    """Lazy import pypdf with a clear error message."""
    try:
        from pypdf import PdfReader, PdfWriter
        return PdfReader, PdfWriter
    except ImportError:
        print(
            "pypdf is required for PDF generation.\n"
            "Install with: uv sync --group pdf",
            file=sys.stderr,
        )
        sys.exit(1)


def _resolve_path(data: dict, path: str):
    """Resolve a dot-separated path into a nested dict.

    Examples:
        _resolve_path({"income": {"total_wages": 75000}}, "income.total_wages")
        => 75000

        _resolve_path({"personal_info": {"first_name": "Alice"}}, "personal_info.first_name")
        => "Alice"

    Returns None if the path doesn't exist.
    """
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        else:
            return None
    return current


def _format_value(value, fmt: str) -> str:
    """Format a value for display in an IRS PDF field.

    Supported formats:
        text       - plain string
        currency   - whole dollars, no cents (IRS convention)
        ssn        - XXX-XX-XXXX format
        checkbox   - "Yes" if truthy
        filing_status_single - checkbox for SINGLE
        filing_status_mfj    - checkbox for MARRIED_FILING_JOINTLY
        filing_status_mfs    - checkbox for MARRIED_FILING_SEPARATELY
        filing_status_hoh    - checkbox for HEAD_OF_HOUSEHOLD
        filing_status_qss    - checkbox for QUALIFYING_SURVIVING_SPOUSE
    """
    if value is None:
        return ""

    if fmt == "text":
        return str(value)

    if fmt == "currency":
        if isinstance(value, (int, float)):
            rounded = round(value)
            if rounded == 0:
                return ""
            return str(rounded)
        return str(value)

    if fmt == "ssn":
        # IRS PDF SSN fields have max-length 9, digits only (displayed with dashes by the form)
        ssn = str(value).replace("-", "").replace(" ", "")
        if len(ssn) == 9:
            return ssn
        return str(value)

    if fmt == "checkbox":
        return "/1" if value else ""

    # Filing status checkboxes
    filing_status_map = {
        "filing_status_single": "SINGLE",
        "filing_status_mfj": "MARRIED_FILING_JOINTLY",
        "filing_status_mfs": "MARRIED_FILING_SEPARATELY",
        "filing_status_hoh": "HEAD_OF_HOUSEHOLD",
        "filing_status_qss": "QUALIFYING_SURVIVING_SPOUSE",
    }
    if fmt in filing_status_map:
        status_str = str(value)
        if isinstance(value, Enum):
            status_str = value.name
        return "/1" if status_str == filing_status_map[fmt] else ""

    return str(value)


def _load_mapping(form_id: str) -> dict:
    """Load a field mapping file for a given form."""
    path = os.path.join(MAPPINGS_DIR, f"{form_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _available_mappings() -> list[str]:
    """List all available form mapping IDs."""
    mappings = []
    if os.path.isdir(MAPPINGS_DIR):
        for f in sorted(os.listdir(MAPPINGS_DIR)):
            if f.endswith(".json"):
                mappings.append(f[:-5])
    return mappings


def determine_required_forms(input_data: dict, output_data: dict) -> list[str]:
    """Auto-detect which forms are needed based on the tax return data.

    Returns a list of form_ids that should be filled.
    """
    forms = ["f1040"]  # Always needed

    income = output_data.get("income", {})
    agi = output_data.get("agi", {})
    deductions = output_data.get("deductions", {})
    tax = output_data.get("tax", {})
    credits_ = output_data.get("credits", {})
    se_tax = output_data.get("se_tax", {})

    # Schedule 1 - Additional income or adjustments
    has_additional_income = any([
        income.get("total_business_income", 0) != 0,
        income.get("total_rental_income", 0) != 0,
        income.get("unemployment_compensation", 0) != 0,
        income.get("total_other_income", 0) != 0,
        income.get("alimony_income", 0) != 0,
        income.get("total_farm_income", 0) != 0,
        income.get("total_royalty_income", 0) != 0,
        income.get("total_k1_ordinary_income", 0) != 0,
        income.get("taxable_home_sale_gain", 0) != 0,
    ])
    has_adjustments = any([
        agi.get("educator_expenses_deduction", 0) != 0,
        agi.get("ira_deduction", 0) != 0,
        agi.get("student_loan_interest_deduction", 0) != 0,
        agi.get("hsa_deduction", 0) != 0,
        agi.get("se_tax_deduction", 0) != 0,
        agi.get("alimony_deduction", 0) != 0,
    ])
    if has_additional_income or has_adjustments:
        forms.append("f1040s1")

    # Schedule 2 - Additional taxes (AMT, NIIT)
    if any([
        tax.get("amt", 0) != 0,
        tax.get("niit_amount", 0) != 0,
        tax.get("additional_medicare_tax", 0) != 0,
        se_tax.get("total_se_tax", 0) != 0,
    ]):
        forms.append("f1040s2")

    # Schedule 3 - Additional credits and payments
    if any([
        credits_.get("education_credits", 0) != 0,
        credits_.get("foreign_tax_credit", 0) != 0,
        credits_.get("child_dependent_care_credit", 0) != 0,
        credits_.get("savers_credit", 0) != 0,
        credits_.get("energy_home_improvement_credit", 0) != 0,
        credits_.get("residential_clean_energy_credit", 0) != 0,
        credits_.get("elderly_disabled_credit", 0) != 0,
    ]):
        forms.append("f1040s3")

    # Schedule A - Itemized deductions
    if deductions.get("deduction_method_used") == "ITEMIZED":
        forms.append("f1040sa")

    # Schedule B - Interest and dividends > $1500
    if (income.get("total_interest", 0) > 1500
            or income.get("total_ordinary_dividends", 0) > 1500):
        forms.append("f1040sb")

    # Schedule C - Business income
    if input_data.get("business_income"):
        forms.append("f1040sc")

    # Schedule D - Capital gains/losses
    if input_data.get("capital_gains_losses"):
        forms.append("f1040sd")

    # Schedule E - Rental/partnership/S-Corp
    if input_data.get("rental_income") or input_data.get("k1_income") or input_data.get("royalty_income"):
        forms.append("f1040se")

    # Schedule F - Farm income
    if input_data.get("farm_income"):
        forms.append("f1040sf")

    # Schedule SE - Self-employment tax
    if se_tax.get("total_se_tax", 0) != 0:
        forms.append("f1040sse")

    # Form 8949 - Capital asset sales
    if input_data.get("capital_gains_losses"):
        forms.append("f8949")

    # Form 2441 - Child and dependent care
    if input_data.get("child_care_expenses"):
        forms.append("f2441")

    # Only return forms that have mapping files
    available = set(_available_mappings())
    return [f for f in forms if f in available]


def _find_checkbox_rect(writer, pdf_field: str, page_hint: int = 0) -> tuple | None:
    """Find the rectangle coordinates of a checkbox annotation by field name.

    IRS forms use XFA hybrid PDFs where checkbox field names in the AcroForm
    tree don't always match the annotation /T names. This function searches
    by the short field name (e.g., 'c1_8[0]') across page annotations.

    Returns (page_index, x1, y1, x2, y2) or None if not found.
    """
    # Extract the short field name (last segment)
    short_name = pdf_field.split(".")[-1] if "." in pdf_field else pdf_field

    for page_idx, page in enumerate(writer.pages):
        annots = page.get("/Annots", [])
        if not annots:
            continue
        for annot_ref in annots:
            annot = annot_ref.get_object()
            t = str(annot.get("/T", ""))
            ft = annot.get("/FT", "")
            if ft == "/Btn" and t == short_name:
                rect = annot.get("/Rect", [])
                if rect:
                    # Build full qualified name to check it matches
                    full_name = t
                    parent = annot.get("/Parent")
                    while parent:
                        p = parent.get_object() if hasattr(parent, "get_object") else parent
                        pn = str(p.get("/T", ""))
                        if pn:
                            full_name = pn + "." + full_name
                        parent = p.get("/Parent")

                    if full_name == pdf_field:
                        return (page_idx, *[float(v) for v in rect])
    return None


def fill_form(form_id: str, input_data: dict, output_data: dict) -> bytes:
    """Fill a single IRS PDF form with tax return data.

    Args:
        form_id: The form identifier (e.g., "f1040")
        input_data: The TaxReturnInput as a dict
        output_data: The TaxReturnOutput as a dict

    Returns:
        The filled PDF as bytes.
    """
    PdfReader, PdfWriter = _import_pypdf()
    from pypdf.generic import (
        NameObject, BooleanObject, ArrayObject, DecodedStreamObject,
    )

    mapping = _load_mapping(form_id)
    if mapping is None:
        raise ValueError(f"No mapping file found for form: {form_id}")

    pdf_file = mapping["pdf_file"]
    pdf_path = os.path.join(BLANKS_DIR, pdf_file)
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"Blank PDF not found: {pdf_path}\n"
            "Run: uv run python forms/download_forms.py"
        )

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.append(reader)

    # Remove XFA layer so AcroForm fields render properly
    if "/AcroForm" in writer._root_object:
        acroform = writer._root_object["/AcroForm"]
        if "/XFA" in acroform:
            del acroform["/XFA"]
        acroform[NameObject("/NeedAppearances")] = BooleanObject(True)

    text_values = {}
    checkbox_fields = []  # list of (pdf_field, on_value)
    for field_def in mapping["fields"]:
        pdf_field = field_def["pdf_field"]
        output_path = field_def["output_path"]
        source = field_def.get("source", "output")
        fmt = field_def.get("format", "text")

        data = input_data if source == "input" else output_data
        raw_value = _resolve_path(data, output_path)
        formatted = _format_value(raw_value, fmt)

        if formatted:
            if formatted.startswith("/"):
                checkbox_fields.append((pdf_field, formatted))
            else:
                text_values[pdf_field] = formatted

    # Apply text field values (auto_regenerate=False to preserve field formatting)
    for page in writer.pages:
        writer.update_page_form_field_values(page, text_values, auto_regenerate=False)

    # Apply checkboxes by drawing X marks on the page content stream.
    # IRS XFA hybrid PDFs don't reliably render AcroForm checkbox appearances,
    # so we draw directly onto the page.
    # Group overlays by page index
    page_overlays: dict[int, list[str]] = {}
    for pdf_field, on_value in checkbox_fields:
        result = _find_checkbox_rect(writer, pdf_field)
        if result is None:
            continue
        page_idx, x1, y1, x2, y2 = result
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        size = min(x2 - x1, y2 - y1) * 0.65
        half = size / 2
        overlay = (
            f"q\n"
            f"0 0 0 rg\n"
            f"0.8 w\n"
            f"{cx - half:.2f} {cy - half:.2f} m\n"
            f"{cx + half:.2f} {cy + half:.2f} l\n"
            f"S\n"
            f"{cx + half:.2f} {cy - half:.2f} m\n"
            f"{cx - half:.2f} {cy + half:.2f} l\n"
            f"S\n"
            f"Q\n"
        )
        page_overlays.setdefault(page_idx, []).append(overlay)

    for page_idx, overlays in page_overlays.items():
        page = writer.pages[page_idx]
        combined = "".join(overlays)
        new_stream = DecodedStreamObject()
        new_stream.set_data(combined.encode())
        stream_ref = writer._add_object(new_stream)

        contents = page.get("/Contents")
        if isinstance(contents, ArrayObject):
            contents.append(stream_ref)
        elif contents is not None:
            page[NameObject("/Contents")] = ArrayObject([contents, stream_ref])

    import io
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def fill_return(
    input_data: dict,
    output_data: dict,
    output_dir: str,
    form_ids: list[str] | None = None,
) -> list[str]:
    """Fill all applicable IRS forms for a tax return.

    Args:
        input_data: The TaxReturnInput as a dict
        output_data: The TaxReturnOutput as a dict
        output_dir: Directory to write filled PDFs
        form_ids: Optional list of specific forms to fill. If None,
                  auto-detects required forms.

    Returns:
        List of file paths written.
    """
    if form_ids is None:
        form_ids = determine_required_forms(input_data, output_data)

    os.makedirs(output_dir, exist_ok=True)
    written = []

    for form_id in form_ids:
        try:
            pdf_bytes = fill_form(form_id, input_data, output_data)
            out_path = os.path.join(output_dir, f"{form_id}_filled.pdf")
            with open(out_path, "wb") as f:
                f.write(pdf_bytes)
            written.append(out_path)
            print(f"  Filled: {out_path}")
        except (ValueError, FileNotFoundError) as e:
            print(f"  Skipped {form_id}: {e}", file=sys.stderr)

    return written


def fill_return_zip(input_data: dict, output_data: dict, form_ids: list[str] | None = None) -> bytes:
    """Fill all applicable forms and return as a ZIP archive in memory.

    Returns:
        ZIP file bytes containing all filled PDFs.
    """
    import io
    import zipfile

    if form_ids is None:
        form_ids = determine_required_forms(input_data, output_data)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for form_id in form_ids:
            try:
                pdf_bytes = fill_form(form_id, input_data, output_data)
                zf.writestr(f"{form_id}_filled.pdf", pdf_bytes)
            except (ValueError, FileNotFoundError):
                pass

    return buf.getvalue()


def main():
    if len(sys.argv) < 3:
        print("Usage: python pdf_filler.py <input.json> <output_dir>")
        print("\nFills IRS PDF forms from calculator input/output.")
        print("Requires: uv sync --group pdf")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]

    from models import TaxReturnInput, TaxReturnOutput
    from calculator import calculate, _deserialize_enum

    with open(input_path) as f:
        data = json.load(f)

    _deserialize_enum(data, TaxReturnInput)
    inp = TaxReturnInput(**data)
    result = calculate(inp)

    input_dict = asdict(inp)
    output_dict = asdict(result)

    # Convert enums to strings for matching
    def _enum_to_str(obj):
        if isinstance(obj, dict):
            return {k: _enum_to_str(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_enum_to_str(v) for v in obj]
        if isinstance(obj, Enum):
            return obj.name
        return obj

    input_dict = _enum_to_str(input_dict)
    output_dict = _enum_to_str(output_dict)

    forms = determine_required_forms(input_dict, output_dict)
    print(f"Required forms: {', '.join(forms)}")

    written = fill_return(input_dict, output_dict, output_dir, forms)
    print(f"\nFilled {len(written)} form(s) in {output_dir}")


if __name__ == "__main__":
    main()
