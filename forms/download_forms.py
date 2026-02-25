"""Download IRS fillable PDF forms from irs.gov.

Uses only the standard library (urllib). Downloads all forms that the
tax calculator computes data for into forms/blanks/.

Usage:
    uv run python forms/download_forms.py
    uv run python forms/download_forms.py --form f1040   # single form
"""

import os
import sys
import urllib.request
import urllib.error

BASE_URL = "https://www.irs.gov/pub/irs-pdf/"

# Map of form_id -> (pdf filename, description)
FORMS = {
    "f1040": ("f1040.pdf", "Form 1040 - U.S. Individual Income Tax Return"),
    "f1040s1": ("f1040s1.pdf", "Schedule 1 - Additional Income and Adjustments"),
    "f1040s2": ("f1040s2.pdf", "Schedule 2 - Additional Taxes"),
    "f1040s3": ("f1040s3.pdf", "Schedule 3 - Additional Credits and Payments"),
    "f1040sa": ("f1040sa.pdf", "Schedule A - Itemized Deductions"),
    "f1040sb": ("f1040sb.pdf", "Schedule B - Interest and Dividends"),
    "f1040sc": ("f1040sc.pdf", "Schedule C - Business Income/Loss"),
    "f1040sd": ("f1040sd.pdf", "Schedule D - Capital Gains and Losses"),
    "f1040se": ("f1040se.pdf", "Schedule E - Rental/Partnership/S-Corp Income"),
    "f1040sf": ("f1040sf.pdf", "Schedule F - Farm Income"),
    "f1040sse": ("f1040sse.pdf", "Schedule SE - Self-Employment Tax"),
    "f8949": ("f8949.pdf", "Form 8949 - Capital Asset Sales"),
    "f2441": ("f2441.pdf", "Form 2441 - Child and Dependent Care"),
}

BLANKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blanks")


def download_form(form_id: str) -> str:
    """Download a single form PDF. Returns the local file path."""
    if form_id not in FORMS:
        raise ValueError(f"Unknown form: {form_id}. Known forms: {', '.join(sorted(FORMS))}")

    filename, description = FORMS[form_id]
    url = BASE_URL + filename
    dest = os.path.join(BLANKS_DIR, filename)

    print(f"  Downloading {description}...")
    print(f"    {url}")

    req = urllib.request.Request(url, headers={"User-Agent": "taxes-bot/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        print(f"    ERROR: HTTP {e.code} - {e.reason}")
        raise
    except urllib.error.URLError as e:
        print(f"    ERROR: {e.reason}")
        raise

    with open(dest, "wb") as f:
        f.write(data)

    size_kb = len(data) / 1024
    print(f"    Saved {dest} ({size_kb:.0f} KB)")
    return dest


def download_all() -> list[str]:
    """Download all forms. Returns list of local file paths."""
    os.makedirs(BLANKS_DIR, exist_ok=True)
    paths = []
    failed = []

    for form_id in FORMS:
        try:
            path = download_form(form_id)
            paths.append(path)
        except Exception as e:
            failed.append((form_id, str(e)))

    print(f"\nDownloaded {len(paths)}/{len(FORMS)} forms.")
    if failed:
        print("Failed:")
        for form_id, err in failed:
            print(f"  {form_id}: {err}")

    return paths


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--form":
        form_id = sys.argv[2] if len(sys.argv) > 2 else None
        if not form_id:
            print("Usage: python forms/download_forms.py --form <form_id>")
            print(f"Available: {', '.join(sorted(FORMS))}")
            sys.exit(1)
        download_form(form_id)
    else:
        download_all()


if __name__ == "__main__":
    main()
