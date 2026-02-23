"""New income types and credits: adoption, elderly/disabled, royalties, farm, alimony, gambling, annuity, scholarship."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field


@pytest.fixture()
def server_url(server):
    return server


# TASK-005: Adoption Credit
def test_adoption_special_needs(page, server_url):
    """Special-needs adoption deemed max expense."""
    state = wizard_state(filing_status="married_filing_jointly",
        personal_info=person("Jay", "Lin", "000-00-0000", "1980-01-10"),
        spouse_info=person("Wei", "Lin", "000-00-0000", "1982-05-20"),
        income_types={"w2": True}, w2_income=[w2("TechCo", "11-1111111", 100000, 15000)])
    payload = {
        "tax_year": 2025, "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "Jay", "last_name": "Lin", "ssn": "000-00-0000", "date_of_birth": "1980-01-10"},
        "spouse_info": {"first_name": "Wei", "last_name": "Lin", "ssn": "000-00-0000", "date_of_birth": "1982-05-20"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "TechCo", "employer_ein": "11-1111111", "wages": 100000, "federal_income_tax_withheld": 15000}],
        "adoption_expenses": [{"child_name": "Hope Lin", "is_special_needs": True, "qualified_expenses": 0, "year_expenses_paid": 2025, "adoption_finalized_year": 2025}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    # Special needs deemed to max ($17,280)
    total_adoption = r["credits"]["adoption_credit_nonrefundable"] + r["credits"]["adoption_credit_refundable"]
    assert total_adoption > 0
    assert r["credits"]["adoption_credit_refundable"] <= 5000


def test_adoption_high_income_phaseout(page, server_url):
    """High income phases out adoption credit completely."""
    state = wizard_state(filing_status="married_filing_jointly",
        personal_info=person("Sam", "Yi", "000-00-0000", "1975-03-01"),
        spouse_info=person("Pat", "Yi", "000-00-0000", "1977-09-15"),
        income_types={"w2": True}, w2_income=[w2("BigLaw", "22-2222222", 320000, 70000)])
    payload = {
        "tax_year": 2025, "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "Sam", "last_name": "Yi", "ssn": "000-00-0000", "date_of_birth": "1975-03-01"},
        "spouse_info": {"first_name": "Pat", "last_name": "Yi", "ssn": "000-00-0000", "date_of_birth": "1977-09-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "BigLaw", "employer_ein": "22-2222222", "wages": 320000, "federal_income_tax_withheld": 70000}],
        "adoption_expenses": [{"child_name": "Max Yi", "qualified_expenses": 20000, "year_expenses_paid": 2025, "adoption_finalized_year": 2025}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    total = r["credits"]["adoption_credit_nonrefundable"] + r["credits"]["adoption_credit_refundable"]
    assert total == 0


# TASK-006: Elderly/Disabled
def test_elderly_disabled_qualifies(page, server_url):
    """Age 67 single filer with low income qualifies."""
    state = wizard_state(filing_status="single",
        personal_info=person("Ruth", "Adams", "000-00-0000", "1958-02-28"),
        income_types={"retirement": True},
        retirement_distributions=[{"payer_name": "Pension", "gross_distribution": 10000, "taxable_amount": 10000, "federal_income_tax_withheld": 800}])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Ruth", "last_name": "Adams", "ssn": "000-00-0000", "date_of_birth": "1958-02-28"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "retirement_distributions": [{"payer_name": "Pension", "gross_distribution": 10000, "taxable_amount": 10000, "federal_income_tax_withheld": 800}],
        "elderly_disabled_info": {"nontaxable_social_security": 2000},
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "credits", "elderly_disabled_credit", gt=0)


def test_elderly_disabled_high_agi(page, server_url):
    """High AGI phases out elderly/disabled credit."""
    state = wizard_state(filing_status="single",
        personal_info=person("Gene", "Black", "000-00-0000", "1955-05-10"),
        income_types={"w2": True}, w2_income=[w2("Consulting", "33-3333333", 80000, 12000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Gene", "last_name": "Black", "ssn": "000-00-0000", "date_of_birth": "1955-05-10"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "Consulting", "employer_ein": "33-3333333", "wages": 80000, "federal_income_tax_withheld": 12000}],
        "elderly_disabled_info": {"nontaxable_social_security": 0},
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "credits", "elderly_disabled_credit", eq=0)


# TASK-007: Royalty Income
def test_royalty_book(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Ian", "Cole", "000-00-0000", "1970-08-12"))
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Ian", "last_name": "Cole", "ssn": "000-00-0000", "date_of_birth": "1970-08-12"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "royalty_income": [{"description": "Book royalties", "payer_name": "Publisher Inc", "gross_royalties": 30000, "expenses": 5000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "total_royalty_income", expected=25000)
    assert_json_field(r, "income", "gross_income", gte=25000)


def test_royalty_oil_gas_se(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Jill", "Ford", "000-00-0000", "1965-04-30"))
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Jill", "last_name": "Ford", "ssn": "000-00-0000", "date_of_birth": "1965-04-30"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "royalty_income": [{"description": "Oil and gas", "payer_name": "Energy Co", "gross_royalties": 50000, "expenses": 10000, "is_subject_to_se_tax": True}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "se_tax", "total_se_tax", gt=0)


# TASK-008: Farm Income
def test_farm_profitable(page, server_url):
    state = wizard_state(filing_status="married_filing_jointly",
        personal_info=person("John", "Deere", "000-00-0000", "1970-03-15"),
        spouse_info=person("Jane", "Deere", "000-00-0000", "1972-07-20"))
    payload = {
        "tax_year": 2025, "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "John", "last_name": "Deere", "ssn": "000-00-0000", "date_of_birth": "1970-03-15"},
        "spouse_info": {"first_name": "Jane", "last_name": "Deere", "ssn": "000-00-0000", "date_of_birth": "1972-07-20"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "farm_income": [{"farm_name": "Deere Ranch", "gross_farm_income": 200000, "feed": 40000, "seeds_plants": 20000, "fertilizers": 15000, "labor_hired": 30000, "repairs_maintenance": 15000, "utilities": 10000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "total_farm_income", expected=70000)
    assert_json_field(r, "se_tax", "total_se_tax", gt=0)


def test_farm_loss(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Hank", "Till", "000-00-0000", "1968-11-05"))
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Hank", "last_name": "Till", "ssn": "000-00-0000", "date_of_birth": "1968-11-05"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "farm_income": [{"farm_name": "Till Farm", "gross_farm_income": 40000, "feed": 25000, "seeds_plants": 15000, "labor_hired": 15000, "repairs_maintenance": 10000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "total_farm_income", expected=-25000)
    assert r["income"]["farm_nol_carryback_eligible"] is True


# TASK-009: Alimony
def test_alimony_pre_2019(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Amy", "Ross", "000-00-0000", "1975-06-01"))
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Amy", "last_name": "Ross", "ssn": "000-00-0000", "date_of_birth": "1975-06-01"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "alimony_received": 24000, "alimony_instrument_date": "2017-06-15",
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "alimony_income", expected=24000)


def test_alimony_post_2018(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Bob", "Stone", "000-00-0000", "1980-09-10"))
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Bob", "last_name": "Stone", "ssn": "000-00-0000", "date_of_birth": "1980-09-10"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "alimony_received": 30000, "alimony_instrument_date": "2020-03-01",
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "alimony_income", eq=0)


# TASK-010: Gambling
def test_gambling_itemized(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Lucky", "Lou", "000-00-0000", "1982-01-20"),
        income_types={"w2": True}, w2_income=[w2("DayCo", "44-4444444", 60000, 8000)],
        deduction_method="itemized", mortgage_interest=[{"lender_name": "Lender", "mortgage_interest_paid": 15000}])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Lucky", "last_name": "Lou", "ssn": "000-00-0000", "date_of_birth": "1982-01-20"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "DayCo", "employer_ein": "44-4444444", "wages": 60000, "federal_income_tax_withheld": 8000}],
        "gambling": {"w2g_winnings": 10000, "losses": 18000},
        "deduction_method": "itemized",
        "mortgage_interest": [{"lender_name": "Lender", "mortgage_interest_paid": 15000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "gambling_income", expected=10000)
    assert r["deductions"]["gambling_loss_deduction"] <= 10000


def test_gambling_standard(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Pat", "Dice", "000-00-0000", "1990-05-05"),
        income_types={"w2": True}, w2_income=[w2("ShopCo", "55-5555555", 45000, 5000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Pat", "last_name": "Dice", "ssn": "000-00-0000", "date_of_birth": "1990-05-05"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "ShopCo", "employer_ein": "55-5555555", "wages": 45000, "federal_income_tax_withheld": 5000}],
        "gambling": {"w2g_winnings": 3000, "losses": 2500},
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "gambling_income", expected=3000)
    assert_json_field(r, "deductions", "gambling_loss_deduction", eq=0)


# TASK-011: Annuity
def test_annuity_exclusion_ratio(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Vera", "Long", "000-00-0000", "1955-08-15"))
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Vera", "last_name": "Long", "ssn": "000-00-0000", "date_of_birth": "1955-08-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "annuity_income": [{"payer_name": "InsureCo", "gross_payment": 12000, "investment_in_contract": 60000, "expected_return": 180000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "annuity_taxable_amount", expected=8000)


def test_annuity_simplified_method(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Walt", "Grey", "000-00-0000", "1957-03-22"))
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Walt", "last_name": "Grey", "ssn": "000-00-0000", "date_of_birth": "1957-03-22"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "annuity_income": [{"payer_name": "EmployerPlan", "contract_type": "employer_plan", "gross_payment": 24000, "investment_in_contract": 72000, "use_simplified_method": True, "annuitant_age_at_start": 66}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "annuity_taxable_amount", lt=24000)


# TASK-012: Scholarship
def test_scholarship_room_board(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Zoe", "Nash", "000-00-0000", "2003-07-14"))
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Zoe", "last_name": "Nash", "ssn": "000-00-0000", "date_of_birth": "2003-07-14"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "scholarship_income": [{"institution_name": "State U", "total_scholarship": 25000, "qualified_tuition_and_fees": 18000, "room_board_stipend": 7000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "taxable_scholarship_income", expected=7000)


def test_scholarship_fully_qualified(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Leo", "Park", "000-00-0000", "2004-01-25"))
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Leo", "last_name": "Park", "ssn": "000-00-0000", "date_of_birth": "2004-01-25"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "scholarship_income": [{"institution_name": "State U", "total_scholarship": 15000, "qualified_tuition_and_fees": 15000, "room_board_stipend": 0}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "taxable_scholarship_income", eq=0)
