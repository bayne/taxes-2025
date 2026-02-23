Feature: Married filing jointly with itemized deductions

  Scenario: MFJ couple with $180,000 income and large itemized deductions
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "George Kim" born "1978-08-22"
    And a spouse "Helen Kim" born "1980-03-14"
    And a W-2 from "LawFirm" with wages $180000 and withholding $30000
    And mortgage interest paid of $18000
    And state and local taxes of $12000 income tax and $8000 property tax
    And charitable contributions of $8000 cash
    And the taxpayer elects to itemize deductions
    When the tax return is calculated
    Then total wages should be $180000
    And AGI should be $180000
    And the deduction method should be "itemized"
    And the SALT deduction should be capped at $20000
    And total itemized deductions should be $46000
    And the marginal tax rate should be 22%
