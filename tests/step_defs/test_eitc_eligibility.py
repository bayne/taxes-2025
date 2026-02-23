from pytest_bdd import scenario


@scenario(
    "eitc_eligibility.feature",
    "Filer with excess investment income is denied EITC",
)
def test_eitc_excess_investment_income():
    pass


@scenario(
    "eitc_eligibility.feature",
    "Eligible single filer with one child receives EITC",
)
def test_eitc_eligible_with_child():
    pass
