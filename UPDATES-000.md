# UPDATES-000 — Input Schema Gaps

> **Goal**: Bring `TaxReturnInput` (and downstream calculator / output) to parity
> with the tax situations documented in `NOTES.md`.
>
> Every task below is **independent** unless explicitly noted in a
> "Depends on" line. Agents may execute all non-dependent tasks **in parallel**.
>
> **Files likely touched per task**: `models.py`, `calculator.py`,
> `tests/conftest.py`, a new `.feature` file under `tests/features/`.

---

## Conventions

* IRC section references use the format `§NNN` with a `title26.md:LINE` pointer.
* NOTES.md section numbers (e.g. "NOTES §10") refer to the heading hierarchy
  inside `NOTES.md`.
* All monetary amounts are **2025 inflation-adjusted** unless stated otherwise.
  Obtain them from the existing constants block at the top of `calculator.py`
  or add new ones sourced from IRS Rev. Proc. 2024-40 / Rev. Proc. 2025-XX.
* BDD scenarios use `pytest-bdd`. Reuse step definitions from
  `tests/conftest.py`; add new Given/When/Then steps there (or in a
  task-specific `step_defs/` module) as needed.
* Each task should add the new dataclass(es) to `models.py`, wire them into
  `TaxReturnInput`, update `TaxReturnOutput` / computation dataclasses as
  needed, implement the logic in `calculator.py`, and add feature files with
  the listed BDD scenarios at minimum.

---

## TASK-001 — Schedule K-1 Income (Partnerships, S-Corps, Estates/Trusts)

**Priority**: High  
**Parallel**: Yes

### Context

IRC §61(a)(12–14) (title26.md:70877–70881) includes distributive shares of
partnership income, S-corp income, and estate/trust income in gross income.
These flow through on Schedule K-1 (Forms 1065, 1120-S, 1041). They are among
the most common non-W2 income sources and currently have **zero** representation
in the input schema.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Partnership distributive share | §702, §704 | 70877 | §2 |
| S-Corp income | §1366 | — | — |
| Estate/trust income | §652, §662 | 70881 | §2 |
| Self-employment from K-1 | §1401 | 377596 | §13 |
| QBI from K-1 | §199A | 146332 | §7 |

### Scope

1. Add a `K1Income` dataclass with fields:
   - `entity_name`, `entity_ein`, `entity_type` (enum: `partnership`,
     `s_corp`, `estate_trust`)
   - `ordinary_business_income`, `net_rental_income`, `interest_income`,
     `ordinary_dividends`, `qualified_dividends`, `net_short_term_capital_gain`,
     `net_long_term_capital_gain`, `net_section_1231_gain`,
     `other_income`, `section_179_deduction`
   - `guaranteed_payments` (partnerships only)
   - `self_employment_earnings` (for SE tax)
   - `foreign_taxes_paid`
   - `tax_exempt_income`
   - `distributions` (for basis tracking, informational)
   - `qualified_business_income`, `w2_wages`, `qualified_property_basis`,
     `is_specified_service_business` (§199A passthrough)
2. Add `k1_income: list[K1Income]` to `TaxReturnInput`.
3. In `calculator.py`, fold K-1 amounts into the appropriate gross income
   lines (ordinary income, interest, dividends, capital gains, etc.), SE tax
   computation, and QBI computation.
4. Update `IncomeComputation` / `TaxReturnOutput` to surface K-1 totals.

### Acceptance Criteria

```gherkin
Feature: Schedule K-1 income flows into return

  Scenario: Partnership K-1 with ordinary income and guaranteed payments
    Given the filing status is "single"
    And the taxpayer is "Dana Kim" born "1985-07-22"
    And a partnership K-1 from "Kim & Associates" with ordinary income $60000 and guaranteed payments $40000
    When the tax return is calculated
    Then gross income should include K-1 ordinary income of $60000
    And gross income should include guaranteed payments of $40000
    And total SE tax should be greater than $0

  Scenario: S-Corp K-1 with qualified dividends and capital gains
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Eli Park" born "1978-11-03"
    And a spouse "Mia Park" born "1980-02-14"
    And an S-Corp K-1 from "Park Holdings" with ordinary income $25000 and long-term capital gains $15000 and qualified dividends $5000
    When the tax return is calculated
    Then gross income should include K-1 ordinary income of $25000
    And net long-term capital gains should include $15000 from K-1
    And qualified dividends should include $5000 from K-1
```

---

## TASK-002 — Premium Tax Credit / ACA Marketplace (§36B)

**Priority**: High  
**Parallel**: Yes

### Context

The Premium Tax Credit (PTC) under §36B (title26.md:26647) is a **refundable**
credit for health insurance purchased through an ACA Exchange. It affects
millions of filers. Advance payments must be reconciled on the return.
Currently there are **no** ACA-related fields in the input schema.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| PTC eligibility & computation | §36B | 26647 | §10 |
| Advance payment reconciliation | §36B(f) | 27160 | §10 |
| FPL-based contribution % | §36B(b)(3)(A) | 26741, 26847 | §10 |
| Employer affordability | §36B(c)(2)(C) | 26914 | §10 |

### Scope

1. Add a `MarketplaceCoverage` dataclass:
   - `marketplace_plan_name`, `state_exchange`
   - `monthly_enrollment` (list of 12 booleans or a coverage-months count)
   - `annual_premium`, `annual_slcsp_premium` (second-lowest-cost silver plan)
   - `advance_ptc_received`
   - `household_size` (for FPL calculation)
