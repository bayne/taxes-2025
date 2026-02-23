Feature: Head of household filer with one child

  Scenario: HOH filer with $55,000 income and one child
    Given the filing status is "head_of_household"
    And the taxpayer is "Diana Ross" born "1988-02-28"
    And a W-2 from "ServiceCo" with wages $55000 and withholding $5500
    And a qualifying child "Maya Ross" born "2016-07-12"
    When the tax return is calculated
    Then total wages should be $55000
    And AGI should be $55000
    And the deduction method should be "standard"
    And the deduction amount should be $23625
    And the child tax credit should be $2200
    And the marginal tax rate should be 12%
