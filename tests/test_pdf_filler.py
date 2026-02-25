"""Tests for the PDF filler module."""

import json
import os
import pytest

from pdf_filler import (
    _resolve_path,
    _format_value,
    determine_required_forms,
    _load_mapping,
    _available_mappings,
)


# --- _resolve_path tests ---

class TestResolvePath:
    def test_simple_key(self):
        assert _resolve_path({"total_tax": 5000}, "total_tax") == 5000

    def test_nested_key(self):
        data = {"income": {"total_wages": 75000}}
        assert _resolve_path(data, "income.total_wages") == 75000

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": 42}}}
        assert _resolve_path(data, "a.b.c") == 42

    def test_missing_key_returns_none(self):
        assert _resolve_path({"a": 1}, "b") is None

    def test_missing_nested_key_returns_none(self):
        assert _resolve_path({"a": {"b": 1}}, "a.c") is None

    def test_missing_intermediate_returns_none(self):
        assert _resolve_path({"a": 1}, "a.b.c") is None

    def test_empty_dict(self):
        assert _resolve_path({}, "anything") is None

    def test_string_value(self):
        data = {"personal_info": {"first_name": "Alice"}}
        assert _resolve_path(data, "personal_info.first_name") == "Alice"

    def test_zero_value(self):
        data = {"tax": {"amt": 0}}
        assert _resolve_path(data, "tax.amt") == 0

    def test_boolean_value(self):
        data = {"penalty": {"penalty_waived": True}}
        assert _resolve_path(data, "penalty.penalty_waived") is True


# --- _format_value tests ---

class TestFormatValue:
    def test_none_returns_empty(self):
        assert _format_value(None, "text") == ""
        assert _format_value(None, "currency") == ""

    def test_text_format(self):
        assert _format_value("Alice", "text") == "Alice"
        assert _format_value(42, "text") == "42"

    def test_currency_rounds_to_whole_dollars(self):
        assert _format_value(75000.0, "currency") == "75000"
        assert _format_value(1234.56, "currency") == "1235"
        assert _format_value(1234.49, "currency") == "1234"

    def test_currency_zero_returns_empty(self):
        assert _format_value(0, "currency") == ""
        assert _format_value(0.0, "currency") == ""

    def test_currency_negative(self):
        assert _format_value(-3000, "currency") == "-3000"

    def test_ssn_formatting(self):
        assert _format_value("123456789", "ssn") == "123456789"
        assert _format_value("123-45-6789", "ssn") == "123456789"

    def test_ssn_short_passthrough(self):
        assert _format_value("12345", "ssn") == "12345"

    def test_checkbox_truthy(self):
        assert _format_value(True, "checkbox") == "/1"
        assert _format_value(1, "checkbox") == "/1"

    def test_checkbox_falsy(self):
        assert _format_value(False, "checkbox") == ""
        assert _format_value(0, "checkbox") == ""

    def test_filing_status_single(self):
        assert _format_value("SINGLE", "filing_status_single") == "/1"
        assert _format_value("MARRIED_FILING_JOINTLY", "filing_status_single") == ""

    def test_filing_status_mfj(self):
        assert _format_value("MARRIED_FILING_JOINTLY", "filing_status_mfj") == "/1"
        assert _format_value("SINGLE", "filing_status_mfj") == ""

    def test_filing_status_mfs(self):
        assert _format_value("MARRIED_FILING_SEPARATELY", "filing_status_mfs") == "/1"

    def test_filing_status_hoh(self):
        assert _format_value("HEAD_OF_HOUSEHOLD", "filing_status_hoh") == "/1"

    def test_filing_status_qss(self):
        assert _format_value("QUALIFYING_SURVIVING_SPOUSE", "filing_status_qss") == "/1"

    def test_unknown_format_returns_str(self):
        assert _format_value(42, "unknown_format") == "42"


# --- determine_required_forms tests ---

