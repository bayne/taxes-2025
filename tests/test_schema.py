"""Unit tests for JSON schema generation with IRC section references.

Verifies that ``generate_schema`` / ``dataclass_to_json_schema`` embed tax-code
references drawn from class docstrings, inline source comments, and enum
docstrings into the ``description`` fields of the produced JSON Schema.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pytest

from models import (
    AdoptionExpense,
    AGIComputation,
    AMTPreferenceItems,
    AnnuityIncome,
    CapitalGainTerm,
    CasualtyLossEvent,
    CreditComputation,
    DeductionComputation,
    DeductionMethod,
    Dependent,
    DependentRelationship,
    EducationCreditType,
    EITCEligibility,
    ElderlyDisabledInfo,
    FarmIncome,
    FilingStatus,
    GamblingIncome,
    IncomeComputation,
    K1EntityType,
    K1Income,
    KiddieTaxInfo,
    LikeKindExchange,
    MarketplaceCoverage,
    PersonalInfo,
    RestrictedStockEvent,
    RetirementAccountType,
    RoyaltyIncome,
    SavingsBondEducationExclusion,
    ScholarshipIncome,
    Section529Distribution,
    TaxComputation,
    # Real model types used for integration-level checks
    TaxReturnInput,
    TaxReturnOutput,
    W2Income,
    # Schema utilities under test
    _clean_docstring,
    _extract_field_comments,
    dataclass_to_json_schema,
    generate_schema,
)

# ============================================================================
# Helpers
# ============================================================================

_IRC_RE = re.compile(r"(?:IRC\s+)?§\d+", re.UNICODE)
"""Matches an IRC section reference like ``§152`` or ``IRC §61``."""


def _has_irc_ref(text: str) -> bool:
    """Return True when *text* contains at least one IRC § reference."""
    return bool(_IRC_RE.search(text))


# ============================================================================
# _clean_docstring
# ============================================================================


class TestCleanDocstring:
    """Tests for the ``_clean_docstring`` helper."""

    def test_empty_string_returns_empty(self):
        assert _clean_docstring("") == ""

    def test_none_returns_empty(self):
        assert _clean_docstring(None) == ""

    def test_single_line(self):
        assert _clean_docstring("Hello world.") == "Hello world."

    def test_strips_leading_trailing_whitespace(self):
        assert _clean_docstring("  Hello world.  ") == "Hello world."

    def test_multiline_preserves_all_content(self):
        doc = """First line.

        IRC §42 (title26.md:12345) — some rule.
        IRC §99 — another rule.
        """
        result = _clean_docstring(doc)
        assert "First line." in result
        assert "IRC §42 (title26.md:12345)" in result
        assert "IRC §99" in result

    def test_multiline_normalizes_indentation(self):
        doc = """First line.

            Indented line.
        """
        result = _clean_docstring(doc)
        # Every line should be stripped of leading whitespace
        for line in result.splitlines():
            assert line == line.strip()

    def test_paragraph_break_preserved(self):
        doc = """Summary line.

        Second paragraph with IRC §1."""
        result = _clean_docstring(doc)
        assert "\n\n" in result or "\n" in result
        assert "IRC §1" in result

    def test_irc_references_not_mangled(self):
        doc = "IRC §199A (title26.md:146332) — QBI deduction up to 20%."
        result = _clean_docstring(doc)
        assert "§199A" in result
        assert "title26.md:146332" in result


# ============================================================================
# _extract_field_comments
# ============================================================================


class TestExtractFieldComments:
    """Tests for the ``_extract_field_comments`` source-parsing helper."""

    def test_returns_dict(self):
        comments = _extract_field_comments(W2Income)
        assert isinstance(comments, dict)

    # -- Inline comments (same-line) -----------------------------------------

    def test_multiline_comment_on_simple_field(self):
        """PersonalInfo.date_of_birth has a multi-line comment with YYYY-MM-DD."""
        comments = _extract_field_comments(PersonalInfo)
        assert "date_of_birth" in comments
        assert "YYYY-MM-DD" in comments["date_of_birth"]

    def test_inline_comment_with_irc_ref(self):
        """W2Income.additional_medicare_tax_withheld has ``# §3101(b)(2)``."""
        comments = _extract_field_comments(W2Income)
        assert "additional_medicare_tax_withheld" in comments
        assert "§3101" in comments["additional_medicare_tax_withheld"]

    def test_inline_comment_on_dependent_field(self):
        """Dependent.gross_income has ``# For qualifying relative test``."""
        comments = _extract_field_comments(Dependent)
        assert "gross_income" in comments

    # -- Multi-line field definitions ----------------------------------------

    def test_multiline_field_comment_extracted(self):
        """TaxReturnInput.capital_loss_carryforward spans multiple lines
        with the comment on the continuation."""
        comments = _extract_field_comments(TaxReturnInput)
        assert "capital_loss_carryforward" in comments
        assert "§1212" in comments["capital_loss_carryforward"]

    def test_multiline_field_scholarship_income(self):
        """TaxReturnInput.scholarship_income comment is on the closing `)`."""
        comments = _extract_field_comments(TaxReturnInput)
        assert "scholarship_income" in comments
        assert "§117" in comments["scholarship_income"]

    # -- Section header comments ---------------------------------------------

    def test_section_header_applied_to_first_field(self):
        """``# Income sources — IRC §61 (title26.md:70846)`` should apply
        to the next field (w2_income)."""
        comments = _extract_field_comments(TaxReturnInput)
        assert "w2_income" in comments
        assert "§61" in comments["w2_income"]

    def test_section_header_for_dependents(self):
        """``# IRC §152 (title26.md:112887)`` precedes ``dependents``."""
        comments = _extract_field_comments(TaxReturnInput)
        assert "dependents" in comments
        assert "§152" in comments["dependents"]

    # -- Fields with no comments ---------------------------------------------

    def test_fields_without_comments_omitted(self):
        """Fields with no inline or section comment should not appear."""

        @dataclass
        class _NoComments:
            bare_field: int = 0
            another_bare: str = ""

        comments = _extract_field_comments(_NoComments)
        assert "bare_field" not in comments
        assert "another_bare" not in comments

    # -- Broad coverage on TaxReturnInput ------------------------------------

    def test_significant_coverage_on_input(self):
        """At least 60% of TaxReturnInput fields should have a comment."""
        from dataclasses import fields as dc_fields

        total = len(dc_fields(TaxReturnInput))
        comments = _extract_field_comments(TaxReturnInput)
        coverage = len(comments) / total
        assert coverage >= 0.60, (
            f"Only {len(comments)}/{total} ({coverage:.0%}) fields have "
            f"extracted comments; expected ≥60%"
        )

    def test_many_comments_contain_irc_refs(self):
        """Most extracted comments should contain an IRC § reference."""
        comments = _extract_field_comments(TaxReturnInput)
        with_ref = sum(1 for v in comments.values() if _has_irc_ref(v))
        ratio = with_ref / len(comments) if comments else 0
        assert ratio >= 0.40, (
            f"Only {with_ref}/{len(comments)} ({ratio:.0%}) comments "
            f"contain IRC references; expected ≥40%"
        )


