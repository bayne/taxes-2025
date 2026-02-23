"""Single filer with self-employment / business income."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field

@pytest.fixture()
def server_url(server):
    return server

def test_self_employed_120k(page, server_url):
    """Single filer with $120,000 gross business income and $30,000 expenses."""
    pi = person("Frank", "Lee", "888-99-0000", "1980-05-10")

    state = wizard_state(
        filing_status="single",
        personal_info=pi,
        income_types={"business": True},
        business_income=[
            {
                "business_name": "Lee Consulting",
                "gross_receipts": 120000,
                "advertising": 5000,
                "office_expense": 5000,
                "supplies": 5000,
                "utilities": 5000,
                "other_expenses": 10000,
            },
        ],
    )
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Frank", "last_name": "Lee", "ssn": "888-99-0000", "date_of_birth": "1980-05-10"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "business_income": [
            {
                "business_name": "Lee Consulting",
                "gross_receipts": 120000,
                "advertising": 5000,
                "office_expense": 5000,
                "supplies": 5000,
                "utilities": 5000,
                "other_expenses": 10000,
            },
        ],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_business_income", expected=90000)
    assert_json_field(r, "income", "gross_income", expected=90000)
    assert_json_field(r, "se_tax", "total_se_tax", gt=0)
    assert_json_field(r, "agi", "se_tax_deduction", gt=0)
    assert r["agi"]["agi"] < r["income"]["gross_income"], (
        f"AGI ({r['agi']['agi']}) should be less than gross income ({r['income']['gross_income']})"
    )
    assert_json_field(r, "marginal_tax_rate", expected=0.22)
