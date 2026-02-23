Feature: Schedule K-1 income flows into return

  Scenario: Partnership K-1 with ordinary income and guaranteed payments
    Given the filing status is "single"
    And the taxpayer is "Dana Kim" born "1985-07-22"
    And a partnership K-1 from "Kim & Associates" with ordinary income $60000 and guaranteed payments $40000
    When the tax return is calculated
    Then gross income should include K-1 ordinary income of $60000
    And gross income should include guaranteed payments of $40000
    And total SE tax should be greater than $0

  Scenario: S-Corp K-1 with qualified dividends and capital gains
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Eli Park" born "1978-11-03"
    And a spouse "Mia Park" born "1980-02-14"
    And an S-Corp K-1 from "Park Holdings" with ordinary income $25000 and long-term capital gains $15000 and qualified dividends $5000
    When the tax return is calculated
    Then gross income should include K-1 ordinary income of $25000
    And net long-term capital gains should include $15000 from K-1
    And qualified dividends should include $5000 from K-1
