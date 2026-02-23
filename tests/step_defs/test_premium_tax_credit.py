from pytest_bdd import scenario


@scenario(
    "premium_tax_credit.feature",
    "Single filer eligible for PTC with advance payments",
)
def test_ptc_eligible_with_advance():
    pass


@scenario(
    "premium_tax_credit.feature",
    "Joint filers with income above 400% FPL — no PTC",
)
def test_ptc_high_income_no_credit():
    pass