2. Add `marketplace_coverage: Optional[MarketplaceCoverage]` to `TaxReturnInput`.
3. Implement PTC calculation:
   - Determine applicable FPL percentage based on household income.
   - Compute expected contribution = household income × applicable %.
   - Credit = max(0, SLCSP premium − expected contribution), capped at actual
     premium.
   - Reconcile against advance PTC: excess must be repaid (subject to
     repayment caps for income < 400% FPL).
4. Add `premium_tax_credit` and `excess_advance_ptc_repayment` to
   `CreditComputation` / `TaxReturnOutput`.

### Acceptance Criteria

```gherkin
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
    And a W-2 from "BigCo" with wages $120000 and withholding $18000
    And marketplace coverage with annual premium $12000 and SLCSP premium $13000 and advance PTC $4000 and household size 2
    When the tax return is calculated
    Then the premium tax credit should be $0
    And the excess advance PTC repayment should be $4000
```

---

## TASK-003 — Alternative Minimum Tax Preference Items (§55)

**Priority**: High  
**Parallel**: Yes

### Context

The calculator already has AMT exemption/phase-out constants but **no input
fields** for AMT preference items. Without them, AMT can never actually
trigger. Key preference items include ISO exercises, tax-exempt interest from
private activity bonds, SALT deduction addback, and miscellaneous adjustments.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| AMT imposed | §55 | 64924 | §12 |
| AMT rates (26%/28%) | §55(b)(1) | 64948 | §12 |
| AMT exemption amounts | §55(d) | 65077 | §12 |
| AMT phase-out of exemption | §55(d)(4) | 65100 | §12 |
| AMTI adjustments | §56 | — | — |
| AMT preference items | §57 | — | — |

### Scope

1. Add an `AMTPreferenceItems` dataclass:
   - `iso_exercise_spread` — spread on incentive stock options exercised
     (§56(b)(19) / §422)
   - `private_activity_bond_interest` — tax-exempt interest from PABs
     (§57(a)(5))
   - `depletion_excess` — excess depletion (§57(a)(1))
   - `intangible_drilling_costs_excess` — (§57(a)(2))
   - `other_adjustments` — catch-all
   - `prior_year_amt_credit` — minimum tax credit carryforward from prior
     years (§53)
2. Add `amt_preferences: Optional[AMTPreferenceItems]` to `TaxReturnInput`.
3. In `calculator.py`:
   - Compute AMTI = taxable income + SALT addback + preference items −
     AMT-specific deductions.
   - Apply AMT exemption and phase-out (constants already exist).
   - Compute tentative minimum tax at 26%/28%.
   - AMT = max(0, tentative minimum tax − regular tax).
   - Apply prior-year AMT credit against regular tax in excess of TMT.
4. Add `amt`, `amti`, `amt_exemption_used`, `prior_year_amt_credit_used` to
   `TaxComputation` / `TaxReturnOutput`.

### Acceptance Criteria

```gherkin
Feature: Alternative Minimum Tax computation

  Scenario: ISO exercise triggers AMT
    Given the filing status is "single"
    And the taxpayer is "Ava Reyes" born "1983-09-20"
    And a W-2 from "TechCo" with wages $200000 and withholding $40000
    And AMT preference items with ISO exercise spread $300000
    When the tax return is calculated
    Then AMTI should be greater than taxable income
    And the AMT amount should be greater than $0
    And total tax should include the AMT amount

  Scenario: High earner with no preference items — no AMT
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Ben Cruz" born "1975-03-01"
    And a spouse "Liz Cruz" born "1977-08-10"
    And a W-2 from "FinCorp" with wages $350000 and withholding $70000
    And no AMT preference items
    When the tax return is calculated
    Then the AMT amount should be $0
```

---

## TASK-004 — EITC Eligibility Fields (§32)

**Priority**: High  
**Parallel**: Yes

### Context

The calculator already computes EITC (`_compute_eitc`), but the input has no
fields to capture disqualifying conditions or required eligibility data such as
investment income, US abode duration, or prior fraud disqualification.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| EITC computation | §32 | 22751 | §10 |
| Investment income limit | §32(i) | 23033 | §10 |
| No-child age requirement | §32(c)(1)(A)(ii) | 22835 | §10 |
| US abode requirement | §32(c)(1)(A)(ii) | 22835 | §10 |
| Disqualification for fraud | §32(k) | 23119 | §10 |
| MFS ineligibility | §32(d) | 22969 | §10 |
| SSN requirement | §32(m) | 22872 | §10 |

### Scope

1. Add an `EITCEligibility` dataclass:
   - `has_valid_ssn_for_employment: bool = True`
   - `investment_income: float = 0.0` (interest + dividends + capital gains +
     rents/royalties net income + passive income)
   - `lived_in_us_more_than_half_year: bool = True`
   - `is_qualifying_child_of_another: bool = False`
   - `prior_eitc_disqualification_year: Optional[int] = None`
   - `prior_eitc_fraud: bool = False`
2. Add `eitc_eligibility: Optional[EITCEligibility]` to `TaxReturnInput`.
3. In `calculator.py`, gate EITC on:
   - Investment income ≤ $11,950 (2025).
   - Filing status not MFS (unless separated-spouse exception).
   - Valid SSN, US abode, not a qualifying child of another, no active
     disqualification period.
4. Surface `eitc_disqualification_reason` (if any) on output.

### Acceptance Criteria

