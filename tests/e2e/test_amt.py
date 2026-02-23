"""Alternative Minimum Tax (AMT) scenarios: ISO exercise and high earner."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field


@pytest.fixture()
def server_url(server):
    return server


def test_iso_triggers_amt(page, server_url):
    """Single filer with large ISO exercise spread triggering AMT."""
    state = wizard_state(
        filing_status="single",
        personal_info=person("Ava", "Reyes", "888-99-0000", "1983-09-20"),
        income_types={"w2": True},
        w2_income=[w2("TechCo", "66-6666666", 200000, 40000)],
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "single",
        "personal_info": {
            "first_name": "Ava", "last_name": "Reyes",
            "ssn": "888-99-0000", "date_of_birth": "1983-09-20",
        },
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [
            {
                "employer_name": "TechCo", "employer_ein": "66-6666666",
                "wages": 200000, "federal_income_tax_withheld": 40000,
            },
        ],
        "amt_preferences": {"iso_exercise_spread": 300000},
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "tax", "amti", gt=r["deductions"]["taxable_income"])
    assert_json_field(r, "tax", "amt", gt=0)


def test_high_earner_no_amt(page, server_url):
    """MFJ high earner with no AMT preferences should owe zero AMT."""
    state = wizard_state(
        filing_status="married_filing_jointly",
        personal_info=person("Ben", "Cruz", "999-00-1111", "1975-03-01"),
        spouse_info=person("Liz", "Cruz", "000-11-2222", "1977-08-10"),
        income_types={"w2": True},
        w2_income=[w2("FinCorp", "77-7777777", 350000, 70000)],
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "married_filing_jointly",
        "personal_info": {
            "first_name": "Ben", "last_name": "Cruz",
            "ssn": "999-00-1111", "date_of_birth": "1975-03-01",
        },
        "spouse_info": {
            "first_name": "Liz", "last_name": "Cruz",
            "ssn": "000-11-2222", "date_of_birth": "1977-08-10",
        },
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [
            {
                "employer_name": "FinCorp", "employer_ein": "77-7777777",
                "wages": 350000, "federal_income_tax_withheld": 70000,
            },
        ],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "tax", "amt", eq=0)
