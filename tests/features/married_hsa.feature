Feature: Married filing jointly with family HSA

  Scenario: MFJ couple with $150,000 income and $7,000 HSA contribution
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Kevin Nguyen" born "1983-01-30"
    And a spouse "Linda Nguyen" born "1985-07-18"
    And a W-2 from "HealthCo" with wages $150000 and withholding $20000
    And a family HSA with $7000 taxpayer contributions and $0 employer contributions
    When the tax return is calculated
    Then total wages should be $150000
    And the HSA deduction should be $7000
    And AGI should be $143000
    And the deduction method should be "standard"
    And the deduction amount should be $31500
