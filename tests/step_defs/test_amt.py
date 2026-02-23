from pytest_bdd import scenario


@scenario("amt.feature", "ISO exercise triggers AMT")
def test_amt_iso_exercise():
    pass


@scenario("amt.feature", "High earner with no preference items — no AMT")
def test_amt_no_preference_items():
    pass
