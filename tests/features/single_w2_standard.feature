Feature: Single filer with W-2 income and standard deduction

  Scenario: Single filer with $75,000 W-2 income
    Given the filing status is "single"
    And the taxpayer is "Alice Smith" born "1990-03-15"
    And a W-2 from "Acme Corp" with wages $75000 and withholding $9000
    When the tax return is calculated
    Then total wages should be $75000
    And gross income should be $75000
    And AGI should be $75000
    And the deduction method should be "standard"
    And the deduction amount should be $15750
    And taxable income should be $59250
    And the marginal tax rate should be 22%
