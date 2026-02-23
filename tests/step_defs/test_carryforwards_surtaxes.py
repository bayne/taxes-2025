from pytest_bdd import scenario

FEATURE = "carryforwards_and_surtaxes.feature"

# ---------------------------------------------------------------------------
# TASK-013 — Net Operating Loss Carryforward (§172)
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Post-2017 NOL limited to 80% of taxable income")
def test_nol_80pct_limit():
    pass


@scenario(FEATURE, "Small NOL fully absorbed")
def test_nol_fully_absorbed():
    pass


# ---------------------------------------------------------------------------
# TASK-014 — Charitable Contribution Carryforward (§170)
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Carryforward from prior year used within AGI limits")
def test_charitable_carryforward_used():
    pass


@scenario(FEATURE, "No carryforward available — current year only")
def test_charitable_no_carryforward():
    pass


# ---------------------------------------------------------------------------
# TASK-015 — §25D Clean Energy Credit Carryforward
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Prior-year solar credit carryforward applied")
def test_energy_credit_carryforward():
    pass


@scenario(FEATURE, "No carryforward — current year credit only")
def test_energy_credit_current_year_only():
    pass


# ---------------------------------------------------------------------------
# TASK-016 — Capital Loss Carryforward Breakdown (Short/Long)
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Short-term carryforward offsets short-term gains first")
def test_st_carryforward_offsets_st_gains():
    pass


@scenario(FEATURE, "Long-term carryforward exceeds gains — $3k ordinary deduction")
def test_lt_carryforward_3k_ordinary():
    pass


# ---------------------------------------------------------------------------
# TASK-017 — Kiddie Tax (§1(g))
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Child under 18 with investment income taxed at parent's rate")
def test_kiddie_tax_under_18():
    pass


@scenario(FEATURE, "Child with only earned income — no kiddie tax")
def test_kiddie_tax_earned_only():
    pass


# ---------------------------------------------------------------------------
# TASK-018 — Casualty and Disaster Loss Detail (§165)
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Single disaster event exceeding 10% AGI floor")
def test_casualty_disaster_event():
    pass


@scenario(FEATURE, "Non-disaster casualty — not deductible post-2017")
def test_casualty_non_disaster():
    pass


# ---------------------------------------------------------------------------
# TASK-019 — Net Investment Income Tax (§1411)
# ---------------------------------------------------------------------------


@scenario(FEATURE, "High-income filer with investment income above threshold")
def test_niit_above_threshold():
    pass


@scenario(FEATURE, "Filer below MAGI threshold — no NIIT")
def test_niit_below_threshold():
    pass


# ---------------------------------------------------------------------------
# TASK-020 — Additional Medicare Tax (§3101(b)(2))
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Single filer with wages above $200k threshold")
def test_additional_medicare_above_threshold():
    pass


@scenario(FEATURE, "Joint filers below $250k combined threshold — no additional tax")
def test_additional_medicare_below_threshold():
    pass


# ---------------------------------------------------------------------------
# TASK-021 — Section 529 Plan Distributions
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Qualified distribution for college tuition — tax-free")
def test_529_qualified_tax_free():
    pass


@scenario(FEATURE, "Non-qualified distribution — earnings taxed with 10% penalty")
def test_529_non_qualified_penalty():
    pass


# ---------------------------------------------------------------------------
# TASK-022 — Like-Kind Exchange (§1031)
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Straight exchange with no boot — full deferral")
def test_lke_no_boot_full_deferral():
    pass


@scenario(FEATURE, "Exchange with boot received — partial recognition")
def test_lke_boot_partial_recognition():
    pass


# ---------------------------------------------------------------------------
# TASK-023 — Restricted Stock / §83(b) Election
# ---------------------------------------------------------------------------


@scenario(FEATURE, "RSU vesting — income at vesting FMV")
def test_rsu_vesting():
    pass


@scenario(FEATURE, "§83(b) election — income at grant FMV")
def test_83b_election():
    pass


# ---------------------------------------------------------------------------
# TASK-024 — Savings Bond Education Exclusion (§135)
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Partial exclusion when expenses are less than proceeds")
def test_savings_bond_partial_exclusion():
    pass


@scenario(FEATURE, "Income above phase-out — no exclusion")
def test_savings_bond_phaseout():
    pass


# ---------------------------------------------------------------------------
# TASK-025 — Investment Interest Expense Limitation (§163(d))
# ---------------------------------------------------------------------------


@scenario(FEATURE, "Investment interest capped at net investment income")
def test_investment_interest_capped():
    pass


@scenario(FEATURE, "Investment interest fully deductible within NII")
def test_investment_interest_fully_deductible():
    pass
