from pytest_bdd import scenario


@scenario(
    "k1_income.feature", "Partnership K-1 with ordinary income and guaranteed payments"
)
def test_k1_partnership():
    pass


@scenario("k1_income.feature", "S-Corp K-1 with qualified dividends and capital gains")
def test_k1_scorp():
    pass