```gherkin
Feature: EITC eligibility gating

  Scenario: Filer with excess investment income is denied EITC
    Given the filing status is "single"
    And the taxpayer is "Nia Jones" born "1990-06-01"
    And a W-2 from "RetailCo" with wages $22000 and withholding $1000
    And EITC eligibility with investment income $15000
    When the tax return is calculated
    Then the earned income credit should be $0
    And the EITC disqualification reason should mention "investment income"

  Scenario: Eligible single filer with one child receives EITC
    Given the filing status is "head_of_household"
    And the taxpayer is "Carlos Vega" born "1988-12-15"
    And a W-2 from "ShopCo" with wages $25000 and withholding $1500
    And a qualifying child "Mia Vega" born "2018-03-20"
    And EITC eligibility with investment income $500
    When the tax return is calculated
    Then the earned income credit should be greater than $0
```

---

## TASK-005 — Adoption Credit (§23)

**Priority**: Medium  
**Parallel**: Yes

### Context

The adoption credit (§23, title26.md:13227) provides up to ~$17,280 (2025
adjusted) per child for qualified adoption expenses. It is partially
refundable (up to $5,000). Special-needs adoptions are deemed to have the
maximum expense. Excess nonrefundable credit carries forward 5 years.
Currently completely absent from the schema.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Adoption credit amount | §23(a) | 13227 | §9 |
| Special needs deemed amount | §23(a)(3) | 13252 | §9 |
| Refundable portion ($5k) | §23(a)(4) | 13261 | §9 |
| AGI phase-out | §23(b) | 13279 | §9 |
| Carryforward (5 years) | §23(c) | 13323 | §9 |

### Scope

1. Add an `AdoptionExpense` dataclass:
   - `child_name`, `child_ssn` (or ATIN)
   - `is_special_needs: bool = False`
   - `is_foreign_adoption: bool = False`
   - `qualified_expenses: float = 0.0`
   - `year_expenses_paid: int` (may differ from finalization year)
   - `adoption_finalized_year: Optional[int] = None`
   - `prior_year_carryforward: float = 0.0`
2. Add `adoption_expenses: list[AdoptionExpense]` to `TaxReturnInput`.
3. Implement credit computation with AGI phase-out (begins ~$252,150,
   complete at ~$292,150 for 2025) and the $5,000 refundable portion.
4. Add `adoption_credit_nonrefundable`, `adoption_credit_refundable`,
   `adoption_credit_carryforward` to `CreditComputation`.

### Acceptance Criteria

```gherkin
Feature: Adoption credit

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
```

---

## TASK-006 — Credit for the Elderly or Disabled (§22)

**Priority**: Medium  
**Parallel**: Yes

### Context

§22 (title26.md:12756) provides a 15% nonrefundable credit for taxpayers age
65+ or permanently/totally disabled with low income. It is phased out by
nontaxable Social Security/VA benefits and by AGI. Currently absent.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Credit rate (15%) | §22(a) | 12762 | §9 |
| Initial amounts | §22(c) | 12791 | §9 |
| SS/VA benefit reduction | §22(c)(3)(A) | 12835 | §9 |
| AGI phase-out | §22(d) | 12865 | §9 |

### Scope

1. Add an `ElderlyDisabledCredit` dataclass:
   - `is_age_65_or_older: bool` (can also be derived from DOB)
   - `is_permanently_totally_disabled: bool = False`
   - `disability_income: float = 0.0` (taxable disability income if under 65)
   - `nontaxable_social_security: float = 0.0`
   - `nontaxable_va_pension: float = 0.0`
2. Add `elderly_disabled_credit: Optional[ElderlyDisabledCredit]` to
   `TaxReturnInput`.
3. Implement the §22 computation: initial amount − nontaxable benefits −
   50% × (AGI − threshold); credit = 15% of remainder.
4. Add `elderly_disabled_credit` to `CreditComputation`.

### Acceptance Criteria

```gherkin
Feature: Credit for the elderly or disabled

  Scenario: Single filer age 67 with low income qualifies
    Given the filing status is "single"
    And the taxpayer is "Ruth Adams" born "1958-02-28"
    And pension income of $18000 gross and $18000 taxable with $1500 withheld
    And elderly/disabled credit info with nontaxable Social Security $6000
    When the tax return is calculated
    Then the elderly or disabled credit should be greater than $0

  Scenario: High-AGI senior — credit fully phased out
    Given the filing status is "single"
    And the taxpayer is "Gene Black" born "1955-05-10"
    And a W-2 from "Consulting" with wages $80000 and withholding $12000
    And elderly/disabled credit info with nontaxable Social Security $0
    When the tax return is calculated
    Then the elderly or disabled credit should be $0
```

---

## TASK-007 — Royalty Income

**Priority**: Medium  
**Parallel**: Yes

### Context

IRC §61(a)(6) (title26.md:70865) explicitly lists royalties in gross income.
Royalty income is reported on Schedule E Part I (alongside rental income) and
may generate QBI or be subject to SE tax depending on the filer's
participation. Currently not in the schema.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Royalties as gross income | §61(a)(6) | 70865 | §2 |
| Deductions for royalties | §62(a)(4) | 71305 | §2 |
| QBI from royalties | §199A | 146332 | §7 |

### Scope

1. Add a `RoyaltyIncome` dataclass:
   - `description` (e.g., "oil/gas", "book", "patent")
   - `payer_name`
   - `gross_royalties: float`
   - `expenses: float = 0.0` (depletion, depreciation, etc.)
   - `is_subject_to_se_tax: bool = False`
2. Add `royalty_income: list[RoyaltyIncome]` to `TaxReturnInput`.
3. Include net royalties in gross income; if SE-flagged, include in SE
   computation. Already-existing `OtherIncome` workaround should not be
   required for royalties.