# ============================================================================
# Enum descriptions
# ============================================================================


class TestEnumDescriptions:
    """Enums should include their docstring (with IRC refs) as description."""

    @pytest.mark.parametrize(
        "enum_cls, expected_section",
        [
            (FilingStatus, "§2"),
            (DependentRelationship, "§152"),
            (CapitalGainTerm, "§1222"),
            (EducationCreditType, "§25A"),
            (RetirementAccountType, "§219"),
            (DeductionMethod, "§63"),
            (K1EntityType, "§702"),
        ],
    )
    def test_enum_schema_has_irc_description(self, enum_cls, expected_section):
        from models import _resolve_type

        schema = _resolve_type(enum_cls)
        assert "description" in schema, (
            f"{enum_cls.__name__} schema missing description"
        )
        assert expected_section in schema["description"], (
            f"{enum_cls.__name__} description missing {expected_section}: "
            f"{schema['description']!r}"
        )

    def test_enum_schema_has_enum_values(self):
        from models import _resolve_type

        schema = _resolve_type(FilingStatus)
        assert schema["type"] == "string"
        assert "single" in schema["enum"]
        assert "description" in schema


# ============================================================================
# Dataclass-level descriptions (full docstrings)
# ============================================================================


class TestDataclassDescriptions:
    """Class-level ``description`` should contain the full docstring,
    including IRC section references — not just the first line."""

    @pytest.mark.parametrize(
        "cls, expected_fragments",
        [
            (
                TaxReturnInput,
                ["IRC §6012", "title26.md:498203", "IRC §6072"],
            ),
            (
                W2Income,
                ["IRC §61(a)(1)", "title26.md:70854", "IRC §31"],
            ),
            (
                Dependent,
                ["IRC §152", "IRC §24", "title26.md:112887"],
            ),
            (
                K1Income,
                ["IRC §702", "title26.md:283000"],
            ),
            (
                FarmIncome,
                ["IRC §162", "IRC §1401", "§172"],
            ),
            (
                AnnuityIncome,
                ["IRC §72", "exclusion ratio"],
            ),
            (
                AMTPreferenceItems,
                ["IRC §55", "§56", "§57"],
            ),
            (
                MarketplaceCoverage,
                ["IRC §36B", "Premium Tax Credit"],
            ),
            (
                GamblingIncome,
                ["IRC §61", "§165"],
            ),
            (
                LikeKindExchange,
                ["IRC §1031"],
            ),
            (
                RestrictedStockEvent,
                ["IRC §83"],
            ),
            (
                Section529Distribution,
                ["IRC §529"],
            ),
            (
                SavingsBondEducationExclusion,
                ["IRC §135"],
            ),
            (
                ScholarshipIncome,
                ["IRC §117"],
            ),
            (
                RoyaltyIncome,
                ["IRC §61(a)(6)"],
            ),
            (
                AdoptionExpense,
                ["IRC §23"],
            ),
            (
                ElderlyDisabledInfo,
                ["IRC §22"],
            ),
            (
                EITCEligibility,
                ["IRC §32"],
            ),
            (
                KiddieTaxInfo,
                ["IRC §1(g)"],
            ),
            (
                CasualtyLossEvent,
                ["IRC §165"],
            ),
        ],
    )
    def test_class_description_includes_irc_refs(self, cls, expected_fragments):
        schema = dataclass_to_json_schema(cls)
        desc = schema.get("description", "")
        for frag in expected_fragments:
            assert frag in desc, (
                f"{cls.__name__} description missing {frag!r}.\nGot: {desc!r}"
            )

    def test_description_is_multiline_when_docstring_is(self):
        """A class with a multi-line docstring should produce a multi-line
        description (not truncated to one line)."""
        schema = dataclass_to_json_schema(TaxReturnInput)
        desc = schema["description"]
        assert "\n" in desc, "Multi-line docstring was collapsed to one line"

    def test_class_without_explicit_docstring_has_no_irc_ref(self):
        """A dataclass with no explicit docstring should not produce a
        description containing IRC references.  (Python may auto-generate
        a ``__doc__`` with the dataclass repr, but it won't contain §.)"""

        @dataclass
        class _Bare:
            x: int = 0

        schema = dataclass_to_json_schema(_Bare)
        desc = schema.get("description", "")
        assert not _has_irc_ref(desc), (
            f"Bare dataclass should not have IRC refs in description: {desc!r}"
        )


