Feature: Single filer with itemized deductions

  Scenario: Single filer with $120,000 income, mortgage interest, stock trades, and state/local/property taxes
    Given the filing status is "single"
    And the taxpayer is "Michael Torres" born "1985-06-10"
    And a W-2 from "TechStartup Inc" with wages $120000 and withholding $20000
    And mortgage interest paid of $14000
    And a long-term capital gain of $25000 proceeds and $18000 cost basis
    And a short-term capital gain of $8000 proceeds and $12000 cost basis
    And state and local taxes of $9000 state income tax and $2000 local income tax and $7500 property tax
    And the taxpayer elects to itemize deductions
    When the tax return is calculated
    Then total wages should be $120000
    And gross income should be $123000
    And AGI should be $123000
    And the deduction method should be "itemized"
    And the SALT deduction should be capped at $18500
    And total itemized deductions should be $32500
    And taxable income should be $90500
    And capital gains tax at 15% should be greater than $0
    And the marginal tax rate should be 22%