4. Add `total_royalty_income` to `IncomeComputation`.

### Acceptance Criteria

```gherkin
Feature: Royalty income on Schedule E

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
```

---

## TASK-008 — Farm Income (Schedule F)

**Priority**: Medium  
**Parallel**: Yes

### Context

Farm income has its own schedule (Schedule F) and special rules: 2-year NOL
carryback (§172(b)(1)(B)), estimated tax exceptions for farmers (§6654(i)),
and farm-specific expense categories. Currently absent.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Trade/business expenses | §162 | 114102 | §7 |
| Farm NOL carryback | §172(b)(1)(B) | 137738 | §7 |
| SE tax on farm income | §1401 | 377596 | §13 |
| Farmer estimated tax | §6654(i) | 566326 | §17 |

### Scope

1. Add a `FarmIncome` dataclass mirroring `BusinessIncome` but with
   farm-specific fields:
   - `farm_name`, `principal_product`
   - `gross_farm_income` (sales of livestock, produce, etc.)
   - `cost_of_livestock_purchased`, `conservation_expenses`,
     `custom_hire`, `feed`, `fertilizers`, `freight`, `gasoline_fuel`,
     `labor_hired`, `pension_plans`, `rent_lease_land`,
     `rent_lease_equipment`, `seeds_plants`, `storage`,
     `supplies`, `taxes`, `utilities`, `vet_fees`,
     `other_expenses`, `depreciation`, `car_and_truck`
   - `crop_insurance_proceeds`, `ccc_loans_reported_as_income`
   - `is_material_participant: bool = True`
2. Add `farm_income: list[FarmIncome]` to `TaxReturnInput`.
3. Compute net farm profit, include in gross income and SE tax. Flag for
   2-year NOL carryback eligibility on output.
4. Add `total_farm_income`, `farm_nol_carryback_eligible` to output.

### Acceptance Criteria

```gherkin
Feature: Farm income on Schedule F

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
```

---

## TASK-009 — Alimony Received (Pre-2019 Instruments)

**Priority**: Low  
**Parallel**: Yes

### Context

For divorce/separation instruments executed **before** January 1, 2019,
alimony received is gross income (former §71, removed by TCJA but still
applies to pre-2019 instruments). The schema has `alimony_paid` but no
`alimony_received`. See NOTES.md §2 (title26.md:70897).

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Alimony in gross income (pre-2019) | former §71 | 70897 | §2 |
| Alimony deduction (pre-2019) | former §215 | — | §2 |

### Scope

1. Add to `TaxReturnInput`:
   - `alimony_received: float = 0.0`
   - `alimony_payer_ssn: str = ""`
   - `alimony_instrument_date: str = ""` (ISO 8601; must be pre-2019 for
     inclusion)
2. In `calculator.py`, include in gross income only if instrument date is
   before 2019-01-01; else ignore with a validation warning.
3. Add `alimony_income` to `IncomeComputation`.

### Acceptance Criteria

```gherkin
Feature: Alimony received for pre-2019 instruments

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
```

---

## TASK-010 — Gambling Income and Losses

**Priority**: Medium  
**Parallel**: Yes

### Context

Gambling winnings are gross income (§61). Gambling losses are deductible on
Schedule A but only to the extent of gambling gains, and limited to 90% of
wagering losses (§165(d), title26.md:120131, NOTES.md §7). Reported on W-2G
or self-reported. Currently absent.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Gross income | §61 | 70846 | §2 |
| Wagering loss limits | §165(d) | 120131 | §7 |

### Scope

1. Add a `GamblingIncome` dataclass:
   - `w2g_winnings: float = 0.0` (from Form W-2G)
   - `other_winnings: float = 0.0` (self-reported)
   - `federal_income_tax_withheld: float = 0.0`
   - `losses: float = 0.0` (for itemized deduction)
2. Add `gambling: Optional[GamblingIncome]` to `TaxReturnInput`.
3. Include winnings in gross income. If itemizing, allow losses as a
   deduction capped at total winnings and further limited to 90% of
   wagering losses (§165(d)).
4. Add `gambling_income`, `gambling_loss_deduction` to output.

### Acceptance Criteria

```gherkin
Feature: Gambling income and losses

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
```

---

## TASK-011 — Annuity Income (§72)

**Priority**: Low  
**Parallel**: Yes

### Context

Annuity payments (non-retirement-plan) use the exclusion ratio or simplified
method to determine the taxable portion (§72, title26.md:74051, NOTES.md §3).
Currently only `RetirementDistribution` exists, which doesn't model the
exclusion ratio.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Annuity taxation | §72 | 74051 | §3 |
| Exclusion ratio | §72(b) | 74051 | §3 |
| Simplified method | §72(d)(1) | 74051 | §3 |

### Scope

1. Add an `AnnuityIncome` dataclass:
   - `payer_name`, `contract_type` (e.g., "commercial", "employer_plan")
   - `gross_payment: float`
   - `investment_in_contract: float` (after-tax basis)
   - `expected_return: float` (or `anticipated_payments: int` for simplified)
   - `amount_previously_recovered: float = 0.0`
   - `use_simplified_method: bool = False`
   - `annuitant_age_at_start: int = 0` (for simplified method divisor)
   - `federal_income_tax_withheld: float = 0.0`
2. Add `annuity_income: list[AnnuityIncome]` to `TaxReturnInput`.
3. Compute taxable amount using exclusion ratio or simplified method.
4. Add `total_annuity_income`, `annuity_taxable_amount` to output.

### Acceptance Criteria

