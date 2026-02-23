"""Married filing jointly with two W-2s and child tax credits."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, dependent, assert_json_field

@pytest.fixture()
def server_url(server):
    return server

def test_mfj_130k_two_children(page, server_url):
    """MFJ couple with $130,000 combined income and 2 children."""
    state = wizard_state(
        filing_status="married_filing_jointly",
        personal_info=person("Bob", "Johnson", "222-33-4444", "1985-06-20"),
        spouse_info=person("Carol", "Johnson", "333-44-5555", "1987-09-10"),
        income_types={"w2": True},
        w2_income=[
            w2("TechCo", "22-2222222", 80000, 10000),
            w2("RetailCo", "33-3333333", 50000, 5000),
        ],
        dependents=[
            dependent("Emma", "Johnson", "444-55-6666", "2015-04-01"),
            dependent("Liam", "Johnson", "555-66-7777", "2018-11-15"),
        ],
    )
    payload = {
        "tax_year": 2025, "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "Bob", "last_name": "Johnson", "ssn": "222-33-4444", "date_of_birth": "1985-06-20"},
        "spouse_info": {"first_name": "Carol", "last_name": "Johnson", "ssn": "333-44-5555", "date_of_birth": "1987-09-10"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [
            {"employer_name": "TechCo", "employer_ein": "22-2222222", "wages": 80000, "federal_income_tax_withheld": 10000},
            {"employer_name": "RetailCo", "employer_ein": "33-3333333", "wages": 50000, "federal_income_tax_withheld": 5000},
        ],
        "dependents": [
            {"first_name": "Emma", "last_name": "Johnson", "ssn": "444-55-6666", "date_of_birth": "2015-04-01", "relationship": "qualifying_child", "months_lived_with_taxpayer": 12},
            {"first_name": "Liam", "last_name": "Johnson", "ssn": "555-66-7777", "date_of_birth": "2018-11-15", "relationship": "qualifying_child", "months_lived_with_taxpayer": 12},
        ],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_wages", expected=130000)
    assert_json_field(r, "agi", "agi", expected=130000)
    assert_json_field(r, "deductions", "deduction_method_used", contains="standard")
    assert_json_field(r, "deductions", "deduction_amount", expected=31500)
    assert_json_field(r, "credits", "child_tax_credit_nonrefundable", expected=4400)
    assert_json_field(r, "marginal_tax_rate", expected=0.22)
