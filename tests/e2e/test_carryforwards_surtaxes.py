"""Carryforwards, surtaxes, and advanced tax situations (TASKs 013-025)."""
import pytest
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field


@pytest.fixture()
def server_url(server):
    return server


# TASK-013: NOL Carryforward
def test_nol_80pct_limit(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Owen", "Blake", "000-00-0000", "1978-10-10"),
        income_types={"w2": True}, w2_income=[w2("WidgetCo", "11-1111111", 100000, 15000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Owen", "last_name": "Blake", "ssn": "000-00-0000", "date_of_birth": "1978-10-10"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "WidgetCo", "employer_ein": "11-1111111", "wages": 100000, "federal_income_tax_withheld": 15000}],
        "nol_carryforward": 200000,
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "deductions", "nol_deduction", gt=0)
    assert_json_field(r, "deductions", "nol_carryforward_remaining", gt=0)


def test_nol_fully_absorbed(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Ivy", "Dunn", "000-00-0000", "1985-04-20"),
        income_types={"w2": True}, w2_income=[w2("BigCo", "22-2222222", 80000, 10000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Ivy", "last_name": "Dunn", "ssn": "000-00-0000", "date_of_birth": "1985-04-20"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "BigCo", "employer_ein": "22-2222222", "wages": 80000, "federal_income_tax_withheld": 10000}],
        "nol_carryforward": 5000,
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "deductions", "nol_deduction", expected=5000)
    assert_json_field(r, "deductions", "nol_carryforward_remaining", eq=0)


# TASK-014: Charitable Carryforward
def test_charitable_carryforward(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Faye", "Gold", "000-00-0000", "1972-09-01"),
        income_types={"w2": True}, w2_income=[w2("MainCo", "33-3333333", 100000, 15000)],
        deduction_method="itemized",
        charitable_contributions=[{"organization_name": "Charity", "cash_amount": 10000}],
        state_local_taxes={"state_income_tax_paid": 8000, "real_property_tax": 5000})
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Faye", "last_name": "Gold", "ssn": "000-00-0000", "date_of_birth": "1972-09-01"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "MainCo", "employer_ein": "33-3333333", "wages": 100000, "federal_income_tax_withheld": 15000}],
        "deduction_method": "itemized",
        "charitable_contributions": [{"organization_name": "Charity", "cash_amount": 10000}],
        "charitable_contribution_carryforward": 30000,
        "state_local_taxes": {"state_income_tax_paid": 8000, "real_property_tax": 5000},
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "deductions", "charitable_deduction", gt=10000)
    assert r["deductions"]["charitable_deduction"] <= 100000 * 0.5 + 1


def test_charitable_no_carryforward(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Greg", "Hale", "000-00-0000", "1980-03-10"),
        income_types={"w2": True}, w2_income=[w2("DevCo", "44-4444444", 80000, 10000)],
        deduction_method="itemized",
        charitable_contributions=[{"organization_name": "Shelter", "cash_amount": 5000}],
        mortgage_interest=[{"lender_name": "Bank", "mortgage_interest_paid": 12000}])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Greg", "last_name": "Hale", "ssn": "000-00-0000", "date_of_birth": "1980-03-10"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "DevCo", "employer_ein": "44-4444444", "wages": 80000, "federal_income_tax_withheld": 10000}],
        "deduction_method": "itemized",
        "charitable_contributions": [{"organization_name": "Shelter", "cash_amount": 5000}],
        "mortgage_interest": [{"lender_name": "Bank", "mortgage_interest_paid": 12000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "deductions", "charitable_carryforward_remaining", eq=0)


# TASK-015: Energy Credit Carryforward
def test_energy_credit_carryforward(page, server_url):
    state = wizard_state(filing_status="married_filing_jointly",
        personal_info=person("Kai", "Moon", "000-00-0000", "1975-06-01"),
        spouse_info=person("Lee", "Moon", "000-00-0000", "1978-02-14"),
        income_types={"w2": True}, w2_income=[w2("SolarCo", "55-5555555", 90000, 12000)])
    payload = {
        "tax_year": 2025, "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "Kai", "last_name": "Moon", "ssn": "000-00-0000", "date_of_birth": "1975-06-01"},
        "spouse_info": {"first_name": "Lee", "last_name": "Moon", "ssn": "000-00-0000", "date_of_birth": "1978-02-14"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "SolarCo", "employer_ein": "55-5555555", "wages": 90000, "federal_income_tax_withheld": 12000}],
        "energy_credit_carryforward": 3000,
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "credits", "energy_credit_carryforward_used", gt=0)


def test_energy_credit_current_year(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Ren", "Sage", "000-00-0000", "1988-12-01"),
        income_types={"w2": True}, w2_income=[w2("GreenCo", "66-6666666", 70000, 9000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Ren", "last_name": "Sage", "ssn": "000-00-0000", "date_of_birth": "1988-12-01"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "GreenCo", "employer_ein": "66-6666666", "wages": 70000, "federal_income_tax_withheld": 9000}],
        "energy_credits": {"solar_electric_expenditures": 20000},
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "credits", "residential_clean_energy_credit", expected=6000)


# TASK-016: Capital Loss Carryforward
def test_capital_loss_st_carryforward(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Nora", "Falk", "000-00-0000", "1980-07-07"),
        income_types={"w2": True, "capitalGains": True},
        w2_income=[w2("TradeCo", "77-7777777", 60000, 8000)],
        capital_gains_losses=[{"description": "STCG", "date_acquired": "2025-01-01", "date_sold": "2025-06-01", "proceeds": 8000, "cost_basis": 3000, "term": "short_term"}])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Nora", "last_name": "Falk", "ssn": "000-00-0000", "date_of_birth": "1980-07-07"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "TradeCo", "employer_ein": "77-7777777", "wages": 60000, "federal_income_tax_withheld": 8000}],
        "capital_gains_losses": [{"description": "STCG", "date_acquired": "2025-01-01", "date_sold": "2025-06-01", "proceeds": 8000, "cost_basis": 3000, "term": "short_term"}],
        "capital_loss_carryforward_short_term": 4000,
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "net_short_term_capital_gain_loss", expected=1000)
    assert_json_field(r, "income", "capital_loss_carryforward_remaining_short", eq=0)


def test_capital_loss_lt_carryforward(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Omar", "Kent", "000-00-0000", "1977-02-18"),
        income_types={"w2": True}, w2_income=[w2("OfficeCo", "88-8888888", 50000, 6000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Omar", "last_name": "Kent", "ssn": "000-00-0000", "date_of_birth": "1977-02-18"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "OfficeCo", "employer_ein": "88-8888888", "wages": 50000, "federal_income_tax_withheld": 6000}],
        "capital_loss_carryforward_long_term": 10000,
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "net_capital_gain_loss", expected=-3000)
    assert_json_field(r, "income", "capital_loss_carryforward_remaining_long", expected=7000)


# TASK-017: Kiddie Tax
def test_kiddie_tax_investment(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Lily", "Grant", "000-00-0000", "2012-05-10"),
        income_types={"interest": True}, interest_income=[{"payer_name": "BankCo", "amount": 5000}])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Lily", "last_name": "Grant", "ssn": "000-00-0000", "date_of_birth": "2012-05-10"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "interest_income": [{"payer_name": "BankCo", "amount": 5000}],
        "kiddie_tax": {"child_unearned_income": 5000, "child_earned_income": 0, "parent_taxable_income": 300000, "parent_filing_status": "married_filing_jointly"},
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "tax", "kiddie_tax_amount", gt=0)


def test_kiddie_tax_earned_only(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Max", "Grant", "000-00-0000", "2009-08-22"),
        income_types={"w2": True}, w2_income=[w2("SummerJob", "99-9999999", 4000, 0)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Max", "last_name": "Grant", "ssn": "000-00-0000", "date_of_birth": "2009-08-22"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "SummerJob", "employer_ein": "99-9999999", "wages": 4000, "federal_income_tax_withheld": 0}],
        "kiddie_tax": {"child_unearned_income": 0, "child_earned_income": 4000, "parent_taxable_income": 300000, "parent_filing_status": "married_filing_jointly"},
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "tax", "kiddie_tax_amount", eq=0)


# TASK-018: Casualty Loss
def test_casualty_disaster_loss(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Tina", "Marsh", "000-00-0000", "1980-01-15"),
        income_types={"w2": True}, w2_income=[w2("LocalCo", "11-1111111", 60000, 8000)],
        deduction_method="itemized", mortgage_interest=[{"lender_name": "Bank", "mortgage_interest_paid": 12000}])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Tina", "last_name": "Marsh", "ssn": "000-00-0000", "date_of_birth": "1980-01-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "LocalCo", "employer_ein": "11-1111111", "wages": 60000, "federal_income_tax_withheld": 8000}],
        "deduction_method": "itemized",
        "mortgage_interest": [{"lender_name": "Bank", "mortgage_interest_paid": 12000}],
        "casualty_losses": [{"description": "Hurricane", "fema_disaster_declaration_number": "DR-4999", "fair_market_value_before": 200000, "fair_market_value_after": 150000, "adjusted_basis": 180000, "insurance_reimbursement": 20000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "deductions", "casualty_loss_deduction", gt=0)


def test_casualty_non_disaster(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Vic", "Pane", "000-00-0000", "1985-06-20"),
        income_types={"w2": True}, w2_income=[w2("OfficeCo", "22-2222222", 50000, 6000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Vic", "last_name": "Pane", "ssn": "000-00-0000", "date_of_birth": "1985-06-20"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "OfficeCo", "employer_ein": "22-2222222", "wages": 50000, "federal_income_tax_withheld": 6000}],
        "casualty_losses": [{"description": "Theft", "fair_market_value_before": 5000, "fair_market_value_after": 0, "adjusted_basis": 5000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "deductions", "casualty_loss_deduction", eq=0)


# TASK-019: NIIT
def test_niit_above_threshold(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Ella", "Voss", "000-00-0000", "1975-11-11"),
        income_types={"w2": True, "interest": True, "dividends": True},
        w2_income=[w2("BigCo", "33-3333333", 180000, 35000)],
        interest_income=[{"payer_name": "BankCo", "amount": 15000}],
        dividend_income=[{"payer_name": "FundCo", "ordinary_dividends": 20000, "qualified_dividends": 15000}])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Ella", "last_name": "Voss", "ssn": "000-00-0000", "date_of_birth": "1975-11-11"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "BigCo", "employer_ein": "33-3333333", "wages": 180000, "federal_income_tax_withheld": 35000}],
        "interest_income": [{"payer_name": "BankCo", "amount": 15000}],
        "dividend_income": [{"payer_name": "FundCo", "ordinary_dividends": 20000, "qualified_dividends": 15000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "tax", "niit_amount", gt=0)


def test_niit_below_threshold(page, server_url):
    state = wizard_state(filing_status="married_filing_jointly",
        personal_info=person("Rick", "Dunn", "000-00-0000", "1982-03-20"),
        spouse_info=person("Sara", "Dunn", "000-00-0000", "1984-07-15"),
        income_types={"w2": True, "interest": True},
        w2_income=[w2("MidCo", "44-4444444", 150000, 22000)],
        interest_income=[{"payer_name": "CreditUnion", "amount": 5000}])
    payload = {
        "tax_year": 2025, "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "Rick", "last_name": "Dunn", "ssn": "000-00-0000", "date_of_birth": "1982-03-20"},
        "spouse_info": {"first_name": "Sara", "last_name": "Dunn", "ssn": "000-00-0000", "date_of_birth": "1984-07-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "MidCo", "employer_ein": "44-4444444", "wages": 150000, "federal_income_tax_withheld": 22000}],
        "interest_income": [{"payer_name": "CreditUnion", "amount": 5000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "tax", "niit_amount", eq=0)


# TASK-020: Additional Medicare Tax
def test_additional_medicare_above(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Nina", "Hart", "000-00-0000", "1976-09-05"),
        income_types={"w2": True},
        w2_income=[w2("MegaCorp", "55-5555555", 280000, 55000, medicare_wages=280000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Nina", "last_name": "Hart", "ssn": "000-00-0000", "date_of_birth": "1976-09-05"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "MegaCorp", "employer_ein": "55-5555555", "wages": 280000, "federal_income_tax_withheld": 55000, "medicare_wages": 280000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "tax", "additional_medicare_tax", expected=720)


def test_additional_medicare_below(page, server_url):
    state = wizard_state(filing_status="married_filing_jointly",
        personal_info=person("Al", "Kent", "000-00-0000", "1980-01-01"),
        spouse_info=person("Jo", "Kent", "000-00-0000", "1982-06-15"),
        income_types={"w2": True},
        w2_income=[w2("CompanyA", "66-6666666", 120000, 18000, medicare_wages=120000), w2("CompanyB", "77-7777777", 100000, 15000, medicare_wages=100000)])
    payload = {
        "tax_year": 2025, "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "Al", "last_name": "Kent", "ssn": "000-00-0000", "date_of_birth": "1980-01-01"},
        "spouse_info": {"first_name": "Jo", "last_name": "Kent", "ssn": "000-00-0000", "date_of_birth": "1982-06-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [
            {"employer_name": "CompanyA", "employer_ein": "66-6666666", "wages": 120000, "federal_income_tax_withheld": 18000, "medicare_wages": 120000},
            {"employer_name": "CompanyB", "employer_ein": "77-7777777", "wages": 100000, "federal_income_tax_withheld": 15000, "medicare_wages": 100000},
        ],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "tax", "additional_medicare_tax", eq=0)


# TASK-021: 529 Distributions
def test_529_qualified(page, server_url):
    state = wizard_state(filing_status="married_filing_jointly",
        personal_info=person("Dan", "Wise", "000-00-0000", "1975-04-01"),
        spouse_info=person("Amy", "Wise", "000-00-0000", "1977-08-20"),
        income_types={"w2": True}, w2_income=[w2("CorpDan", "88-8888888", 80000, 10000)])
    payload = {
        "tax_year": 2025, "filing_status": "married_filing_jointly",
        "personal_info": {"first_name": "Dan", "last_name": "Wise", "ssn": "000-00-0000", "date_of_birth": "1975-04-01"},
        "spouse_info": {"first_name": "Amy", "last_name": "Wise", "ssn": "000-00-0000", "date_of_birth": "1977-08-20"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "CorpDan", "employer_ein": "88-8888888", "wages": 80000, "federal_income_tax_withheld": 10000}],
        "section_529_distributions": [{"plan_name": "StatePlan", "gross_distribution": 20000, "earnings_portion": 8000, "qualified_education_expenses": 20000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "taxable_529_income", eq=0)


def test_529_nonqualified(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Eve", "Stone", "000-00-0000", "1990-12-01"),
        income_types={"w2": True}, w2_income=[w2("CorpEve", "99-9999999", 50000, 6000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Eve", "last_name": "Stone", "ssn": "000-00-0000", "date_of_birth": "1990-12-01"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "CorpEve", "employer_ein": "99-9999999", "wages": 50000, "federal_income_tax_withheld": 6000}],
        "section_529_distributions": [{"plan_name": "Plan529", "gross_distribution": 15000, "earnings_portion": 6000, "qualified_education_expenses": 5000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "taxable_529_income", gt=0)


# TASK-022: Like-Kind Exchange
def test_lke_no_boot(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Roy", "Tate", "000-00-0000", "1970-02-14"),
        income_types={"w2": True}, w2_income=[w2("CorpRoy", "11-1111111", 70000, 9000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Roy", "last_name": "Tate", "ssn": "000-00-0000", "date_of_birth": "1970-02-14"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "CorpRoy", "employer_ein": "11-1111111", "wages": 70000, "federal_income_tax_withheld": 9000}],
        "like_kind_exchanges": [{"property_relinquished_description": "Office bldg", "adjusted_basis_relinquished": 200000, "fmv_relinquished": 350000, "fmv_received": 350000, "boot_received": 0}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "like_kind_recognized_gain", eq=0)
    assert_json_field(r, "income", "like_kind_deferred_gain", expected=150000)


def test_lke_with_boot(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("May", "Fenn", "000-00-0000", "1968-06-30"),
        income_types={"w2": True}, w2_income=[w2("CorpMay", "22-2222222", 60000, 7000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "May", "last_name": "Fenn", "ssn": "000-00-0000", "date_of_birth": "1968-06-30"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "CorpMay", "employer_ein": "22-2222222", "wages": 60000, "federal_income_tax_withheld": 7000}],
        "like_kind_exchanges": [{"property_relinquished_description": "Rental", "adjusted_basis_relinquished": 150000, "fmv_relinquished": 300000, "fmv_received": 260000, "boot_received": 40000}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "like_kind_recognized_gain", expected=40000)
    assert_json_field(r, "income", "like_kind_deferred_gain", expected=110000)


# TASK-023: Restricted Stock
def test_rsu_vesting(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Kim", "Cho", "000-00-0000", "1988-04-15"),
        income_types={"w2": True}, w2_income=[w2("StartupCo", "33-3333333", 90000, 13000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Kim", "last_name": "Cho", "ssn": "000-00-0000", "date_of_birth": "1988-04-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "StartupCo", "employer_ein": "33-3333333", "wages": 90000, "federal_income_tax_withheld": 13000}],
        "restricted_stock_events": [{"description": "RSU vest", "fmv_at_vesting": 50, "shares": 1000, "amount_paid": 0}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "restricted_stock_income", expected=50000)


def test_83b_election(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Dev", "Patel", "000-00-0000", "1992-11-20"),
        income_types={"w2": True}, w2_income=[w2("EarlyCo", "44-4444444", 80000, 11000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Dev", "last_name": "Patel", "ssn": "000-00-0000", "date_of_birth": "1992-11-20"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "EarlyCo", "employer_ein": "44-4444444", "wages": 80000, "federal_income_tax_withheld": 11000}],
        "restricted_stock_events": [{"description": "83b grant", "section_83b_election": True, "fmv_at_grant": 2, "shares": 5000, "amount_paid": 0}],
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "restricted_stock_income", expected=10000)


# TASK-024: Savings Bond
def test_savings_bond_partial(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Meg", "Drew", "000-00-0000", "1978-05-15"),
        income_types={"w2": True}, w2_income=[w2("EduCo", "55-5555555", 60000, 8000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Meg", "last_name": "Drew", "ssn": "000-00-0000", "date_of_birth": "1978-05-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "EduCo", "employer_ein": "55-5555555", "wages": 60000, "federal_income_tax_withheld": 8000}],
        "savings_bond_education": {"total_bond_proceeds": 10000, "bond_interest": 3000, "qualified_education_expenses": 7000},
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "agi", "savings_bond_interest_excluded", expected=2100)


def test_savings_bond_phaseout(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Phil", "Knox", "000-00-0000", "1975-10-01"),
        income_types={"w2": True}, w2_income=[w2("BigCo", "66-6666666", 120000, 22000)])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Phil", "last_name": "Knox", "ssn": "000-00-0000", "date_of_birth": "1975-10-01"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "BigCo", "employer_ein": "66-6666666", "wages": 120000, "federal_income_tax_withheld": 22000}],
        "savings_bond_education": {"total_bond_proceeds": 10000, "bond_interest": 3000, "qualified_education_expenses": 10000},
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "agi", "savings_bond_interest_excluded", eq=0)


# TASK-025: Investment Interest
def test_investment_interest_capped(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Gus", "Webb", "000-00-0000", "1970-04-01"),
        income_types={"w2": True, "interest": True},
        w2_income=[w2("BankCo", "77-7777777", 100000, 15000)],
        interest_income=[{"payer_name": "SavingsBank", "amount": 3000}],
        deduction_method="itemized",
        mortgage_interest=[{"lender_name": "HomeLoan", "mortgage_interest_paid": 12000}])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Gus", "last_name": "Webb", "ssn": "000-00-0000", "date_of_birth": "1970-04-01"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "BankCo", "employer_ein": "77-7777777", "wages": 100000, "federal_income_tax_withheld": 15000}],
        "interest_income": [{"payer_name": "SavingsBank", "amount": 3000}],
        "deduction_method": "itemized",
        "mortgage_interest": [{"lender_name": "HomeLoan", "mortgage_interest_paid": 12000}],
        "investment_interest_expense": 8000,
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "deductions", "investment_interest_deduction", expected=3000)
    assert_json_field(r, "deductions", "investment_interest_carryforward_to_next_year", expected=5000)


def test_investment_interest_fully_deductible(page, server_url):
    state = wizard_state(filing_status="single", personal_info=person("Hal", "West", "000-00-0000", "1968-09-15"),
        income_types={"w2": True, "interest": True},
        w2_income=[w2("FundCo", "88-8888888", 90000, 13000)],
        interest_income=[{"payer_name": "BondFund", "amount": 10000}],
        deduction_method="itemized",
        mortgage_interest=[{"lender_name": "Bank", "mortgage_interest_paid": 15000}])
    payload = {
        "tax_year": 2025, "filing_status": "single",
        "personal_info": {"first_name": "Hal", "last_name": "West", "ssn": "000-00-0000", "date_of_birth": "1968-09-15"},
        "address": {"street": "1 Test Ln", "city": "Test", "state": "CA", "zip_code": "90000"},
        "w2_income": [{"employer_name": "FundCo", "employer_ein": "88-8888888", "wages": 90000, "federal_income_tax_withheld": 13000}],
        "interest_income": [{"payer_name": "BondFund", "amount": 10000}],
        "deduction_method": "itemized",
        "mortgage_interest": [{"lender_name": "Bank", "mortgage_interest_paid": 15000}],
        "investment_interest_expense": 4000,
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "deductions", "investment_interest_deduction", expected=4000)
    assert_json_field(r, "deductions", "investment_interest_carryforward_to_next_year", eq=0)
