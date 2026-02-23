Feature: Married filing jointly with two W-2s and child tax credits

  Scenario: MFJ couple with $130,000 combined income and 2 children
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Bob Johnson" born "1985-06-20"
    And a spouse "Carol Johnson" born "1987-09-10"
    And a W-2 from "TechCo" with wages $80000 and withholding $10000
    And a W-2 from "RetailCo" with wages $50000 and withholding $5000
    And a qualifying child "Emma Johnson" born "2015-04-01"
    And a qualifying child "Liam Johnson" born "2018-11-15"
    When the tax return is calculated
    Then total wages should be $130000
    And AGI should be $130000
    And the deduction method should be "standard"
    And the deduction amount should be $31500
    And the child tax credit should be $4400
    And the marginal tax rate should be 22%