class TestDetermineRequiredForms:
    def _empty_output(self):
        return {
            "income": {},
            "agi": {},
            "deductions": {},
            "tax": {},
            "credits": {},
            "se_tax": {},
        }

    def test_always_includes_f1040(self):
        forms = determine_required_forms({}, self._empty_output())
        assert "f1040" in forms

    def test_schedule_a_for_itemized(self):
        output = self._empty_output()
        output["deductions"]["deduction_method_used"] = "ITEMIZED"
        forms = determine_required_forms({}, output)
        if "f1040sa" in _available_mappings():
            assert "f1040sa" in forms

    def test_schedule_c_for_business(self):
        output = self._empty_output()
        input_data = {"business_income": [{"gross_receipts": 50000}]}
        forms = determine_required_forms(input_data, output)
        if "f1040sc" in _available_mappings():
            assert "f1040sc" in forms

    def test_schedule_d_for_capital_gains(self):
        output = self._empty_output()
        input_data = {"capital_gains_losses": [{"proceeds": 10000}]}
        forms = determine_required_forms(input_data, output)
        if "f1040sd" in _available_mappings():
            assert "f1040sd" in forms

    def test_schedule_se_for_se_tax(self):
        output = self._empty_output()
        output["se_tax"]["total_se_tax"] = 5000
        forms = determine_required_forms({}, output)
        if "f1040sse" in _available_mappings():
            assert "f1040sse" in forms

    def test_schedule_1_for_adjustments(self):
        output = self._empty_output()
        output["agi"]["student_loan_interest_deduction"] = 2500
        forms = determine_required_forms({}, output)
        if "f1040s1" in _available_mappings():
            assert "f1040s1" in forms

    def test_schedule_2_for_amt(self):
        output = self._empty_output()
        output["tax"]["amt"] = 10000
        forms = determine_required_forms({}, output)
        if "f1040s2" in _available_mappings():
            assert "f1040s2" in forms

    def test_form_2441_for_child_care(self):
        output = self._empty_output()
        input_data = {"child_care_expenses": [{"amount": 5000}]}
        forms = determine_required_forms(input_data, output)
        if "f2441" in _available_mappings():
            assert "f2441" in forms

    def test_only_returns_forms_with_mappings(self):
        """All returned forms must have a mapping file."""
        output = self._empty_output()
        output["se_tax"]["total_se_tax"] = 5000
        output["tax"]["amt"] = 10000
        forms = determine_required_forms({"business_income": [{}]}, output)
        available = set(_available_mappings())
        for f in forms:
            assert f in available

    def test_minimal_return_only_f1040(self):
        """A simple W-2 return should only need Form 1040."""
        forms = determine_required_forms({}, self._empty_output())
        assert forms == ["f1040"]


# --- Mapping file tests ---

class TestMappingFiles:
    def test_f1040_mapping_exists(self):
        assert "f1040" in _available_mappings()

    def test_f1040_mapping_loads(self):
        mapping = _load_mapping("f1040")
        assert mapping is not None
        assert mapping["form_id"] == "f1040"
        assert mapping["pdf_file"] == "f1040.pdf"
        assert len(mapping["fields"]) > 0

    def test_f1040_fields_have_required_keys(self):
        mapping = _load_mapping("f1040")
        for field in mapping["fields"]:
            assert "pdf_field" in field
            assert "output_path" in field
            assert "source" in field
            assert "format" in field

    def test_nonexistent_mapping_returns_none(self):
        assert _load_mapping("nonexistent_form") is None


# --- Integration tests (require downloaded PDFs and pypdf) ---

@pytest.fixture
def simple_w2_input():
    return {
        "tax_year": 2025,
        "filing_status": "SINGLE",
        "personal_info": {
            "first_name": "Alice",
            "last_name": "Smith",
            "ssn": "123456789",
            "date_of_birth": "1990-03-15",
            "occupation": "Engineer",
        },
        "address": {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip_code": "90210",
        },
        "w2_income": [
            {
                "employer_name": "Acme Corp",
                "employer_ein": "12-3456789",
                "wages": 75000,
                "federal_income_tax_withheld": 9000,
                "social_security_wages": 75000,
                "social_security_tax_withheld": 4650,
                "medicare_wages": 75000,
                "medicare_tax_withheld": 1087.5,
            }
        ],
    }


@pytest.fixture
def simple_w2_output():
    return {
        "tax_year": 2025,
        "filing_status": "SINGLE",
        "income": {
            "total_wages": 75000,
            "total_interest": 0,
            "total_ordinary_dividends": 0,
            "total_qualified_dividends": 0,
            "net_capital_gain_loss": 0,
            "gross_income": 75000,
        },
        "agi": {
            "gross_income": 75000,
            "agi": 75000,
        },
        "deductions": {
            "deduction_method_used": "STANDARD",
            "deduction_amount": 15750,
            "taxable_income": 59250,
        },
        "tax": {
            "total_income_tax": 8523,
            "total_tax_before_credits": 8523,
            "amt": 0,
            "niit_amount": 0,
        },
        "credits": {
            "total_nonrefundable_credits": 0,
            "earned_income_credit": 0,
            "additional_child_tax_credit": 0,
        },
        "se_tax": {
            "total_se_tax": 0,
        },
        "payments": {
            "federal_income_tax_withheld": 9000,
            "estimated_tax_payments": 0,
            "total_payments": 9000,
        },
        "total_tax": 8523,
        "total_payments": 9000,
        "overpayment": 477,
        "amount_owed": 0,
    }


