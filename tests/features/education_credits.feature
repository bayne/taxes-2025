Feature: Single filer with student loan interest and AOTC

  Scenario: Single filer with $55,000 income, student loan interest, and AOTC
    Given the filing status is "single"
    And the taxpayer is "Jack Park" born "1998-10-05"
    And a W-2 from "StartupCo" with wages $55000 and withholding $5000
    And student loan interest paid of $2500
    And education expenses of $4000 for AOTC for "Jack Park"
    When the tax return is calculated
    Then total wages should be $55000
    And the student loan interest deduction should be $2500
    And AGI should be $52500
    And the AOTC refundable portion should be $1000
    And the AOTC nonrefundable portion should be $1500
