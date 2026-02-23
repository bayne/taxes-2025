"""Premium Tax Credit (PTC) e2e scenarios."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field


@pytest.fixture()
def server_url(server):
    return server


def test_ptc_with_advance_payments(page, server_url):
    """Single filer with marketplace coverage and advance PTC received."""
    state = wizard_state(
        filing_status="single",
        personal_info=person("Rosa", "Chen", "000-00-0000", "1992-04-10"),
        income_types={"w2": True},
        w2_income=[w2("Cafe LLC", "11-1111111", 32000, 2500)],
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "single",
        "personal_info": {"first_name": "Rosa", "last_name": "Chen", "ssn": "000-00-0000", "date_of_birth": "1992-04-10"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "Cafe LLC", "employer_ein": "11-1111111", "wages": 32000, "federal_income_tax_withheld": 2500}],
        "deduction_method": "standard",
        "marketplace_coverage": {
            "annual_premium": 6000,
            "annual_slcsp_premium": 6500,
            "advance_ptc_received": 3000,
            "household_size": 1,
            "coverage_months": 12,
        },
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "credits", "premium_tax_credit", gt=0)
    assert_json_field(r, "credits", "excess_advance_ptc_repayment", gte=0)


def test_ptc_above_400_fpl(page, server_url):
    """MFJ couple with income above 400% FPL gets no PTC and must repay advance."""
    state = wizard_state(
        filing_status="married_filing_jointly",
        personal_info=person("Tom", "Hall", "000-00-0000", "1980-01-01"),
        spouse_info=person("Sue", "Hall", "000-00-0000", "1982-06-15"),
        income_types={"w2": True},
        w2_income=[w2("BigCo", "22-2222222", 200000, 35000)],
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "Tom", "last_name": "Hall", "ssn": "000-00-0000", "date_of_birth": "1980-01-01"},
        "spouse_info": {"first_name": "Sue", "last_name": "Hall", "ssn": "000-00-0000", "date_of_birth": "1982-06-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "BigCo", "employer_ein": "22-2222222", "wages": 200000, "federal_income_tax_withheld": 35000}],
        "deduction_method": "standard",
        "marketplace_coverage": {
            "annual_premium": 12000,
            "annual_slcsp_premium": 13000,
            "advance_ptc_received": 4000,
            "household_size": 2,
            "coverage_months": 12,
        },
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "credits", "premium_tax_credit", eq=0)
    assert_json_field(r, "credits", "excess_advance_ptc_repayment", eq=4000)