# ============================================================================
# Output model descriptions
# ============================================================================


class TestOutputModelDescriptions:
    """The output-side models should also carry IRC references."""

    @pytest.mark.parametrize(
        "cls, expected_fragment",
        [
            (IncomeComputation, "IRC §61"),
            (AGIComputation, "IRC §62"),
            (DeductionComputation, "IRC §63"),
            (TaxComputation, "IRC §1"),
            (CreditComputation, "Nonrefundable credits"),
        ],
    )
    def test_output_class_description(self, cls, expected_fragment):
        schema = dataclass_to_json_schema(cls)
        desc = schema.get("description", "")
        assert expected_fragment in desc

    def test_tax_computation_mentions_amt_and_niit(self):
        schema = dataclass_to_json_schema(TaxComputation)
        desc = schema.get("description", "")
        assert "§55" in desc, "TaxComputation description missing AMT §55"
        assert "§1411" in desc, "TaxComputation description missing NIIT §1411"


# ============================================================================
# Field-level descriptions in generated schemas
# ============================================================================


class TestFieldDescriptionsInSchema:
    """Individual property schemas should carry ``description`` sourced from
    inline comments when those comments exist."""

    @pytest.fixture(scope="class")
    def input_schema(self):
        return generate_schema(TaxReturnInput, "TaxReturnInput")

    # -- TaxReturnInput top-level fields -------------------------------------

    def test_dependents_has_irc_152(self, input_schema):
        desc = input_schema["properties"]["dependents"].get("description", "")
        assert "§152" in desc

    def test_w2_income_has_irc_61(self, input_schema):
        desc = input_schema["properties"]["w2_income"].get("description", "")
        assert "§61" in desc

    def test_student_loan_interest_has_irc_221(self, input_schema):
        desc = input_schema["properties"]["student_loan_interest_paid"].get(
            "description", ""
        )
        assert "§221" in desc

    def test_hsa_has_irc_223(self, input_schema):
        desc = input_schema["properties"]["hsa"].get("description", "")
        assert "§223" in desc

    def test_qualified_tips_has_irc_224(self, input_schema):
        desc = input_schema["properties"]["qualified_tips"].get("description", "")
        assert "§224" in desc

    def test_qualified_overtime_has_irc_225(self, input_schema):
        desc = input_schema["properties"]["qualified_overtime"].get("description", "")
        assert "§225" in desc

    def test_k1_income_has_irc_ref(self, input_schema):
        desc = input_schema["properties"]["k1_income"].get("description", "")
        assert "§702" in desc or "§1366" in desc or "§652" in desc

    def test_royalty_income_has_irc_ref(self, input_schema):
        desc = input_schema["properties"]["royalty_income"].get("description", "")
        assert "§61" in desc

    def test_gambling_has_irc_ref(self, input_schema):
        desc = input_schema["properties"]["gambling"].get("description", "")
        assert "§61" in desc or "§165" in desc

    def test_nol_carryforward_description(self, input_schema):
        desc = input_schema["properties"]["nol_carryforward"].get("description", "")
        assert desc  # Should exist
        assert "NOL" in desc or "80%" in desc

    def test_charitable_contribution_carryforward_has_irc_170(self, input_schema):
        desc = input_schema["properties"]["charitable_contribution_carryforward"].get(
            "description", ""
        )
        assert "§170" in desc

    def test_energy_credit_carryforward_has_irc_25d(self, input_schema):
        desc = input_schema["properties"]["energy_credit_carryforward"].get(
            "description", ""
        )
        assert "§25D" in desc

    def test_marketplace_coverage_has_irc_36b(self, input_schema):
        desc = input_schema["properties"]["marketplace_coverage"].get("description", "")
        assert "§36B" in desc

    def test_amt_preferences_has_irc_55(self, input_schema):
        desc = input_schema["properties"]["amt_preferences"].get("description", "")
        assert "§55" in desc or "§56" in desc or "§57" in desc

    def test_savings_bond_education_has_irc_135(self, input_schema):
        desc = input_schema["properties"]["savings_bond_education"].get(
            "description", ""
        )
        assert "§135" in desc

    def test_capital_loss_carryforward_has_irc_1212(self, input_schema):
        desc = input_schema["properties"]["capital_loss_carryforward"].get(
            "description", ""
        )
        assert "§1212" in desc

    # -- Nested dataclass descriptions inside arrays -------------------------

    def test_w2_items_description_has_irc_ref(self, input_schema):
        items = input_schema["properties"]["w2_income"]["items"]
        desc = items.get("description", "")
        assert "IRC §61" in desc

    def test_dependent_items_description_has_irc_ref(self, input_schema):
        items = input_schema["properties"]["dependents"]["items"]
        desc = items.get("description", "")
        assert "IRC §152" in desc
        assert "IRC §24" in desc

    def test_k1_items_description_has_irc_ref(self, input_schema):
        items = input_schema["properties"]["k1_income"]["items"]
        desc = items.get("description", "")
        assert "IRC §702" in desc

    def test_farm_items_description_has_irc_ref(self, input_schema):
        items = input_schema["properties"]["farm_income"]["items"]
        desc = items.get("description", "")
        assert "IRC §162" in desc

    # -- Deeply nested field descriptions (fields inside nested objects) ------

    def test_nested_enum_field_has_description(self, input_schema):
        """The ``relationship`` field inside Dependent should carry the enum
        docstring with IRC §152."""
        dep_props = input_schema["properties"]["dependents"]["items"]["properties"]
        desc = dep_props["relationship"].get("description", "")
        assert "§152" in desc

    def test_nested_k1_entity_type_has_description(self, input_schema):
        """The ``entity_type`` field inside K1Income should carry the enum
        docstring with IRC §702."""
        k1_props = input_schema["properties"]["k1_income"]["items"]["properties"]
        desc = k1_props["entity_type"].get("description", "")
        assert "§702" in desc or "§1366" in desc

    def test_amt_iso_exercise_spread_has_description(self, input_schema):
        """The ``iso_exercise_spread`` field inside AMTPreferenceItems should
        reference §56 or §422."""
        amt_props = input_schema["properties"]["amt_preferences"]["properties"]
        desc = amt_props["iso_exercise_spread"].get("description", "")
        assert "§56" in desc or "§422" in desc

    def test_amt_prior_year_credit_has_description(self, input_schema):
        amt_props = input_schema["properties"]["amt_preferences"]["properties"]
        desc = amt_props["prior_year_amt_credit"].get("description", "")
        assert "§53" in desc


