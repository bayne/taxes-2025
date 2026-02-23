from pytest_bdd import scenario

# ---------------------------------------------------------------------------
# TASK-005 — Adoption Credit (§23)
# ---------------------------------------------------------------------------


@scenario(
    "new_income_credits.feature",
    "Special-needs adoption with full deemed expense",
)
def test_adoption_special_needs():
    pass


@scenario(
    "new_income_credits.feature",
    "High-income filer — adoption credit phased out",
)
def test_adoption_phased_out():
    pass


# ---------------------------------------------------------------------------
# TASK-006 — Credit for the Elderly or Disabled (§22)
# ---------------------------------------------------------------------------


@scenario(
    "new_income_credits.feature",
    "Single filer age 67 with low income qualifies",
)
def test_elderly_credit_qualifies():
    pass


@scenario(
    "new_income_credits.feature",
    "High-AGI senior — credit fully phased out",
)
def test_elderly_credit_phased_out():
    pass


# ---------------------------------------------------------------------------
# TASK-007 — Royalty Income
# ---------------------------------------------------------------------------


@scenario(
    "new_income_credits.feature",
    "Book royalties with deductible expenses",
)
def test_royalty_with_expenses():
    pass


@scenario(
    "new_income_credits.feature",
    "Oil and gas royalties subject to SE tax",
)
def test_royalty_se_tax():
    pass


# ---------------------------------------------------------------------------
# TASK-008 — Farm Income (Schedule F)
# ---------------------------------------------------------------------------


@scenario(
    "new_income_credits.feature",
    "Profitable farm with standard expenses",
)
def test_farm_profitable():
    pass


@scenario(
    "new_income_credits.feature",
    "Farm loss — eligible for 2-year carryback",
)
def test_farm_loss_carryback():
    pass


# ---------------------------------------------------------------------------
# TASK-009 — Alimony Received (Pre-2019 Instruments)
# ---------------------------------------------------------------------------


@scenario(
    "new_income_credits.feature",
    "Pre-2019 divorce — alimony is gross income",
)
def test_alimony_pre2019():
    pass


@scenario(
    "new_income_credits.feature",
    "Post-2018 divorce — alimony is NOT gross income",
)
def test_alimony_post2018():
    pass


# ---------------------------------------------------------------------------
# TASK-010 — Gambling Income and Losses
# ---------------------------------------------------------------------------


@scenario(
    "new_income_credits.feature",
    "Gambler who itemizes — losses capped at winnings",
)
def test_gambling_itemized_loss_cap():
    pass


@scenario(
    "new_income_credits.feature",
    "Gambler taking standard deduction — no loss deduction",
)
def test_gambling_standard_no_loss():
    pass


# ---------------------------------------------------------------------------
# TASK-011 — Annuity Income (§72)
# ---------------------------------------------------------------------------


@scenario(
    "new_income_credits.feature",
    "Commercial annuity — partial exclusion via exclusion ratio",
)
def test_annuity_exclusion_ratio():
    pass


@scenario(
    "new_income_credits.feature",
    "Simplified method — employer plan annuity",
)
def test_annuity_simplified_method():
    pass


# ---------------------------------------------------------------------------
# TASK-012 — Scholarship Income (§117)
# ---------------------------------------------------------------------------


@scenario(
    "new_income_credits.feature",
    "Scholarship with room and board stipend",
)
def test_scholarship_room_board():
    pass


@scenario(
    "new_income_credits.feature",
    "Fully qualified scholarship — no taxable income",
)
def test_scholarship_fully_qualified():
    pass
