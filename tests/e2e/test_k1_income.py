"""K-1 income scenarios: partnership and S-Corp pass-through income."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, assert_json_field


@pytest.fixture()
def server_url(server):
    return server


def test_partnership_k1(page, server_url):
    """Single filer with K-1 partnership income and guaranteed payments."""
    state = wizard_state(
        filing_status="single",
        personal_info=person("Dana", "Kim", "555-66-7777", "1985-07-22"),
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "single",
        "personal_info": {
            "first_name": "Dana", "last_name": "Kim",
            "ssn": "555-66-7777", "date_of_birth": "1985-07-22",
        },
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "k1_income": [
            {
                "entity_name": "Kim & Associates",
                "entity_type": "partnership",
                "ordinary_business_income": 60000,
                "guaranteed_payments": 40000,
                "self_employment_earnings": 40000,
            },
        ],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_k1_ordinary_income", expected=60000)
    assert_json_field(r, "income", "total_k1_guaranteed_payments", expected=40000)
    assert_json_field(r, "se_tax", "total_se_tax", gt=0)


def test_scorp_k1(page, server_url):
    """MFJ couple with S-Corp K-1 income including capital gains and dividends."""
    state = wizard_state(
        filing_status="married_filing_jointly",
        personal_info=person("Eli", "Park", "666-77-8888", "1978-11-03"),
        spouse_info=person("Mia", "Park", "777-88-9999", "1980-02-14"),
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "married_filing_jointly",
        "personal_info": {
            "first_name": "Eli", "last_name": "Park",
            "ssn": "666-77-8888", "date_of_birth": "1978-11-03",
        },
        "spouse_info": {
            "first_name": "Mia", "last_name": "Park",
            "ssn": "777-88-9999", "date_of_birth": "1980-02-14",
        },
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "k1_income": [
            {
                "entity_name": "Park Holdings",
                "entity_type": "s_corp",
                "ordinary_business_income": 25000,
                "net_long_term_capital_gain": 15000,
                "qualified_dividends": 5000,
            },
        ],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_k1_ordinary_income", expected=25000)
    assert_json_field(r, "income", "net_long_term_capital_gain_loss", gte=15000)
    assert_json_field(r, "income", "total_qualified_dividends", gte=5000)