class TestFillFormIntegration:
    """Integration tests that fill real PDFs. Require pypdf and downloaded forms."""

    @pytest.fixture(autouse=True)
    def check_prerequisites(self):
        blanks_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "forms", "blanks")
        pdf_path = os.path.join(blanks_dir, "f1040.pdf")
        if not os.path.exists(pdf_path):
            pytest.skip("f1040.pdf not downloaded (run forms/download_forms.py)")
        try:
            import pypdf
        except ImportError:
            pytest.skip("pypdf not installed (run uv sync --group pdf)")

    def test_fill_f1040_returns_bytes(self, simple_w2_input, simple_w2_output):
        from pdf_filler import fill_form
        result = fill_form("f1040", simple_w2_input, simple_w2_output)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:5] == b"%PDF-"

    def test_fill_f1040_has_correct_values(self, simple_w2_input, simple_w2_output):
        from pdf_filler import fill_form
        from pypdf import PdfReader
        import io

        pdf_bytes = fill_form("f1040", simple_w2_input, simple_w2_output)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        fields = reader.get_fields()
        assert fields is not None

        def fv(name):
            """Return field value as a stripped string, or empty string if absent/blank."""
            f = fields.get(name)
            if f is None:
                return ""
            v = f.get("/V", "")
            return str(v).strip()

        # Personal information
        assert fv("topmostSubform[0].Page1[0].f1_14[0]") == "Alice"
        assert fv("topmostSubform[0].Page1[0].f1_15[0]") == "Smith"
        assert fv("topmostSubform[0].Page1[0].f1_16[0]") == "123456789"

        # Address
        assert fv("topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_20[0]") == "123 Main St"
        assert fv("topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_22[0]") == "Anytown"
        assert fv("topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_23[0]") == "CA"
        assert fv("topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_24[0]") == "90210"

        # Income – Page 1
        assert fv("topmostSubform[0].Page1[0].f1_47[0]") == "75000"   # Line 1a – W-2 wages
        assert fv("topmostSubform[0].Page1[0].f1_57[0]") == "75000"   # Line 1z – total wages
        assert fv("topmostSubform[0].Page1[0].f1_73[0]") == "75000"   # Line 9  – total income
        assert fv("topmostSubform[0].Page1[0].f1_75[0]") == "75000"   # Line 11a – AGI

        # Zero-valued income lines must be blank (not "0")
        assert fv("topmostSubform[0].Page1[0].f1_59[0]") == ""        # Line 2b – taxable interest
        assert fv("topmostSubform[0].Page1[0].f1_61[0]") == ""        # Line 3b – ordinary dividends
        assert fv("topmostSubform[0].Page1[0].f1_70[0]") == ""        # Line 7a – capital gain/loss

        # Deductions and taxable income – Page 2
        assert fv("topmostSubform[0].Page2[0].f2_01[0]") == "75000"   # Line 11b – AGI (repeated)
        assert fv("topmostSubform[0].Page2[0].f2_02[0]") == "15750"   # Line 12e – deduction
        assert fv("topmostSubform[0].Page2[0].f2_06[0]") == "59250"   # Line 15  – taxable income

        # Tax
        assert fv("topmostSubform[0].Page2[0].f2_08[0]") == "8523"    # Line 16  – tax
        assert fv("topmostSubform[0].Page2[0].f2_10[0]") == "8523"    # Line 18  – tax before credits
        assert fv("topmostSubform[0].Page2[0].f2_16[0]") == "8523"    # Line 24  – total tax

        # Payments and refund
        assert fv("topmostSubform[0].Page2[0].f2_20[0]") == "9000"    # Line 25d – withholding
        assert fv("topmostSubform[0].Page2[0].f2_29[0]") == "9000"    # Line 33  – total payments
        assert fv("topmostSubform[0].Page2[0].f2_30[0]") == "477"     # Line 34  – overpayment

        # Amount owed is zero → must be blank
        assert fv("topmostSubform[0].Page2[0].f2_35[0]") == ""        # Line 37  – amount owed

    def test_fill_f1040_values_match_calculator(self):
        """End-to-end: fill Form 1040 from real calculator output and assert field values."""
        from pdf_filler import fill_form
        from pypdf import PdfReader
        from models import TaxReturnInput, PersonalInfo, Address, W2Income, FilingStatus
        from calculator import calculate
        from dataclasses import asdict
        from enum import Enum
        import io

        inp = TaxReturnInput(
            tax_year=2025,
            filing_status=FilingStatus.SINGLE,
            personal_info=PersonalInfo(
                first_name="Alice",
                last_name="Smith",
                ssn="123456789",
                date_of_birth="1990-03-15",
            ),
            address=Address(street="123 Main St", city="Anytown", state="CA", zip_code="90210"),
            w2_income=[W2Income(
                employer_name="Acme Corp",
                employer_ein="12-3456789",
                wages=75000,
                federal_income_tax_withheld=9000,
                social_security_wages=75000,
                social_security_tax_withheld=4650,
                medicare_wages=75000,
                medicare_tax_withheld=1087.5,
            )],
        )
        result = calculate(inp)

        def _enum_to_str(obj):
            if isinstance(obj, dict):
                return {k: _enum_to_str(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_enum_to_str(v) for v in obj]
            if isinstance(obj, Enum):
                return obj.name
            return obj

        input_dict = _enum_to_str(asdict(inp))
        output_dict = _enum_to_str(asdict(result))

        pdf_bytes = fill_form("f1040", input_dict, output_dict)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        fields = reader.get_fields()

        def fv(name):
            f = fields.get(name)
            if f is None:
                return ""
            return str(f.get("/V", "")).strip()

        # Personal info
        assert fv("topmostSubform[0].Page1[0].f1_14[0]") == "Alice"
        assert fv("topmostSubform[0].Page1[0].f1_15[0]") == "Smith"

        # Income lines match calculator output
        wages = round(result.income.total_wages)
        assert fv("topmostSubform[0].Page1[0].f1_47[0]") == str(wages)
        assert fv("topmostSubform[0].Page1[0].f1_73[0]") == str(round(result.income.gross_income))
        assert fv("topmostSubform[0].Page1[0].f1_75[0]") == str(round(result.agi.agi))

        # Deductions
        assert fv("topmostSubform[0].Page2[0].f2_02[0]") == str(round(result.deductions.deduction_amount))
        assert fv("topmostSubform[0].Page2[0].f2_06[0]") == str(round(result.deductions.taxable_income))

        # Tax
        assert fv("topmostSubform[0].Page2[0].f2_08[0]") == str(round(result.tax.total_income_tax))
        assert fv("topmostSubform[0].Page2[0].f2_16[0]") == str(round(result.total_tax))

        # Payments and refund
        assert fv("topmostSubform[0].Page2[0].f2_20[0]") == str(round(result.payments.federal_income_tax_withheld))
        assert fv("topmostSubform[0].Page2[0].f2_29[0]") == str(round(result.total_payments))

        if result.overpayment > 0:
            assert fv("topmostSubform[0].Page2[0].f2_30[0]") == str(round(result.overpayment))
            assert fv("topmostSubform[0].Page2[0].f2_35[0]") == ""
        else:
            assert fv("topmostSubform[0].Page2[0].f2_30[0]") == ""
            assert fv("topmostSubform[0].Page2[0].f2_35[0]") == str(round(result.amount_owed))

    def test_fill_return_writes_files(self, simple_w2_input, simple_w2_output, tmp_path):
        from pdf_filler import fill_return
        written = fill_return(simple_w2_input, simple_w2_output, str(tmp_path))
        assert len(written) > 0
        for path in written:
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

    def test_fill_return_zip_produces_valid_zip(self, simple_w2_input, simple_w2_output):
        import zipfile
        import io
        from pdf_filler import fill_return_zip

        zip_bytes = fill_return_zip(simple_w2_input, simple_w2_output)
        assert len(zip_bytes) > 0

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "f1040_filled.pdf" in names
            for name in names:
                data = zf.read(name)
                assert data[:5] == b"%PDF-"


class TestDetermineRequiredFormsWithCalculator:
    """Tests using the real calculator for end-to-end form detection."""

    def test_simple_w2_needs_only_f1040(self):
        from models import TaxReturnInput, PersonalInfo, Address, W2Income, FilingStatus
        from calculator import calculate, _deserialize_enum
        from dataclasses import asdict
        from enum import Enum

        inp = TaxReturnInput(
            tax_year=2025,
            filing_status=FilingStatus.SINGLE,
            personal_info=PersonalInfo(
                first_name="Alice",
                last_name="Smith",
                ssn="123456789",
                date_of_birth="1990-03-15",
            ),
            address=Address(street="123 Main St", city="Anytown", state="CA", zip_code="90210"),
            w2_income=[W2Income(
                employer_name="Acme Corp",
                employer_ein="12-3456789",
                wages=75000,
                federal_income_tax_withheld=9000,
                social_security_wages=75000,
                social_security_tax_withheld=4650,
                medicare_wages=75000,
                medicare_tax_withheld=1087.5,
            )],
        )

        result = calculate(inp)

        def _enum_to_str(obj):
            if isinstance(obj, dict):
                return {k: _enum_to_str(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_enum_to_str(v) for v in obj]
            if isinstance(obj, Enum):
                return obj.name
            return obj

        input_dict = _enum_to_str(asdict(inp))
        output_dict = _enum_to_str(asdict(result))

        forms = determine_required_forms(input_dict, output_dict)
        assert "f1040" in forms
