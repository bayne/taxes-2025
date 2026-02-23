Feature: Carryforwards, surtaxes, and additional tax situations (TASKs 013-025)

  # ---------------------------------------------------------------------------
  # TASK-013 — Net Operating Loss Carryforward (§172)
  # ---------------------------------------------------------------------------

  Scenario: Post-2017 NOL limited to 80% of taxable income
    Given the filing status is "single"
    And the taxpayer is "Owen Blake" born "1978-10-10"
    And a W-2 from "WidgetCo" with wages $100000 and withholding $15000
    And a NOL carryforward of $200000
    When the tax return is calculated
    Then the NOL deduction should equal 80% of taxable income before NOL
    And NOL carryforward remaining should be greater than $0

  Scenario: Small NOL fully absorbed
    Given the filing status is "single"
    And the taxpayer is "Ivy Dunn" born "1985-04-20"
    And a W-2 from "BigCo" with wages $80000 and withholding $10000
    And a NOL carryforward of $5000
    When the tax return is calculated
    Then the NOL deduction should be $5000
    And NOL carryforward remaining should be $0

  # ---------------------------------------------------------------------------
  # TASK-014 — Charitable Contribution Carryforward (§170)
  # ---------------------------------------------------------------------------

  Scenario: Carryforward from prior year used within AGI limits
    Given the filing status is "single"
    And the taxpayer is "Faye Gold" born "1972-09-01"
    And a W-2 from "MainCo" with wages $100000 and withholding $15000
    And the taxpayer elects to itemize deductions
    And charitable contributions of $10000 cash
    And a charitable contribution carryforward of $30000
    And state and local taxes of $8000 income tax and $5000 property tax
    When the tax return is calculated
    Then the charitable deduction should include carryforward amounts
    And the total charitable deduction should not exceed 50% of AGI

  Scenario: No carryforward available — current year only
    Given the filing status is "single"
    And the taxpayer is "Greg Hale" born "1980-03-10"
    And a W-2 from "DevCo" with wages $80000 and withholding $10000
    And the taxpayer elects to itemize deductions
    And charitable contributions of $5000 cash
    And mortgage interest paid of $12000
    When the tax return is calculated
    Then the charitable carryforward remaining should be $0

  # ---------------------------------------------------------------------------
  # TASK-015 — §25D Clean Energy Credit Carryforward
  # ---------------------------------------------------------------------------

  Scenario: Prior-year solar credit carryforward applied
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Kai Moon" born "1975-06-01"
    And a spouse "Lee Moon" born "1978-02-14"
    And a W-2 from "SolarCo" with wages $90000 and withholding $12000
    And an energy credit carryforward of $3000
    When the tax return is calculated
    Then the energy credit should include the $3000 carryforward
    And the total energy credit applied should be limited by tax liability

  Scenario: No carryforward — current year credit only
    Given the filing status is "single"
    And the taxpayer is "Ren Sage" born "1988-12-01"
    And a W-2 from "GreenCo" with wages $70000 and withholding $9000
    And residential clean energy expenditures of $20000 for solar
    When the tax return is calculated
    Then the §25D credit should be $6000
    And energy credit carryforward remaining should be $0 or a positive amount

  # ---------------------------------------------------------------------------
  # TASK-016 — Capital Loss Carryforward Breakdown (Short/Long)
  # ---------------------------------------------------------------------------

  Scenario: Short-term carryforward offsets short-term gains first
    Given the filing status is "single"
    And the taxpayer is "Nora Falk" born "1980-07-07"
    And a W-2 from "TradeCo" with wages $60000 and withholding $8000
    And a short-term capital gain of $8000 proceeds and $3000 cost basis
    And a short-term capital loss carryforward of $4000
    When the tax return is calculated
    Then net short-term capital gain should be $1000
    And capital loss carryforward remaining short-term should be $0

  Scenario: Long-term carryforward exceeds gains — $3k ordinary deduction
    Given the filing status is "single"
    And the taxpayer is "Omar Kent" born "1977-02-18"
    And a W-2 from "OfficeCo" with wages $50000 and withholding $6000
    And a long-term capital loss carryforward of $10000
    When the tax return is calculated
    Then the capital loss deduction against ordinary income should be $3000
    And capital loss carryforward remaining long-term should be $7000

  # ---------------------------------------------------------------------------
  # TASK-017 — Kiddie Tax (§1(g))
  # ---------------------------------------------------------------------------

  Scenario: Child under 18 with investment income taxed at parent's rate
    Given the filing status is "single"
    And the taxpayer is "Lily Grant" born "2012-05-10"
    And interest income of $5000 from "BankCo"
    And kiddie tax info with parent taxable income $300000 and parent filing status "married_filing_jointly"
    When the tax return is calculated
    Then the kiddie tax amount should be greater than $0
    And the kiddie tax should apply the parent's marginal rate to unearned income above the threshold

  Scenario: Child with only earned income — no kiddie tax
    Given the filing status is "single"
    And the taxpayer is "Max Grant" born "2009-08-22"
    And a W-2 from "SummerJob" with wages $4000 and withholding $0
    And kiddie tax info with parent taxable income $300000 and parent filing status "married_filing_jointly"
    When the tax return is calculated
    Then the kiddie tax amount should be $0

  # ---------------------------------------------------------------------------
  # TASK-018 — Casualty and Disaster Loss Detail (§165)
  # ---------------------------------------------------------------------------

  Scenario: Single disaster event exceeding 10% AGI floor
    Given the filing status is "single"
    And the taxpayer is "Tina Marsh" born "1980-01-15"
    And a W-2 from "LocalCo" with wages $60000 and withholding $8000
    And the taxpayer elects to itemize deductions
    And a casualty loss event with FMV before $200000 and FMV after $150000 and basis $180000 and insurance $20000 and FEMA number "DR-4999"
    And mortgage interest paid of $12000
    When the tax return is calculated
    Then the per-event casualty loss before floors should be $30000
    And the casualty loss deduction should be $30000 minus $500 minus 10% of AGI

  Scenario: Non-disaster casualty — not deductible post-2017
    Given the filing status is "single"
    And the taxpayer is "Vic Pane" born "1985-06-20"
    And a W-2 from "OfficeCo" with wages $50000 and withholding $6000
    And a casualty loss event with no FEMA disaster declaration
    When the tax return is calculated
    Then the casualty loss deduction should be $0

  # ---------------------------------------------------------------------------
  # TASK-019 — Net Investment Income Tax (§1411)
  # ---------------------------------------------------------------------------

  Scenario: High-income filer with investment income above threshold
    Given the filing status is "single"
    And the taxpayer is "Ella Voss" born "1975-11-11"
    And a W-2 from "BigCo" with wages $180000 and withholding $35000
    And interest income of $15000 from "BankCo"
    And dividend income of $20000 ordinary and $15000 qualified from "FundCo"
    When the tax return is calculated
    Then net investment income should be $35000
    And the NIIT amount should be 3.8% of the lesser of NII or MAGI over $200000
    And total tax should include the NIIT amount

  Scenario: Filer below MAGI threshold — no NIIT
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Rick Dunn" born "1982-03-20"
    And a spouse "Sara Dunn" born "1984-07-15"
    And a W-2 from "MidCo" with wages $150000 and withholding $22000
    And interest income of $5000 from "CreditUnion"
    When the tax return is calculated
    Then the NIIT amount should be $0

  # ---------------------------------------------------------------------------
  # TASK-020 — Additional Medicare Tax (§3101(b)(2))
  # ---------------------------------------------------------------------------

  Scenario: Single filer with wages above $200k threshold
    Given the filing status is "single"
    And the taxpayer is "Nina Hart" born "1976-09-05"
    And a W-2 from "MegaCorp" with wages $280000 and withholding $55000 and medicare wages $280000
    When the tax return is calculated
    Then the additional Medicare tax should be 0.9% of $80000
    And total tax should include the additional Medicare tax of $720

  Scenario: Joint filers below $250k combined threshold — no additional tax
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Al Kent" born "1980-01-01"
    And a spouse "Jo Kent" born "1982-06-15"
    And a W-2 from "CompanyA" with wages $120000 and withholding $18000 and medicare wages $120000
    And a W-2 from "CompanyB" with wages $100000 and withholding $15000 and medicare wages $100000
    When the tax return is calculated
    Then the additional Medicare tax should be $0

  # ---------------------------------------------------------------------------
  # TASK-021 — Section 529 Plan Distributions
  # ---------------------------------------------------------------------------

  Scenario: Qualified distribution for college tuition — tax-free
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Dan Wise" born "1975-04-01"
    And a spouse "Amy Wise" born "1977-08-20"
    And a W-2 from "CorpDan" with wages $80000 and withholding $10000
    And a 529 distribution of $20000 with $8000 earnings and $20000 in qualified expenses
    When the tax return is calculated
    Then taxable 529 income should be $0
    And the 529 penalty should be $0

  Scenario: Non-qualified distribution — earnings taxed with 10% penalty
    Given the filing status is "single"
    And the taxpayer is "Eve Stone" born "1990-12-01"
    And a W-2 from "CorpEve" with wages $50000 and withholding $6000
    And a 529 distribution of $15000 with $6000 earnings and $5000 in qualified expenses
    When the tax return is calculated
    Then taxable 529 income should be greater than $0
    And the 529 penalty should be 10% of the taxable earnings portion

  # ---------------------------------------------------------------------------
  # TASK-022 — Like-Kind Exchange (§1031)
  # ---------------------------------------------------------------------------

  Scenario: Straight exchange with no boot — full deferral
    Given the filing status is "single"
    And the taxpayer is "Roy Tate" born "1970-02-14"
    And a W-2 from "CorpRoy" with wages $70000 and withholding $9000
    And a like-kind exchange of property with basis $200000 and FMV $350000 for property with FMV $350000 and no boot
    When the tax return is calculated
    Then the recognized gain should be $0
    And the deferred gain should be $150000
    And the new basis of received property should be $200000

  Scenario: Exchange with boot received — partial recognition
    Given the filing status is "single"
    And the taxpayer is "May Fenn" born "1968-06-30"
    And a W-2 from "CorpMay" with wages $60000 and withholding $7000
    And a like-kind exchange of property with basis $150000 and FMV $300000 for property with FMV $260000 and boot received $40000
    When the tax return is calculated
    Then the recognized gain should be $40000
    And the deferred gain should be $110000

  # ---------------------------------------------------------------------------
  # TASK-023 — Restricted Stock / §83(b) Election
  # ---------------------------------------------------------------------------

  Scenario: RSU vesting — income at vesting FMV
    Given the filing status is "single"
    And the taxpayer is "Kim Cho" born "1988-04-15"
    And a W-2 from "StartupCo" with wages $90000 and withholding $13000
    And restricted stock vesting of 1000 shares at FMV $50 per share with $0 paid
    When the tax return is calculated
    Then restricted stock income should be $50000
    And gross income should include restricted stock income of $50000

  Scenario: §83(b) election — income at grant FMV
    Given the filing status is "single"
    And the taxpayer is "Dev Patel" born "1992-11-20"
    And a W-2 from "EarlyCo" with wages $80000 and withholding $11000
    And restricted stock with §83(b) election of 5000 shares at grant FMV $2 per share with $0 paid
    When the tax return is calculated
    Then restricted stock income should be $10000
    And gross income should include restricted stock income of $10000

  # ---------------------------------------------------------------------------
  # TASK-024 — Savings Bond Education Exclusion (§135)
  # ---------------------------------------------------------------------------

  Scenario: Partial exclusion when expenses are less than proceeds
    Given the filing status is "single"
    And the taxpayer is "Meg Drew" born "1978-05-15"
    And a W-2 from "EduCo" with wages $60000 and withholding $8000
    And savings bond redemption with $10000 proceeds and $3000 interest and $7000 qualified education expenses
    When the tax return is calculated
    Then the excluded savings bond interest should be $2100
    And gross income should be reduced by the excluded amount

  Scenario: Income above phase-out — no exclusion
    Given the filing status is "single"
    And the taxpayer is "Phil Knox" born "1975-10-01"
    And a W-2 from "BigCo" with wages $120000 and withholding $22000
    And savings bond redemption with $10000 proceeds and $3000 interest and $10000 qualified education expenses
    When the tax return is calculated
    Then the excluded savings bond interest should be $0

  # ---------------------------------------------------------------------------
  # TASK-025 — Investment Interest Expense Limitation (§163(d))
  # ---------------------------------------------------------------------------

  Scenario: Investment interest capped at net investment income
    Given the filing status is "single"
    And the taxpayer is "Gus Webb" born "1970-04-01"
    And a W-2 from "BankCo" with wages $100000 and withholding $15000
    And the taxpayer elects to itemize deductions
    And interest income of $3000 from "SavingsBank"
    And investment interest expense of $8000
    And mortgage interest paid of $12000
    When the tax return is calculated
    Then the investment interest deduction should be $3000
    And the investment interest carryforward should be $5000

  Scenario: Investment interest fully deductible within NII
    Given the filing status is "single"
    And the taxpayer is "Hal West" born "1968-09-15"
    And a W-2 from "FundCo" with wages $90000 and withholding $13000
    And the taxpayer elects to itemize deductions
    And interest income of $10000 from "BondFund"
    And investment interest expense of $4000
    And mortgage interest paid of $15000
    When the tax return is calculated
    Then the investment interest deduction should be $4000
    And the investment interest carryforward should be $0
