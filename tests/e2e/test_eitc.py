"""EITC (Earned Income Tax Credit) e2e scenarios."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, dependent, assert_json_field


@pytest.fixture()
def server_url(server):
    return server


def test_eitc_denied_excess_investment(page, server_url):
    """Single filer denied EITC due to excess investment income."""
    state = wizard_state(
        filing_status="single",
        personal_info=person("Nia", "Jones", "000-00-0000", "1990-06-01"),
        income_types={"w2": True},
        w2_income=[w2("RetailCo", "11-1111111", 22000, 1000)],
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "single",
        "personal_info": {"first_name": "Nia", "last_name": "Jones", "ssn": "000-00-0000", "date_of_birth": "1990-06-01"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "RetailCo", "employer_ein": "11-1111111", "wages": 22000, "federal_income_tax_withheld": 1000}],
        "deduction_method": "standard",
        "eitc_eligibility": {
            "investment_income": 15000,
            "has_valid_ssn_for_employment": True,
            "lived_in_us_more_than_half_year": True,
        },
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "credits", "earned_income_credit", eq=0)
    assert_json_field(r, "credits", "eitc_disqualification_reason", contains="investment")


def test_eitc_eligible_one_child(page, server_url):
    """HOH filer with one qualifying child is eligible for EITC."""
    state = wizard_state(
        filing_status="head_of_household",
        personal_info=person("Carlos", "Vega", "000-00-0000", "1988-12-15"),
        income_types={"w2": True},
        w2_income=[w2("ShopCo", "22-2222222", 25000, 1500)],
        dependents=[dependent("Mia", "Vega", "000-00-0000", "2018-03-20")],
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "head_of_household",
        "personal_info": {"first_name": "Carlos", "last_name": "Vega", "ssn": "000-00-0000", "date_of_birth": "1988-12-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "ShopCo", "employer_ein": "22-2222222", "wages": 25000, "federal_income_tax_withheld": 1500}],
        "dependents": [
            {"first_name": "Mia", "last_name": "Vega", "ssn": "000-00-0000", "date_of_birth": "2018-03-20", "relationship": "qualifying_child", "months_lived_with_taxpayer": 12},
        ],
        "deduction_method": "standard",
        "eitc_eligibility": {
            "investment_income": 500,
            "has_valid_ssn_for_employment": True,
            "lived_in_us_more_than_half_year": True,
        },
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "credits", "earned_income_credit", gt=0)
