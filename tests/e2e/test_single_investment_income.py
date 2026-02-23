"""Single filer with W-2 income plus interest, dividends, and capital gains."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field

@pytest.fixture()
def server_url(server):
    return server

def test_single_investment_income(page, server_url):
    """Single filer with $70,000 W-2 plus interest, dividends, and LTCG."""
    pi = person("Eve", "Chen", "666-77-8888", "1982-12-01")
    w2s = [w2("Acme Corp", "11-1111111", 70000, 8000)]

    state = wizard_state(
        filing_status="single",
        personal_info=pi,
        income_types={"w2": True, "interest": True, "dividends": True, "capitalGains": True},
        w2_income=w2s,
        interest_income=[
            {"payer_name": "Bank of America", "amount": 2000},
        ],
        dividend_income=[
            {"payer_name": "Vanguard", "ordinary_dividends": 3000, "qualified_dividends": 2500},
        ],
        capital_gains_losses=[
            {"description": "Stock Sale", "date_acquired": "2020-01-15",
             "date_sold": "2025-06-01", "proceeds": 15000, "cost_basis": 10000,
             "term": "long_term"},
        ],
    )
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Eve", "last_name": "Chen", "ssn": "666-77-8888", "date_of_birth": "1982-12-01"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "Acme Corp", "employer_ein": "11-1111111", "wages": 70000, "federal_income_tax_withheld": 8000}],
        "interest_income": [{"payer_name": "Bank of America", "amount": 2000}],
        "dividend_income": [{"payer_name": "Vanguard", "ordinary_dividends": 3000, "qualified_dividends": 2500}],
        "capital_gains_losses": [
            {"description": "Stock Sale", "date_acquired": "2020-01-15",
             "date_sold": "2025-06-01", "proceeds": 15000, "cost_basis": 10000,
             "term": "long_term"},
        ],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_wages", expected=70000)
    assert_json_field(r, "income", "gross_income", expected=80000)
    assert_json_field(r, "deductions", "deduction_method_used", contains="standard")
    assert_json_field(r, "tax", "capital_gains_tax_at_15_pct", gt=0)
    assert_json_field(r, "marginal_tax_rate", expected=0.22)
