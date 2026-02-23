"""
Federal individual income tax calculator.

Accepts a TaxReturnInput instance (JSON-schema-describable), validates it,
performs all necessary computations, and returns a TaxReturnOutput instance.

Tax year support: 2025 (with 2018 base amounts inflation-adjusted where noted).
All calculations reference IRC sections as documented in NOTES.md.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from dataclasses import asdict
from datetime import date, datetime
from enum import Enum
from typing import Union, get_args, get_origin, get_type_hints

from models import (
    AdoptionExpense,
    AGIComputation,
    AMTPreferenceItems,
    AnnuityIncome,
    CapitalGainTerm,
    CasualtyLossEvent,
    CreditComputation,
    DeductionComputation,
    DeductionMethod,
    EducationCreditType,
    EITCEligibility,
    ElderlyDisabledInfo,
    FarmIncome,
    FilingStatus,
    GamblingIncome,
    IncomeComputation,
    K1EntityType,
    K1Income,
    KiddieTaxInfo,
    LikeKindExchange,
    MarketplaceCoverage,
    PaymentSummary,
    PenaltyComputation,
    RestrictedStockEvent,
    RetirementAccountType,
    RoyaltyIncome,
    SavingsBondEducationExclusion,
    ScholarshipIncome,
    Section529Distribution,
    SelfEmploymentTaxComputation,
    TaxComputation,
    TaxReturnInput,
    TaxReturnOutput,
)

# ---------------------------------------------------------------------------
# Tax Year Constants (2025)
# These are inflation-adjusted amounts from IRS Revenue Procedures.
# Base statutory amounts are in NOTES.md; these are the 2025 effective values.
# ---------------------------------------------------------------------------

TAX_YEAR = 2025

# IRC §1(j) — Tax brackets (title26.md:5292, 6120-6190)
# 2025 inflation-adjusted amounts
TAX_BRACKETS = {
    FilingStatus.MARRIED_FILING_JOINTLY: [
        (23850, 0.10),
        (96950, 0.12),
        (206700, 0.22),
        (394600, 0.24),
        (501050, 0.32),
        (751600, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: [
        (23850, 0.10),
        (96950, 0.12),
        (206700, 0.22),
        (394600, 0.24),
        (501050, 0.32),
        (751600, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.HEAD_OF_HOUSEHOLD: [
        (17000, 0.10),
        (64850, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250500, 0.32),
        (626350, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.SINGLE: [
        (11925, 0.10),
        (48475, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250525, 0.32),
        (626350, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.MARRIED_FILING_SEPARATELY: [
        (11925, 0.10),
        (48475, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250525, 0.32),
        (375800, 0.35),
        (float("inf"), 0.37),
    ],
}

# IRC §63(c) — Standard deduction (title26.md:72514-72536)
STANDARD_DEDUCTION = {
    FilingStatus.SINGLE: 15750,
    FilingStatus.MARRIED_FILING_JOINTLY: 31500,
    FilingStatus.MARRIED_FILING_SEPARATELY: 15750,
    FilingStatus.HEAD_OF_HOUSEHOLD: 23625,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 31500,
}

# IRC §63(f) — Additional standard deduction for age 65+ or blind (title26.md:72598-72627)
ADDITIONAL_STD_DEDUCTION_MARRIED = 1600  # Per qualifying condition
ADDITIONAL_STD_DEDUCTION_UNMARRIED = 2000  # Per qualifying condition

# IRC §1(h) — Capital gains rate thresholds (title26.md:5703, 6259-6288)
# 2025 inflation-adjusted
CAPGAIN_0_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 96700,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 96700,
    FilingStatus.HEAD_OF_HOUSEHOLD: 64750,
    FilingStatus.SINGLE: 48350,
    FilingStatus.MARRIED_FILING_SEPARATELY: 48350,
}

CAPGAIN_15_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 600050,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 600050,
    FilingStatus.HEAD_OF_HOUSEHOLD: 566700,
    FilingStatus.SINGLE: 533400,
    FilingStatus.MARRIED_FILING_SEPARATELY: 300025,
}

# IRC §1211 — Capital loss limitation (title26.md:350175-350190)
CAPITAL_LOSS_LIMIT = {
    FilingStatus.MARRIED_FILING_SEPARATELY: 1500,
}
CAPITAL_LOSS_LIMIT_DEFAULT = 3000

# IRC §86 — Social Security taxation thresholds (title26.md:80658-80743)
SS_BASE_AMOUNT = {
    FilingStatus.SINGLE: 25000,
    FilingStatus.HEAD_OF_HOUSEHOLD: 25000,
    FilingStatus.MARRIED_FILING_JOINTLY: 32000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 32000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 0,
}
SS_ADJUSTED_BASE = {
    FilingStatus.SINGLE: 34000,
    FilingStatus.HEAD_OF_HOUSEHOLD: 34000,
    FilingStatus.MARRIED_FILING_JOINTLY: 44000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 44000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 0,
}

# IRC §164(b)(6) — SALT cap (title26.md:119469-119543)
SALT_CAP = {
    FilingStatus.MARRIED_FILING_SEPARATELY: 20000,
}
SALT_CAP_DEFAULT = 40000

# SALT phase-down threshold for high earners — IRC §164(b)(6)(H) (title26.md:119518-119543)
SALT_PHASE_DOWN_THRESHOLD = {
    FilingStatus.MARRIED_FILING_SEPARATELY: 250000,
}
SALT_PHASE_DOWN_THRESHOLD_DEFAULT = 500000

# IRC §121 — Home sale exclusion (title26.md:90818-90871)
HOME_SALE_EXCLUSION = {
    FilingStatus.MARRIED_FILING_JOINTLY: 500000,
}
HOME_SALE_EXCLUSION_DEFAULT = 250000

# IRC §24 — Child Tax Credit (title26.md:13963, 14148-14190)
CHILD_TAX_CREDIT_AMOUNT = 2200  # Per qualifying child under 17
OTHER_DEPENDENT_CREDIT = 500
CTC_PHASE_OUT_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 400000,
}
CTC_PHASE_OUT_THRESHOLD_DEFAULT = 200000
CTC_REFUNDABLE_MAX = 1400  # Additional child tax credit

# IRC §32 — EITC parameters (title26.md:22751-23119)
# 2025 inflation-adjusted amounts
EITC_PARAMS = {
    0: {
        "credit_pct": 0.0765,
        "phaseout_pct": 0.0765,
        "earned_income_amt": 7840,
        "phaseout_start": 10330,
        "phaseout_start_joint": 17530,
    },
    1: {
        "credit_pct": 0.34,
        "phaseout_pct": 0.1598,
        "earned_income_amt": 12220,
        "phaseout_start": 22120,
        "phaseout_start_joint": 29120,
    },
    2: {
        "credit_pct": 0.40,
        "phaseout_pct": 0.2106,
        "earned_income_amt": 17160,
        "phaseout_start": 22120,
        "phaseout_start_joint": 29120,
    },
    3: {
        "credit_pct": 0.45,
        "phaseout_pct": 0.2106,
        "earned_income_amt": 17160,
        "phaseout_start": 22120,
        "phaseout_start_joint": 29120,
    },
}
EITC_INVESTMENT_INCOME_LIMIT = 11950
EITC_MAX_AGE_NO_CHILDREN = 64
EITC_MIN_AGE_NO_CHILDREN = 25

# IRC §55 — AMT (title26.md:64924-65100)
AMT_EXEMPTION = {
    FilingStatus.MARRIED_FILING_JOINTLY: 137000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 137000,
    FilingStatus.SINGLE: 88100,
    FilingStatus.HEAD_OF_HOUSEHOLD: 88100,
    FilingStatus.MARRIED_FILING_SEPARATELY: 68500,
}
AMT_PHASEOUT_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 1252700,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 1252700,
    FilingStatus.SINGLE: 626350,
    FilingStatus.HEAD_OF_HOUSEHOLD: 626350,
    FilingStatus.MARRIED_FILING_SEPARATELY: 626350,
}
AMT_RATE_THRESHOLD = 248300  # 26% up to this, 28% above (MFS: half)

# IRC §1401 — Self-employment tax (title26.md:377596-377630)
SE_TAX_RATE_OASDI = 0.124
SE_TAX_RATE_MEDICARE = 0.029
SE_TAX_ADDITIONAL_MEDICARE = 0.009
SE_WAGE_BASE_2025 = 176100  # Social Security wage base
SE_ADDITIONAL_MEDICARE_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 250000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 250000,
    FilingStatus.SINGLE: 200000,
    FilingStatus.HEAD_OF_HOUSEHOLD: 200000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 125000,
}

# IRC §221 — Student loan interest (title26.md:151853)
STUDENT_LOAN_INTEREST_MAX = 2500
STUDENT_LOAN_PHASEOUT_START = {
    FilingStatus.MARRIED_FILING_JOINTLY: 165000,
}
STUDENT_LOAN_PHASEOUT_START_DEFAULT = 85000
STUDENT_LOAN_PHASEOUT_RANGE = {
    FilingStatus.MARRIED_FILING_JOINTLY: 30000,
}
STUDENT_LOAN_PHASEOUT_RANGE_DEFAULT = 15000

# IRC §223 — HSA limits (title26.md:152303)
HSA_LIMIT_SELF = 4300
HSA_LIMIT_FAMILY = 8550
HSA_CATCHUP = 1000

# IRC §224 — Qualified tips (title26.md:153381)
TIPS_DEDUCTION_MAX = 25000
TIPS_PHASEOUT_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 300000,
}
TIPS_PHASEOUT_THRESHOLD_DEFAULT = 150000

# IRC §225 — Qualified overtime (title26.md:153525)
OVERTIME_DEDUCTION_MAX = {
    FilingStatus.MARRIED_FILING_JOINTLY: 25000,
}
OVERTIME_DEDUCTION_MAX_DEFAULT = 12500
OVERTIME_PHASEOUT_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 300000,
}
OVERTIME_PHASEOUT_THRESHOLD_DEFAULT = 150000

# IRC §219 — IRA deduction limit (title26.md:149106-149191)
IRA_CONTRIBUTION_LIMIT = 7000
IRA_CATCHUP_50_PLUS = 1000

# IRC §151(f) — Senior deduction (title26.md:112427-112471)
SENIOR_DEDUCTION_AMOUNT = 6000
SENIOR_DEDUCTION_PHASEOUT_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 150000,
}
SENIOR_DEDUCTION_PHASEOUT_THRESHOLD_DEFAULT = 75000

# IRC §25A — Education credits (title26.md:16106-16243)
AOTC_MAX = 2500
LLC_MAX = 2000
EDUCATION_CREDIT_PHASEOUT_START = {
    FilingStatus.MARRIED_FILING_JOINTLY: 160000,
}
EDUCATION_CREDIT_PHASEOUT_START_DEFAULT = 80000
EDUCATION_CREDIT_PHASEOUT_RANGE = 10000
EDUCATION_CREDIT_PHASEOUT_RANGE_JOINT = 20000

# IRC §21 — Child and dependent care (title26.md:12007-12114)
DEPENDENT_CARE_MAX_ONE = 3000
DEPENDENT_CARE_MAX_TWO_PLUS = 6000

# IRC §213 — Medical expense threshold (title26.md:147452-147461)
MEDICAL_EXPENSE_AGI_THRESHOLD = 0.075

# IRC §1411 — Net Investment Income Tax (NIIT)
NIIT_RATE = 0.038
NIIT_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 250000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 250000,
    FilingStatus.SINGLE: 200000,
    FilingStatus.HEAD_OF_HOUSEHOLD: 200000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 125000,
}

# IRC §3101(b)(2) — Additional Medicare Tax (employee side)
ADDITIONAL_MEDICARE_TAX_RATE = 0.009
ADDITIONAL_MEDICARE_THRESHOLD = {
    FilingStatus.MARRIED_FILING_JOINTLY: 250000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 250000,
    FilingStatus.SINGLE: 200000,
    FilingStatus.HEAD_OF_HOUSEHOLD: 200000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 125000,
}

# IRC §23 — Adoption credit (title26.md:13227-13323)
ADOPTION_CREDIT_MAX = 17280  # 2025 inflation-adjusted
ADOPTION_CREDIT_PHASEOUT_START = 252150  # 2025
ADOPTION_CREDIT_PHASEOUT_RANGE = 40000
ADOPTION_CREDIT_REFUNDABLE_MAX = 5000  # §23(a)(4)

# IRC §22 — Credit for elderly or disabled (title26.md:12756-12865)
ELDERLY_DISABLED_INITIAL_SINGLE = 5000
ELDERLY_DISABLED_INITIAL_JOINT_BOTH = 7500
ELDERLY_DISABLED_INITIAL_JOINT_ONE = 5000
ELDERLY_DISABLED_INITIAL_MFS = 3750
ELDERLY_DISABLED_AGI_THRESHOLD_SINGLE = 7500
ELDERLY_DISABLED_AGI_THRESHOLD_JOINT = 10000
ELDERLY_DISABLED_CREDIT_RATE = 0.15

# IRC §36B — Premium Tax Credit / FPL (title26.md:26647)
# 2025 Federal Poverty Line for contiguous 48 states
FPL_BASE = 15650  # 1-person household
FPL_PER_ADDITIONAL = 5580  # Per additional person
# Applicable percentage table — household income as % of FPL
# (lower_pct_fpl, upper_pct_fpl, initial_premium_pct, final_premium_pct)
PTC_PERCENTAGE_TABLE = [
    (0, 150, 0.0, 0.0),
    (150, 200, 0.0, 0.02),
    (200, 250, 0.02, 0.04),
    (250, 300, 0.04, 0.06),
    (300, 400, 0.06, 0.085),
    (400, float("inf"), 0.085, 0.085),
]
# Excess advance PTC repayment caps by income as % of FPL (single / other)
PTC_REPAYMENT_CAPS = [
    (200, 350, 700),
    (300, 900, 1800),
    (400, 1500, 2700),
]

# IRC §1(g) — Kiddie tax (title26.md:5520)
KIDDIE_TAX_THRESHOLD = 2500  # 2025 — unearned income threshold (2x $1,250)
KIDDIE_TAX_STANDARD_DEDUCTION = 1350  # 2025 — child standard deduction for unearned

# IRC §72(d)(1) — Simplified method anticipated payments by age
ANNUITY_SIMPLIFIED_DIVISORS = {
    55: 360,
    60: 310,
    65: 260,
    70: 210,
    75: 160,
}

# IRC §135 — Savings bond education exclusion phase-out
SAVINGS_BOND_PHASEOUT_START = {
    FilingStatus.MARRIED_FILING_JOINTLY: 158650,
}
SAVINGS_BOND_PHASEOUT_START_DEFAULT = 100800
SAVINGS_BOND_PHASEOUT_RANGE = {
    FilingStatus.MARRIED_FILING_JOINTLY: 30000,
}
SAVINGS_BOND_PHASEOUT_RANGE_DEFAULT = 15000

# IRC §165(h) — Casualty loss floors
CASUALTY_LOSS_PER_EVENT_FLOOR = 500
CASUALTY_LOSS_AGI_THRESHOLD = 0.10


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationError(Exception):
    """Raised when input data fails validation."""

    pass


def _get_age(dob_str: str, tax_year: int) -> int:
    """Calculate age as of December 31 of the tax year."""
    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    end_of_year = date(tax_year, 12, 31)
    age = end_of_year.year - dob.year
    if (end_of_year.month, end_of_year.day) < (dob.month, dob.day):
        age -= 1
    return age


def _is_married_status(status: FilingStatus) -> bool:
    return status in (
        FilingStatus.MARRIED_FILING_JOINTLY,
        FilingStatus.MARRIED_FILING_SEPARATELY,
    )


def validate(inp: TaxReturnInput) -> list[str]:
    """Validate input data. Returns list of error messages (empty if valid).

    Checks constraints that cannot be expressed in JSON Schema alone.
    """
    errors = []

    # Filing status consistency
    if _is_married_status(inp.filing_status) and inp.spouse_info is None:
        errors.append(
            "Spouse info required for married filing status (IRC §2, title26.md:10051)"
        )

    if inp.filing_status == FilingStatus.HEAD_OF_HOUSEHOLD:
        # IRC §2(b) — must have qualifying dependent
        if not inp.dependents:
            errors.append(
                "Head of household requires at least one qualifying dependent "
                "(IRC §2(b), title26.md:10107)"
            )

    # Dependent validation — IRC §152
    for dep in inp.dependents:
        age = _get_age(dep.date_of_birth, inp.tax_year)
        if dep.relationship.value == "qualifying_child":
            if (
                age >= 19
                and not dep.is_full_time_student
                and not dep.is_permanently_disabled
            ):
                errors.append(
                    f"Dependent {dep.first_name} {dep.last_name}: qualifying child must be "
                    f"under 19, or under 24 if student, or permanently disabled "
                    f"(IRC §152(c)(3), title26.md:112980)"
                )
            if dep.is_full_time_student and age >= 24:
                errors.append(
                    f"Dependent {dep.first_name} {dep.last_name}: student qualifying child "
                    f"must be under 24 (IRC §152(c)(3), title26.md:112980)"
                )
            if dep.months_lived_with_taxpayer < 7:
                errors.append(
                    f"Dependent {dep.first_name} {dep.last_name}: qualifying child must live "
                    f"with taxpayer for more than half the year "
                    f"(IRC §152(c)(1)(B), title26.md:112948)"
                )

    # Home sale — IRC §121
    if inp.home_sale:
        if inp.home_sale.years_used_as_residence < 2.0:
            errors.append(
                "Home sale exclusion requires 2 years of use as principal residence "
                "in the last 5 years (IRC §121(a), title26.md:90822)"
            )
        if inp.home_sale.years_owned < 2.0:
            errors.append(
                "Home sale exclusion requires 2 years of ownership "
                "(IRC §121(a), title26.md:90822)"
            )

    # AOTC eligibility — IRC §25A
    for edu in inp.education_expenses:
        if edu.credit_type == EducationCreditType.AOTC:
            if edu.year_in_postsecondary > 4:
                errors.append(
                    f"AOTC for {edu.student_name}: only available for first 4 years "
                    f"of postsecondary education (IRC §25A(b)(2)(C), title26.md:16136)"
                )
            if edu.has_felony_drug_conviction:
                errors.append(
                    f"AOTC for {edu.student_name}: not available for students with "
                    f"felony drug conviction (IRC §25A(b)(2)(D))"
                )

    # MFS restrictions
    if inp.filing_status == FilingStatus.MARRIED_FILING_SEPARATELY:
        if inp.deduction_method == DeductionMethod.STANDARD:
            # IRC §63(c)(6)(A) — cannot use standard deduction if spouse itemizes
            pass  # We can't know spouse's choice from input; warn in output

    # Clean vehicle — §30D / §25E termination
    if inp.clean_vehicle and inp.tax_year >= 2025:
        if inp.clean_vehicle.purchase_date:
            pdate = datetime.strptime(
                inp.clean_vehicle.purchase_date, "%Y-%m-%d"
            ).date()
            if pdate > date(2025, 9, 30):
                errors.append(
                    "Clean vehicle credits (§30D/§25E) terminated after September 30, 2025 "
                    "(Pub. L. 119-21)"
                )

    # Energy credits — §25C/§25D termination
    if inp.energy_credits and inp.tax_year > 2025:
        errors.append(
            "Energy efficient home improvement (§25C) and residential clean energy (§25D) "
            "credits do not apply after December 31, 2025 (title26.md:17591, 18362)"
        )

    return errors


# ---------------------------------------------------------------------------
# Computation Functions
# ---------------------------------------------------------------------------


def _compute_bracket_tax(
    taxable_income: float, status: FilingStatus
) -> tuple[float, list[dict]]:
    """Compute ordinary income tax using IRC §1 brackets.

    IRC §1(a)-(d), (j) (title26.md:5292, 6120-6190).
    Returns (tax, bracket_details).
    """
    brackets = TAX_BRACKETS[status]
    tax = 0.0
    details = []
    prev_threshold = 0.0

    for threshold, rate in brackets:
        if taxable_income <= 0:
            break
        bracket_income = min(taxable_income, threshold) - prev_threshold
        if bracket_income > 0:
            bracket_tax = round(bracket_income * rate, 2)
            tax += bracket_tax
            details.append(
                {
                    "rate": rate,
                    "bracket_income": round(bracket_income, 2),
                    "tax": bracket_tax,
                }
            )
        prev_threshold = threshold
        if taxable_income <= threshold:
            break

    return round(tax, 2), details


def _compute_capital_gains_tax(
    net_ltcg: float,
    qualified_dividends: float,
    taxable_income: float,
    status: FilingStatus,
) -> dict:
    """Compute preferential capital gains tax.

    IRC §1(h) (title26.md:5703-5895).
    Returns dict with tax amounts at each rate tier.
    """
    total_preferential = net_ltcg + qualified_dividends
    if total_preferential <= 0:
        return {"at_0": 0.0, "at_15": 0.0, "at_20": 0.0}

    threshold_0 = CAPGAIN_0_THRESHOLD[status]
    threshold_15 = CAPGAIN_15_THRESHOLD[status]

    ordinary_income = max(0, taxable_income - total_preferential)

    # Amount taxed at 0%
    room_at_0 = max(0, threshold_0 - ordinary_income)
    at_0 = min(total_preferential, room_at_0)

    # Amount taxed at 15%
    room_at_15 = max(0, threshold_15 - ordinary_income - at_0)
    remaining = total_preferential - at_0
    at_15 = min(remaining, room_at_15)

    # Amount taxed at 20%
    at_20 = max(0, remaining - at_15)

    return {
        "at_0": round(at_0 * 0.0, 2),
        "at_15": round(at_15 * 0.15, 2),
        "at_20": round(at_20 * 0.20, 2),
    }


def _compute_social_security_taxable(
    total_benefits: float,
    provisional_income: float,
    status: FilingStatus,
) -> float:
    """Compute taxable portion of Social Security benefits.

    IRC §86 (title26.md:80658-80743).
    """
    if total_benefits <= 0:
        return 0.0

    base = SS_BASE_AMOUNT[status]
    adjusted_base = SS_ADJUSTED_BASE[status]

    if provisional_income <= base:
        return 0.0

    # Up to 50% taxable
    excess_over_base = provisional_income - base
    taxable_50 = min(total_benefits * 0.5, excess_over_base * 0.5)

    if provisional_income <= adjusted_base:
        return round(taxable_50, 2)

    # Up to 85% taxable
    excess_over_adjusted = provisional_income - adjusted_base
    taxable_85 = min(
        total_benefits * 0.85,
        taxable_50 + excess_over_adjusted * 0.85,
    )

    return round(taxable_85, 2)


def _compute_self_employment_tax(
    net_se_income: float,
    status: FilingStatus,
    w2_ss_wages: float = 0.0,
) -> SelfEmploymentTaxComputation:
    """Compute self-employment tax.

    IRC §1401 (title26.md:377596-377630).
    SE tax base = 92.35% of net SE earnings.
    """
    result = SelfEmploymentTaxComputation()

    if net_se_income <= 0:
        return result

    result.net_se_earnings = round(net_se_income, 2)
    # 92.35% factor accounts for the employer-equivalent portion
    result.se_tax_base = round(net_se_income * 0.9235, 2)

    # OASDI — 12.4% up to wage base, reduced by W-2 SS wages
    remaining_wage_base = max(0, SE_WAGE_BASE_2025 - w2_ss_wages)
    oasdi_income = min(result.se_tax_base, remaining_wage_base)
    result.oasdi_tax = round(oasdi_income * SE_TAX_RATE_OASDI, 2)

    # Medicare — 2.9% on all SE income
    result.medicare_tax = round(result.se_tax_base * SE_TAX_RATE_MEDICARE, 2)

    # Additional Medicare — 0.9% over threshold
    threshold = SE_ADDITIONAL_MEDICARE_THRESHOLD[status]
    excess = max(0, result.se_tax_base - threshold)
    result.additional_medicare_tax = round(excess * SE_TAX_ADDITIONAL_MEDICARE, 2)

    result.total_se_tax = round(
        result.oasdi_tax + result.medicare_tax + result.additional_medicare_tax, 2
    )
    # 50% of SE tax is deductible above-the-line — IRC §164(f)
    result.se_tax_deduction = round(result.total_se_tax * 0.5, 2)

    return result


def _compute_eitc(
    earned_income: float,
    agi: float,
    num_qualifying_children: int,
    status: FilingStatus,
    investment_income: float,
) -> float:
    """Compute Earned Income Tax Credit.

    IRC §32 (title26.md:22751-23119).
    """
    if investment_income > EITC_INVESTMENT_INCOME_LIMIT:
        return 0.0

    children_key = min(num_qualifying_children, 3)
    params = EITC_PARAMS[children_key]

    credit = params["credit_pct"] * min(earned_income, params["earned_income_amt"])

    phaseout_start = params["phaseout_start"]
    if status == FilingStatus.MARRIED_FILING_JOINTLY:
        phaseout_start = params["phaseout_start_joint"]

    phaseout_income = max(agi, earned_income)
    if phaseout_income > phaseout_start:
        reduction = params["phaseout_pct"] * (phaseout_income - phaseout_start)
        credit = max(0, credit - reduction)

    return round(credit, 2)


def _phaseout_amount(
    value: float, magi: float, threshold: float, rate_per_1000: float = 100.0
) -> float:
    """Apply a linear phase-out reduction.

    Reduces value by rate_per_1000 for each $1,000 of MAGI over threshold.
    """
    if magi <= threshold:
        return value
    excess = magi - threshold
    reduction = (excess / 1000) * rate_per_1000
    return round(max(0, value - reduction), 2)


# ---------------------------------------------------------------------------
# Main Calculation Pipeline
# ---------------------------------------------------------------------------


def calculate(inp: TaxReturnInput) -> TaxReturnOutput:
    """Perform all tax computations and return the completed tax return.

    Validates input, computes income, AGI, deductions, tax, credits,
    SE tax, payments, and determines refund or amount owed.
    """
    errors = validate(inp)
    if errors:
        raise ValidationError(
            "Input validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    out = TaxReturnOutput(tax_year=inp.tax_year, filing_status=inp.filing_status)
    taxpayer_age = _get_age(inp.personal_info.date_of_birth, inp.tax_year)
    spouse_age = (
        _get_age(inp.spouse_info.date_of_birth, inp.tax_year) if inp.spouse_info else 0
    )

    # ===== STEP 1: Compute Income — IRC §61 (title26.md:70846) =====
    inc = IncomeComputation()

    # Wages — IRC §61(a)(1)
    inc.total_wages = round(sum(w.wages for w in inp.w2_income), 2)

    # Interest — IRC §61(a)(4), §103
    inc.total_interest = round(sum(i.amount for i in inp.interest_income), 2)
    inc.tax_exempt_interest = round(
        sum(i.tax_exempt_amount for i in inp.interest_income), 2
    )

    # Dividends — IRC §61(a)(7)
    inc.total_ordinary_dividends = round(
        sum(d.ordinary_dividends for d in inp.dividend_income), 2
    )
    inc.total_qualified_dividends = round(
        sum(d.qualified_dividends for d in inp.dividend_income), 2
    )

    # Capital gains/losses — IRC §1001, §1221, §1222, §1211, §1212
    for cg in inp.capital_gains_losses:
        gain_loss = cg.proceeds - cg.cost_basis + cg.wash_sale_loss_disallowed
        if cg.term == CapitalGainTerm.SHORT_TERM:
            inc.net_short_term_capital_gain_loss += gain_loss
        else:
            inc.net_long_term_capital_gain_loss += gain_loss
    # Add capital gain distributions from mutual funds
    inc.net_long_term_capital_gain_loss += sum(
        d.capital_gain_distributions for d in inp.dividend_income
    )

    # TASK-001: K-1 flows into interest, dividends, capital gains — IRC §702
    for k1 in inp.k1_income:
        inc.total_interest += k1.interest_income
        inc.total_ordinary_dividends += k1.ordinary_dividends
        inc.total_qualified_dividends += k1.qualified_dividends
        inc.net_short_term_capital_gain_loss += k1.net_short_term_capital_gain
        inc.net_long_term_capital_gain_loss += (
            k1.net_long_term_capital_gain + k1.net_section_1231_gain
        )
        inc.tax_exempt_interest += k1.tax_exempt_income

    inc.total_interest = round(inc.total_interest, 2)
    inc.total_ordinary_dividends = round(inc.total_ordinary_dividends, 2)
    inc.total_qualified_dividends = round(inc.total_qualified_dividends, 2)
    inc.net_short_term_capital_gain_loss = round(
        inc.net_short_term_capital_gain_loss, 2
    )
    inc.net_long_term_capital_gain_loss = round(inc.net_long_term_capital_gain_loss, 2)

    # TASK-016: Apply capital loss carryforward with ST/LT character — IRC §1212(b)
    st_carryforward = inp.capital_loss_carryforward_short_term
    lt_carryforward = inp.capital_loss_carryforward_long_term
    # Legacy single-value field: treat as long-term if ST/LT not specified
    if (
        inp.capital_loss_carryforward > 0
        and st_carryforward == 0
        and lt_carryforward == 0
    ):
        lt_carryforward = inp.capital_loss_carryforward

    # Apply ST carryforward against ST gains first
    inc.net_short_term_capital_gain_loss -= st_carryforward
    inc.net_long_term_capital_gain_loss -= lt_carryforward

    # Capital loss limitation — IRC §1211 (title26.md:350175-350190)
    loss_limit = CAPITAL_LOSS_LIMIT.get(inp.filing_status, CAPITAL_LOSS_LIMIT_DEFAULT)
    raw_net = inc.net_short_term_capital_gain_loss + inc.net_long_term_capital_gain_loss
    if raw_net < -loss_limit:
        inc.net_capital_gain_loss = -loss_limit
        inc.capital_loss_carryforward_to_next_year = round(abs(raw_net) - loss_limit, 2)
        # Preserve ST/LT character for carryforward
        # Excess ST loss carries as ST, excess LT loss carries as LT
        remaining_loss = abs(raw_net) - loss_limit
        if inc.net_short_term_capital_gain_loss < 0:
            st_excess = abs(min(0, inc.net_short_term_capital_gain_loss))
            inc.capital_loss_carryforward_remaining_short = round(
                min(st_excess, remaining_loss), 2
            )
            inc.capital_loss_carryforward_remaining_long = round(
                max(0, remaining_loss - st_excess), 2
            )
        else:
            inc.capital_loss_carryforward_remaining_short = 0.0
            inc.capital_loss_carryforward_remaining_long = round(remaining_loss, 2)
    else:
        inc.net_capital_gain_loss = round(raw_net, 2)
        inc.capital_loss_carryforward_to_next_year = 0.0
        inc.capital_loss_carryforward_remaining_short = 0.0
        inc.capital_loss_carryforward_remaining_long = 0.0

    # Business income — IRC §162, Schedule C
    for biz in inp.business_income:
        gross = biz.gross_receipts - biz.returns_and_allowances - biz.cost_of_goods_sold
        expenses = (
            biz.advertising
            + biz.car_and_truck
            + biz.commissions_and_fees
            + biz.contract_labor
            + biz.depreciation
            + biz.insurance
            + biz.interest_mortgage
            + biz.interest_other
            + biz.legal_and_professional
            + biz.office_expense
            + biz.rent_lease
            + biz.repairs_maintenance
            + biz.supplies
            + biz.taxes_licenses
            + biz.travel
            + (biz.meals * 0.5)  # IRC §274 — 50% meal limitation
            + biz.utilities
            + biz.wages
            + biz.other_expenses
            + biz.home_office_deduction
        )
        inc.total_business_income += gross - expenses
    inc.total_business_income = round(inc.total_business_income, 2)

    # Rental income — IRC §61(a)(5), §280A
    for rental in inp.rental_income:
        expenses = (
            rental.advertising
            + rental.auto_and_travel
            + rental.cleaning_and_maintenance
            + rental.commissions
            + rental.insurance
            + rental.legal_and_professional
            + rental.management_fees
            + rental.mortgage_interest
            + rental.repairs
            + rental.supplies
            + rental.taxes
            + rental.utilities
            + rental.depreciation
            + rental.other_expenses
        )
        # IRC §280A(g) — 14-day rental exclusion
        if rental.days_rented < 15:
            continue  # Income excluded, no deductions
        inc.total_rental_income += rental.rental_income - expenses
    inc.total_rental_income = round(inc.total_rental_income, 2)

    # Retirement distributions — IRC §72
    inc.total_retirement_distributions = round(
        sum(r.gross_distribution for r in inp.retirement_distributions), 2
    )
    inc.taxable_retirement_distributions = round(
        sum(
            r.taxable_amount
            for r in inp.retirement_distributions
            if not r.is_qualified_roth_distribution
        ),
        2,
    )

    # Social Security — IRC §86 (computed after provisional income is known)
    if inp.social_security:
        inc.total_social_security = round(
            inp.social_security.total_benefits - inp.social_security.repayments, 2
        )

    # Unemployment — IRC §85
    if inp.unemployment:
        inc.unemployment_compensation = inp.unemployment.amount

    # Home sale — IRC §121
    if inp.home_sale:
        hs = inp.home_sale
        gain = hs.selling_price - hs.selling_expenses - hs.cost_basis - hs.improvements
        exclusion_limit = HOME_SALE_EXCLUSION.get(
            inp.filing_status, HOME_SALE_EXCLUSION_DEFAULT
        )
        if hs.exclusion_used_in_prior_2_years:
            exclusion_limit = 0
        excludable = min(max(gain, 0), exclusion_limit)
        # Depreciation recapture not excludable — IRC §121(d)(6)
        inc.taxable_home_sale_gain = round(
            max(0, gain - excludable) + hs.depreciation_after_may_1997, 2
        )

    # Other income — IRC §61
    inc.total_other_income = round(sum(o.amount for o in inp.other_income), 2)

    # Cancelled debt — IRC §108
    for cd in inp.cancelled_debt:
        if cd.is_bankruptcy or cd.is_student_loan_qualifying:
            continue  # Fully excluded
        if cd.is_principal_residence_debt:
            continue  # Excluded before Jan 1, 2026
        excluded = min(cd.amount_discharged, cd.taxpayer_insolvent_amount)
        inc.total_cancelled_debt_income += cd.amount_discharged - excluded
    inc.total_cancelled_debt_income = round(inc.total_cancelled_debt_income, 2)

    # TASK-001: K-1 ordinary income and guaranteed payments — IRC §702, §704
    for k1 in inp.k1_income:
        inc.total_k1_ordinary_income += (
            k1.ordinary_business_income + k1.other_income - k1.section_179_deduction
        )
        inc.total_k1_guaranteed_payments += k1.guaranteed_payments
        # K-1 rental income flows into total_rental_income
        inc.total_rental_income += k1.net_rental_income
    inc.total_k1_ordinary_income = round(inc.total_k1_ordinary_income, 2)
    inc.total_k1_guaranteed_payments = round(inc.total_k1_guaranteed_payments, 2)
    inc.total_rental_income = round(inc.total_rental_income, 2)

    # TASK-007: Royalty income — IRC §61(a)(6) (title26.md:70865)
    for roy in inp.royalty_income:
        inc.total_royalty_income += roy.gross_royalties - roy.expenses
    inc.total_royalty_income = round(inc.total_royalty_income, 2)

    # TASK-008: Farm income — Schedule F, IRC §162 (title26.md:114102)
    for farm in inp.farm_income:
        gross = (
            farm.gross_farm_income
            + farm.crop_insurance_proceeds
            + farm.ccc_loans_reported_as_income
        )
        expenses = (
            farm.cost_of_livestock_purchased
            + farm.conservation_expenses
            + farm.custom_hire
            + farm.feed
            + farm.fertilizers
            + farm.freight
            + farm.gasoline_fuel
            + farm.labor_hired
            + farm.pension_plans
            + farm.rent_lease_land
            + farm.rent_lease_equipment
            + farm.seeds_plants
            + farm.storage
            + farm.supplies
            + farm.taxes
            + farm.utilities
            + farm.vet_fees
            + farm.other_expenses
            + farm.depreciation
            + farm.car_and_truck
            + farm.insurance
            + farm.interest_mortgage
            + farm.interest_other
            + farm.repairs_maintenance
        )
        inc.total_farm_income += gross - expenses
    inc.total_farm_income = round(inc.total_farm_income, 2)
    if inc.total_farm_income < 0:
        inc.farm_nol_carryback_eligible = True  # §172(b)(1)(B) — 2-year carryback

    # TASK-009: Alimony received — former §71 (pre-2019 instruments only)
    if inp.alimony_received > 0 and inp.alimony_instrument_date:
        try:
            instrument_date = datetime.strptime(
                inp.alimony_instrument_date, "%Y-%m-%d"
            ).date()
            if instrument_date < date(2019, 1, 1):
                inc.alimony_income = round(inp.alimony_received, 2)
        except ValueError:
            pass  # Invalid date — ignore

    # TASK-010: Gambling income — IRC §61 (title26.md:70846)
    if inp.gambling:
        inc.gambling_income = round(
            inp.gambling.w2g_winnings + inp.gambling.other_winnings, 2
        )

    # TASK-011: Annuity income — IRC §72 (title26.md:74051)
    for ann in inp.annuity_income:
        if ann.gross_payment <= 0:
            continue
        remaining_basis = max(
            0, ann.investment_in_contract - ann.amount_previously_recovered
        )
        if remaining_basis <= 0:
            # Fully recovered — all taxable
            inc.annuity_taxable_amount += ann.gross_payment
        elif ann.use_simplified_method:
            # Simplified method — IRC §72(d)(1)
            age = ann.annuitant_age_at_start
            if age <= 55:
                divisor = 360
            elif age <= 60:
                divisor = 310
            elif age <= 65:
                divisor = 260
            elif age <= 70:
                divisor = 210
            else:
                divisor = 160
            excluded_per_payment = ann.investment_in_contract / divisor
            excluded = min(excluded_per_payment, ann.gross_payment, remaining_basis)
            inc.annuity_taxable_amount += ann.gross_payment - excluded
        else:
            # Exclusion ratio method
            if ann.expected_return > 0:
                ratio = min(1.0, ann.investment_in_contract / ann.expected_return)
                excluded = min(ann.gross_payment * ratio, remaining_basis)
                inc.annuity_taxable_amount += ann.gross_payment - excluded
            else:
                inc.annuity_taxable_amount += ann.gross_payment
    inc.annuity_taxable_amount = round(inc.annuity_taxable_amount, 2)

    # TASK-012: Scholarship income — IRC §117 (title26.md:89656)
    for sch in inp.scholarship_income:
        taxable = sch.total_scholarship - sch.qualified_tuition_and_fees
        inc.taxable_scholarship_income += max(0, taxable)
    inc.taxable_scholarship_income = round(inc.taxable_scholarship_income, 2)

    # TASK-023: Restricted stock income — IRC §83 (title26.md:78996)
    for rse in inp.restricted_stock_events:
        if rse.section_83b_election:
            income = (rse.fmv_at_grant * rse.shares) - rse.amount_paid
        else:
            income = (rse.fmv_at_vesting * rse.shares) - rse.amount_paid
        inc.restricted_stock_income += max(0, income)
    inc.restricted_stock_income = round(inc.restricted_stock_income, 2)

    # TASK-021: Section 529 distributions — IRC §529 (title26.md:263347)
    total_529_penalty = 0.0
    for dist529 in inp.section_529_distributions:
        if dist529.gross_distribution <= 0:
            continue
        qualified = dist529.qualified_education_expenses
        if dist529.is_k12_tuition:
            qualified = min(qualified, 10000)  # $10k/year cap for K-12
        qualified += min(dist529.student_loan_repayment, 10000)  # $10k lifetime cap
        qualified += dist529.rollover_to_roth
        non_qualified_portion = max(0, dist529.gross_distribution - qualified)
        if non_qualified_portion > 0 and dist529.earnings_portion > 0:
            earnings_ratio = dist529.earnings_portion / dist529.gross_distribution
            taxable_earnings = non_qualified_portion * earnings_ratio
            inc.taxable_529_income += taxable_earnings
            total_529_penalty += taxable_earnings * 0.10  # 10% penalty
    inc.taxable_529_income = round(inc.taxable_529_income, 2)

    # TASK-022: Like-kind exchanges — IRC §1031 (title26.md:342673)
    for lke in inp.like_kind_exchanges:
        realized_gain = lke.fmv_relinquished - lke.adjusted_basis_relinquished
        net_boot = (
            lke.boot_received
            + lke.liabilities_relieved
            - lke.boot_paid
            - lke.liabilities_assumed
        )
        net_boot = max(0, net_boot)
        recognized = min(max(0, realized_gain), net_boot)
        deferred = max(0, realized_gain - recognized)
        inc.like_kind_recognized_gain += recognized
        inc.like_kind_deferred_gain += deferred
    inc.like_kind_recognized_gain = round(inc.like_kind_recognized_gain, 2)
    inc.like_kind_deferred_gain = round(inc.like_kind_deferred_gain, 2)

    # Compute provisional income for SS taxation BEFORE finalizing gross income
    provisional = (
        inc.total_wages
        + inc.total_interest
        + inc.total_ordinary_dividends
        + inc.net_capital_gain_loss
        + inc.total_business_income
        + inc.total_rental_income
        + inc.taxable_retirement_distributions
        + inc.unemployment_compensation
        + inc.taxable_home_sale_gain
        + inc.total_other_income
        + inc.total_cancelled_debt_income
        + inc.total_k1_ordinary_income
        + inc.total_k1_guaranteed_payments
        + inc.total_royalty_income
        + inc.total_farm_income
        + inc.alimony_income
        + inc.gambling_income
        + inc.annuity_taxable_amount
        + inc.taxable_scholarship_income
        + inc.restricted_stock_income
        + inc.taxable_529_income
        + inc.like_kind_recognized_gain
        + inc.tax_exempt_interest  # Tax-exempt interest included in provisional
        + (inc.total_social_security * 0.5)
    )

    if inp.social_security:
        inc.taxable_social_security = _compute_social_security_taxable(
            inc.total_social_security, provisional, inp.filing_status
        )

    # Gross income — IRC §61
    inc.gross_income = round(
        inc.total_wages
        + inc.total_interest
        + inc.total_ordinary_dividends
        + inc.net_capital_gain_loss
        + inc.total_business_income
        + inc.total_rental_income
        + inc.taxable_retirement_distributions
        + inc.taxable_social_security
        + inc.unemployment_compensation
        + inc.taxable_home_sale_gain
        + inc.total_other_income
        + inc.total_cancelled_debt_income
        + inc.total_k1_ordinary_income
        + inc.total_k1_guaranteed_payments
        + inc.total_royalty_income
        + inc.total_farm_income
        + inc.alimony_income
        + inc.gambling_income
        + inc.annuity_taxable_amount
        + inc.taxable_scholarship_income
        + inc.restricted_stock_income
        + inc.taxable_529_income
        + inc.like_kind_recognized_gain,
        2,
    )
    out.income = inc

    # ===== STEP 2: Compute Self-Employment Tax =====
    # Must compute before AGI since 50% SE tax is an above-the-line deduction
    net_se = inc.total_business_income + sum(
        o.amount for o in inp.other_income if o.is_subject_to_se_tax
    )
    # TASK-001: K-1 self-employment earnings — IRC §1401
    for k1 in inp.k1_income:
        net_se += k1.self_employment_earnings
        net_se += k1.guaranteed_payments  # Guaranteed payments are always SE income
    # TASK-008: Farm income — IRC §1401
    for farm in inp.farm_income:
        if farm.is_material_participant:
            gross = (
                farm.gross_farm_income
                + farm.crop_insurance_proceeds
                + farm.ccc_loans_reported_as_income
            )
            expenses = (
                farm.cost_of_livestock_purchased
                + farm.conservation_expenses
                + farm.custom_hire
                + farm.feed
                + farm.fertilizers
                + farm.freight
                + farm.gasoline_fuel
                + farm.labor_hired
                + farm.pension_plans
                + farm.rent_lease_land
                + farm.rent_lease_equipment
                + farm.seeds_plants
                + farm.storage
                + farm.supplies
                + farm.taxes
                + farm.utilities
                + farm.vet_fees
                + farm.other_expenses
                + farm.depreciation
                + farm.car_and_truck
                + farm.insurance
                + farm.interest_mortgage
                + farm.interest_other
                + farm.repairs_maintenance
            )
            net_se += gross - expenses
    # TASK-007: Royalty income subject to SE tax
    for roy in inp.royalty_income:
        if roy.is_subject_to_se_tax:
            net_se += roy.gross_royalties - roy.expenses
    w2_ss_wages = sum(w.social_security_wages for w in inp.w2_income)
    out.se_tax = _compute_self_employment_tax(net_se, inp.filing_status, w2_ss_wages)

    # ===== STEP 3: Compute AGI — IRC §62 (title26.md:71233) =====
    agi_comp = AGIComputation()
    agi_comp.gross_income = inc.gross_income

    # Educator expenses — IRC §62(a)(2)(D), max $250
    agi_comp.educator_expenses_deduction = min(inp.educator_expenses, 250)

    # SE tax deduction — IRC §164(f)
    agi_comp.se_tax_deduction = out.se_tax.se_tax_deduction

    # IRA deduction — IRC §219 (title26.md:149106)
    for contrib in inp.ira_contributions:
        if contrib.account_type == RetirementAccountType.TRADITIONAL_IRA:
            limit = IRA_CONTRIBUTION_LIMIT
            if taxpayer_age >= 50:
                limit += IRA_CATCHUP_50_PLUS
            deductible = min(contrib.contribution_amount, limit)
            # Phase-out for active participants handled by simplified check
            if contrib.is_active_participant_in_employer_plan:
                # Simplified: reduce proportionally (actual phase-out depends on MAGI)
                pass  # Full phase-out calculation would require iterative AGI
            agi_comp.ira_deduction += deductible
    agi_comp.ira_deduction = round(agi_comp.ira_deduction, 2)

    # Student loan interest — IRC §221 (title26.md:151853)
    sli = min(inp.student_loan_interest_paid, STUDENT_LOAN_INTEREST_MAX)
    # Phase-out applied after AGI is computed (simplified: use gross income as proxy)
    threshold = STUDENT_LOAN_PHASEOUT_START.get(
        inp.filing_status, STUDENT_LOAN_PHASEOUT_START_DEFAULT
    )
    phaseout_range = STUDENT_LOAN_PHASEOUT_RANGE.get(
        inp.filing_status, STUDENT_LOAN_PHASEOUT_RANGE_DEFAULT
    )
    if inc.gross_income > threshold:
        excess = inc.gross_income - threshold
        reduction = sli * min(1, excess / phaseout_range)
        sli = max(0, sli - reduction)
    agi_comp.student_loan_interest_deduction = round(sli, 2)

    # HSA deduction — IRC §223 (title26.md:152303)
    if inp.hsa:
        limit = HSA_LIMIT_SELF if inp.hsa.is_self_only_coverage else HSA_LIMIT_FAMILY
        if taxpayer_age >= 55:
            limit += HSA_CATCHUP
        total_contributions = (
            inp.hsa.taxpayer_contributions + inp.hsa.employer_contributions
        )
        agi_comp.hsa_deduction = round(
            min(
                inp.hsa.taxpayer_contributions,
                max(0, limit - inp.hsa.employer_contributions),
            ),
            2,
        )

    # Alimony (pre-2019 instruments) — IRC §215 (repealed for post-2018)
    agi_comp.alimony_deduction = inp.alimony_paid

    # Qualified tips — IRC §224 (title26.md:153381)
    if inp.qualified_tips > 0 and inp.tax_year >= 2025 and inp.tax_year <= 2028:
        tips_ded = min(inp.qualified_tips, TIPS_DEDUCTION_MAX)
        threshold = TIPS_PHASEOUT_THRESHOLD.get(
            inp.filing_status, TIPS_PHASEOUT_THRESHOLD_DEFAULT
        )
        tips_ded = _phaseout_amount(tips_ded, inc.gross_income, threshold)
        agi_comp.qualified_tips_deduction = tips_ded

    # Qualified overtime — IRC §225 (title26.md:153525)
    if inp.qualified_overtime > 0 and inp.tax_year >= 2025 and inp.tax_year <= 2028:
        ot_max = OVERTIME_DEDUCTION_MAX.get(
            inp.filing_status, OVERTIME_DEDUCTION_MAX_DEFAULT
        )
        ot_ded = min(inp.qualified_overtime, ot_max)
        threshold = OVERTIME_PHASEOUT_THRESHOLD.get(
            inp.filing_status, OVERTIME_PHASEOUT_THRESHOLD_DEFAULT
        )
        ot_ded = _phaseout_amount(ot_ded, inc.gross_income, threshold)
        agi_comp.qualified_overtime_deduction = ot_ded

    # Early withdrawal penalty
    agi_comp.early_withdrawal_penalty = inp.early_withdrawal_penalty

    # TASK-024: Savings bond education exclusion — IRC §135 (title26.md:90338)
    if inp.savings_bond_education:
        sbe = inp.savings_bond_education
        net_qualified = max(
            0, sbe.qualified_education_expenses - sbe.scholarships_and_grants
        )
        if sbe.total_bond_proceeds > 0 and net_qualified > 0:
            ratio = min(1.0, net_qualified / sbe.total_bond_proceeds)
            excludable = sbe.bond_interest * ratio
            # Apply MAGI phase-out
            phaseout_start = SAVINGS_BOND_PHASEOUT_START.get(
                inp.filing_status, SAVINGS_BOND_PHASEOUT_START_DEFAULT
            )
            phaseout_range = SAVINGS_BOND_PHASEOUT_RANGE.get(
                inp.filing_status, SAVINGS_BOND_PHASEOUT_RANGE_DEFAULT
            )
            # Use gross income as proxy for MAGI (before this exclusion)
            if inc.gross_income > phaseout_start:
                excess = inc.gross_income - phaseout_start
                reduction_pct = min(1.0, excess / phaseout_range)
                excludable *= 1 - reduction_pct
            agi_comp.savings_bond_interest_excluded = round(max(0, excludable), 2)

    # Total adjustments
    agi_comp.total_adjustments = round(
        agi_comp.educator_expenses_deduction
        + agi_comp.ira_deduction
        + agi_comp.student_loan_interest_deduction
        + agi_comp.hsa_deduction
        + agi_comp.se_tax_deduction
        + agi_comp.alimony_deduction
        + agi_comp.qualified_tips_deduction
        + agi_comp.qualified_overtime_deduction
        + agi_comp.early_withdrawal_penalty
        + agi_comp.savings_bond_interest_excluded,
        2,
    )
    agi_comp.agi = round(agi_comp.gross_income - agi_comp.total_adjustments, 2)
    out.agi = agi_comp

    agi = agi_comp.agi

    # ===== STEP 4: Compute Deductions — IRC §63 (title26.md:72402) =====
    ded = DeductionComputation()

    # Standard deduction — IRC §63(c)
    ded.basic_standard_deduction = STANDARD_DEDUCTION[inp.filing_status]

    # Additional standard deduction — IRC §63(f)
    is_married = _is_married_status(inp.filing_status)
    additional_amount = (
        ADDITIONAL_STD_DEDUCTION_MARRIED
        if is_married
        else ADDITIONAL_STD_DEDUCTION_UNMARRIED
    )

    if taxpayer_age >= 65:
        ded.additional_standard_deduction_age += additional_amount
    if inp.personal_info.is_blind:
        ded.additional_standard_deduction_blind += additional_amount
    if inp.spouse_info:
        if spouse_age >= 65:
            ded.additional_standard_deduction_age += ADDITIONAL_STD_DEDUCTION_MARRIED
        if inp.spouse_info.is_blind:
            ded.additional_standard_deduction_blind += ADDITIONAL_STD_DEDUCTION_MARRIED

    ded.total_standard_deduction = (
        ded.basic_standard_deduction
        + ded.additional_standard_deduction_age
        + ded.additional_standard_deduction_blind
    )

    # Itemized deductions
    # Medical — IRC §213 (title26.md:147452)
    if inp.medical_expenses:
        total_medical = (
            inp.medical_expenses.total_medical_dental
            + inp.medical_expenses.health_insurance_premiums
            + inp.medical_expenses.long_term_care_premiums
            + inp.medical_expenses.prescription_drugs
            + inp.medical_expenses.medical_travel
        )
        threshold = round(agi * MEDICAL_EXPENSE_AGI_THRESHOLD, 2)
        ded.medical_deduction = round(max(0, total_medical - threshold), 2)

    # SALT — IRC §164 (title26.md:119300-119543)
    if inp.state_local_taxes:
        slt = inp.state_local_taxes
        if slt.elect_sales_tax:
            income_or_sales = slt.sales_tax_paid
        else:
            income_or_sales = slt.state_income_tax_paid + slt.local_income_tax_paid
        total_salt = income_or_sales + slt.real_property_tax + slt.personal_property_tax

        cap = SALT_CAP.get(inp.filing_status, SALT_CAP_DEFAULT)
        # Phase-down for high earners
        pd_threshold = SALT_PHASE_DOWN_THRESHOLD.get(
            inp.filing_status, SALT_PHASE_DOWN_THRESHOLD_DEFAULT
        )
        if agi > pd_threshold:
            excess = agi - pd_threshold
            reduction = cap * 0.30 * (excess / cap) if cap > 0 else 0
            cap = max(10000, cap - reduction)

        ded.salt_deduction = round(min(total_salt, cap), 2)

    # Mortgage interest — IRC §163(h)
    for mtg in inp.mortgage_interest:
        ded.mortgage_interest_deduction += mtg.mortgage_interest_paid + mtg.points_paid
    ded.mortgage_interest_deduction = round(ded.mortgage_interest_deduction, 2)

    # Charitable contributions — IRC §170 (title26.md:132628)
    total_cash_charity = 0.0
    total_noncash_charity = 0.0
    for ch in inp.charitable_contributions:
        total_cash_charity += ch.cash_amount
        total_noncash_charity += ch.noncash_amount

    # TASK-014: Add prior year carryforward — IRC §170(d)
    total_cash_charity += inp.charitable_contribution_carryforward

    # Apply AGI limitations — IRC §170(b)
    cash_limit = agi * 0.60  # 60% for cash to public charities
    noncash_limit = agi * 0.30  # 30% for capital gain property
    cash_deductible = min(total_cash_charity, cash_limit)
    noncash_deductible = min(total_noncash_charity, noncash_limit)
    ded.charitable_deduction = round(cash_deductible + noncash_deductible, 2)

    # Track carryforward usage and new excess
    carryforward_used = min(inp.charitable_contribution_carryforward, cash_deductible)
    ded.charitable_carryforward_used = round(carryforward_used, 2)
    excess_cash = max(0, total_cash_charity - cash_limit)
    excess_noncash = max(0, total_noncash_charity - noncash_limit)
    ded.charitable_carryforward_remaining = round(excess_cash + excess_noncash, 2)
    out.charitable_contribution_carryforward = ded.charitable_carryforward_remaining

    # TASK-018: Casualty losses — IRC §165(h) (title26.md:120131)
    total_casualty_after_floors = 0.0
    if inp.casualty_losses:
        for event in inp.casualty_losses:
            # Post-2017: must be federally declared disaster
            if not event.fema_disaster_declaration_number:
                continue
            decline_fmv = event.fair_market_value_before - event.fair_market_value_after
            loss = min(decline_fmv, event.adjusted_basis)
            loss -= event.insurance_reimbursement + event.other_reimbursement
            loss = max(0, loss)
            # Per-event $500 floor — IRC §165(h)(1)
            loss = max(0, loss - CASUALTY_LOSS_PER_EVENT_FLOOR)
            total_casualty_after_floors += loss
        # 10% AGI threshold — IRC §165(h)(2)
        ded.casualty_loss_deduction = round(
            max(0, total_casualty_after_floors - agi * CASUALTY_LOSS_AGI_THRESHOLD), 2
        )
    elif inp.casualty_loss_from_disaster > 0:
        # Legacy simple field
        after_floor = max(
            0, inp.casualty_loss_from_disaster - CASUALTY_LOSS_PER_EVENT_FLOOR
        )
        ded.casualty_loss_deduction = round(
            max(0, after_floor - agi * CASUALTY_LOSS_AGI_THRESHOLD), 2
        )

    # TASK-010: Gambling loss deduction — IRC §165(d)
    if inp.gambling and inp.gambling.losses > 0:
        if (
            ded.deduction_method_used == DeductionMethod.ITEMIZED
            or inp.deduction_method == DeductionMethod.ITEMIZED
        ):
            # Losses limited to 90% of wagering losses AND capped at winnings
            max_loss = min(inp.gambling.losses * 0.90, inc.gambling_income)
            ded.gambling_loss_deduction = round(max(0, max_loss), 2)

    # TASK-025: Investment interest — IRC §163(d) (title26.md:116555)
    net_investment_income = (
        inc.total_interest
        + inc.total_ordinary_dividends
        - inc.total_qualified_dividends  # Qualified dividends not NII by default
        + max(0, inc.net_short_term_capital_gain_loss)
        + inc.total_royalty_income
    )
    # §163(d)(4)(B) election: include qualified dividends/LTCG in NII
    if inp.elect_to_include_qualified_dividends_in_nii:
        net_investment_income += inc.total_qualified_dividends
        net_investment_income += max(0, inc.net_long_term_capital_gain_loss)
    net_investment_income = max(0, net_investment_income)

    total_inv_interest = (
        inp.investment_interest_expense + inp.investment_interest_carryforward
    )
    ded.investment_interest_deduction = round(
        min(total_inv_interest, net_investment_income), 2
    )
    ded.investment_interest_carryforward_to_next_year = round(
        max(0, total_inv_interest - net_investment_income), 2
    )

    ded.total_itemized_deductions = round(
        ded.medical_deduction
        + ded.salt_deduction
        + ded.mortgage_interest_deduction
        + ded.charitable_deduction
        + ded.casualty_loss_deduction
        + ded.gambling_loss_deduction
        + ded.investment_interest_deduction,
        2,
    )

    # Determine deduction method
    if inp.deduction_method == DeductionMethod.ITEMIZED:
        ded.deduction_method_used = DeductionMethod.ITEMIZED
        ded.deduction_amount = ded.total_itemized_deductions
    else:
        # Use whichever is greater
        if ded.total_itemized_deductions > ded.total_standard_deduction:
            ded.deduction_method_used = DeductionMethod.ITEMIZED
            ded.deduction_amount = ded.total_itemized_deductions
        else:
            ded.deduction_method_used = DeductionMethod.STANDARD
            ded.deduction_amount = ded.total_standard_deduction

    # QBI deduction — IRC §199A (title26.md:146332)
    if inp.qbi:
        total_qbi_deduction = 0.0
        for qbi in inp.qbi:
            qbi_ded = qbi.qualified_business_income * 0.20
            # Simplified: W-2 wage limitation check for high income
            # Full phase-in logic omitted for brevity
            total_qbi_deduction += max(0, qbi_ded)
        # Also include REIT dividends and PTP income
        total_qbi_deduction += sum(q.reit_dividends * 0.20 for q in inp.qbi)
        total_qbi_deduction += sum(q.ptp_income * 0.20 for q in inp.qbi)

        # Cap at 20% of (taxable income - net capital gain) — IRC §199A(a)
        preliminary_taxable = agi - ded.deduction_amount
        cap = max(0, preliminary_taxable - max(0, inc.net_capital_gain_loss)) * 0.20
        ded.qbi_deduction = round(min(total_qbi_deduction, cap), 2)

    # Senior deduction — IRC §151(f) (title26.md:112427-112471)
    if inp.tax_year < 2029:
        seniors = 0
        if taxpayer_age >= 65:
            seniors += 1
        if inp.spouse_info and spouse_age >= 65:
            if inp.filing_status == FilingStatus.MARRIED_FILING_JOINTLY:
                seniors += 1
        if seniors > 0:
            total_senior = SENIOR_DEDUCTION_AMOUNT * seniors
            threshold = SENIOR_DEDUCTION_PHASEOUT_THRESHOLD.get(
                inp.filing_status, SENIOR_DEDUCTION_PHASEOUT_THRESHOLD_DEFAULT
            )
            if agi > threshold:
                reduction = total_senior * 0.06 * ((agi - threshold) / 1000)
                total_senior = max(0, total_senior - reduction)
            ded.senior_deduction = round(total_senior, 2)

    # TASK-013: Net Operating Loss deduction — IRC §172 (title26.md:137738)
    preliminary_taxable = max(
        0, agi - ded.deduction_amount - ded.qbi_deduction - ded.senior_deduction
    )
    nol_deduction = 0.0
    # Pre-2018 NOLs: no 80% limitation
    if inp.nol_carryforward_pre_2018 > 0:
        pre2018_used = min(inp.nol_carryforward_pre_2018, preliminary_taxable)
        nol_deduction += pre2018_used
        preliminary_taxable -= pre2018_used
    # Post-2017 NOLs: limited to 80% of remaining taxable income
    if inp.nol_carryforward > 0 and preliminary_taxable > 0:
        post2017_limit = preliminary_taxable * 0.80
        post2017_used = min(inp.nol_carryforward, post2017_limit)
        nol_deduction += post2017_used
    ded.nol_deduction = round(nol_deduction, 2)
    total_nol_available = inp.nol_carryforward + inp.nol_carryforward_pre_2018
    ded.nol_carryforward_remaining = round(
        max(0, total_nol_available - nol_deduction), 2
    )

    # Taxable income — IRC §63
    ded.taxable_income = round(
        max(
            0,
            agi
            - ded.deduction_amount
            - ded.qbi_deduction
            - ded.senior_deduction
            - ded.nol_deduction,
        ),
        2,
    )
    out.deductions = ded

    # ===== STEP 5: Compute Tax — IRC §1 (title26.md:5292) =====
    tax = TaxComputation()

    # Split income into ordinary and preferential
    preferential = (
        max(0, inc.net_long_term_capital_gain_loss) + inc.total_qualified_dividends
    )
    ordinary_taxable = max(0, ded.taxable_income - preferential)

    # Ordinary income tax — IRC §1(a)-(d)
    tax.ordinary_income_tax, tax.tax_bracket_details = _compute_bracket_tax(
        ordinary_taxable, inp.filing_status
    )

    # Capital gains tax — IRC §1(h)
    if preferential > 0:
        tax.qualified_dividends_and_ltcg = round(preferential, 2)
        cg_result = _compute_capital_gains_tax(
            max(0, inc.net_long_term_capital_gain_loss),
            inc.total_qualified_dividends,
            ded.taxable_income,
            inp.filing_status,
        )
        tax.capital_gains_tax_at_0_pct = cg_result["at_0"]
        tax.capital_gains_tax_at_15_pct = cg_result["at_15"]
        tax.capital_gains_tax_at_20_pct = cg_result["at_20"]

    tax.total_income_tax = round(
        tax.ordinary_income_tax
        + tax.capital_gains_tax_at_0_pct
        + tax.capital_gains_tax_at_15_pct
        + tax.capital_gains_tax_at_20_pct
        + tax.collectibles_gain_tax
        + tax.unrecaptured_1250_gain_tax,
        2,
    )

    # TASK-003: AMT — IRC §55 (title26.md:64924-65100)
    # Compute AMTI: taxable income + SALT addback + preference items
    amt_adjustments = 0.0
    if ded.deduction_method_used == DeductionMethod.ITEMIZED:
        amt_adjustments += ded.salt_deduction  # SALT not deductible for AMT
    # Add AMT preference items — IRC §56, §57
    if inp.amt_preferences:
        amt_adjustments += inp.amt_preferences.iso_exercise_spread
        amt_adjustments += inp.amt_preferences.private_activity_bond_interest
        amt_adjustments += inp.amt_preferences.depletion_excess
        amt_adjustments += inp.amt_preferences.intangible_drilling_costs_excess
        amt_adjustments += inp.amt_preferences.other_adjustments
    tax.amti = round(ded.taxable_income + amt_adjustments, 2)

    exemption = AMT_EXEMPTION[inp.filing_status]
    phaseout_threshold = AMT_PHASEOUT_THRESHOLD[inp.filing_status]
    if tax.amti > phaseout_threshold:
        exemption_reduction = (tax.amti - phaseout_threshold) * 0.25
        exemption = max(0, exemption - exemption_reduction)
    tax.amt_exemption = round(exemption, 2)

    amt_taxable = max(0, tax.amti - tax.amt_exemption)
    rate_threshold = AMT_RATE_THRESHOLD
    if inp.filing_status == FilingStatus.MARRIED_FILING_SEPARATELY:
        rate_threshold = AMT_RATE_THRESHOLD / 2
    if amt_taxable <= rate_threshold:
        tax.tentative_minimum_tax = round(amt_taxable * 0.26, 2)
    else:
        tax.tentative_minimum_tax = round(
            rate_threshold * 0.26 + (amt_taxable - rate_threshold) * 0.28, 2
        )

    tax.amt = round(max(0, tax.tentative_minimum_tax - tax.total_income_tax), 2)

    # Apply prior year AMT credit — IRC §53
    if inp.amt_preferences and inp.amt_preferences.prior_year_amt_credit > 0:
        # Credit against regular tax in excess of TMT
        regular_over_tmt = max(0, tax.total_income_tax - tax.tentative_minimum_tax)
        tax.prior_year_amt_credit_used = round(
            min(inp.amt_preferences.prior_year_amt_credit, regular_over_tmt), 2
        )

    # TASK-019: Net Investment Income Tax — IRC §1411
    niit_threshold = NIIT_THRESHOLD[inp.filing_status]
    if inp.net_investment_income_override is not None:
        tax.net_investment_income = round(inp.net_investment_income_override, 2)
    else:
        tax.net_investment_income = round(
            max(
                0,
                inc.total_interest
                + inc.total_ordinary_dividends
                + max(0, inc.net_capital_gain_loss)
                + inc.total_rental_income
                + inc.total_royalty_income
                + inc.annuity_taxable_amount
                + inc.taxable_529_income
                + inc.like_kind_recognized_gain,
            ),
            2,
        )
    magi_over_threshold = max(0, agi - niit_threshold)
    if magi_over_threshold > 0 and tax.net_investment_income > 0:
        tax.niit_amount = round(
            min(tax.net_investment_income, magi_over_threshold) * NIIT_RATE, 2
        )

    # TASK-020: Additional Medicare Tax (employee side) — IRC §3101(b)(2)
    # SE portion already computed in se_tax.additional_medicare_tax
    addl_medicare_threshold = ADDITIONAL_MEDICARE_THRESHOLD[inp.filing_status]
    total_medicare_wages = sum(w.medicare_wages for w in inp.w2_income)
    wage_excess = max(0, total_medicare_wages - addl_medicare_threshold)
    if wage_excess > 0:
        tax.additional_medicare_tax = round(
            wage_excess * ADDITIONAL_MEDICARE_TAX_RATE, 2
        )
    tax.additional_medicare_tax_withheld = round(
        sum(w.additional_medicare_tax_withheld for w in inp.w2_income), 2
    )

    # TASK-017: Kiddie tax — IRC §1(g) (title26.md:5520)
    if inp.kiddie_tax:
        kt = inp.kiddie_tax
        child_age = taxpayer_age  # The taxpayer IS the child in this case
        applies = False
        if child_age < 18:
            applies = True
        elif (
            child_age < 24
            and kt.child_is_full_time_student
            and not kt.child_provides_over_half_support
        ):
            applies = True
        if applies and kt.child_unearned_income > KIDDIE_TAX_THRESHOLD:
            # Tax the excess at parent's marginal rate
            excess = kt.child_unearned_income - KIDDIE_TAX_THRESHOLD
            if kt.parent_marginal_rate > 0:
                parent_rate = kt.parent_marginal_rate
            else:
                # Compute parent's marginal rate from their taxable income
                _, parent_brackets = _compute_bracket_tax(
                    kt.parent_taxable_income, kt.parent_filing_status
                )
                parent_rate = parent_brackets[-1]["rate"] if parent_brackets else 0.10
            # Kiddie tax = excess unearned income * (parent rate - child rate)
            _, child_brackets = _compute_bracket_tax(
                ded.taxable_income, inp.filing_status
            )
            child_rate = child_brackets[-1]["rate"] if child_brackets else 0.10
            if parent_rate > child_rate:
                tax.kiddie_tax_amount = round(excess * (parent_rate - child_rate), 2)

    tax.total_tax_before_credits = round(
        tax.total_income_tax
        + tax.amt
        + tax.niit_amount
        + tax.additional_medicare_tax
        + tax.kiddie_tax_amount,
        2,
    )
    out.tax = tax

    # ===== STEP 6: Compute Credits =====
    cred = CreditComputation()

    # Child Tax Credit — IRC §24 (title26.md:13963-14190)
    qualifying_children_under_17 = 0
    other_dependents = 0
    qualifying_children_for_eitc = 0
    for dep in inp.dependents:
        dep_age = _get_age(dep.date_of_birth, inp.tax_year)
        if dep_age < 17:
            qualifying_children_under_17 += 1
        else:
            other_dependents += 1
        # EITC qualifying children — different age test
        if dep.relationship.value == "qualifying_child" and dep_age < 19:
            qualifying_children_for_eitc += 1
        elif (
            dep.relationship.value == "qualifying_child"
            and dep.is_full_time_student
            and dep_age < 24
        ):
            qualifying_children_for_eitc += 1
        elif dep.is_permanently_disabled:
            qualifying_children_for_eitc += 1

    total_ctc = CHILD_TAX_CREDIT_AMOUNT * qualifying_children_under_17
    total_odc = OTHER_DEPENDENT_CREDIT * other_dependents

    # Phase-out — IRC §24(b)
    ctc_threshold = CTC_PHASE_OUT_THRESHOLD.get(
        inp.filing_status, CTC_PHASE_OUT_THRESHOLD_DEFAULT
    )
    if agi > ctc_threshold:
        excess = agi - ctc_threshold
        reduction = (excess // 1000) * 50
        total_ctc = max(0, total_ctc - reduction)
        remaining_reduction = max(
            0,
            reduction
            - (CHILD_TAX_CREDIT_AMOUNT * qualifying_children_under_17 - total_ctc),
        )
        total_odc = max(
            0,
            total_odc
            - max(
                0, reduction - (CHILD_TAX_CREDIT_AMOUNT * qualifying_children_under_17)
            ),
        )

    # Split into nonrefundable and refundable (Additional CTC)
    # Nonrefundable portion limited to tax liability (applied later)
    cred.child_tax_credit_nonrefundable = round(total_ctc, 2)
    cred.other_dependent_credit = round(total_odc, 2)

    # Additional CTC (refundable) — IRC §24(d)
    earned_income = inc.total_wages + max(0, inc.total_business_income)
    refundable_ctc = min(
        qualifying_children_under_17 * CTC_REFUNDABLE_MAX,
        max(0, earned_income - 2500) * 0.15,
    )
    cred.additional_child_tax_credit = round(refundable_ctc, 2)

    # TASK-005: Adoption credit — IRC §23 (title26.md:13227-13323)
    for adoption in inp.adoption_expenses:
        if adoption.is_special_needs:
            qualified = ADOPTION_CREDIT_MAX  # Deemed full amount
        else:
            qualified = min(adoption.qualified_expenses, ADOPTION_CREDIT_MAX)
        qualified += adoption.prior_year_carryforward
        # AGI phase-out
        if agi > ADOPTION_CREDIT_PHASEOUT_START:
            excess = agi - ADOPTION_CREDIT_PHASEOUT_START
            reduction_pct = min(1.0, excess / ADOPTION_CREDIT_PHASEOUT_RANGE)
            qualified *= 1 - reduction_pct
        qualified = round(max(0, qualified), 2)
        # Split into refundable ($5,000 max) and nonrefundable
        refundable = min(qualified, ADOPTION_CREDIT_REFUNDABLE_MAX)
        nonrefundable = qualified - refundable
        cred.adoption_credit_refundable += refundable
        cred.adoption_credit_nonrefundable += nonrefundable
    cred.adoption_credit_refundable = round(cred.adoption_credit_refundable, 2)
    cred.adoption_credit_nonrefundable = round(cred.adoption_credit_nonrefundable, 2)

    # TASK-006: Credit for elderly or disabled — IRC §22 (title26.md:12756-12865)
    if inp.elderly_disabled_info:
        edi = inp.elderly_disabled_info
        is_65_or_older = taxpayer_age >= 65
        qualifies = is_65_or_older or edi.is_permanently_totally_disabled
        if qualifies:
            # Determine initial amount
            if inp.filing_status == FilingStatus.MARRIED_FILING_JOINTLY:
                spouse_qualifies = False
                if inp.spouse_info:
                    spouse_65 = spouse_age >= 65
                    spouse_qualifies = spouse_65 or edi.is_permanently_totally_disabled
                if qualifies and spouse_qualifies:
                    initial = ELDERLY_DISABLED_INITIAL_JOINT_BOTH
                else:
                    initial = ELDERLY_DISABLED_INITIAL_JOINT_ONE
            elif inp.filing_status == FilingStatus.MARRIED_FILING_SEPARATELY:
                initial = ELDERLY_DISABLED_INITIAL_MFS
            else:
                initial = ELDERLY_DISABLED_INITIAL_SINGLE
            # Reduce by nontaxable SS and VA benefits
            initial -= edi.nontaxable_social_security + edi.nontaxable_va_pension
            # Reduce by 50% of AGI over threshold
            agi_threshold = (
                ELDERLY_DISABLED_AGI_THRESHOLD_JOINT
                if inp.filing_status == FilingStatus.MARRIED_FILING_JOINTLY
                else ELDERLY_DISABLED_AGI_THRESHOLD_SINGLE
            )
            if agi > agi_threshold:
                initial -= (agi - agi_threshold) * 0.5
            initial = max(0, initial)
            cred.elderly_disabled_credit = round(
                initial * ELDERLY_DISABLED_CREDIT_RATE, 2
            )

    # Child and Dependent Care Credit — IRC §21 (title26.md:12007-12114)
    if inp.child_care_expenses:
        total_care = sum(c.amount_paid for c in inp.child_care_expenses)
        num_care_recipients = len(
            set(c.care_recipient_ssn for c in inp.child_care_expenses)
        )
        max_expenses = (
            DEPENDENT_CARE_MAX_TWO_PLUS
            if num_care_recipients >= 2
            else DEPENDENT_CARE_MAX_ONE
        )
        qualifying_expenses = min(total_care, max_expenses)

        # Credit percentage — IRC §21(a)(2)
        if agi <= 15000:
            pct = 0.50
        elif agi <= 45000:
            pct = max(0.35, 0.50 - (agi - 15000) // 2000 * 0.01)
        elif agi <= 75000:
            pct = max(0.20, 0.35 - (agi - 45000) // 2000 * 0.01)
        elif agi <= 150000:
            pct = 0.20
        else:
            pct = 0.20
        cred.child_dependent_care_credit = round(qualifying_expenses * pct, 2)

    # Education Credits — IRC §25A (title26.md:16106-16243)
    for edu in inp.education_expenses:
        qualified_expenses = max(
            0, edu.qualified_tuition_and_fees - edu.scholarships_and_grants
        )
        # Phase-out
        phaseout_start = EDUCATION_CREDIT_PHASEOUT_START.get(
            inp.filing_status, EDUCATION_CREDIT_PHASEOUT_START_DEFAULT
        )
        phaseout_range = (
            EDUCATION_CREDIT_PHASEOUT_RANGE_JOINT
            if inp.filing_status == FilingStatus.MARRIED_FILING_JOINTLY
            else EDUCATION_CREDIT_PHASEOUT_RANGE
        )

        if edu.credit_type == EducationCreditType.AOTC:
            # AOTC: 100% of first $2000 + 25% of next $2000 = max $2500
            credit = (
                min(2000, qualified_expenses)
                + max(0, min(2000, qualified_expenses - 2000)) * 0.25
            )
            credit = min(credit, AOTC_MAX)
            if agi > phaseout_start:
                reduction_pct = min(1.0, (agi - phaseout_start) / phaseout_range)
                credit *= 1 - reduction_pct
            # 40% refundable — IRC §25A(i)
            refundable_portion = round(credit * 0.40, 2)
            nonrefundable_portion = round(credit * 0.60, 2)
            cred.aotc_refundable += refundable_portion
            cred.education_credits += nonrefundable_portion
        else:
            # LLC: 20% of up to $10,000 = max $2000
            credit = min(qualified_expenses, 10000) * 0.20
            credit = min(credit, LLC_MAX)
            if agi > phaseout_start:
                reduction_pct = min(1.0, (agi - phaseout_start) / phaseout_range)
                credit *= 1 - reduction_pct
            cred.education_credits += round(credit, 2)

    cred.education_credits = round(cred.education_credits, 2)
    cred.aotc_refundable = round(cred.aotc_refundable, 2)

    # Saver's Credit — IRC §25B (title26.md:16825-16892)
    if inp.retirement_savings_contributions:
        total_contributions = sum(
            c.contribution_amount for c in inp.retirement_savings_contributions
        )
        qualified_amount = min(total_contributions, 2000)

        # Credit percentage by AGI — IRC §25B(b)
        if inp.filing_status == FilingStatus.MARRIED_FILING_JOINTLY:
            if agi <= 46000:
                pct = 0.50
            elif agi <= 50000:
                pct = 0.20
            elif agi <= 76500:
                pct = 0.10
            else:
                pct = 0.0
        elif inp.filing_status == FilingStatus.HEAD_OF_HOUSEHOLD:
            if agi <= 34500:
                pct = 0.50
            elif agi <= 37500:
                pct = 0.20
            elif agi <= 57375:
                pct = 0.10
            else:
                pct = 0.0
        else:
            if agi <= 23000:
                pct = 0.50
            elif agi <= 25000:
                pct = 0.20
            elif agi <= 38250:
                pct = 0.10
            else:
                pct = 0.0
        cred.savers_credit = round(qualified_amount * pct, 2)

    # Energy credits — IRC §25C, §25D
    if inp.energy_credits and inp.tax_year <= 2025:
        ec = inp.energy_credits
        # §25C — 30% with caps
        home_improvement = min(ec.home_improvement_expenditures, 1200) * 0.30
        heat_pump = min(ec.heat_pump_expenditures, 2000) * 0.30
        audit = min(ec.home_energy_audit, 150)
        cred.energy_home_improvement_credit = round(
            min(home_improvement, 1200 * 0.30) + heat_pump + audit, 2
        )

        # §25D — 30% no cap
        clean_energy_total = (
            ec.solar_electric_expenditures
            + ec.solar_water_heating_expenditures
            + ec.battery_storage_expenditures
            + ec.geothermal_expenditures
            + ec.wind_expenditures
        )
        cred.residential_clean_energy_credit = round(clean_energy_total * 0.30, 2)

    # TASK-015: §25D energy credit carryforward (title26.md:18156)
    if inp.energy_credit_carryforward > 0:
        cred.energy_credit_carryforward_used = round(inp.energy_credit_carryforward, 2)
        cred.residential_clean_energy_credit += cred.energy_credit_carryforward_used
        cred.residential_clean_energy_credit = round(
            cred.residential_clean_energy_credit, 2
        )

    # Clean vehicle credit — IRC §30D / §25E
    if inp.clean_vehicle:
        cv = inp.clean_vehicle
        magi_limit = {
            FilingStatus.MARRIED_FILING_JOINTLY: 300000
            if cv.is_new_vehicle
            else 150000,
            FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 300000
            if cv.is_new_vehicle
            else 150000,
            FilingStatus.HEAD_OF_HOUSEHOLD: 225000 if cv.is_new_vehicle else 112500,
        }
        limit = magi_limit.get(
            inp.filing_status, 150000 if cv.is_new_vehicle else 75000
        )
        if agi <= limit:
            if cv.is_new_vehicle:
                # §30D — up to $7,500
                credit = 0
                if cv.meets_critical_minerals_requirement:
                    credit += 3750
                if cv.meets_battery_component_requirement:
                    credit += 3750
                cred.clean_vehicle_credit = credit
            else:
                # §25E — lesser of $4,000 or 30% of price
                cred.clean_vehicle_credit = round(
                    min(4000, cv.purchase_price * 0.30), 2
                )

    # Foreign tax credit — IRC §27 / §901
    for fi in inp.foreign_income:
        cred.foreign_tax_credit += fi.foreign_taxes_paid
    cred.foreign_tax_credit = round(cred.foreign_tax_credit, 2)

    # TASK-002: Premium Tax Credit — IRC §36B (title26.md:26647)
    if inp.marketplace_coverage:
        mc = inp.marketplace_coverage
        fpl = FPL_BASE + (mc.household_size - 1) * FPL_PER_ADDITIONAL
        household_income = agi
        income_pct_fpl = (household_income / fpl) * 100 if fpl > 0 else 999

        # Determine applicable percentage from table
        applicable_pct = 0.085  # Default for above 400% FPL
        for lower, upper, initial, final in PTC_PERCENTAGE_TABLE:
            if lower <= income_pct_fpl < upper:
                if upper == float("inf"):
                    applicable_pct = final
                else:
                    # Linear interpolation within the band
                    frac = (income_pct_fpl - lower) / (upper - lower)
                    applicable_pct = initial + frac * (final - initial)
                break

        expected_contribution = household_income * applicable_pct
        monthly_credit = max(
            0, (mc.annual_slcsp_premium / 12) - (expected_contribution / 12)
        )
        annual_credit = round(monthly_credit * mc.coverage_months, 2)
        # Cap at actual premium
        annual_credit = min(annual_credit, mc.annual_premium)

        # Reconcile with advance payments
        if annual_credit >= mc.advance_ptc_received:
            cred.premium_tax_credit = round(annual_credit - mc.advance_ptc_received, 2)
            cred.excess_advance_ptc_repayment = 0.0
        else:
            cred.premium_tax_credit = 0.0
            excess = round(mc.advance_ptc_received - annual_credit, 2)
            # Apply repayment caps for income < 400% FPL
            if income_pct_fpl < 400:
                cap = excess  # Default: full repayment
                for pct_limit, single_cap, other_cap in PTC_REPAYMENT_CAPS:
                    if income_pct_fpl < pct_limit:
                        if inp.filing_status in (
                            FilingStatus.SINGLE,
                            FilingStatus.MARRIED_FILING_SEPARATELY,
                        ):
                            cap = single_cap
                        else:
                            cap = other_cap
                        break
                excess = min(excess, cap)
            cred.excess_advance_ptc_repayment = excess

    # Total nonrefundable credits (limited to tax liability)
    total_nonrefundable = (
        cred.child_dependent_care_credit
        + cred.elderly_disabled_credit
        + cred.education_credits
        + cred.savers_credit
        + cred.child_tax_credit_nonrefundable
        + cred.other_dependent_credit
        + cred.adoption_credit_nonrefundable
        + cred.energy_home_improvement_credit
        + cred.residential_clean_energy_credit
        + cred.foreign_tax_credit
        + cred.clean_vehicle_credit
    )
    # Energy credit carryforward: limited by remaining liability
    remaining_liability = max(0, tax.total_tax_before_credits - total_nonrefundable)
    cred.energy_credit_carryforward_remaining = (
        round(max(0, cred.energy_credit_carryforward_used - remaining_liability), 2)
        if cred.energy_credit_carryforward_used > 0
        else 0.0
    )

    cred.total_nonrefundable_credits = round(
        min(total_nonrefundable, tax.total_tax_before_credits), 2
    )
    # Apply prior year AMT credit against regular tax
    cred.total_nonrefundable_credits = round(
        cred.total_nonrefundable_credits + tax.prior_year_amt_credit_used, 2
    )

    # TASK-004 + existing: EITC — IRC §32 (title26.md:22751)
    investment_income = (
        inc.total_interest
        + inc.total_ordinary_dividends
        + max(0, inc.net_capital_gain_loss)
        + max(0, inc.total_rental_income)
        + max(0, inc.total_royalty_income)
    )
    # EITC eligibility gating
    eitc_eligible = True
    eitc_reason = ""
    if inp.eitc_eligibility:
        elig = inp.eitc_eligibility
        # Use provided investment income if set, else use computed
        if elig.investment_income > 0:
            investment_income = elig.investment_income
        if not elig.has_valid_ssn_for_employment:
            eitc_eligible = False
            eitc_reason = "Missing valid SSN for employment"
        elif not elig.lived_in_us_more_than_half_year:
            eitc_eligible = False
            eitc_reason = "Did not live in US for more than half the year"
        elif elig.is_qualifying_child_of_another:
            eitc_eligible = False
            eitc_reason = "Taxpayer is a qualifying child of another person"
        elif elig.prior_eitc_fraud:
            eitc_eligible = False
            eitc_reason = "Prior EITC fraud disqualification (10-year ban)"
        elif elig.prior_eitc_disqualification_year:
            # 2-year disqualification for reckless/intentional disregard
            if inp.tax_year - elig.prior_eitc_disqualification_year < 2:
                eitc_eligible = False
                eitc_reason = "Within 2-year EITC disqualification period"
    if investment_income > EITC_INVESTMENT_INCOME_LIMIT:
        eitc_eligible = False
        eitc_reason = f"Investment income ${investment_income:,.0f} exceeds limit ${EITC_INVESTMENT_INCOME_LIMIT:,}"
    if inp.filing_status == FilingStatus.MARRIED_FILING_SEPARATELY:
        eitc_eligible = False
        eitc_reason = "Married filing separately not eligible for EITC"

    if eitc_eligible:
        cred.earned_income_credit = _compute_eitc(
            earned_income,
            agi,
            qualifying_children_for_eitc,
            inp.filing_status,
            investment_income,
        )
    else:
        cred.earned_income_credit = 0.0
        cred.eitc_disqualification_reason = eitc_reason

    # Total refundable credits
    cred.total_refundable_credits = round(
        cred.additional_child_tax_credit
        + cred.earned_income_credit
        + cred.aotc_refundable
        + cred.premium_tax_credit
        + cred.adoption_credit_refundable,
        2,
    )

    cred.total_credits = round(
        cred.total_nonrefundable_credits + cred.total_refundable_credits, 2
    )
    out.credits = cred

    # ===== STEP 7: Compute Total Tax =====
    # Early distribution penalty — IRC §72(t)
    early_dist_penalty = 0.0
    for rd in inp.retirement_distributions:
        if rd.is_early_distribution and not rd.early_distribution_exception_code:
            early_dist_penalty += rd.taxable_amount * 0.10
    early_dist_penalty = round(early_dist_penalty, 2)

    # HSA penalty for non-qualified distributions — IRC §223(f)(4)
    hsa_penalty = 0.0
    if inp.hsa:
        non_qualified = max(
            0, inp.hsa.distributions - inp.hsa.qualified_medical_expenses_from_hsa
        )
        hsa_penalty = round(non_qualified * 0.20, 2)

    # TASK-021: 529 penalty — IRC §529(c)(6)
    out.section_529_penalty = round(total_529_penalty, 2)

    out.total_tax = round(
        max(0, tax.total_tax_before_credits - cred.total_nonrefundable_credits)
        + out.se_tax.total_se_tax
        + early_dist_penalty
        + hsa_penalty
        + out.section_529_penalty
        + cred.excess_advance_ptc_repayment
        - cred.total_refundable_credits,
        2,
    )

    # ===== STEP 8: Compute Payments =====
    pay = PaymentSummary()
    pay.federal_income_tax_withheld = round(
        sum(w.federal_income_tax_withheld for w in inp.w2_income)
        + sum(r.federal_income_tax_withheld for r in inp.retirement_distributions)
        + (inp.unemployment.federal_income_tax_withheld if inp.unemployment else 0)
        + (inp.gambling.federal_income_tax_withheld if inp.gambling else 0)
        + sum(a.federal_income_tax_withheld for a in inp.annuity_income)
        + inp.other_federal_withholding
        + tax.additional_medicare_tax_withheld,
        2,
    )
    if inp.estimated_tax_payments:
        ep = inp.estimated_tax_payments
        pay.estimated_tax_payments = round(
            ep.q1_amount + ep.q2_amount + ep.q3_amount + ep.q4_amount, 2
        )
        pay.amount_applied_from_prior_year = ep.amount_applied_from_prior_year

    pay.total_payments = round(
        pay.federal_income_tax_withheld
        + pay.estimated_tax_payments
        + pay.amount_applied_from_prior_year
        + pay.excess_social_security_withheld
        + pay.other_payments,
        2,
    )
    out.payments = pay
    out.total_payments = pay.total_payments

    # ===== STEP 9: Compute Refund or Amount Owed =====
    if out.total_payments > out.total_tax:
        out.overpayment = round(out.total_payments - out.total_tax, 2)
        out.amount_owed = 0.0
    else:
        out.overpayment = 0.0
        out.amount_owed = round(out.total_tax - out.total_payments, 2)

    # Effective and marginal rates
    if inc.gross_income > 0:
        out.effective_tax_rate = round(out.total_tax / inc.gross_income, 4)
    if tax.tax_bracket_details:
        out.marginal_tax_rate = tax.tax_bracket_details[-1]["rate"]

    # Carryforwards
    out.capital_loss_carryforward = inc.capital_loss_carryforward_to_next_year
    out.capital_loss_carryforward_short = inc.capital_loss_carryforward_remaining_short
    out.capital_loss_carryforward_long = inc.capital_loss_carryforward_remaining_long
    out.nol_carryforward_remaining = ded.nol_carryforward_remaining
    out.investment_interest_carryforward = (
        ded.investment_interest_carryforward_to_next_year
    )
    out.energy_credit_carryforward = cred.energy_credit_carryforward_remaining
    # AMT credit carryforward
    if inp.amt_preferences and inp.amt_preferences.prior_year_amt_credit > 0:
        out.amt_credit_carryforward = round(
            max(
                0,
                inp.amt_preferences.prior_year_amt_credit
                - tax.prior_year_amt_credit_used,
            ),
            2,
        )
    # Adoption credit carryforward (nonrefundable unused portion — 5 years)
    if cred.adoption_credit_nonrefundable > 0:
        unused_adoption = max(
            0,
            cred.adoption_credit_nonrefundable
            - max(
                0,
                tax.total_tax_before_credits
                - (
                    cred.total_nonrefundable_credits
                    - cred.adoption_credit_nonrefundable
                ),
            ),
        )
        cred.adoption_credit_carryforward = round(unused_adoption, 2)

    # ===== STEP 10: Estimated Tax Penalty — IRC §6654 (title26.md:566326) =====
    pen = PenaltyComputation()
    current_year_tax = out.total_tax
    pen.required_annual_payment = round(
        min(
            current_year_tax * 0.90,
            inp.prior_year_tax * (1.10 if inp.prior_year_agi > 150000 else 1.00),
        ),
        2,
    )
    pen.total_payments_and_withholding = pay.total_payments

    if (current_year_tax - pay.federal_income_tax_withheld) < 1000:
        pen.penalty_waived = True
    elif pay.total_payments >= pen.required_annual_payment:
        pen.penalty_waived = True
    elif inp.prior_year_tax == 0:
        pen.penalty_waived = True

    if not pen.penalty_waived:
        shortfall = max(0, pen.required_annual_payment - pay.total_payments)
        # Simplified penalty: ~3% annual rate on shortfall for ~6 months average
        pen.estimated_tax_penalty = round(shortfall * 0.08 * 0.5, 2)

    out.penalty = pen

    return out


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------


def _deserialize_enum(data: dict, cls):
    """Recursively convert enum string values back to enum instances."""
    hints = get_type_hints(cls)
    for f in dataclasses.fields(cls):
        if f.name not in data:
            continue
        tp = hints[f.name]
        origin = get_origin(tp)
        args = get_args(tp)

        # Handle Optional
        if origin is Union:
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                tp = non_none[0]
                origin = get_origin(tp)
                args = get_args(tp)

        if data[f.name] is None:
            continue

        if isinstance(tp, type) and issubclass(tp, Enum):
            data[f.name] = tp(data[f.name])
        elif dataclasses.is_dataclass(tp) and isinstance(data[f.name], dict):
            _deserialize_enum(data[f.name], tp)
            data[f.name] = tp(**data[f.name])
        elif origin is list and args:
            item_type = args[0]
            if dataclasses.is_dataclass(item_type):
                items = []
                for item in data[f.name]:
                    if isinstance(item, dict):
                        _deserialize_enum(item, item_type)
                        items.append(item_type(**item))
                    else:
                        items.append(item)
                data[f.name] = items
            elif isinstance(item_type, type) and issubclass(item_type, Enum):
                data[f.name] = [item_type(v) for v in data[f.name]]


def main():
    """Read JSON input from stdin or file, compute tax return, output JSON."""
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    _deserialize_enum(data, TaxReturnInput)
    inp = TaxReturnInput(**data)

    try:
        result = calculate(inp)
    except ValidationError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(asdict(result), indent=2, default=str))


if __name__ == "__main__":
    main()