```gherkin
Feature: Annuity income with exclusion ratio

  Scenario: Commercial annuity — partial exclusion
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
```

---

## TASK-012 — Scholarship Income (§117)

**Priority**: Low  
**Parallel**: Yes

### Context

Qualified scholarships for degree candidates are excluded (§117,
title26.md:89656, NOTES.md §4). Amounts for room/board or services rendered
are **taxable**. This distinction is not captured.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Qualified scholarship exclusion | §117(a) | 89656 | §4 |
| Room/board not excluded | §117(b) | 89656 | §4 |
| Service payments not excluded | §117(c) | 89656 | §4 |

### Scope

1. Add a `ScholarshipIncome` dataclass:
   - `institution_name`
   - `total_scholarship: float`
   - `qualified_tuition_and_fees: float` (excluded portion)
   - `room_board_stipend: float = 0.0` (taxable)
   - `service_compensation: float = 0.0` (teaching/research — taxable)
2. Add `scholarship_income: list[ScholarshipIncome]` to `TaxReturnInput`.
3. Taxable amount = total − qualified portion. Include in gross income.
4. Add `taxable_scholarship_income` to output.

### Acceptance Criteria

```gherkin
Feature: Scholarship income — taxable vs. excluded portions

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
```

---

## TASK-013 — NOL Carryforward (§172)

**Priority**: High  
**Parallel**: Yes

### Context

Post-2017 NOLs carry forward **indefinitely** but are limited to 80% of
taxable income (§172, title26.md:137738, NOTES.md §7). The input has no field
for prior-year NOL carryforward, so filers with prior losses cannot apply them.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| NOL deduction | §172(a) | 137738 | §7 |
| 80% limitation | §172(a)(2) | 137738 | §7 |
| Indefinite carryforward | §172(b)(1) | 137738 | §7 |
| Farm loss carryback | §172(b)(1)(B) | 137738 | §7 |

### Scope

1. Add to `TaxReturnInput`:
   - `nol_carryforward: float = 0.0` (total NOL available from prior years)
   - `nol_carryforward_pre_2018: float = 0.0` (pre-2018 NOLs — no 80% limit)
2. In `calculator.py`, apply NOL deduction after computing taxable income:
   - Pre-2018 NOLs applied first, no percentage limit.
   - Post-2017 NOLs limited to 80% of remaining taxable income (before
     §199A and §250).
3. Add `nol_deduction`, `nol_carryforward_remaining` to
   `DeductionComputation` / output.

### Acceptance Criteria

```gherkin
Feature: Net operating loss carryforward

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
```

---

## TASK-014 — Charitable Contribution Carryforward (§170)

**Priority**: Medium  
**Parallel**: Yes

### Context

Charitable contributions exceeding the AGI-based percentage limits carry
forward for 5 years (§170(d), title26.md:132765, NOTES.md §6). No input
field exists.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Contribution limits (50%/30%/20%) | §170(b) | 132738–132818 | §6 |
| 5-year carryforward | §170(d) | 132765 | §6 |

### Scope

1. Add to `TaxReturnInput`:
   - `charitable_contribution_carryforward: float = 0.0`
   - Optionally break down by limit category (50%/30%/20%).
2. In `calculator.py`, apply carryforward after current-year contributions,
   still subject to AGI limits.
3. Add `charitable_carryforward_used`, `charitable_carryforward_remaining` to
   `DeductionComputation`.

### Acceptance Criteria

```gherkin
Feature: Charitable contribution carryforward

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
```

---

## TASK-015 — §25D Clean Energy Credit Carryforward

**Priority**: Low  
**Parallel**: Yes

### Context

The residential clean energy credit (§25D, title26.md:18115, NOTES.md §9)
explicitly allows unused credit to carry forward. No input field exists for
prior-year carryforward.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Carryforward allowed | §25D(c) | 18156 | §9 |
| 30% credit rate | §25D(a) | 18347 | §9 |
| Sunset Dec 31, 2025 | §25D(h) | 18362 | §9 |

### Scope

1. Add to `TaxReturnInput`:
   - `energy_credit_carryforward: float = 0.0`
2. Apply carryforward after current-year §25D credit, limited by tax
   liability.
3. Add `energy_credit_carryforward_used`,
   `energy_credit_carryforward_remaining` to `CreditComputation`.

### Acceptance Criteria

```gherkin
Feature: Residential clean energy credit carryforward

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
```

---

## TASK-016 — Capital Loss Carryforward Breakdown (Short/Long)

**Priority**: Medium  
**Parallel**: Yes

### Context

The existing `capital_loss_carryforward: float` is a single number, but
capital loss carryforwards retain their character — short-term losses carry
forward as short-term, long-term as long-term (§1212(b),
title26.md:350269). This affects netting and tax rates.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Capital loss carryover rules | §1212(b) | 350269 | §11 |
| Capital loss limitation ($3k) | §1211(b) | 350175 | §11 |
| Netting rules | §1222 | 351190 | §11 |

### Scope

1. Replace or augment `capital_loss_carryforward: float` on
   `TaxReturnInput` with:
   - `capital_loss_carryforward_short_term: float = 0.0`
   - `capital_loss_carryforward_long_term: float = 0.0`
   (keep the original field for backward compatibility; if set, treat as
   long-term)
2. In `calculator.py`, net ST carryforward against ST gains first, then
   LT carryforward against LT gains, then cross-net per §1(h) ordering.
3. Add `capital_loss_carryforward_remaining_short`,
   `capital_loss_carryforward_remaining_long` to output.

### Acceptance Criteria

