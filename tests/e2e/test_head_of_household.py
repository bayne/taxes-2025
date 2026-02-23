"""Head of household filer with one child."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, dependent, assert_json_field

@pytest.fixture()
def server_url(server):
    return server

def test_hoh_55k_one_child(page, server_url):
    """HOH filer with $55,000 income and one child."""
    state = wizard_state(
        filing_status="head_of_household",
        personal_info=person("Diana", "Ross", "111-11-1111", "1988-02-28"),
        income_types={"w2": True},
        w2_income=[w2("ServiceCo", "44-4444444", 55000, 5500)],
        dependents=[dependent("Maya", "Ross", "666-77-8888", "2016-07-12")],
    )
    payload = {
        "tax_year": 2025, "filing_status": "head_of_household",
        "personal_info": {"first_name": "Diana", "last_name": "Ross", "ssn": "111-11-1111", "date_of_birth": "1988-02-28"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "ServiceCo", "employer_ein": "44-4444444", "wages": 55000, "federal_income_tax_withheld": 5500}],
        "dependents": [{"first_name": "Maya", "last_name": "Ross", "ssn": "666-77-8888", "date_of_birth": "2016-07-12", "relationship": "qualifying_child", "months_lived_with_taxpayer": 12}],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_wages", expected=55000)
    assert_json_field(r, "agi", "agi", expected=55000)
    assert_json_field(r, "deductions", "deduction_method_used", contains="standard")
    assert_json_field(r, "deductions", "deduction_amount", expected=23625)
    assert_json_field(r, "credits", "child_tax_credit_nonrefundable", expected=2200)
    assert_json_field(r, "marginal_tax_rate", expected=0.12)
