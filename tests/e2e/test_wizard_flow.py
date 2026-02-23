"""
Full wizard flow tests — navigate every step, fill in forms, click Continue.

These tests produce the most useful video recordings for manual review
because they show the complete data-entry experience.
"""
import pytest
from .conftest import Wizard, assert_json_field


@pytest.fixture()
def wiz(page, server):
    w = Wizard(page, server)
    w.start()
    return w


# ── 1. Single filer with W-2 ──────────────────────────────────────────────────


def test_wizard_single_w2(wiz, page):
    """Full flow: single filer, $75k W-2, standard deduction."""
    # Filing Status
    wiz.select_filing_status("single")
    wiz.next()

    # Personal Info
    wiz.fill("First name", "Alice")
    wiz.fill("Last name", "Smith")
    wiz.fill("SSN", "111-22-3333")
    wiz.fill("Date of birth", "1990-03-15")
    wiz.fill("Street address", "100 Main St")
    wiz.fill("City", "Springfield")
    wiz.select("State", "IL")
    wiz.fill("ZIP", "62704")
    wiz.next()

    # Dependents — none
    wiz.next()

    # Income Sources
    wiz.check_income("W-2 Wages")
    wiz.next()

    # W-2 Income
    wiz.fill("Employer name", "Acme Corp")
    wiz.fill("EIN", "11-1111111")
    wiz.fill("Box 1: Wages, tips, compensation", "75000")
    wiz.fill("Box 2: Federal tax withheld", "9000")
    wiz.next()

    # Adjustments — skip
    wiz.next()
    # Deductions — standard (default)
    wiz.next()
    # Credits — skip
    wiz.next()
    # Payments — skip
    wiz.next()

    # Review & Calculate
    wiz.calculate()
    r = wiz.results()

    assert_json_field(r, "income", "total_wages", expected=75000)
    assert_json_field(r, "agi", "agi", expected=75000)
    assert_json_field(r, "deductions", "deduction_amount", expected=15750)
    assert_json_field(r, "deductions", "taxable_income", expected=59250)
    assert_json_field(r, "marginal_tax_rate", expected=0.22)


# ── 2. Married filing jointly with two children ───────────────────────────────


def test_wizard_mfj_children(wiz, page):
    """Full flow: MFJ, two W-2s, two qualifying children."""
    # Filing Status
    wiz.select_filing_status("married_filing_jointly")
    wiz.next()

    # Personal Info — taxpayer
    wiz.fill("First name", "Bob", nth=0)
    wiz.fill("Last name", "Johnson", nth=0)
    wiz.fill("SSN", "222-33-4444", nth=0)
    wiz.fill("Date of birth", "1985-06-20", nth=0)
    # Spouse
    wiz.fill("First name", "Carol", nth=1)
    wiz.fill("Last name", "Johnson", nth=1)
    wiz.fill("SSN", "333-44-5555", nth=1)
    wiz.fill("Date of birth", "1987-09-10", nth=1)
    # Address
    wiz.fill("Street address", "200 Oak Ave")
    wiz.fill("City", "Denver")
    wiz.select("State", "CO")
    wiz.fill("ZIP", "80202")
    wiz.next()

    # Dependents
    wiz.toggle("I have dependents to claim", on=True)
    page.wait_for_timeout(400)
    # First child (card auto-created)
    wiz.fill_in_card(0, "First name", "Emma")
    wiz.fill_in_card(0, "Last name", "Johnson")
    wiz.fill_in_card(0, "SSN", "444-55-6666")
    wiz.fill_in_card(0, "Date of birth", "2015-04-01")
    # Second child
    wiz.click_add("Add another dependent")
    wiz.fill_in_card(1, "First name", "Liam")
    wiz.fill_in_card(1, "Last name", "Johnson")
    wiz.fill_in_card(1, "SSN", "555-66-7777")
    wiz.fill_in_card(1, "Date of birth", "2018-11-15")
    wiz.next()

    # Income Sources
    wiz.check_income("W-2 Wages")
    wiz.next()

    # W-2 Income — first employer
    wiz.fill_in_card(0, "Employer name", "TechCo")
    wiz.fill_in_card(0, "EIN", "22-2222222")
    wiz.fill_in_card(0, "Box 1: Wages, tips, compensation", "80000")
    wiz.fill_in_card(0, "Box 2: Federal tax withheld", "10000")
    # Second employer
    wiz.click_add("Add another W-2")
    wiz.fill_in_card(1, "Employer name", "RetailCo")
    wiz.fill_in_card(1, "EIN", "33-3333333")
    wiz.fill_in_card(1, "Box 1: Wages, tips, compensation", "50000")
    wiz.fill_in_card(1, "Box 2: Federal tax withheld", "5000")
    wiz.next()

    # Adjustments, Deductions, Credits, Payments — skip
    wiz.next()  # Adjustments
    wiz.next()  # Deductions
    wiz.next()  # Credits
    wiz.next()  # Payments

    # Review & Calculate
    wiz.calculate()
    r = wiz.results()

    assert_json_field(r, "income", "total_wages", expected=130000)
    assert_json_field(r, "agi", "agi", expected=130000)
    assert_json_field(r, "deductions", "deduction_amount", expected=31500)
    assert_json_field(r, "credits", "child_tax_credit_nonrefundable", expected=4400)
    assert_json_field(r, "marginal_tax_rate", expected=0.22)


