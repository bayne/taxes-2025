Feature: Alternative Minimum Tax computation

  Scenario: ISO exercise triggers AMT
    Given the filing status is "single"
    And the taxpayer is "Ava Reyes" born "1983-09-20"
    And a W-2 from "TechCo" with wages $200000 and withholding $40000
    And AMT preference items with ISO exercise spread $300000
    When the tax return is calculated
    Then AMTI should be greater than taxable income
    And the AMT amount should be greater than $0
    And total tax should include the AMT amount

  Scenario: High earner with no preference items — no AMT
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Ben Cruz" born "1975-03-01"
    And a spouse "Liz Cruz" born "1977-08-10"
    And a W-2 from "FinCorp" with wages $350000 and withholding $70000
    And no AMT preference items
    When the tax return is calculated
    Then the AMT amount should be $0
