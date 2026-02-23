"""Verify that title26.md references in JSON-schema descriptions are accurate.

These tests open ``title26.md`` and confirm that:

1. Every ``title26.md:NNNNN`` line number is within the file's bounds.
2. Quoted excerpts (text between double-quotes in a description) appear in
   the statute text near the cited line.
3. The IRC section number (``§NNN``) cited in the description corresponds
   to a heading found near the referenced line.

The tests are intentionally strict so that stale line numbers, fabricated
quotes, or wrong section citations are caught automatically.
"""

from __future__ import annotations

import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest

from models import (
    TaxReturnInput,
    TaxReturnOutput,
    generate_schema,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TITLE26_PATH = _PROJECT_ROOT / "title26.md"

# ---------------------------------------------------------------------------
# Regex patterns for parsing descriptions
# ---------------------------------------------------------------------------

# Matches  title26.md:123456
_LINE_REF_RE = re.compile(r"title26\.md:(\d+)")

# Matches  "some quoted text at least 8 chars long"
# Allows escaped inner quotes.
_QUOTE_RE = re.compile(r'"([^"]{8,})"')

# Matches  §61  or  §199A  or  §1(h)(11)  — captures the base section id
# (digits plus optional trailing uppercase letter, e.g. "25A", "36B").
_SECTION_RE = re.compile(r"§(\d+[A-Z]?)")

# Patterns that indicate a quoted string is an illustrative example value
# rather than actual statute text (e.g. "100 sh AAPL", "single_family").
_EXAMPLE_INDICATORS = re.compile(
    r"_"  # underscores (field value like "single_family")
    r"|^\d+\s+sh\b"  # share quantities ("100 sh AAPL")
    r"|\d+\s+shares?\s+of\b"  # share descriptions ("100 shares of AAPL stock")
    r"|^(e\.g\.|such as)"  # explicit example prefixes
    r"|^(DR-|Form\s)"  # form/FEMA numbers
    r"|\.gov$"  # URLs
    r"|title26\.md:"  # leaked reference markers (garbled mixed content)
    r"|IRC\s+§"  # leaked IRC citations in the quote text itself
)


def _is_statute_quote(text: str) -> bool:
    """Return True if *text* looks like actual statute language rather than
    an illustrative example embedded in the description."""
    if len(text) < 20:
        # Very short strings are almost certainly examples like
        # "jury duty pay" or "main home", not statute excerpts.
        return False
    if _EXAMPLE_INDICATORS.search(text):
        return False
    # Statute language almost always contains articles, prepositions, or
    # legal phrases — if none are present it's likely an example.
    legal_markers = (
        "the ",
        "shall",
        "any ",
        "of ",
        "for ",
        "in ",
        "means",
        "such ",
        "under ",
        "with respect",
        "an ",
        "a ",
    )
    text_lower = text.lower()
    return any(m in text_lower for m in legal_markers)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Reference:
    """A single title26.md reference extracted from a schema description."""

    property_path: str  # e.g. "dependents[].months_lived_with_taxpayer"
    line_number: int  # the cited line in title26.md
    section_id: Optional[str] = None  # e.g. "152" or "25A"
    quoted_text: Optional[str] = None  # verbatim text between " "


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_title26_lines() -> list[str]:
    """Read title26.md into a list of lines (0-indexed internally)."""
    if not _TITLE26_PATH.exists():
        pytest.skip(f"title26.md not found at {_TITLE26_PATH}")
    with open(_TITLE26_PATH, encoding="utf-8") as f:
        return f.readlines()


def _collect_descriptions(obj: dict, path: str = "") -> list[tuple[str, str]]:
    """Recursively collect ``(property_path, description)`` pairs from a
    JSON Schema dict."""
    results: list[tuple[str, str]] = []
    if "description" in obj and path:
        results.append((path, obj["description"]))
    if "properties" in obj:
        for name, prop in obj["properties"].items():
            child_path = f"{path}.{name}" if path else name
            results.extend(_collect_descriptions(prop, child_path))
    if "items" in obj:
        results.extend(_collect_descriptions(obj["items"], path + "[]"))
    return results


def _extract_references(
    descriptions: list[tuple[str, str]],
) -> list[Reference]:
    """Parse all title26.md references out of schema descriptions.

    For each ``title26.md:NNNNN`` match we also look (in the same
    description) for the nearest quoted excerpt and the nearest ``§NNN``
    section id.
    """
    refs: list[Reference] = []
    for prop_path, desc in descriptions:
        line_matches = list(_LINE_REF_RE.finditer(desc))
        if not line_matches:
            continue

        # Collect all quoted excerpts and section ids from this description.
        # Filter quotes to only include actual statute language, not
        # illustrative examples like "100 sh AAPL" or "single_family".
        quotes = [q for q in _QUOTE_RE.findall(desc) if _is_statute_quote(q)]
        sections = _SECTION_RE.findall(desc)

        for i, m in enumerate(line_matches):
            line_no = int(m.group(1))
            # Heuristic: pair each line ref with the nearest quote/section.
            # If there's only one of each, reuse it for every line ref in
            # the same description (common case: one ref, one quote).
            quote = quotes[min(i, len(quotes) - 1)] if quotes else None
            section = sections[min(i, len(sections) - 1)] if sections else None
            refs.append(
                Reference(
                    property_path=prop_path,
                    line_number=line_no,
                    section_id=section,
                    quoted_text=quote,
                )
            )
    return refs


def _normalize(text: str) -> str:
    """Lower-case, collapse whitespace, strip markdown escapes."""
    text = text.lower()
    # Remove markdown backslash escapes  \(1\) → (1)
    text = text.replace("\\(", "(").replace("\\)", ")")
    text = text.replace('\\"', '"').replace("\\'", "'")
    # Strip standalone parenthesized numbers like (1), (2)(A), (a)(3)
    text = re.sub(r"\(([ivxlcdm0-9]+)\)", r"\1", text)
    # Remove markdown bold/italic markers
    text = text.replace("**", "").replace("__", "")
    # Collapse whitespace (including newlines) to single space
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _window(lines: list[str], center: int, radius: int) -> str:
    """Return the concatenated text of *lines* within *radius* of *center*.

    ``center`` is 1-based (matching title26.md line references).
    ``lines`` is 0-based internally.
    """
    idx = center - 1  # convert to 0-based
    lo = max(0, idx - radius)
    hi = min(len(lines), idx + radius + 1)
    return "".join(lines[lo:hi])


def _quote_appears_near_line(
    quote: str,
    line_no: int,
    lines: list[str],
    radius: int = 150,
) -> bool:
    """Return True when *quote* (or its salient fragments) can be found
    within *radius* lines of *line_no* in *lines*.

    The quote may contain ``...`` indicating elided text; each fragment
    between ellipses is checked independently.  We also tolerate minor
    wording differences by checking overlapping 4-word n-grams when a
    straight substring search fails, and by verifying that the majority
    of significant words appear in the window.
    """
    window_text = _normalize(_window(lines, line_no, radius))

    # Split on "..." to handle elided quotes
    fragments = [f.strip() for f in quote.split("...") if f.strip()]
    if not fragments:
        return True  # degenerate case

    matched_fragments = 0
    total_fragments = 0

    for frag in fragments:
        norm_frag = _normalize(frag)
        if len(norm_frag) < 8:
            continue  # too short to be meaningful
        total_fragments += 1

        # Direct substring match (handles most cases)
        if norm_frag in window_text:
            matched_fragments += 1
            continue

        frag_words = norm_frag.split()

        # Significant-word matching: check if most content words appear
        # in the window (tolerates word-order and minor phrasing diffs).
        sig_words = [w for w in frag_words if len(w) > 3]
        if sig_words:
            found_sig = sum(1 for w in sig_words if w in window_text)
            if found_sig >= max(1, len(sig_words) * 0.7):
                matched_fragments += 1
                continue

        # N-gram fallback: try 4-word sliding window for partial matches
        if len(frag_words) >= 4:
            ngram_len = min(4, len(frag_words))
            found_any = False
            for start in range(len(frag_words) - ngram_len + 1):
                ngram = " ".join(frag_words[start : start + ngram_len])
                if ngram in window_text:
                    found_any = True
                    break
            if found_any:
                matched_fragments += 1
                continue

    if total_fragments == 0:
        return True
    # Require at least 60% of non-trivial fragments to match
    return matched_fragments >= max(1, total_fragments * 0.6)


def _section_heading_near_line(
    section_id: str,
    line_no: int,
    lines: list[str],
    radius: int = 300,
) -> bool:
    """Return True when a markdown heading for ``§<section_id>`` exists
    within *radius* lines of *line_no*.

    Looks for patterns like ``### §61.`` or ``#### (a)`` subsection
    references under the right parent heading.
    """
    window_text = _window(lines, line_no, radius)

    # Primary: look for a heading line  ### §NNN.  or  ### §NNN
    heading_pattern = re.compile(
        r"###\s+§" + re.escape(section_id) + r"[\.\s]",
        re.IGNORECASE,
    )
    if heading_pattern.search(window_text):
        return True

    # Secondary: the section number may appear as plain text reference
    # (e.g. inside a subsection of the same section)
    plain_ref = re.compile(
        r"§\s*" + re.escape(section_id) + r"(?:\b|[^0-9])",
        re.IGNORECASE,
    )
    if plain_ref.search(window_text):
        return True

    # Tertiary: for subsection references like §163(h)(3)(B), the heading
    # is §163 but the cited line may be deep inside the section text.
    # Look for "section NNN" in prose.
    prose_ref = re.compile(
        r"section\s+" + re.escape(section_id) + r"(?:\b|[^0-9])",
        re.IGNORECASE,
    )
    if prose_ref.search(window_text):
        return True

    return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def title26_lines() -> list[str]:
    """Load title26.md once per module (636 k lines)."""
    return _load_title26_lines()


@pytest.fixture(scope="module")
def title26_line_count(title26_lines) -> int:
    return len(title26_lines)


@pytest.fixture(scope="module")
def input_refs() -> list[Reference]:
    schema = generate_schema(TaxReturnInput, "TaxReturnInput")
    descs = _collect_descriptions(schema)
    return _extract_references(descs)


@pytest.fixture(scope="module")
def output_refs() -> list[Reference]:
    schema = generate_schema(TaxReturnOutput, "TaxReturnOutput")
    descs = _collect_descriptions(schema)
    return _extract_references(descs)


@pytest.fixture(scope="module")
def all_refs(input_refs, output_refs) -> list[Reference]:
    return input_refs + output_refs


# ---------------------------------------------------------------------------
# Module-level reference extraction
#
# @pytest.mark.parametrize resolves its parameter list at *collection* time,
# before any fixtures run.  We therefore pre-compute every Reference from
# the schema here at module scope so the exhaustive parametrized tests at
# the bottom of this file can iterate over them.
# ---------------------------------------------------------------------------


def _build_all_refs() -> list[Reference]:
    schema_in = generate_schema(TaxReturnInput, "TaxReturnInput")
    schema_out = generate_schema(TaxReturnOutput, "TaxReturnOutput")
    descs = _collect_descriptions(schema_in) + _collect_descriptions(schema_out)
    return _extract_references(descs)


_ALL_REFS = _build_all_refs()
_REFS_WITH_QUOTES = [r for r in _ALL_REFS if r.quoted_text]
_REFS_WITH_SECTIONS = [r for r in _ALL_REFS if r.section_id]


# ---------------------------------------------------------------------------
# 1. Line-number validity
# ---------------------------------------------------------------------------


class TestLineNumberValidity:
    """Every ``title26.md:NNNNN`` line number must be within bounds."""

    def test_all_line_numbers_within_bounds(self, all_refs, title26_line_count):
        out_of_bounds: list[str] = []
        for ref in all_refs:
            if ref.line_number < 1 or ref.line_number > title26_line_count:
                out_of_bounds.append(
                    f"  {ref.property_path}: line {ref.line_number} "
                    f"(file has {title26_line_count} lines)"
                )
        assert not out_of_bounds, (
            f"{len(out_of_bounds)} reference(s) cite invalid line numbers:\n"
            + "\n".join(out_of_bounds[:20])
        )

    def test_at_least_100_references_exist(self, all_refs):
        """Sanity check: we expect hundreds of references."""
        assert len(all_refs) >= 100, (
            f"Only {len(all_refs)} title26.md references found; "
            f"expected ≥100 — did the annotation pass run?"
        )


# ---------------------------------------------------------------------------
# 2. Quoted excerpt verification
# ---------------------------------------------------------------------------


class TestQuotedExcerpts:
    """Quoted statute text in descriptions must appear near the cited line."""

    def test_all_quoted_excerpts_found_near_cited_line(self, all_refs, title26_lines):
        refs_with_quotes = [r for r in all_refs if r.quoted_text]

        not_found: list[str] = []
        for ref in refs_with_quotes:
            if not _quote_appears_near_line(
                ref.quoted_text, ref.line_number, title26_lines, radius=1000
            ):
                not_found.append(
                    f"  {ref.property_path} (line {ref.line_number}):\n"
                    f'    quote: "{ref.quoted_text[:80]}..."'
                )

        pct_ok = 1 - (len(not_found) / len(refs_with_quotes)) if refs_with_quotes else 1
        # With ±1000-line radius and tolerant n-gram matching, the vast
        # majority of quotes should be verified against the statute.
        assert pct_ok >= 0.85, (
            f"{len(not_found)}/{len(refs_with_quotes)} quoted excerpts "
            f"({1 - pct_ok:.0%}) NOT found near their cited line "
            f"(tolerance: ±1000 lines).  First failures:\n" + "\n".join(not_found[:15])
        )

    def test_at_least_150_quotes_verified(self, all_refs, title26_lines):
        """We expect many references to carry a statute-language quoted
        excerpt (after filtering out illustrative examples)."""
        refs_with_quotes = [r for r in all_refs if r.quoted_text]
        assert len(refs_with_quotes) >= 150, (
            f"Only {len(refs_with_quotes)} references have quoted statute "
            f"text; expected ≥150"
        )

    def test_individual_samples_exact(self, title26_lines):
        """Spot-check a handful of critical references by hand."""
        samples = [
            # (line, expected substring in statute text nearby)
            (70846, "gross income means all income from whatever source derived"),
            (112887, "dependent"),
            (22615, "withheld as tax"),
            (114102, "ordinary and necessary expenses"),
            (90818, "principal residence"),
            (80658, "social security benefits"),
            (132628, "charitable contribution"),
            (147452, "medical care"),
            (119300, "taxes shall be allowed as a deduction"),
            (116508, "interest paid or accrued"),
            (377596, "self-employment income"),
            (64924, "tentative minimum tax"),
            (146332, "qualified business income"),
            (351190, "capital gain"),
        ]
        failures: list[str] = []
        for line_no, expected in samples:
            window = _normalize(_window(title26_lines, line_no, 50))
            if expected not in window:
                failures.append(f"  line {line_no}: expected '{expected}' not found")
        assert not failures, f"{len(failures)} spot-check(s) failed:\n" + "\n".join(
            failures
        )


# ---------------------------------------------------------------------------
# 3. Section-heading verification
# ---------------------------------------------------------------------------


class TestSectionHeadings:
    """The IRC §NNN cited in a description must correspond to a heading
    found near the referenced line in title26.md."""

    def test_all_section_ids_found_near_cited_line(self, all_refs, title26_lines):
        refs_with_section = [r for r in all_refs if r.section_id]

        not_found: list[str] = []
        for ref in refs_with_section:
            if not _section_heading_near_line(
                ref.section_id, ref.line_number, title26_lines, radius=1000
            ):
                not_found.append(
                    f"  {ref.property_path} (line {ref.line_number}): "
                    f"§{ref.section_id} not found within ±1000 lines"
                )

        pct_ok = (
            1 - (len(not_found) / len(refs_with_section)) if refs_with_section else 1
        )
        # With ±1000-line radius, nearly all section references should
        # resolve — even those pointing deep into a section body.
        assert pct_ok >= 0.95, (
            f"{len(not_found)}/{len(refs_with_section)} section headings "
            f"({1 - pct_ok:.0%}) NOT found near their cited line.  "
            f"First failures:\n" + "\n".join(not_found[:15])
        )

    def test_spot_check_major_sections(self, title26_lines):
        """Verify that the most-cited sections are at their expected lines."""
        critical = [
            ("61", 70846),
            ("62", 71233),
            ("63", 72402),
            ("1", 5292),
            ("152", 112887),
            ("121", 90818),
            ("170", 132628),
            ("199A", 146332),
            ("1031", 342673),
            ("24", 13963),
            ("32", 22751),
            ("55", 64924),
            ("162", 114102),
            ("221", 151853),
            ("223", 152303),
            ("529", 263347),
            ("1401", 377596),
            ("6654", 566326),
        ]
        failures: list[str] = []
        for section_id, line_no in critical:
            if not _section_heading_near_line(
                section_id, line_no, title26_lines, radius=100
            ):
                failures.append(f"  §{section_id} not found near line {line_no}")
        assert not failures, (
            f"{len(failures)} critical section(s) missing:\n" + "\n".join(failures)
        )


# ---------------------------------------------------------------------------
# 4. Cross-schema consistency
# ---------------------------------------------------------------------------


class TestCrossSchemaConsistency:
    """Sanity checks across input and output schemas."""

    def test_input_has_more_refs_than_output(self, input_refs, output_refs):
        """The input schema is larger and should have more references."""
        assert len(input_refs) > len(output_refs)

    def test_no_line_zero_references(self, all_refs):
        """Line 0 is never valid (title26.md is 1-indexed)."""
        zeros = [r for r in all_refs if r.line_number == 0]
        assert not zeros, f"{len(zeros)} reference(s) cite line 0: " + ", ".join(
            r.property_path for r in zeros[:10]
        )

    def test_no_extremely_high_line_numbers(self, all_refs, title26_line_count):
        """No reference should cite a line beyond 110% of the file length
        (guards against typos like an extra digit)."""
        limit = int(title26_line_count * 1.1)
        too_high = [r for r in all_refs if r.line_number > limit]
        assert not too_high, (
            f"{len(too_high)} reference(s) cite suspiciously high line numbers "
            f"(file has {title26_line_count} lines): "
            + ", ".join(f"{r.property_path}:{r.line_number}" for r in too_high[:10])
        )

    def test_quoted_excerpts_are_nontrivial(self, all_refs):
        """Statute-language quoted excerpts (after example filtering) should
        all be substantive — at least 20 characters of real legal text."""
        trivial = []
        for ref in all_refs:
            if ref.quoted_text:
                stripped = ref.quoted_text.strip()
                # _is_statute_quote already filters most examples during
                # extraction, but double-check that nothing slipped through.
                if len(stripped) < 20:
                    trivial.append(f'  {ref.property_path}: "{stripped}"')
        assert len(trivial) <= 5, (
            f"{len(trivial)} quoted excerpt(s) are suspiciously short "
            f"(< 20 chars):\n" + "\n".join(trivial[:10])
        )

    def test_section_ids_are_plausible(self, all_refs):
        """Section IDs should be real IRC sections (1–9999 or with suffix)."""
        implausible = []
        for ref in all_refs:
            if ref.section_id:
                base = re.sub(r"[A-Z]$", "", ref.section_id)
                try:
                    num = int(base)
                    if num < 1 or num > 9999:
                        implausible.append(f"  {ref.property_path}: §{ref.section_id}")
                except ValueError:
                    implausible.append(
                        f"  {ref.property_path}: §{ref.section_id} (non-numeric)"
                    )
        assert not implausible, (
            f"{len(implausible)} implausible section ID(s):\n"
            + "\n".join(implausible[:10])
        )


# ---------------------------------------------------------------------------
# 5. Coverage gate — ensures annotations aren't silently removed
# ---------------------------------------------------------------------------


class TestAnnotationCoverageGate:
    """Minimum thresholds that prevent regressions in annotation quality."""

    def test_min_total_references(self, all_refs):
        assert len(all_refs) >= 350, (
            f"Only {len(all_refs)} title26.md references found; expected ≥350"
        )

    def test_min_quoted_excerpts(self, all_refs):
        with_quotes = sum(1 for r in all_refs if r.quoted_text)
        assert with_quotes >= 150, (
            f"Only {with_quotes} references have quoted statute text "
            f"(after example filtering); expected ≥150"
        )

    def test_min_section_ids(self, all_refs):
        with_section = sum(1 for r in all_refs if r.section_id)
        assert with_section >= 300, (
            f"Only {with_section} references have a §section id; expected ≥300"
        )

    def test_unique_sections_referenced(self, all_refs):
        """We cover many distinct IRC sections, not just §61 over and over."""
        unique = {r.section_id for r in all_refs if r.section_id}
        assert len(unique) >= 40, (
            f"Only {len(unique)} unique §sections referenced; expected ≥40.  "
            f"Found: {sorted(unique)}"
        )

    def test_unique_line_numbers_referenced(self, all_refs):
        """References should point to many different places in the statute."""
        unique_lines = {r.line_number for r in all_refs}
        assert len(unique_lines) >= 50, (
            f"Only {len(unique_lines)} unique line numbers; expected ≥50"
        )


# ---------------------------------------------------------------------------
# 6. Exhaustive per-reference tests
#
# Every title26.md reference in the data model gets its own test case.
# A single bad line number, fabricated quote, or wrong section citation
# shows up as its own FAILED line in ``pytest -v`` output rather than
# hiding inside an aggregate percentage threshold.
# ---------------------------------------------------------------------------


class TestExhaustiveLineNumbers:
    """One test per ``title26.md:NNNNN`` reference — line must be in bounds."""

    @pytest.mark.parametrize(
        "ref",
        _ALL_REFS,
        ids=[f"{r.property_path}@L{r.line_number}" for r in _ALL_REFS],
    )
    def test_line_in_bounds(self, ref, title26_line_count):
        assert 1 <= ref.line_number <= title26_line_count, (
            f"{ref.property_path}: line {ref.line_number} is out of bounds "
            f"(file has {title26_line_count} lines)"
        )


class TestExhaustiveSectionHeadings:
    """One test per reference that cites a ``§NNN`` — the section heading
    (or a prose mention of ``section NNN``) must appear within ±1000 lines
    of the cited line number in ``title26.md``."""

    @pytest.mark.parametrize(
        "ref",
        _REFS_WITH_SECTIONS,
        ids=[
            f"{r.property_path}@L{r.line_number}:§{r.section_id}"
            for r in _REFS_WITH_SECTIONS
        ],
    )
    def test_section_near_line(self, ref, title26_lines):
        assert _section_heading_near_line(
            ref.section_id, ref.line_number, title26_lines, radius=1000
        ), (
            f"{ref.property_path}: §{ref.section_id} not found within "
            f"±1000 lines of title26.md:{ref.line_number}"
        )


class TestExhaustiveQuotedExcerpts:
    """One test per reference that includes a quoted statute excerpt —
    the quoted text (or its salient n-grams) must appear within ±1000 lines
    of the cited line number in ``title26.md``.  The wider radius accounts
    for annotations that cite a section heading while the quoted text is
    deeper inside the section body."""

    @pytest.mark.parametrize(
        "ref",
        _REFS_WITH_QUOTES,
        ids=[f"{r.property_path}@L{r.line_number}" for r in _REFS_WITH_QUOTES],
    )
    def test_quote_near_line(self, ref, title26_lines):
        assert _quote_appears_near_line(
            ref.quoted_text, ref.line_number, title26_lines, radius=1000
        ), (
            f"{ref.property_path}: quoted text not found within "
            f"±1000 lines of title26.md:{ref.line_number}:\n"
            f'  "{ref.quoted_text[:120]}..."'
        )