```gherkin
Feature: Capital loss carryforward with ST/LT character

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
```

---

## TASK-017 — Kiddie Tax (§1(g))

**Priority**: Medium  
**Parallel**: Yes

### Context

Children under 18 (or under 24 if a student whose earned income ≤ half their
support) have unearned income above a threshold taxed at the parent's marginal
rate (§1(g), title26.md:5520, NOTES.md §1). This requires parent tax info
that is not currently captured.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Kiddie tax rules | §1(g) | 5520 | §1 |
| Threshold amount | §1(g)(4) | 5520 | §1 |
| Parent's rate | §1(g)(3) | 5520 | §1 |

### Scope

1. Add a `KiddieTaxInfo` dataclass:
   - `child_unearned_income: float`
   - `child_earned_income: float`
   - `parent_taxable_income: float` (parent's taxable income for rate
     lookup)
   - `parent_filing_status: FilingStatus`
   - `parent_marginal_rate: float` (alternatively compute from above)
   - `child_is_full_time_student: bool = False`
   - `child_provides_over_half_support: bool = False`
2. Add `kiddie_tax: Optional[KiddieTaxInfo]` to `TaxReturnInput`.
3. In `calculator.py`, if kiddie tax applies, compute the tax on unearned
   income above the threshold at the parent's marginal rate.
4. Add `kiddie_tax_amount` to `TaxComputation`.

### Acceptance Criteria

```gherkin
Feature: Kiddie tax on child's unearned income

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
```

---

## TASK-018 — Casualty and Disaster Loss Detail (§165)

**Priority**: Low  
**Parallel**: Yes

### Context

The existing `casualty_loss_from_disaster: float` is a single number, but the
rules require per-event $500 floor, 10% AGI threshold, and a federally
declared disaster designation (§165(h), title26.md:120131, NOTES.md §7).

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Casualty loss rules | §165(c)(3) | 120131 | §7 |
| $500 per-event floor | §165(h)(1) | 120131 | §7 |
| 10% AGI threshold | §165(h)(2) | 120131 | §7 |
| Disaster-only limitation | §165(h)(5) | 120131 | §7 |

### Scope

1. Add a `CasualtyLossEvent` dataclass:
   - `description`
   - `fema_disaster_declaration_number: str`
   - `date_of_loss: str`
   - `property_type: str`
   - `fair_market_value_before: float`
   - `fair_market_value_after: float`
   - `adjusted_basis: float`
   - `insurance_reimbursement: float = 0.0`
   - `other_reimbursement: float = 0.0`
2. Replace `casualty_loss_from_disaster: float` with
   `casualty_losses: list[CasualtyLossEvent]` on `TaxReturnInput` (or keep
   the simple field as a fallback).
3. Compute per-event loss = min(decline in FMV, adjusted basis) −
   reimbursements − $500 floor. Sum all events, then subtract 10% of AGI.
4. Add `total_casualty_loss_deduction`, `casualty_loss_per_event_details` to
   output.

### Acceptance Criteria

```gherkin
Feature: Itemized casualty loss from federally declared disasters

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
```

---

## TASK-019 — Net Investment Income Tax (§1411)

**Priority**: High  
**Parallel**: Yes

### Context

The 3.8% Net Investment Income Tax (NIIT) applies to the lesser of net
investment income or MAGI exceeding $200k/$250k (§1411). The calculator does
not compute this. While most inputs can be derived from existing fields, an
explicit NII breakdown is helpful for accuracy.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| NIIT rate (3.8%) | §1411(a) | — | — |
| MAGI threshold | §1411(b) | — | — |
| Net investment income defined | §1411(c) | — | — |

### Scope

1. No new input dataclass strictly required — NII is derivable from existing
   interest, dividends, capital gains, rental income, royalties, and passive
   business income. However, add:
   - `net_investment_income_override: Optional[float] = None` to
     `TaxReturnInput` for filers who need to manually specify NII (e.g.,
     complex trust/estate situations).
2. In `calculator.py`:
   - Compute NII = interest + ordinary dividends + capital gains + rental
     income + royalty income + passive business income − investment expenses.
   - NIIT = 3.8% × min(NII, MAGI − threshold).
   - Thresholds: $250,000 MFJ, $200,000 single/HoH, $125,000 MFS.
3. Add `net_investment_income`, `niit_amount` to `TaxComputation` / output.
   Include NIIT in `total_tax`.

### Acceptance Criteria

```gherkin
Feature: Net Investment Income Tax (3.8% surtax)

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
```

---

## TASK-020 — Additional Medicare Tax (§3101(b)(2) / §1401(b)(2))

**Priority**: High  
**Parallel**: Yes

### Context

The 0.9% Additional Medicare Tax applies to wages/SE income exceeding
$200k/$250k (§3101(b)(2) for employees, §1401(b)(2) for self-employed). The
SE tax computation in `calculator.py` already references this
(`SE_ADDITIONAL_MEDICARE`), but the **employee** side is not computed — W-2
box 6 only contains base Medicare, not the additional tax. The additional tax
must be computed on the return and reconciled against any withholding.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Employee additional Medicare | §3101(b)(2) | — | — |
| SE additional Medicare | §1401(b)(2) | 377621 | §13 |
| Threshold amounts | — | — | §13 |

### Scope

1. No new input fields required — wages come from W-2, thresholds from
   filing status. However, add:
   - `additional_medicare_tax_withheld: float = 0.0` to `W2Income` (W-2
     box 14 / reported separately by some employers).