# ============================================================================
# generate_schema top-level structure
# ============================================================================


class TestGenerateSchema:
    """Tests for the ``generate_schema`` wrapper."""

    def test_has_schema_key(self):
        schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        assert "$schema" in schema
        assert "json-schema.org" in schema["$schema"]

    def test_has_title(self):
        schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        assert schema["title"] == "TaxReturnInput"

    def test_has_description_with_irc_refs(self):
        schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        assert "IRC §6012" in schema["description"]

    def test_output_schema_has_description(self):
        schema = generate_schema(TaxReturnOutput, "TaxReturnOutput")
        assert "description" in schema
        assert "Form 1040" in schema["description"]

    def test_input_schema_has_required_fields(self):
        schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        assert "required" in schema
        assert "tax_year" in schema["required"]
        assert "filing_status" in schema["required"]


# ============================================================================
# Coverage statistics (informational, but enforces a minimum bar)
# ============================================================================


class TestDescriptionCoverage:
    """Ensure a meaningful fraction of schema properties carry descriptions
    across the entire input and output schemas."""

    @staticmethod
    def _count_descriptions(obj: dict) -> tuple[int, int]:
        """Return (total_properties, properties_with_description)."""
        total = 0
        has_desc = 0
        if "properties" in obj:
            for prop in obj["properties"].values():
                total += 1
                if "description" in prop:
                    has_desc += 1
                sub_t, sub_h = TestDescriptionCoverage._count_descriptions(prop)
                total += sub_t
                has_desc += sub_h
        if "items" in obj:
            sub_t, sub_h = TestDescriptionCoverage._count_descriptions(obj["items"])
            total += sub_t
            has_desc += sub_h
        return total, has_desc

    def test_input_schema_description_coverage_above_35_pct(self):
        schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        total, has_desc = self._count_descriptions(schema)
        pct = has_desc / total if total else 0
        assert pct >= 0.35, (
            f"Input schema: {has_desc}/{total} ({pct:.0%}) properties have "
            f"descriptions; expected ≥35%"
        )

    def test_output_schema_description_coverage_above_25_pct(self):
        schema = generate_schema(TaxReturnOutput, "TaxReturnOutput")
        total, has_desc = self._count_descriptions(schema)
        pct = has_desc / total if total else 0
        assert pct >= 0.25, (
            f"Output schema: {has_desc}/{total} ({pct:.0%}) properties have "
            f"descriptions; expected ≥25%"
        )

    def test_top_level_input_fields_mostly_described(self):
        """At least 90% of the top-level TaxReturnInput properties should
        have a description (from inline comment, section header, or type)."""
        schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        props = schema["properties"]
        total = len(props)
        has_desc = sum(1 for p in props.values() if "description" in p)
        pct = has_desc / total
        assert pct >= 0.90, (
            f"Top-level input fields: {has_desc}/{total} ({pct:.0%}) have "
            f"descriptions; expected ≥90%"
        )

    def test_irc_ref_density_in_input_descriptions(self):
        """Among top-level input properties that *have* a description, at
        least 50% should mention an IRC § section."""
        schema = generate_schema(TaxReturnInput, "TaxReturnInput")
        props = schema["properties"]
        described = [p for p in props.values() if "description" in p]
        with_irc = sum(1 for p in described if _has_irc_ref(p["description"]))
        pct = with_irc / len(described) if described else 0
        assert pct >= 0.50, (
            f"Only {with_irc}/{len(described)} ({pct:.0%}) described fields "
            f"contain IRC references; expected ≥50%"
        )
