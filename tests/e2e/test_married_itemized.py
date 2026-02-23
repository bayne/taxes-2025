"""Married filing jointly with itemized deductions (mortgage, SALT, charity)."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field


@pytest.fixture()
def server_url(server):
    return server


def test_mfj_itemized_180k(page, server_url):
    """MFJ couple with $180,000 W-2 income and itemized deductions."""
    state = wizard_state(
        filing_status="married_filing_jointly",
        personal_info=person("George", "Kim", "222-11-3333", "1978-08-22"),
        spouse_info=person("Helen", "Kim", "333-22-4444", "1980-03-14"),
        income_types={"w2": True},
        w2_income=[w2("LawFirm", "55-5555555", 180000, 30000)],
        deduction_method="itemized",
        mortgage_interest=[{"lender_name": "BigBank", "mortgage_interest_paid": 18000}],
        state_local_taxes={"state_income_tax_paid": 12000, "real_property_tax": 8000},
        charitable_contributions=[{"organization_name": "RedCross", "cash_amount": 8000}],
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "married_filing_jointly",
        "personal_info": {
            "first_name": "George", "last_name": "Kim",
            "ssn": "222-11-3333", "date_of_birth": "1978-08-22",
        },
        "spouse_info": {
            "first_name": "Helen", "last_name": "Kim",
            "ssn": "333-22-4444", "date_of_birth": "1980-03-14",
        },
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [
            {
                "employer_name": "LawFirm", "employer_ein": "55-5555555",
                "wages": 180000, "federal_income_tax_withheld": 30000,
            },
        ],
        "deduction_method": "itemized",
        "mortgage_interest": [{"lender_name": "BigBank", "mortgage_interest_paid": 18000}],
        "state_local_taxes": {
            "state_income_tax_paid": 12000,
            "real_property_tax": 8000,
        },
        "charitable_contributions": [{"organization_name": "RedCross", "cash_amount": 8000}],
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_wages", expected=180000)
    assert_json_field(r, "agi", "agi", expected=180000)
    assert_json_field(r, "deductions", "deduction_method_used", contains="itemized")
    assert_json_field(r, "deductions", "salt_deduction", expected=20000)
    assert_json_field(r, "deductions", "total_itemized_deductions", expected=46000)
    assert_json_field(r, "marginal_tax_rate", expected=0.22)