2. In `calculator.py`:
   - Compute Additional Medicare Tax = 0.9% × (total Medicare wages + SE
     income − threshold).
   - Credit withholding already captured against liability.
3. Add `additional_medicare_tax`, `additional_medicare_tax_withheld` to
   output. Include in `total_tax`.

### Acceptance Criteria

```gherkin
Feature: Additional Medicare Tax (0.9%)

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
```

---

## TASK-021 — §529 Plan Distributions

**Priority**: Low  
**Parallel**: Yes

### Context

§529 (title26.md:263347, NOTES.md §14) qualified tuition program
distributions are tax-free for qualified expenses but the earnings portion of
non-qualified distributions is taxable income plus 10% penalty. Also supports
529-to-Roth IRA rollovers.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Qualified distributions | §529(c)(3)(B) | 263347 | §14 |
| Penalty on non-qualified | §529(c)(6) | 263347 | §14 |
| K-12 tuition | §529(c)(7) | 263347 | §14 |
| Student loan repayment ($10k) | §529(c)(9) | 263347 | §14 |
| 529-to-Roth rollover | §529(c)(3)(C)(iv) | 263347 | §14 |

### Scope

1. Add a `Section529Distribution` dataclass:
   - `plan_name`, `beneficiary_name`, `beneficiary_ssn`
   - `gross_distribution: float`
   - `earnings_portion: float`
   - `qualified_education_expenses: float`
   - `is_k12_tuition: bool = False` (capped at $10,000/year)
   - `student_loan_repayment: float = 0.0` (capped at $10,000 lifetime)
   - `rollover_to_roth: float = 0.0`
2. Add `section_529_distributions: list[Section529Distribution]` to
   `TaxReturnInput`.
3. Compute taxable earnings on non-qualified portion. Apply 10% penalty on
   taxable non-qualified earnings.
4. Add `taxable_529_income`, `section_529_penalty` to output.

### Acceptance Criteria

```gherkin
Feature: Section 529 plan distributions

  Scenario: Qualified distribution for college tuition — tax-free
    Given the filing status is "married_filing_jointly"
    And the taxpayer is "Dan Wise" born "1975-04-01"
    And a spouse "Amy Wise" born "1977-08-20"
    And a 529 distribution of $20000 with $8000 earnings and $20000 in qualified expenses
    When the tax return is calculated
    Then taxable 529 income should be $0
    And the 529 penalty should be $0

  Scenario: Non-qualified distribution — earnings taxed with 10% penalty
    Given the filing status is "single"
    And the taxpayer is "Eve Stone" born "1990-12-01"
    And a 529 distribution of $15000 with $6000 earnings and $5000 in qualified expenses
    When the tax return is calculated
    Then taxable 529 income should be greater than $0
    And the 529 penalty should be 10% of the taxable earnings portion
```

---

## TASK-022 — Like-Kind Exchange (§1031)

**Priority**: Low  
**Parallel**: Yes

### Context

§1031 (title26.md:342673, NOTES.md §11) defers gain/loss recognition on
exchanges of like-kind **real property** held for business or investment. Boot
(cash or non-like-kind property received) triggers partial gain recognition.
Currently absent.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Like-kind exchange rules | §1031(a) | 342673 | §11 |
| Boot recognition | §1031(b) | 342673 | §11 |
| 45-day identification | §1031(a)(3) | 342673 | §11 |
| Related party 2-year rule | §1031(f) | 342673 | §11 |

### Scope

1. Add a `LikeKindExchange` dataclass:
   - `property_relinquished_description: str`
   - `property_received_description: str`
   - `date_relinquished: str`
   - `date_received: str`
   - `fmv_relinquished: float`
   - `adjusted_basis_relinquished: float`
   - `fmv_received: float`
   - `boot_received: float = 0.0`
   - `boot_paid: float = 0.0`
   - `liabilities_relieved: float = 0.0`
   - `liabilities_assumed: float = 0.0`
   - `is_related_party: bool = False`
2. Add `like_kind_exchanges: list[LikeKindExchange]` to `TaxReturnInput`.
3. Compute recognized gain = min(realized gain, net boot received). Compute
   deferred gain and new basis of received property.
4. Add `like_kind_recognized_gain`, `like_kind_deferred_gain`,
   `like_kind_new_basis` to output.

### Acceptance Criteria

```gherkin
Feature: Like-kind exchange (§1031) gain deferral

  Scenario: Straight exchange with no boot — full deferral
    Given the filing status is "single"
    And the taxpayer is "Roy Tate" born "1970-02-14"
    And a like-kind exchange of property with basis $200000 and FMV $350000 for property with FMV $350000 and no boot
    When the tax return is calculated
    Then the recognized gain should be $0
    And the deferred gain should be $150000
    And the new basis of received property should be $200000

  Scenario: Exchange with boot received — partial recognition
    Given the filing status is "single"
    And the taxpayer is "May Fenn" born "1968-06-30"
    And a like-kind exchange of property with basis $150000 and FMV $300000 for property with FMV $260000 and boot received $40000
    When the tax return is calculated
    Then the recognized gain should be $40000
    And the deferred gain should be $110000
```

---

## TASK-023 — Restricted Stock / §83(b) Election

**Priority**: Low  
**Parallel**: Yes

### Context

Property received for services (e.g., restricted stock) is taxed at
substantial vesting unless a §83(b) election is filed (§83, title26.md:78996,
NOTES.md §3). This is common for startup employees and is not captured.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Property transferred for services | §83(a) | 78996 | §3 |
| §83(b) election | §83(b) | 78996 | §3 |

### Scope