# ── 3. Head of Household ──────────────────────────────────────────────────────


def test_wizard_hoh(wiz, page):
    """Full flow: HOH filer, one child, $55k W-2."""
    wiz.select_filing_status("head_of_household")
    wiz.next()

    # Personal Info
    wiz.fill("First name", "Diana")
    wiz.fill("Last name", "Ross")
    wiz.fill("SSN", "111-11-1111")
    wiz.fill("Date of birth", "1988-02-28")
    wiz.fill("Street address", "300 Pine St")
    wiz.fill("City", "Portland")
    wiz.select("State", "OR")
    wiz.fill("ZIP", "97201")
    wiz.next()

    # Dependents
    wiz.toggle("I have dependents to claim", on=True)
    page.wait_for_timeout(400)
    wiz.fill_in_card(0, "First name", "Maya")
    wiz.fill_in_card(0, "Last name", "Ross")
    wiz.fill_in_card(0, "SSN", "666-77-8888")
    wiz.fill_in_card(0, "Date of birth", "2016-07-12")
    wiz.next()

    # Income Sources
    wiz.check_income("W-2 Wages")
    wiz.next()

    # W-2
    wiz.fill("Employer name", "ServiceCo")
    wiz.fill("EIN", "44-4444444")
    wiz.fill("Box 1: Wages, tips, compensation", "55000")
    wiz.fill("Box 2: Federal tax withheld", "5500")
    wiz.next()

    # Skip through remaining steps
    wiz.next()  # Adjustments
    wiz.next()  # Deductions
    wiz.next()  # Credits
    wiz.next()  # Payments

    wiz.calculate()
    r = wiz.results()

    assert_json_field(r, "income", "total_wages", expected=55000)
    assert_json_field(r, "deductions", "deduction_amount", expected=23625)
    assert_json_field(r, "credits", "child_tax_credit_nonrefundable", expected=2200)
    assert_json_field(r, "marginal_tax_rate", expected=0.12)


# ── 4. Investment income ──────────────────────────────────────────────────────


