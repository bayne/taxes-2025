Feature: Premium Tax Credit for ACA marketplace coverage

  Scenario: Single filer eligible for PTC with advance payments
    Given the filing status is "single"
    And the taxpayer is "Rosa Chen" born "1992-04-10"
    And a W-2 from "Cafe LLC" with wages $32000 and withholding $2500
    And marketplace coverage with annual premium $6000 and SLCSP premium $6500 and advance PTC $3000 and household size 1
    When the tax return is calculated
    Then the premium tax credit should be greater than $0
    And the excess advance PTC repayment should be $0 or a positive amount

  Scenario: Joint filers with income above 400% FPL — no PTC
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Tom Hall" born "1980-01-01"
    And a spouse "Sue Hall" born "1982-06-15"
    And a W-2 from "BigCo" with wages $200000 and withholding $35000
    And marketplace coverage with annual premium $12000 and SLCSP premium $13000 and advance PTC $4000 and household size 2
    When the tax return is calculated
    Then the premium tax credit should be $0
    And the excess advance PTC repayment should be $4000
