"""Single filer with education credits and student loan interest."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field

@pytest.fixture()
def server_url(server):
    return server

def test_education_credits_aotc(page, server_url):
    """Single filer with W-2, student loan interest deduction, and AOTC."""
    pi = person("Jack", "Park", "777-88-9999", "1998-10-05")
    w2s = [w2("StartupCo", "44-4444444", 55000, 5000)]

    state = wizard_state(
        filing_status="single",
        personal_info=pi,
        income_types={"w2": True},
        w2_income=w2s,
        student_loan_interest_paid=2500,
        education_expenses=[
            {
                "student_name": "Jack Park",
                "student_ssn": "777-88-9999",
                "institution_name": "State University",
                "qualified_tuition_and_fees": 4000,
                "credit_type": "aotc",
            },
        ],
    )
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Jack", "last_name": "Park", "ssn": "777-88-9999", "date_of_birth": "1998-10-05"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "StartupCo", "employer_ein": "44-4444444", "wages": 55000, "federal_income_tax_withheld": 5000}],
        "student_loan_interest_paid": 2500,
        "education_expenses": [
            {
                "student_name": "Jack Park",
                "student_ssn": "777-88-9999",
                "institution_name": "State University",
                "qualified_tuition_and_fees": 4000,
                "credit_type": "aotc",
            },
        ],
        "deduction_method": "standard",
    }

    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)

    assert_json_field(r, "income", "total_wages", expected=55000)
    assert_json_field(r, "agi", "student_loan_interest_deduction", expected=2500)
    assert_json_field(r, "agi", "agi", expected=52500)
    assert_json_field(r, "credits", "aotc_refundable", expected=1000)
    assert_json_field(r, "credits", "education_credits", expected=1500)
