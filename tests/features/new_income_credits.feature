Feature: New income types and credits (TASKs 005-012)

  # ---------------------------------------------------------------------------
  # TASK-005 — Adoption Credit (§23)
  # ---------------------------------------------------------------------------

  Scenario: Special-needs adoption with full deemed expense
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Jay Lin" born "1980-01-10"
    And a spouse "Wei Lin" born "1982-05-20"
    And a W-2 from "TechCo" with wages $100000 and withholding $15000
    And a special-needs adoption of "Hope Lin" with $0 in qualified expenses
    When the tax return is calculated
    Then the adoption credit should equal the maximum per-child amount
    And the refundable adoption credit should be up to $5000

  Scenario: High-income filer — adoption credit phased out
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Sam Yi" born "1975-03-01"
    And a spouse "Pat Yi" born "1977-09-15"
    And a W-2 from "BigLaw" with wages $320000 and withholding $70000
    And an adoption of "Max Yi" with $20000 in qualified expenses
    When the tax return is calculated
    Then the adoption credit should be $0

  # ---------------------------------------------------------------------------
  # TASK-006 — Credit for the Elderly or Disabled (§22)
  # ---------------------------------------------------------------------------

  Scenario: Single filer age 67 with low income qualifies
    Given the filing status is "single"
    And the taxpayer is "Ruth Adams" born "1958-02-28"
    And pension income of $10000 gross and $10000 taxable with $800 withheld
    And elderly/disabled credit info with nontaxable Social Security $2000
    When the tax return is calculated
    Then the elderly or disabled credit should be greater than $0

  Scenario: High-AGI senior — credit fully phased out
    Given the filing status is "single"
    And the taxpayer is "Gene Black" born "1955-05-10"
    And a W-2 from "Consulting" with wages $80000 and withholding $12000
    And elderly/disabled credit info with nontaxable Social Security $0
    When the tax return is calculated
    Then the elderly or disabled credit should be $0

  # ---------------------------------------------------------------------------
  # TASK-007 — Royalty Income
  # ---------------------------------------------------------------------------

  Scenario: Book royalties with deductible expenses
    Given the filing status is "single"
    And the taxpayer is "Ian Cole" born "1970-08-12"
    And royalty income of $30000 gross with $5000 in expenses from "Publisher Inc"
    When the tax return is calculated
    Then total royalty income should be $25000
    And gross income should include royalty income of $25000

  Scenario: Oil and gas royalties subject to SE tax
    Given the filing status is "single"
    And the taxpayer is "Jill Ford" born "1965-04-30"
    And royalty income of $50000 gross with $10000 in expenses from "Energy Co" subject to SE tax
    When the tax return is calculated
    Then total SE tax should be greater than $0

  # ---------------------------------------------------------------------------
  # TASK-008 — Farm Income (Schedule F)
  # ---------------------------------------------------------------------------

  Scenario: Profitable farm with standard expenses
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "John Deere" born "1970-03-15"
    And a spouse "Jane Deere" born "1972-07-20"
    And farm income of $200000 gross with $130000 in expenses
    When the tax return is calculated
    Then total farm income should be $70000
    And gross income should include farm income of $70000
    And total SE tax should be greater than $0

  Scenario: Farm loss — eligible for 2-year carryback
    Given the filing status is "single"
    And the taxpayer is "Hank Till" born "1968-11-05"
    And farm income of $40000 gross with $65000 in expenses
    When the tax return is calculated
    Then total farm income should be -$25000
    And the farm NOL should be eligible for 2-year carryback

  # ---------------------------------------------------------------------------
  # TASK-009 — Alimony Received (Pre-2019 Instruments)
  # ---------------------------------------------------------------------------

  Scenario: Pre-2019 divorce — alimony is gross income
    Given the filing status is "single"
    And the taxpayer is "Amy Ross" born "1975-06-01"
    And alimony received of $24000 under a "2017-06-15" instrument
    When the tax return is calculated
    Then gross income should include alimony income of $24000

  Scenario: Post-2018 divorce — alimony is NOT gross income
    Given the filing status is "single"
    And the taxpayer is "Bob Stone" born "1980-09-10"
    And alimony received of $30000 under a "2020-03-01" instrument
    When the tax return is calculated
    Then gross income should not include any alimony income

  # ---------------------------------------------------------------------------
  # TASK-010 — Gambling Income and Losses
  # ---------------------------------------------------------------------------

  Scenario: Gambler who itemizes — losses capped at winnings
    Given the filing status is "single"
    And the taxpayer is "Lucky Lou" born "1982-01-20"
    And a W-2 from "DayCo" with wages $60000 and withholding $8000
    And gambling winnings of $10000 with losses of $18000
    And the taxpayer elects to itemize deductions
    And mortgage interest paid of $15000
    When the tax return is calculated
    Then gross income should include gambling winnings of $10000
    And the gambling loss deduction should be at most $10000

  Scenario: Gambler taking standard deduction — no loss deduction
    Given the filing status is "single"
    And the taxpayer is "Pat Dice" born "1990-05-05"
    And a W-2 from "ShopCo" with wages $45000 and withholding $5000
    And gambling winnings of $3000 with losses of $2500
    When the tax return is calculated
    Then gross income should include gambling winnings of $3000
    And the gambling loss deduction should be $0

  # ---------------------------------------------------------------------------
  # TASK-011 — Annuity Income (§72)
  # ---------------------------------------------------------------------------

  Scenario: Commercial annuity — partial exclusion via exclusion ratio
    Given the filing status is "single"
    And the taxpayer is "Vera Long" born "1955-08-15"
    And annuity income of $12000 from "InsureCo" with $60000 investment and $180000 expected return
    When the tax return is calculated
    Then the annuity taxable amount should be $8000
    And gross income should include annuity taxable amount of $8000

  Scenario: Simplified method — employer plan annuity
    Given the filing status is "single"
    And the taxpayer is "Walt Grey" born "1957-03-22"
    And employer plan annuity income of $24000 with $72000 investment using simplified method at age 66
    When the tax return is calculated
    Then the annuity exclusion per payment should use 260 anticipated payments
    And the annuity taxable amount should be less than $24000

  # ---------------------------------------------------------------------------
  # TASK-012 — Scholarship Income (§117)
  # ---------------------------------------------------------------------------

  Scenario: Scholarship with room and board stipend
    Given the filing status is "single"
    And the taxpayer is "Zoe Nash" born "2003-07-14"
    And scholarship income of $25000 total with $18000 for tuition and $7000 for room and board
    When the tax return is calculated
    Then taxable scholarship income should be $7000
    And gross income should include scholarship income of $7000

  Scenario: Fully qualified scholarship — no taxable income
    Given the filing status is "single"
    And the taxpayer is "Leo Park" born "2004-01-25"
    And scholarship income of $15000 total with $15000 for tuition and $0 for room and board
    When the tax return is calculated
    Then taxable scholarship income should be $0
