Feature: Single senior with Social Security and pension income

  Scenario: Single filer age 68 with $24,000 SS and $30,000 pension
    Given the filing status is "single"
    And the taxpayer is "Irene Walsh" born "1957-04-20"
    And Social Security benefits of $24000
    And pension income of $30000 gross and $30000 taxable with $3000 withheld
    When the tax return is calculated
    Then Social Security taxable amount should be $15300
    And gross income should be $45300
    And the standard deduction should be $17750
    And the senior deduction should be $6000
    And the marginal tax rate should be 12%
