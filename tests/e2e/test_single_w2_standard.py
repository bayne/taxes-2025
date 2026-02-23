"""Single filer with W-2 income and standard deduction."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field

@pytest.fixture()
def server_url(server):
    return server

def test_single_w2_75k(page, server_url):
    """Single filer with $75,000 W-2 income."""
    pi = person("Alice", "Smith", "111-22-3333", "1990-03-15")
    addr = {"street": "100 Main St", "city": "Springfield", "state": "IL", "zip_code": "62704"}
    w2s = [w2("Acme Corp", "11-1111111", 75000, 9000)]

    state = wizard_state(
        filing_status="single",
        personal_info=pi,
        income_types={"w2": True},
        w2_income=w2s,
    )
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Alice", "last_name": "Smith", "ssn": "111-22-3333", "date_of_birth": "1990-03-15"},
        "address": addr,
        "w2_income": [{"employer_name": "Acme Corp", "employer_ein": "11-1111111", "wages": 75000, "federal_income_tax_withheld": 9000}],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_wages", expected=75000)
    assert_json_field(r, "income", "gross_income", expected=75000)
    assert_json_field(r, "agi", "agi", expected=75000)
    assert_json_field(r, "deductions", "deduction_method_used", contains="standard")
    assert_json_field(r, "deductions", "deduction_amount", expected=15750)
    assert_json_field(r, "deductions", "taxable_income", expected=59250)
    assert_json_field(r, "marginal_tax_rate", expected=0.22)
