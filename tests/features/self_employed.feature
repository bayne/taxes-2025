Feature: Single self-employed filer with Schedule C

  Scenario: Single filer with $120,000 gross receipts and $30,000 expenses
    Given the filing status is "single"
    And the taxpayer is "Frank Lee" born "1980-05-10"
    And business income of $120000 gross receipts and $30000 in expenses
    When the tax return is calculated
    Then total business income should be $90000
    And gross income should be $90000
    And total SE tax should be greater than $0
    And the SE tax deduction should be greater than $0
    And AGI should be less than gross income
    And the marginal tax rate should be 22%