def test_wizard_investment_income(wiz, page):
    """Full flow: single, W-2 + interest + dividends + LTCG."""
    wiz.select_filing_status("single")
    wiz.next()

    wiz.fill("First name", "Eve")
    wiz.fill("Last name", "Chen")
    wiz.fill("SSN", "666-77-8888")
    wiz.fill("Date of birth", "1982-12-01")
    wiz.fill("Street address", "400 Elm Dr")
    wiz.fill("City", "Austin")
    wiz.select("State", "TX")
    wiz.fill("ZIP", "78701")
    wiz.next()

    # No dependents
    wiz.next()

    # Income Sources — select multiple
    wiz.check_income("W-2 Wages")
    wiz.check_income("Interest")
    wiz.check_income("Dividends")
    wiz.check_income("Capital Gains")
    wiz.next()

    # W-2
    wiz.fill("Employer name", "FinanceCo")
    wiz.fill("EIN", "55-5555555")
    wiz.fill("Box 1: Wages, tips, compensation", "70000")
    wiz.fill("Box 2: Federal tax withheld", "8500")
    wiz.next()

    # Interest & Dividends
    wiz.click_add("Add interest")
    wiz.fill_in_card(0, "Payer name", "Bank of America")
    wiz.fill_in_card(0, "Box 1: Interest income", "2000")
    wiz.click_add("Add dividend")
    wiz.fill_in_card(1, "Payer name", "Vanguard")
    wiz.fill_in_card(1, "Box 1a: Ordinary dividends", "3000")
    wiz.fill_in_card(1, "Box 1b: Qualified dividends", "2500")
    wiz.next()

    # Capital Gains
    wiz.click_add("Add transaction")
    wiz.fill_in_card(0, "Description", "100 sh AAPL")
    wiz.fill_in_card(0, "Date acquired", "2020-01-15")
    wiz.fill_in_card(0, "Date sold", "2025-06-01")
    wiz.select_in_card(0, "Holding period", "long_term")
    wiz.fill_in_card(0, "Sale proceeds", "15000")
    wiz.fill_in_card(0, "Cost basis", "10000")
    wiz.next()

    # Skip remaining
    wiz.next()  # Adjustments
    wiz.next()  # Deductions
    wiz.next()  # Credits
    wiz.next()  # Payments

    wiz.calculate()
    r = wiz.results()

    assert_json_field(r, "income", "total_wages", expected=70000)
    assert_json_field(r, "income", "gross_income", expected=80000)
    assert_json_field(r, "tax", "capital_gains_tax_at_15_pct", gt=0)
    assert_json_field(r, "marginal_tax_rate", expected=0.22)


# ── 5. Self-employed ──────────────────────────────────────────────────────────


def test_wizard_self_employed(wiz, page):
    """Full flow: single, business income $120k gross, $30k expenses."""
    wiz.select_filing_status("single")
    wiz.next()

    wiz.fill("First name", "Frank")
    wiz.fill("Last name", "Lee")
    wiz.fill("SSN", "888-99-0000")
    wiz.fill("Date of birth", "1980-05-10")
    wiz.fill("Street address", "500 Market St")
    wiz.fill("City", "San Francisco")
    wiz.select("State", "CA")
    wiz.fill("ZIP", "94105")
    wiz.next()

    # No dependents
    wiz.next()

    # Income Sources
    wiz.check_income("Self-Employment")
    wiz.next()

    # Business Income — add a business first
    wiz.click_add("Add business")
    wiz.fill_in_card(0, "Business name", "Lee Consulting")
    wiz.fill_in_card(0, "Gross receipts", "120000")
    wiz.fill_in_card(0, "Advertising", "5000")
    wiz.fill_in_card(0, "Office expense", "5000")
    wiz.fill_in_card(0, "Supplies", "5000")
    wiz.fill_in_card(0, "Utilities", "5000")
    wiz.fill_in_card(0, "Other expenses", "10000")
    wiz.next()

    # Skip remaining
    wiz.next()  # Adjustments
    wiz.next()  # Deductions
    wiz.next()  # Credits
    wiz.next()  # Payments

    wiz.calculate()
    r = wiz.results()

    assert_json_field(r, "income", "total_business_income", expected=90000)
    assert_json_field(r, "se_tax", "total_se_tax", gt=0)
    assert_json_field(r, "agi", "se_tax_deduction", gt=0)
    assert r["agi"]["agi"] < r["income"]["gross_income"]


# ── 6. Education credits ─────────────────────────────────────────────────────