1. Add a `RestrictedStockEvent` dataclass:
   - `description: str`
   - `grant_date: str`
   - `vesting_date: str` (or election date if §83(b))
   - `fmv_at_vesting: float` (or FMV at grant if §83(b))
   - `amount_paid: float = 0.0`
   - `section_83b_election: bool = False`
   - `fmv_at_grant: float = 0.0` (needed if §83(b) elected)
   - `shares: int = 0`
2. Add `restricted_stock_events: list[RestrictedStockEvent]` to
   `TaxReturnInput`.
3. Compute compensation income = FMV at relevant date − amount paid.
   Include in gross income (wages-like). If §83(b), income recognized at
   grant; if forfeited later, no deduction.
4. Add `restricted_stock_income` to `IncomeComputation`.

### Acceptance Criteria

```gherkin
Feature: Restricted stock compensation (§83)

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
```

---

## TASK-024 — Savings Bond Education Exclusion (§135)

**Priority**: Low  
**Parallel**: Yes

### Context

Interest from Series EE/I bonds redeemed to pay qualified higher education
expenses may be excluded (§135, title26.md:90338, NOTES.md §4). The
`InterestIncome` model has `us_savings_bond_interest` but there is no way to
link it to education expenses or provide the income phase-out data.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Education savings bond exclusion | §135 | 90338 | §4 |
| Income phase-out | §135(b)(2) | 90338 | §4 |

### Scope

1. Add a `SavingsBondEducationExclusion` dataclass:
   - `total_bond_proceeds: float` (principal + interest)
   - `bond_interest: float`
   - `qualified_education_expenses: float`
   - `scholarships_and_grants: float = 0.0` (reduce qualified expenses)
2. Add `savings_bond_education: Optional[SavingsBondEducationExclusion]` to
   `TaxReturnInput`.
3. Excludable interest = bond_interest × (qualified expenses / total
   proceeds), subject to MAGI phase-out.
4. Add `savings_bond_interest_excluded` to `AGIComputation` / output.

### Acceptance Criteria

```gherkin
Feature: Savings bond interest exclusion for education (§135)

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
    And a W-2 from "BigCo" with wages $110000 and withholding $20000
    And savings bond redemption with $10000 proceeds and $3000 interest and $10000 qualified education expenses
    When the tax return is calculated
    Then the excluded savings bond interest should be $0
```

---

## TASK-025 — Investment Interest Expense Limitation Detail (§163(d))

**Priority**: Medium  
**Parallel**: Yes  
**Depends on**: Partially benefits from TASK-007 (royalty income) and TASK-019
(NIIT) but can proceed independently.

### Context

The input has `investment_interest_expense: float` but no `net_investment_income`
field. Under §163(d), investment interest is deductible only to the extent of
net investment income. Excess carries forward. The calculator cannot enforce
this limit without the income counterpart.

### References

| Topic | IRC | title26.md | NOTES.md |
|---|---|---|---|
| Investment interest limitation | §163(d) | 116555 | §6 |
| Net investment income defined | §163(d)(4) | 116555 | §6 |

### Scope

1. Add to `TaxReturnInput`:
   - `net_investment_income_override: Optional[float] = None` (if the filer
     wants to manually specify; otherwise derive from interest + ordinary
     dividends + short-term capital gains − investment expenses).
   - `investment_interest_carryforward: float = 0.0`
   - `elect_to_include_qualified_dividends_in_nii: bool = False` (§163(d)(4)(B)
     election to treat qualified dividends / LTCG as investment income so more
     interest can be deducted — but they lose preferential rates).
2. In `calculator.py`, compute NII (from existing inputs or override), limit
   investment interest deduction to NII, carry forward excess.
3. Add `investment_interest_deduction`, `investment_interest_carryforward` to
   `DeductionComputation`.

### Acceptance Criteria

```gherkin
Feature: Investment interest expense limitation (§163(d))

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
```

---

## Dependency Graph

All tasks are independent unless noted. The following shows optional
"benefits from" relationships where output of one task enriches another, but
none are hard blockers:

```
TASK-001 (K-1)
TASK-002 (ACA/PTC)
TASK-003 (AMT)
TASK-004 (EITC eligibility)
TASK-005 (Adoption credit)
TASK-006 (Elderly/disabled credit)
TASK-007 (Royalty income)        ──benefits──▶ TASK-019 (NIIT), TASK-025 (Inv. interest)
TASK-008 (Farm income)           ──benefits──▶ TASK-013 (NOL)
TASK-009 (Alimony received)
TASK-010 (Gambling)
TASK-011 (Annuity income)
TASK-012 (Scholarship income)
TASK-013 (NOL carryforward)
TASK-014 (Charitable carryforward)
TASK-015 (§25D credit carryforward)
TASK-016 (Cap loss ST/LT split)
TASK-017 (Kiddie tax)
TASK-018 (Casualty loss detail)
TASK-019 (NIIT)                  ──benefits──▶ TASK-025 (Inv. interest)
TASK-020 (Additional Medicare)
TASK-021 (§529 distributions)
TASK-022 (§1031 exchanges)
TASK-023 (§83 restricted stock)
TASK-024 (Savings bond exclusion)
TASK-025 (Inv. interest limit)
```

All 25 tasks may be assigned to agents in parallel. After all tasks merge,
a follow-up integration pass should:

1. Ensure no duplicate fields or conflicting enum values in `models.py`.
2. Run the full test suite (`pytest tests/`) to catch interaction regressions.
3. Regenerate and review the JSON schemas
   (`python main.py --schema input`, `python main.py --schema output`).