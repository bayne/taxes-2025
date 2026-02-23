"""Single retiree with Social Security and pension income."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, assert_json_field


@pytest.fixture()
def server_url(server):
    return server


def test_single_retiree_ss_pension(page, server_url):
    """Single filer age 68 with Social Security benefits and pension distribution."""
    state = wizard_state(
        filing_status="single",
        personal_info=person("Irene", "Walsh", "444-55-6666", "1957-04-20"),
        income_types={"socialSecurity": True, "retirement": True},
        social_security={"total_benefits": 24000},
        retirement_distributions=[
            {
                "payer_name": "StatePension",
                "gross_distribution": 30000,
                "taxable_amount": 30000,
                "federal_income_tax_withheld": 3000,
            },
        ],
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "single",
        "personal_info": {
            "first_name": "Irene", "last_name": "Walsh",
            "ssn": "444-55-6666", "date_of_birth": "1957-04-20",
        },
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "social_security": {"total_benefits": 24000},
        "retirement_distributions": [
            {
                "payer_name": "StatePension",
                "gross_distribution": 30000,
                "taxable_amount": 30000,
                "federal_income_tax_withheld": 3000,
            },
        ],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "taxable_social_security", expected=15300)
    assert_json_field(r, "income", "gross_income", expected=45300)
    assert_json_field(r, "deductions", "total_standard_deduction", expected=17750)
    assert_json_field(r, "deductions", "senior_deduction", expected=6000)
    assert_json_field(r, "marginal_tax_rate", expected=0.12)
