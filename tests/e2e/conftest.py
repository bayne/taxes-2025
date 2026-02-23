"""
Playwright e2e test fixtures for the tax calculator web UI.

Starts the server, configures video recording, and provides helpers
for navigating the wizard and asserting results.
"""

import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER_PORT = 8765
SERVER_URL = f"http://localhost:{SERVER_PORT}"


# ── Server fixture ────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def server():
    """Start the tax calculator server for the duration of the test session."""
    proc = subprocess.Popen(
        [sys.executable, "server.py", str(SERVER_PORT)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{SERVER_URL}/", timeout=2)
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("Server failed to start")

    yield SERVER_URL

    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=5)


# ── Video recording ───────────────────────────────────────────────────────────

VIDEO_DIR = os.path.join(PROJECT_ROOT, "test-results", "videos")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    os.makedirs(VIDEO_DIR, exist_ok=True)
    return {
        **browser_context_args,
        "record_video_dir": VIDEO_DIR,
        "record_video_size": {"width": 1280, "height": 720},
        "viewport": {"width": 1280, "height": 720},
    }


# ── Wizard helper ─────────────────────────────────────────────────────────────


def _default_wizard_state():
    """Return the default wizard state matching app.js defaultState()."""
    return {
        "stepIndex": 99,
        "tax_year": 2025,
        "filing_status": "single",
        "personal_info": {
            "first_name": "Test", "last_name": "User",
            "ssn": "000-00-0000", "date_of_birth": "1990-01-01",
            "is_blind": False, "occupation": "",
        },
        "spouse_info": {
            "first_name": "", "last_name": "",
            "ssn": "", "date_of_birth": "",
            "is_blind": False, "occupation": "",
        },
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "hasDependents": False,
        "dependents": [],
        "incomeTypes": {
            "w2": False, "interest": False, "dividends": False,
            "capitalGains": False, "business": False, "rental": False,
            "retirement": False, "socialSecurity": False,
            "unemployment": False, "other": False,
        },
        "w2_income": [],
        "interest_income": [],
        "dividend_income": [],
        "capital_gains_losses": [],
        "business_income": [],
        "rental_income": [],
        "retirement_distributions": [],
        "social_security": {"total_benefits": 0},
        "unemployment": {"amount": 0},
        "other_income": [],
        "educator_expenses": 0,
        "student_loan_interest_paid": 0,
        "hasHSA": False,
        "hsa": {
            "is_self_only_coverage": True, "taxpayer_contributions": 0,
            "employer_contributions": 0, "distributions": 0,
            "qualified_medical_expenses_from_hsa": 0,
        },
        "deduction_method": "standard",
        "medical_expenses": {
            "total_medical_dental": 0, "health_insurance_premiums": 0,
            "prescription_drugs": 0, "medical_travel": 0,
        },
        "state_local_taxes": {
            "state_income_tax_paid": 0, "real_property_tax": 0,
            "personal_property_tax": 0,
        },
        "mortgage_interest": [],
        "charitable_contributions": [],
        "hasEducationCredits": False,
        "education_expenses": [],
        "hasChildCare": False,
        "child_care_expenses": [],
        "estimated_tax_payments": {
            "q1_amount": 0, "q2_amount": 0, "q3_amount": 0, "q4_amount": 0,
        },
        "prior_year_agi": 0,
        "prior_year_tax": 0,
        "results": None,
        "errors": None,
        "calculating": False,
    }


def wizard_state(
    filing_status="single",
    personal_info=None,
    spouse_info=None,
    dependents=None,
    income_types=None,
    w2_income=None,
    interest_income=None,
    dividend_income=None,
    capital_gains_losses=None,
    business_income=None,
    rental_income=None,
    retirement_distributions=None,
    social_security=None,
    unemployment=None,
    other_income=None,
    student_loan_interest_paid=0,
    educator_expenses=0,
    hsa=None,
    deduction_method="standard",
    medical_expenses=None,
    state_local_taxes=None,
    mortgage_interest=None,
    charitable_contributions=None,
    education_expenses=None,
    child_care_expenses=None,
    estimated_tax_payments=None,
    **_extra,
):
    """Build a wizard state dict for localStorage injection."""
    s = _default_wizard_state()
    s["filing_status"] = filing_status
    if personal_info:
        s["personal_info"].update(personal_info)
    if spouse_info:
        s["spouse_info"].update(spouse_info)
    if dependents:
        s["hasDependents"] = True
        s["dependents"] = dependents
    if income_types:
        s["incomeTypes"].update(income_types)
    if w2_income is not None:
        s["w2_income"] = w2_income
    if interest_income is not None:
        s["interest_income"] = interest_income
    if dividend_income is not None:
        s["dividend_income"] = dividend_income
    if capital_gains_losses is not None:
        s["capital_gains_losses"] = capital_gains_losses
    if business_income is not None:
        s["business_income"] = business_income
    if rental_income is not None:
        s["rental_income"] = rental_income
    if retirement_distributions is not None:
        s["retirement_distributions"] = retirement_distributions
    if social_security is not None:
        s["social_security"] = social_security
    if unemployment is not None:
        s["unemployment"] = unemployment
    if other_income is not None:
        s["other_income"] = other_income
    s["student_loan_interest_paid"] = student_loan_interest_paid
    s["educator_expenses"] = educator_expenses
    if hsa:
        s["hasHSA"] = True
        s["hsa"].update(hsa)
    s["deduction_method"] = deduction_method
    if medical_expenses:
        s["medical_expenses"].update(medical_expenses)
    if state_local_taxes:
        s["state_local_taxes"].update(state_local_taxes)
    if mortgage_interest is not None:
        s["mortgage_interest"] = mortgage_interest
    if charitable_contributions is not None:
        s["charitable_contributions"] = charitable_contributions
    if education_expenses is not None:
        s["hasEducationCredits"] = True
        s["education_expenses"] = education_expenses
    if child_care_expenses is not None:
        s["hasChildCare"] = True
        s["child_care_expenses"] = child_care_expenses
    if estimated_tax_payments:
        s["estimated_tax_payments"].update(estimated_tax_payments)
    return s


def person(first, last, ssn="000-00-0000", dob="1990-01-01"):
    return {"first_name": first, "last_name": last, "ssn": ssn, "date_of_birth": dob}


def w2(employer, ein, wages, withheld, **kw):
    return {"employer_name": employer, "employer_ein": ein,
            "wages": wages, "federal_income_tax_withheld": withheld, **kw}


def dependent(first, last, ssn, dob, relationship="qualifying_child", months=12):
    return {"first_name": first, "last_name": last, "ssn": ssn,
            "date_of_birth": dob, "relationship": relationship,
            "months_lived_with_taxpayer": months}


# ── Wizard flow helper ────────────────────────────────────────────────────────


class Wizard:
    """Navigate the tax wizard step-by-step, filling in forms."""

    def __init__(self, page, base_url):
        self.page = page
        self.base_url = base_url

    def start(self):
        """Open the app with a fresh state."""
        self.page.goto(self.base_url)
        self.page.evaluate("([]) => localStorage.removeItem('tax-wizard-state')", [])
        self.page.reload()
        self.page.locator("h2").first.wait_for(timeout=15000)

    def next(self):
        """Click Continue and wait for the transition."""
        self.page.get_by_role("button", name="Continue").click()
        self.page.wait_for_timeout(400)

    def fill(self, label, value, nth=0):
        """Fill a text or number input by its label."""
        field = self.page.locator(".field").filter(
            has=self.page.locator(f"label:has-text('{label}')")
        ).nth(nth)
        inp = field.locator("input").first
        inp.fill(str(value))

    def fill_in_card(self, card_index, label, value):
        """Fill a field inside the nth .item-card."""
        card = self.page.locator(".item-card").nth(card_index)
        field = card.locator(".field").filter(
            has=self.page.locator(f"label:has-text('{label}')")
        ).first
        field.locator("input").first.fill(str(value))

    def select(self, label, value, nth=0):
        """Select a dropdown option by label."""
        field = self.page.locator(".field").filter(
            has=self.page.locator(f"label:has-text('{label}')")
        ).nth(nth)
        field.locator("select").select_option(value)

    def select_in_card(self, card_index, label, value):
        """Select a dropdown inside the nth .item-card."""
        card = self.page.locator(".item-card").nth(card_index)
        field = card.locator(".field").filter(
            has=self.page.locator(f"label:has-text('{label}')")
        ).first
        field.locator("select").select_option(value)

    def toggle(self, label_text, on=True):
        """Toggle a switch. Clicks the slider if state doesn't match."""
        row = self.page.locator(".toggle-row").filter(has_text=label_text).first
        cb = row.locator("input[type='checkbox']")
        if cb.is_checked() != on:
            row.locator(".toggle-slider").click()

    def select_filing_status(self, status):
        """Select a filing status radio button."""
        self.page.locator(f"input[value='{status}']").click()

    def select_radio(self, value):
        """Select any radio button by value."""
        self.page.locator(f"input[value='{value}']").click()

    def check_income(self, label_text):
        """Check an income-type checkbox."""
        option = self.page.locator(".check-option").filter(has_text=label_text).first
        option.locator("input[type='checkbox']").check(force=True)

    def click_add(self, text="Add"):
        """Click an '+ Add ...' button."""
        self.page.locator(".add-btn").filter(has_text=text).first.click()
        self.page.wait_for_timeout(300)

    def calculate(self):
        """Click Calculate and wait for results."""
        self.page.get_by_role("button", name="Calculate My Tax").click()
        self.page.wait_for_selector(".refund-banner", timeout=30000)
        self.page.wait_for_timeout(1000)

    def results(self):
        """Return raw results JSON from localStorage."""
        return self.page.evaluate(
            "JSON.parse(localStorage.getItem('tax-wizard-state'))?.results"
        )


# ── Test runner helpers ───────────────────────────────────────────────────────


def run_scenario(page, server_url, state, payload):
    """
    Navigate to the app, inject wizard state, intercept the API call
    with the full payload, click Calculate, and wait for results.
    """
    page.goto(server_url)
    page.wait_for_selector("h2", timeout=15000)

    # Inject wizard state into localStorage
    state_json = json.dumps(state)
    page.evaluate(
        "([s]) => localStorage.setItem('tax-wizard-state', s)",
        [state_json],
    )
    page.reload()
    page.wait_for_selector("text=Review & Calculate", timeout=10000)

    # Brief pause so video shows the review summary
    page.wait_for_timeout(500)

    # Intercept the API call and replace with our exact payload
    def handle_route(route):
        route.continue_(post_data=json.dumps(payload))

    page.route("**/api/calculate", handle_route)

    # Click Calculate
    page.get_by_role("button", name="Calculate My Tax").click()

    # Wait for results
    page.wait_for_selector(".refund-banner", timeout=30000)

    # Pause so video captures results
    page.wait_for_timeout(1000)


def get_results_json(page):
    """Extract the raw calculation results from the page's app state."""
    return page.evaluate(
        "JSON.parse(localStorage.getItem('tax-wizard-state'))?.results"
    )


# ── Assertion helpers ─────────────────────────────────────────────────────────


def _parse_dollar(text):
    """Parse a dollar string like '$75,000.00' or '-$1,234.56' into a float."""
    if not text:
        return 0.0
    text = text.strip()
    negative = text.startswith("-")
    digits = re.sub(r"[^0-9.]", "", text)
    val = float(digits) if digits else 0.0
    return -val if negative else val


def assert_result(page, label, expected_text):
    """Assert a result row contains the expected text."""
    row = page.locator(f".result-row:has-text('{label}')").last
    actual = row.locator(".amount").text_content()
    assert expected_text in actual, f"{label}: expected '{expected_text}' in '{actual}'"


def assert_result_value(page, label, expected_value, tolerance=1.0):
    """Assert a result row's dollar value equals expected within tolerance."""
    row = page.locator(f".result-row:has-text('{label}')").last
    actual_text = row.locator(".amount").text_content()
    actual = _parse_dollar(actual_text)
    assert abs(actual - expected_value) <= tolerance, (
        f"{label}: expected ${expected_value:,.2f}, got {actual_text} (${actual:,.2f})"
    )


def assert_result_gt(page, label, min_value=0):
    """Assert a result row's dollar value is greater than min_value."""
    row = page.locator(f".result-row:has-text('{label}')").last
    actual_text = row.locator(".amount").text_content()
    actual = _parse_dollar(actual_text)
    assert actual > min_value, f"{label}: expected > ${min_value}, got {actual_text}"


def assert_json_field(results, *path, expected=None, gt=None, eq=None,
                      lt=None, gte=None, contains=None):
    """Assert on a field in the raw results JSON."""
    val = results
    for key in path:
        val = val[key]
    label = ".".join(str(p) for p in path)
    if expected is not None:
        assert abs(val - expected) <= 1.0, f"{label}: expected {expected}, got {val}"
    if eq is not None:
        assert abs(val - eq) <= 1.0, f"{label}: expected {eq}, got {val}"
    if gt is not None:
        assert val > gt, f"{label}: expected > {gt}, got {val}"
    if gte is not None:
        assert val >= gte, f"{label}: expected >= {gte}, got {val}"
    if lt is not None:
        assert val < lt, f"{label}: expected < {lt}, got {val}"
    if contains is not None:
        assert contains.lower() in str(val).lower(), f"{label}: expected '{contains}' in '{val}'"