def test_wizard_education_credits(wiz, page):
    """Full flow: single, W-2, student loan interest, AOTC."""
    wiz.select_filing_status("single")
    wiz.next()

    wiz.fill("First name", "Jack")
    wiz.fill("Last name", "Park")
    wiz.fill("SSN", "777-88-9999")
    wiz.fill("Date of birth", "1998-10-05")
    wiz.fill("Street address", "600 College Ave")
    wiz.fill("City", "Ann Arbor")
    wiz.select("State", "MI")
    wiz.fill("ZIP", "48104")
    wiz.next()

    # No dependents
    wiz.next()

    # Income Sources
    wiz.check_income("W-2 Wages")
    wiz.next()

    # W-2
    wiz.fill("Employer name", "StartupCo")
    wiz.fill("EIN", "66-6666666")
    wiz.fill("Box 1: Wages, tips, compensation", "55000")
    wiz.fill("Box 2: Federal tax withheld", "5000")
    wiz.next()

    # Adjustments — student loan interest
    wiz.fill("Student loan interest paid", "2500")
    wiz.next()

    # Deductions — standard
    wiz.next()

    # Credits — education
    wiz.toggle("I have education expenses", on=True)
    page.wait_for_timeout(400)
    wiz.click_add("Add student")
    wiz.fill_in_card(0, "Student name", "Jack Park")
    wiz.fill_in_card(0, "Student SSN", "777-88-9999")
    wiz.fill_in_card(0, "Institution name", "State University")
    wiz.fill_in_card(0, "Tuition & fees paid", "4000")
    wiz.next()

    # Payments — skip
    wiz.next()

    wiz.calculate()
    r = wiz.results()

    assert_json_field(r, "income", "total_wages", expected=55000)
    assert_json_field(r, "agi", "student_loan_interest_deduction", expected=2500)
    assert_json_field(r, "agi", "agi", expected=52500)
    assert_json_field(r, "credits", "aotc_refundable", expected=1000)
    assert_json_field(r, "credits", "education_credits", expected=1500)


# ── 7. Married with HSA ──────────────────────────────────────────────────────


def test_wizard_married_hsa(wiz, page):
    """Full flow: MFJ, $150k W-2, family HSA $7k contribution."""
    wiz.select_filing_status("married_filing_jointly")
    wiz.next()

    # Personal
    wiz.fill("First name", "Kevin", nth=0)
    wiz.fill("Last name", "Nguyen", nth=0)
    wiz.fill("SSN", "555-66-7777", nth=0)
    wiz.fill("Date of birth", "1983-01-30", nth=0)
    wiz.fill("First name", "Linda", nth=1)
    wiz.fill("Last name", "Nguyen", nth=1)
    wiz.fill("SSN", "666-77-8888", nth=1)
    wiz.fill("Date of birth", "1985-07-18", nth=1)
    wiz.fill("Street address", "700 Birch Ln")
    wiz.fill("City", "Seattle")
    wiz.select("State", "WA")
    wiz.fill("ZIP", "98101")
    wiz.next()

    # No dependents
    wiz.next()

    # Income Sources
    wiz.check_income("W-2 Wages")
    wiz.next()

    # W-2
    wiz.fill("Employer name", "HealthCo")
    wiz.fill("EIN", "77-7777777")
    wiz.fill("Box 1: Wages, tips, compensation", "150000")
    wiz.fill("Box 2: Federal tax withheld", "20000")
    wiz.next()

    # Adjustments — HSA
    wiz.toggle("I have a Health Savings Account", on=True)
    page.wait_for_timeout(400)
    wiz.select("Coverage type", "family")
    wiz.fill("Your HSA contributions", "7000")
    wiz.next()

    # Skip remaining
    wiz.next()  # Deductions
    wiz.next()  # Credits
    wiz.next()  # Payments

    wiz.calculate()
    r = wiz.results()

    assert_json_field(r, "income", "total_wages", expected=150000)
    assert_json_field(r, "agi", "hsa_deduction", expected=7000)
    assert_json_field(r, "agi", "agi", expected=143000)
    assert_json_field(r, "deductions", "deduction_amount", expected=31500)


# ── 8. Married itemized deductions ────────────────────────────────────────────


