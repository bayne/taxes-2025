Feature: EITC eligibility gating

  Scenario: Filer with excess investment income is denied EITC
    Given the filing status is "single"
    And the taxpayer is "Nia Jones" born "1990-06-01"
    And a W-2 from "RetailCo" with wages $22000 and withholding $1000
    And EITC eligibility with investment income $15000
    When the tax return is calculated
    Then the earned income credit should be $0
    And the EITC disqualification reason should mention "investment income"

  Scenario: Eligible single filer with one child receives EITC
    Given the filing status is "head_of_household"
    And the taxpayer is "Carlos Vega" born "1988-12-15"
    And a W-2 from "ShopCo" with wages $25000 and withholding $1500
    And a qualifying child "Mia Vega" born "2018-03-20"
    And EITC eligibility with investment income $500
    When the tax return is calculated
    Then the earned income credit should be greater than $0
