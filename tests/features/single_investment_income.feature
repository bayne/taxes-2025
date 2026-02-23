Feature: Single filer with W-2 and investment income

  Scenario: Single filer with $70,000 W-2 plus interest, dividends, and LTCG
    Given the filing status is "single"
    And the taxpayer is "Eve Chen" born "1982-12-01"
    And a W-2 from "FinanceCo" with wages $70000 and withholding $8500
    And interest income of $2000 from "Bank of America"
    And dividend income of $3000 ordinary and $2500 qualified from "Vanguard"
    And a long-term capital gain of $15000 proceeds and $10000 cost basis
    When the tax return is calculated
    Then total wages should be $70000
    And gross income should be $80000
    And the deduction method should be "standard"
    And capital gains tax at 15% should be greater than $0
    And the marginal tax rate should be 22%
