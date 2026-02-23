"""Married filing jointly with HSA contributions."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field

@pytest.fixture()
def server_url(server):
    return server

def test_married_hsa_family(page, server_url):
    """MFJ couple with $150,000 W-2 income and family HSA contributions."""
    pi = person("Kevin", "Nguyen", "111-22-3333", "1983-01-30")
    sp = person("Linda", "Nguyen", "222-33-4444", "1985-07-18")
    w2s = [w2("HealthCo", "55-5555555", 150000, 20000)]

    state = wizard_state(
        filing_status="married_filing_jointly",
        personal_info=pi,
        spouse_info=sp,
        income_types={"w2": True},
        w2_income=w2s,
        hsa={
            "taxpayer_contributions": 7000,
            "employer_contributions": 0,
            "is_self_only_coverage": False,
        },
    )
    payload = {
        "tax_year": 2025, "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "Kevin", "last_name": "Nguyen", "ssn": "111-22-3333", "date_of_birth": "1983-01-30"},
        "spouse_info": {"first_name": "Linda", "last_name": "Nguyen", "ssn": "222-33-4444", "date_of_birth": "1985-07-18"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "HealthCo", "employer_ein": "55-5555555", "wages": 150000, "federal_income_tax_withheld": 20000}],
        "hsa": {
            "taxpayer_contributions": 7000,
            "employer_contributions": 0,
            "is_self_only_coverage": False,
        },
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_wages", expected=150000)
    assert_json_field(r, "agi", "hsa_deduction", expected=7000)
    assert_json_field(r, "agi", "agi", expected=143000)
    assert_json_field(r, "deductions", "deduction_method_used", contains="standard")
    assert_json_field(r, "deductions", "deduction_amount", expected=31500)