def test_wizard_itemized(wiz, page):
    """Full flow: MFJ, $180k W-2, itemized (mortgage, SALT, charity)."""
    wiz.select_filing_status("married_filing_jointly")
    wiz.next()

    # Personal
    wiz.fill("First name", "George", nth=0)
    wiz.fill("Last name", "Kim", nth=0)
    wiz.fill("SSN", "222-11-3333", nth=0)
    wiz.fill("Date of birth", "1978-08-22", nth=0)
    wiz.fill("First name", "Helen", nth=1)
    wiz.fill("Last name", "Kim", nth=1)
    wiz.fill("SSN", "333-22-4444", nth=1)
    wiz.fill("Date of birth", "1980-03-14", nth=1)
    wiz.fill("Street address", "800 Walnut Way")
    wiz.fill("City", "Chicago")
    wiz.select("State", "IL")
    wiz.fill("ZIP", "60601")
    wiz.next()

    # No dependents
    wiz.next()

    # Income Sources
    wiz.check_income("W-2 Wages")
    wiz.next()

    # W-2
    wiz.fill("Employer name", "LawFirm LLP")
    wiz.fill("EIN", "55-5555555")
    wiz.fill("Box 1: Wages, tips, compensation", "180000")
    wiz.fill("Box 2: Federal tax withheld", "30000")
    wiz.next()

    # Adjustments — skip
    wiz.next()

    # Deductions — itemized
    wiz.select_radio("itemized")
    page.wait_for_timeout(400)

    # SALT
    wiz.fill("State income tax paid", "12000")
    wiz.fill("Real property tax", "8000")

    # Mortgage
    wiz.click_add("Add mortgage")
    wiz.fill_in_card(0, "Lender name", "BigBank")
    wiz.fill_in_card(0, "Interest paid", "18000")

    # Charity
    wiz.click_add("Add contribution")
    wiz.fill_in_card(1, "Organization name", "Red Cross")
    wiz.fill_in_card(1, "Cash contributions", "8000")
    wiz.next()

    # Credits — skip
    wiz.next()
    # Payments — skip
    wiz.next()

    wiz.calculate()
    r = wiz.results()

    assert_json_field(r, "income", "total_wages", expected=180000)
    assert_json_field(r, "agi", "agi", expected=180000)
    assert_json_field(r, "deductions", "deduction_method_used", contains="itemized")
    assert_json_field(r, "deductions", "salt_deduction", expected=20000)
    assert_json_field(r, "deductions", "total_itemized_deductions", expected=46000)
    assert_json_field(r, "marginal_tax_rate", expected=0.22)


# ── 9. Retirement income ─────────────────────────────────────────────────────


def test_wizard_retirement(wiz, page):
    """Full flow: single retiree age 68, Social Security + pension."""
    wiz.select_filing_status("single")
    wiz.next()

    wiz.fill("First name", "Irene")
    wiz.fill("Last name", "Walsh")
    wiz.fill("SSN", "444-55-6666")
    wiz.fill("Date of birth", "1957-04-20")
    wiz.fill("Street address", "900 Sunset Blvd")
    wiz.fill("City", "Phoenix")
    wiz.select("State", "AZ")
    wiz.fill("ZIP", "85001")
    wiz.next()

    # No dependents
    wiz.next()

    # Income Sources
    wiz.check_income("Social Security")
    wiz.check_income("Retirement")
    wiz.next()

    # Retirement & SS step
    # Retirement distribution
    wiz.click_add("Add distribution")
    wiz.fill_in_card(0, "Payer name", "State Pension Fund")
    wiz.fill_in_card(0, "Box 1: Gross distribution", "30000")
    wiz.fill_in_card(0, "Box 2a: Taxable amount", "30000")
    wiz.fill_in_card(0, "Box 4: Federal tax withheld", "3000")
    # Social Security
    wiz.fill("Box 5: Total benefits received", "24000")
    wiz.next()

    # Skip remaining
    wiz.next()  # Adjustments
    wiz.next()  # Deductions
    wiz.next()  # Credits
    wiz.next()  # Payments

    wiz.calculate()
    r = wiz.results()

    assert_json_field(r, "income", "taxable_social_security", expected=15300)
    assert_json_field(r, "income", "gross_income", expected=45300)
    assert_json_field(r, "deductions", "total_standard_deduction", expected=17750)
    assert_json_field(r, "deductions", "senior_deduction", expected=6000)
    assert_json_field(r, "marginal_tax_rate", expected=0.12)
