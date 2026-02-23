# UPDATES-001 — Annotate Every Field with Legal Excerpts and Plain-English Descriptions

> **Goal**: Add a structured comment to every field in every `@dataclass` in
> `models.py`.  Each comment must contain:
>
> 1. A **plain-English description** that a typical US taxpayer would understand.
> 2. A **legal-text reference** — the IRC section, the `title26.md` line
>    number, and a **verbatim quoted excerpt** from the statute.
>
> These comments are parsed by `_extract_field_comments()` and flow into the
> JSON Schema `description` values produced by `generate_schema()`.

---

## Comment Format

Every field must have a comment block of **one or more `#` lines immediately
above the field definition**.  Use this template:

```python
# <Plain-English description — 1-2 sentences a non-expert would understand>
# IRC §NNN(x)(y) (title26.md:LLLLL): "<verbatim excerpt from statute>"
field_name: type = default
```

For fields that reference an IRS form rather than a statute (e.g. Schedule C
expense line items), use the form name and the statutory authority:

```python
# What you spent on office supplies for the business (Schedule C, Line 22).
# IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses
# paid or incurred during the taxable year in carrying on any trade or business"
supplies: float = 0.0
```

Fields whose semantics are purely structural (e.g. `entity_name`, `payer_name`)
still need a plain-English line but may reference the form instructions instead
of the statute:

```python
# The legal name of the partnership, S-Corp, or trust that issued the K-1.
# Form 1065 / 1120-S / 1041 Schedule K-1, Box A.
entity_name: str
```

### Multi-line comments

When the quoted excerpt is long, wrap it across multiple `#` lines.  The
parser concatenates consecutive `#` lines into a single description string.

```python
# The amount of mortgage interest you paid this year on your home loan.
# IRC §163(h)(3)(B) (title26.md:116508): "The term 'acquisition indebtedness'
# means any indebtedness which is incurred in acquiring, constructing, or
# substantially improving any qualified residence of the taxpayer"
mortgage_interest_paid: float = 0.0
```

---

## Prerequisite — TASK-000

### TASK-000 — Enhance `_extract_field_comments` for multi-line comment blocks

**Parallel**: No — all other tasks depend on this.

### Context

The current `_extract_field_comments()` in `models.py` captures only a single
`#` line (either inline or a section header).  For the richer comments
specified in this update, consecutive `#` lines preceding a field must be
concatenated into a single description string separated by spaces.

### Scope

1. Update `_extract_field_comments()` so that when multiple consecutive `#`
   lines appear immediately before a field definition, they are joined with
   a single space into one description string.
2. Continue to support the existing single-line inline comment pattern
   (`field: type  # comment`) as a fallback.
3. When both a multi-line block *and* an inline comment exist, prefer the
   multi-line block (it is more detailed).

### Acceptance Criteria

```
Scenario: Multi-line comment block is captured as one description
  Given a dataclass with the following source:
      # This is line one.
      # IRC §61 (title26.md:70846): "gross income means all income"
      some_field: float = 0.0
  When _extract_field_comments is called on that dataclass
  Then the comment for "some_field" should equal
       "This is line one. IRC §61 (title26.md:70846): \"gross income means all income\""

Scenario: Single-line inline comment still works
  Given a dataclass with: wages: float  # IRC §61(a)(1)
  When _extract_field_comments is called
  Then the comment for "wages" should equal "IRC §61(a)(1)"
```

---

## How to Find Legal Excerpts

Each task lists the `title26.md` line ranges to consult.  To extract the
relevant statute text:

```bash
sed -n '<START>,<END>p' title26.md | head -40
```

`NOTES.md` provides digested summaries and cross-references that can help
locate the exact subparagraph.  When a field maps to a specific IRS form
box rather than a statute subsection, cite the form and the authorizing
statute (e.g. "Form W-2, Box 1; IRC §61(a)(1)").

---

## Parallel Tasks — Input Component Dataclasses

All TASK-001 through TASK-017 are independent and may execute in parallel
once TASK-000 is complete.

---

### TASK-001 — PersonalInfo, Address, Dependent (22 fields)

**Parallel**: Yes (after TASK-000)

#### Classes and field counts

| Class | Fields | Primary IRC §§ | title26.md lines |
|-------|--------|----------------|------------------|
| `PersonalInfo` | 7 | §6012, §6109 | 498203–498400 |
| `Address` | 5 | §6012 (return filing) | 498203–498400 |
| `Dependent` | 10 | §152, §24 | 112887–113100, 13963–14200 |

#### Fields to annotate

**PersonalInfo**: `first_name`, `last_name`, `ssn`, `date_of_birth`,
`is_blind`, `is_deceased`, `occupation`

**Address**: `street`, `city`, `state`, `zip_code`, `country`

**Dependent**: `first_name`, `last_name`, `ssn`, `date_of_birth`,
`relationship`, `months_lived_with_taxpayer`, `is_full_time_student`,
`is_permanently_disabled`, `gross_income`, `support_provided_by_taxpayer_pct`

#### Example (one field)

```python
# The number of months this dependent lived in your home during the tax year (0-12).
# IRC §152(c)(1)(B) (title26.md:112948): "such individual has the same principal
# place of abode as the taxpayer for more than one-half of such taxable year"
months_lived_with_taxpayer: int  # 0-12
```

#### Acceptance Criteria

```
Scenario: Dependent.relationship has legal excerpt and plain English
  Given the generated JSON schema for Dependent
  Then the description for "relationship" should contain "title26.md:"
  And the description for "relationship" should contain a quoted legal excerpt
  And the description for "relationship" should be understandable without tax expertise

Scenario: PersonalInfo.ssn references IRC §6109
  Given the generated JSON schema for PersonalInfo
  Then the description for "ssn" should mention "§6109" or "taxpayer identification"
  And the description for "ssn" should contain a quoted legal excerpt
```

---

### TASK-002 — W2Income (12 fields)

**Parallel**: Yes (after TASK-000)

#### References

| IRC §§ | title26.md lines | IRS Form |
|--------|------------------|----------|
| §61(a)(1), §3401, §3402 | 70854, 376xxx | W-2 |
| §31 (withholding credit) | 22615–22650 | W-2 |
| §3101 (FICA employee) | — | W-2 Boxes 4,6 |
| §3111 (FICA employer) | — | — |

#### Fields to annotate

`employer_name`, `employer_ein`, `wages`,
`federal_income_tax_withheld`, `social_security_wages`,
`social_security_tax_withheld`, `medicare_wages`,
`medicare_tax_withheld`, `state_wages`, `state_income_tax_withheld`,
`local_income_tax_withheld`, `additional_medicare_tax_withheld`

#### Acceptance Criteria

```
Scenario: W2Income.wages has §61 excerpt
  Given the generated JSON schema for W2Income
  Then the description for "wages" should contain "title26.md:"
  And the description for "wages" should contain "§61"
  And the description for "wages" should contain a quoted excerpt

Scenario: W2Income.additional_medicare_tax_withheld references §3101(b)(2)
  Given the generated JSON schema for W2Income
  Then the description for "additional_medicare_tax_withheld" should contain "§3101"
```

---

### TASK-003 — InterestIncome, DividendIncome, CapitalGainLoss (17 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines | IRS Form |
|-------|--------|------------------|----------|
| `InterestIncome` | §61(a)(4), §103, §135 | 70861, 83090, 90338 | 1099-INT |
| `DividendIncome` | §61(a)(7), §1(h)(11) | 70867, 5895 | 1099-DIV |
| `CapitalGainLoss` | §1001, §1221, §1222 | 339459, 350914, 351190 | 8949 / Sch D |

#### Fields to annotate

**InterestIncome** (4): `payer_name`, `amount`, `tax_exempt_amount`,
`us_savings_bond_interest`

**DividendIncome** (4): `payer_name`, `ordinary_dividends`,
`qualified_dividends`, `capital_gain_distributions`

**CapitalGainLoss** (9): `description`, `date_acquired`, `date_sold`,
`proceeds`, `cost_basis`, `term`, `is_collectible`, `is_section_1250`,
`wash_sale_loss_disallowed`

#### Acceptance Criteria

```
Scenario: InterestIncome.tax_exempt_amount references §103
  Given the generated JSON schema for InterestIncome
  Then the description for "tax_exempt_amount" should contain "§103"
  And the description should contain a quoted excerpt about state/local bonds

Scenario: CapitalGainLoss.term references §1222
  Given the generated JSON schema for CapitalGainLoss
  Then the description for "term" should contain "§1222"
  And the description should explain the 1-year holding period rule in plain English
```

---

### TASK-004 — BusinessIncome (26 fields)

**Parallel**: Yes (after TASK-000)

#### References

| IRC §§ | title26.md lines | IRS Form |
|--------|------------------|----------|
| §162 (ordinary & necessary) | 114102–114400 | Schedule C |
| §274 (meals limitation) | — | Schedule C Line 24b |
| §280A (home office) | 164272–164500 | Form 8829 |
| §1401 (SE tax) | 377596–377630 | Schedule SE |

#### Fields to annotate

`business_name`, `business_ein`, `principal_business_code`,
`gross_receipts`, `returns_and_allowances`, `cost_of_goods_sold`,
`advertising`, `car_and_truck`, `commissions_and_fees`, `contract_labor`,
`depreciation`, `insurance`, `interest_mortgage`, `interest_other`,
`legal_and_professional`, `office_expense`, `rent_lease`,
`repairs_maintenance`, `supplies`, `taxes_licenses`, `travel`, `meals`,
`utilities`, `wages`, `other_expenses`, `home_office_deduction`

All 26 expense fields reference IRC §162(a).  Each should quote the
"ordinary and necessary" language and then describe the specific Schedule C
line item in plain English.  The `meals` field must additionally cite
§274(n) and explain the 50% limitation.

#### Acceptance Criteria

```
Scenario: BusinessIncome.meals references both §162 and §274
  Given the generated JSON schema for BusinessIncome
  Then the description for "meals" should contain "§274"
  And the description should mention the 50% limit in plain English

Scenario: BusinessIncome.home_office_deduction references §280A
  Given the generated JSON schema for BusinessIncome
  Then the description for "home_office_deduction" should contain "§280A"
  And the description should explain the exclusive-use requirement
```

---

### TASK-005 — RentalIncome, RoyaltyIncome (24 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines | IRS Form |
|-------|--------|------------------|----------|
| `RentalIncome` | §61(a)(5), §280A | 70863, 164272 | Schedule E Part I |
| `RoyaltyIncome` | §61(a)(6), §611-§613 | 70865 | Schedule E Part I |

#### Fields to annotate

**RentalIncome** (19): `property_description`, `property_type`,
`days_rented`, `days_personal_use`, `rental_income`, `advertising`,
`auto_and_travel`, `cleaning_and_maintenance`, `commissions`, `insurance`,
`legal_and_professional`, `management_fees`, `mortgage_interest`, `repairs`,
`supplies`, `taxes`, `utilities`, `depreciation`, `other_expenses`

**RoyaltyIncome** (5): `description`, `payer_name`, `gross_royalties`,
`expenses`, `is_subject_to_se_tax`

Note: `days_rented` and `days_personal_use` must cite the §280A(g) 14-day
rental exclusion rule and the §280A(d)(1) "used as a residence" test.

#### Acceptance Criteria

```
Scenario: RentalIncome.days_rented references the 14-day rule
  Given the generated JSON schema for RentalIncome
  Then the description for "days_rented" should contain "§280A"
  And the description should explain that renting fewer than 15 days excludes the income

Scenario: RoyaltyIncome.gross_royalties references §61(a)(6)
  Given the generated JSON schema for RoyaltyIncome
  Then the description for "gross_royalties" should contain "§61(a)(6)"
  And the description should contain "title26.md:"
```

---

### TASK-006 — K1Income (22 fields)

**Parallel**: Yes (after TASK-000)

#### References

| IRC §§ | title26.md lines | IRS Forms |
|--------|------------------|-----------|
| §702 (partnership income) | 70877 | Schedule K-1 (1065) |
| §704 (partner's distributive share) | — | Schedule K-1 (1065) |
| §1366 (S-Corp passthrough) | — | Schedule K-1 (1120-S) |
| §652, §662 (trust/estate) | 70881 | Schedule K-1 (1041) |
| §199A (QBI) | 146332–146440 | — |
| §1401 (SE tax on partnerships) | 377596 | Schedule SE |

#### Fields to annotate

`entity_name`, `entity_ein`, `entity_type`,
`ordinary_business_income`, `net_rental_income`, `interest_income`,
`ordinary_dividends`, `qualified_dividends`,
`net_short_term_capital_gain`, `net_long_term_capital_gain`,
`net_section_1231_gain`, `other_income`, `section_179_deduction`,
`guaranteed_payments`, `self_employment_earnings`,
`foreign_taxes_paid`, `tax_exempt_income`, `distributions`,
`qualified_business_income`, `w2_wages`, `qualified_property_basis`,
`is_specified_service_business`

#### Acceptance Criteria

```
Scenario: K1Income.guaranteed_payments references §707(c)
  Given the generated JSON schema for K1Income
  Then the description for "guaranteed_payments" should contain "§707"
  And the description should explain these are payments for services regardless of profit

Scenario: K1Income.is_specified_service_business references §199A(d)(2)
  Given the generated JSON schema for K1Income
  Then the description for "is_specified_service_business" should contain "§199A"
  And the description should list examples like law, medicine, consulting
```

---

### TASK-007 — FarmIncome (30 fields)

**Parallel**: Yes (after TASK-000)

#### References

| IRC §§ | title26.md lines | IRS Form |
|--------|------------------|----------|
| §61(a)(2) (business income) | 70857 | Schedule F |
| §162 (business expenses) | 114102 | Schedule F |
| §175 (conservation) | — | Schedule F Line 12 |
| §1401 (SE tax) | 377596 | Schedule SE |
| §172(b)(1)(B) (farm NOL) | 137738 | — |

#### Fields to annotate

`farm_name`, `principal_product`, `gross_farm_income`,
`cost_of_livestock_purchased`, `conservation_expenses`, `custom_hire`,
`feed`, `fertilizers`, `freight`, `gasoline_fuel`, `labor_hired`,
`pension_plans`, `rent_lease_land`, `rent_lease_equipment`, `seeds_plants`,
`storage`, `supplies`, `taxes`, `utilities`, `vet_fees`, `other_expenses`,
`depreciation`, `car_and_truck`, `insurance`, `interest_mortgage`,
`interest_other`, `repairs_maintenance`, `crop_insurance_proceeds`,
`ccc_loans_reported_as_income`, `is_material_participant`

All expense fields cite §162(a) with the "ordinary and necessary" quote.
`conservation_expenses` should additionally cite §175.
`crop_insurance_proceeds` should cite §451(d).
`is_material_participant` should cite §469 (passive activity rules).

#### Acceptance Criteria

```
Scenario: FarmIncome.conservation_expenses references §175
  Given the generated JSON schema for FarmIncome
  Then the description for "conservation_expenses" should contain "§175"
  And the description should explain soil/water conservation in plain English

Scenario: FarmIncome.is_material_participant references §469
  Given the generated JSON schema for FarmIncome
  Then the description for "is_material_participant" should contain "§469"
  And the description should explain the concept of material participation
```

---

### TASK-008 — RetirementDistribution, SocialSecurityIncome, UnemploymentIncome, AnnuityIncome (21 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines | IRS Form |
|-------|--------|------------------|----------|
| `RetirementDistribution` | §72, §408A | 74051, 206057 | 1099-R |
| `SocialSecurityIncome` | §86 | 80658–80760 | SSA-1099 |
| `UnemploymentIncome` | §85 | 80444–80470 | 1099-G |
| `AnnuityIncome` | §72(b), §72(d) | 74051 | 1099-R |

#### Fields to annotate

**RetirementDistribution** (8): `payer_name`, `gross_distribution`,
`taxable_amount`, `federal_income_tax_withheld`, `is_early_distribution`,
`early_distribution_exception_code`, `is_roth`,
`is_qualified_roth_distribution`

**SocialSecurityIncome** (2): `total_benefits`, `repayments`

**UnemploymentIncome** (2): `amount`, `federal_income_tax_withheld`

**AnnuityIncome** (9): `payer_name`, `contract_type`, `gross_payment`,
`investment_in_contract`, `expected_return`,
`amount_previously_recovered`, `use_simplified_method`,
`annuitant_age_at_start`, `federal_income_tax_withheld`

#### Acceptance Criteria

```
Scenario: RetirementDistribution.is_early_distribution references §72(t)
  Given the generated JSON schema for RetirementDistribution
  Then the description for "is_early_distribution" should contain "§72(t)"
  And the description should mention the 10% penalty and age 59½ in plain English

Scenario: SocialSecurityIncome.total_benefits references §86
  Given the generated JSON schema for SocialSecurityIncome
  Then the description for "total_benefits" should contain "§86"
  And the description should explain that up to 85% may be taxable
```

---

### TASK-009 — OtherIncome, HomeSale, ScholarshipIncome, GamblingIncome, CancelledDebt, RestrictedStockEvent (32 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines |
|-------|--------|------------------|
| `OtherIncome` | §61, §74 | 70846, 75794 |
| `HomeSale` | §121 | 90818–91110 |
| `ScholarshipIncome` | §117 | 89656–89750 |
| `GamblingIncome` | §61, §165(d) | 70846, 120131 |
| `CancelledDebt` | §108 | 86700–86900 |
| `RestrictedStockEvent` | §83 | 78996–79100 |

#### Fields to annotate

**OtherIncome** (3): `description`, `amount`, `is_subject_to_se_tax`

**HomeSale** (9): `date_sold`, `selling_price`, `selling_expenses`,
`cost_basis`, `improvements`, `depreciation_after_may_1997`,
`years_owned`, `years_used_as_residence`,
`exclusion_used_in_prior_2_years`

**ScholarshipIncome** (5): `institution_name`, `total_scholarship`,
`qualified_tuition_and_fees`, `room_board_stipend`,
`service_compensation`

**GamblingIncome** (4): `w2g_winnings`, `other_winnings`,
`federal_income_tax_withheld`, `losses`

**CancelledDebt** (6): `creditor_name`, `amount_discharged`,
`is_principal_residence_debt`, `is_student_loan_qualifying`,
`taxpayer_insolvent_amount`, `is_bankruptcy`

**RestrictedStockEvent** (5+): `description`, `grant_date`,
`vesting_date`, `fmv_at_vesting`, `amount_paid`,
`section_83b_election`, `fmv_at_grant`, `shares`

#### Acceptance Criteria

```
Scenario: HomeSale.years_used_as_residence references §121 ownership test
  Given the generated JSON schema for HomeSale
  Then the description for "years_used_as_residence" should contain "§121"
  And the description should explain the 2-out-of-5-year rule in plain English

Scenario: CancelledDebt.is_principal_residence_debt references §108(a)(1)(E)
  Given the generated JSON schema for CancelledDebt
  Then the description for "is_principal_residence_debt" should contain "§108"
  And the description should explain the exclusion for forgiven mortgage debt
```

---

### TASK-010 — LikeKindExchange, Section529Distribution, SavingsBondEducationExclusion, ForeignIncomeInfo (27 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines |
|-------|--------|------------------|
| `LikeKindExchange` | §1031 | 342673–343000 |
| `Section529Distribution` | §529 | 263347–263600 |
| `SavingsBondEducationExclusion` | §135 | 90338–90500 |
| `ForeignIncomeInfo` | §911, §901, §27 | 325314, 19867 |

#### Fields to annotate

**LikeKindExchange** (12): `property_relinquished_description`,
`property_received_description`, `date_relinquished`, `date_received`,
`fmv_relinquished`, `adjusted_basis_relinquished`, `fmv_received`,
`boot_received`, `boot_paid`, `liabilities_relieved`,
`liabilities_assumed`, `is_related_party`

**Section529Distribution** (9): `plan_name`, `beneficiary_name`,
`beneficiary_ssn`, `gross_distribution`, `earnings_portion`,
`qualified_education_expenses`, `is_k12_tuition`,
`student_loan_repayment`, `rollover_to_roth`

**SavingsBondEducationExclusion** (4): `total_bond_proceeds`,
`bond_interest`, `qualified_education_expenses`,
`scholarships_and_grants`

**ForeignIncomeInfo** (6): `country`, `foreign_earned_income`,
`foreign_taxes_paid`, `days_in_foreign_country`,
`is_bona_fide_resident`, `housing_expenses`

#### Acceptance Criteria

```
Scenario: LikeKindExchange.boot_received references §1031(b)
  Given the generated JSON schema for LikeKindExchange
  Then the description for "boot_received" should contain "§1031"
  And the description should explain that cash or unlike property received triggers tax

Scenario: Section529Distribution.is_k12_tuition references the $10,000 cap
  Given the generated JSON schema for Section529Distribution
  Then the description for "is_k12_tuition" should contain "§529"
  And the description should mention the $10,000 per year limit
```

---

### TASK-011 — Itemized Deduction Inputs: MedicalExpense, StateLocalTaxes, MortgageInterest, CharitableContribution, CasualtyLossEvent (34 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines |
|-------|--------|------------------|
| `MedicalExpense` | §213 | 147452–147600 |
| `StateLocalTaxes` | §164 | 119300–119550 |
| `MortgageInterest` | §163(h) | 116508–116600 |
| `CharitableContribution` | §170 | 132628–132900 |
| `CasualtyLossEvent` | §165(c)(3), §165(h) | 120131–120300 |

#### Fields to annotate

**MedicalExpense** (5): `total_medical_dental`,
`health_insurance_premiums`, `long_term_care_premiums`,
`prescription_drugs`, `medical_travel`

**StateLocalTaxes** (6): `state_income_tax_paid`,
`local_income_tax_paid`, `real_property_tax`, `personal_property_tax`,
`sales_tax_paid`, `elect_sales_tax`

**MortgageInterest** (8): `lender_name`, `lender_ein`,
`mortgage_interest_paid`, `mortgage_insurance_premiums`, `points_paid`,
`outstanding_mortgage_principal`, `mortgage_origination_date`,
`is_acquisition_debt`

**CharitableContribution** (6): `organization_name`, `cash_amount`,
`noncash_amount`, `noncash_description`, `is_capital_gain_property`,
`is_public_charity`

**CasualtyLossEvent** (9): `description`,
`fema_disaster_declaration_number`, `date_of_loss`, `property_type`,
`fair_market_value_before`, `fair_market_value_after`, `adjusted_basis`,
`insurance_reimbursement`, `other_reimbursement`

#### Acceptance Criteria

```
Scenario: MedicalExpense.total_medical_dental references the 7.5% floor
  Given the generated JSON schema for MedicalExpense
  Then the description for "total_medical_dental" should contain "§213"
  And the description should explain the 7.5% of AGI threshold

Scenario: StateLocalTaxes.elect_sales_tax references §164(b)(5)(I)
  Given the generated JSON schema for StateLocalTaxes
  Then the description for "elect_sales_tax" should contain "§164"
  And the description should explain the choice between income tax and sales tax deduction
```

---

### TASK-012 — Credit Inputs (Part 1): EducationExpense, ChildCareExpense, RetirementContribution, HSAInfo, EstimatedTaxPayment, AdoptionExpense, ElderlyDisabledInfo (42 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines |
|-------|--------|------------------|
| `EducationExpense` | §25A | 16106–16300 |
| `ChildCareExpense` | §21 | 12007–12120 |
| `RetirementContribution` | §219, §408A | 149106–149400, 206057 |
| `HSAInfo` | §223 | 152303–152500 |
| `EstimatedTaxPayment` | §6654 | 566326–566500 |
| `AdoptionExpense` | §23 | 13227–13350 |
| `ElderlyDisabledInfo` | §22 | 12756–12900 |

#### Fields to annotate

**EducationExpense** (10): `student_name`, `student_ssn`,
`institution_name`, `institution_ein`, `qualified_tuition_and_fees`,
`scholarships_and_grants`, `credit_type`, `year_in_postsecondary`,
`is_at_least_half_time`, `has_felony_drug_conviction`

**ChildCareExpense** (6): `provider_name`, `provider_tin`,
`provider_address`, `amount_paid`, `care_recipient_name`,
`care_recipient_ssn`

**RetirementContribution** (4): `account_type`, `contribution_amount`,
`employer_match`, `is_active_participant_in_employer_plan`

**HSAInfo** (5): `is_self_only_coverage`, `taxpayer_contributions`,
`employer_contributions`, `distributions`,
`qualified_medical_expenses_from_hsa`

**EstimatedTaxPayment** (5): `q1_amount`, `q2_amount`, `q3_amount`,
`q4_amount`, `amount_applied_from_prior_year`

**AdoptionExpense** (8): `child_name`, `child_ssn`, `is_special_needs`,
`is_foreign_adoption`, `qualified_expenses`, `year_expenses_paid`,
`adoption_finalized_year`, `prior_year_carryforward`

**ElderlyDisabledInfo** (4): `is_permanently_totally_disabled`,
`disability_income`, `nontaxable_social_security`,
`nontaxable_va_pension`

#### Acceptance Criteria

```
Scenario: EducationExpense.has_felony_drug_conviction references §25A(b)(2)(D)
  Given the generated JSON schema for EducationExpense
  Then the description for "has_felony_drug_conviction" should contain "§25A"
  And the description should explain AOTC is denied for drug felonies

Scenario: HSAInfo.distributions references §223(f)
  Given the generated JSON schema for HSAInfo
  Then the description for "distributions" should contain "§223"
  And the description should explain qualified vs non-qualified withdrawals
```

---

### TASK-013 — Credit Inputs (Part 2): CleanVehicleCredit, EnergyCredit, MarketplaceCoverage, QualifiedBusinessIncome, AMTPreferenceItems, EITCEligibility, KiddieTaxInfo (39 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines |
|-------|--------|------------------|
| `CleanVehicleCredit` | §30D, §25E | 21693, 18698 |
| `EnergyCredit` | §25C, §25D | 17281, 18115 |
| `MarketplaceCoverage` | §36B | 26647–27200 |
| `QualifiedBusinessIncome` | §199A | 146332–146440 |
| `AMTPreferenceItems` | §55, §56, §57, §53 | 64924–65110 |
| `EITCEligibility` | §32 | 22751–23150 |
| `KiddieTaxInfo` | §1(g) | 5520–5700 |

#### Fields to annotate

**CleanVehicleCredit** (8): `is_new_vehicle`, `vehicle_vin`,
`purchase_price`, `purchase_date`, `vehicle_msrp`,
`meets_critical_minerals_requirement`,
`meets_battery_component_requirement`, `is_qualified_manufacturer`

**EnergyCredit** (8): `home_improvement_expenditures`,
`heat_pump_expenditures`, `home_energy_audit`,
`solar_electric_expenditures`, `solar_water_heating_expenditures`,
`battery_storage_expenditures`, `geothermal_expenditures`,
`wind_expenditures`

**MarketplaceCoverage** (7): `marketplace_plan_name`, `state_exchange`,
`coverage_months`, `annual_premium`, `annual_slcsp_premium`,
`advance_ptc_received`, `household_size`

**QualifiedBusinessIncome** (7): `business_name`,
`qualified_business_income`, `w2_wages_paid`,
`qualified_property_basis`, `is_specified_service_business`,
`reit_dividends`, `ptp_income`

**AMTPreferenceItems** (6): `iso_exercise_spread`,
`private_activity_bond_interest`, `depletion_excess`,
`intangible_drilling_costs_excess`, `other_adjustments`,
`prior_year_amt_credit`

**EITCEligibility** (6): `has_valid_ssn_for_employment`,
`investment_income`, `lived_in_us_more_than_half_year`,
`is_qualifying_child_of_another`,
`prior_eitc_disqualification_year`, `prior_eitc_fraud`

**KiddieTaxInfo** (7): `child_unearned_income`, `child_earned_income`,
`parent_taxable_income`, `parent_filing_status`,
`parent_marginal_rate`, `child_is_full_time_student`,
`child_provides_over_half_support`

#### Acceptance Criteria

```
Scenario: AMTPreferenceItems.iso_exercise_spread references §56 or §422
  Given the generated JSON schema for AMTPreferenceItems
  Then the description for "iso_exercise_spread" should contain "§56" or "§422"
  And the description should explain what an ISO exercise spread is in plain English

Scenario: MarketplaceCoverage.annual_slcsp_premium references §36B
  Given the generated JSON schema for MarketplaceCoverage
  Then the description for "annual_slcsp_premium" should contain "§36B"
  And the description should explain the benchmark silver plan concept
```

---

### TASK-014 — TaxReturnInput Top-Level Fields (75 fields)

**Parallel**: Yes (after TASK-000)

#### Context

Most `TaxReturnInput` fields are typed references to the component
dataclasses above.  For these, the comment should briefly state what the
field represents, name the relevant IRS form/schedule, and cite the
authorizing IRC section.  The component dataclass docstring provides the
full legal context, so the top-level comment can be shorter.

Fields that are primitive types (floats, booleans) need full treatment.

#### References

| Section | IRC §§ | title26.md lines |
|---------|--------|------------------|
| Filing | §6012, §6072, §2 | 498203, 516367, 10051 |
| Income | §61 | 70846 |
| Adjustments | §62 | 71233 |
| Deductions | §63 | 72402 |
| Credits | various | various |
| Payments | §31, §6654 | 22615, 566326 |

#### Fields to annotate

All 75 fields on `TaxReturnInput`.  The full list is too long to enumerate
here; iterate over `dataclasses.fields(TaxReturnInput)`.

#### Example

```python
# Your W-2 wage statements — one per employer.
# IRC §61(a)(1) (title26.md:70854): "Compensation for services, including fees,
# commissions, fringe benefits, and similar items"
# See W2Income for individual field descriptions.
w2_income: list[W2Income] = field(default_factory=list)
```

```python
# Amount you paid toward student loan interest this year (max $2,500 deduction).
# IRC §221(a) (title26.md:151853): "In the case of an individual, there shall be
# allowed as a deduction... interest paid by the taxpayer during the taxable year
# on any qualified education loan"
student_loan_interest_paid: float = 0.0
```

#### Acceptance Criteria

```
Scenario: At least 90% of TaxReturnInput fields have a title26.md reference
  Given the generated JSON schema for TaxReturnInput
  Then at least 90% of top-level properties should have a description
  And at least 60% of those descriptions should contain "title26.md:"

Scenario: Primitive fields have full legal excerpts
  Given the generated JSON schema for TaxReturnInput
  Then the description for "educator_expenses" should contain a quoted excerpt
  And the description for "alimony_received" should contain a quoted excerpt
```

---

## Parallel Tasks — Output Model Dataclasses

---

### TASK-015 — IncomeComputation, AGIComputation (48 fields)

**Parallel**: Yes (after TASK-000)

#### Context

Output fields represent **computed results** rather than user input.  The
comment should explain what the computed value means, cite the IRC section
that defines the computation, and quote the relevant statutory language.

#### References

| Class | IRC §§ | title26.md lines |
|-------|--------|------------------|
| `IncomeComputation` | §61, §86, §121, §108, §1211, §1212 | 70846, 80658, 90818, 86700, 350175, 350269 |
| `AGIComputation` | §62 | 71233–71430 |

#### Fields to annotate

**IncomeComputation** (35): all fields (`total_wages` through
`gross_income`)

**AGIComputation** (13): all fields (`gross_income` through `agi`)

#### Example

```python
# Your total taxable Social Security — up to 85% of benefits may be included,
# depending on your other income.
# IRC §86(a) (title26.md:80658): "If the taxpayer's modified adjusted gross income...
# exceeds the adjusted base amount, the amount included in gross income shall not
# exceed... 85 percent of the Social Security benefits received"
taxable_social_security: float = 0.0
```

#### Acceptance Criteria

```
Scenario: IncomeComputation.gross_income references §61
  Given the generated JSON schema for IncomeComputation
  Then the description for "gross_income" should contain "§61"
  And the description should explain this is total income before deductions

Scenario: AGIComputation.agi references §62
  Given the generated JSON schema for AGIComputation
  Then the description for "agi" should contain "§62"
  And the description should explain AGI in plain English
```

---

### TASK-016 — DeductionComputation, TaxComputation, SelfEmploymentTaxComputation (50 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines |
|-------|--------|------------------|
| `DeductionComputation` | §63, §170(d), §165, §163(d), §172, §199A, §151(f) | 72402, 132765, 120131, 116555, 137738, 146332, 112427 |
| `TaxComputation` | §1, §55, §1411, §3101(b)(2), §1(g) | 5292, 64924, — |
| `SelfEmploymentTaxComputation` | §1401 | 377596–377630 |

#### Fields to annotate

**DeductionComputation** (23): all fields (`basic_standard_deduction`
through `taxable_income`)

**TaxComputation** (20): all fields (`ordinary_income_tax` through
`total_tax_before_credits`)

**SelfEmploymentTaxComputation** (7): all fields (`net_se_earnings`
through `se_tax_deduction`)

#### Acceptance Criteria

```
Scenario: TaxComputation.niit_amount references §1411
  Given the generated JSON schema for TaxComputation
  Then the description for "niit_amount" should contain "§1411"
  And the description should explain the 3.8% surtax on investment income

Scenario: DeductionComputation.nol_deduction references §172
  Given the generated JSON schema for DeductionComputation
  Then the description for "nol_deduction" should contain "§172"
  And the description should explain the 80% limitation on post-2017 NOLs
```

---

### TASK-017 — CreditComputation, PenaltyComputation, PaymentSummary, TaxReturnOutput (59 fields)

**Parallel**: Yes (after TASK-000)

#### References

| Class | IRC §§ | title26.md lines |
|-------|--------|------------------|
| `CreditComputation` | §21–§36B, various | various |
| `PenaltyComputation` | §6654 | 566326–566500 |
| `PaymentSummary` | §31 | 22615–22650 |
| `TaxReturnOutput` | §1212, §170(d), §53, §172, §163(d), §25D | various |

#### Fields to annotate

**CreditComputation** (24): all fields (`child_dependent_care_credit`
through `total_credits`)

**PenaltyComputation** (4): all fields

**PaymentSummary** (6): all fields

**TaxReturnOutput** (25): all fields

#### Example

```python
# The Earned Income Credit — a refundable credit for lower-income workers.
# The amount depends on your earned income, filing status, and number of
# qualifying children.
# IRC §32(a) (title26.md:22757): "In the case of an eligible individual, there
# shall be allowed as a credit... an amount equal to the credit percentage of
# so much of the taxpayer's earned income"
earned_income_credit: float = 0.0
```

#### Acceptance Criteria

```
Scenario: CreditComputation.premium_tax_credit references §36B
  Given the generated JSON schema for CreditComputation
  Then the description for "premium_tax_credit" should contain "§36B"
  And the description should explain this helps pay for ACA marketplace insurance

Scenario: TaxReturnOutput.effective_tax_rate has plain-English description
  Given the generated JSON schema for TaxReturnOutput
  Then the description for "effective_tax_rate" should be present
  And the description should explain this is total tax divided by total income
```

---

## Dependency Graph

```
TASK-000 (parser enhancement)
    │
    ├──▶ TASK-001 (PersonalInfo, Address, Dependent)
    ├──▶ TASK-002 (W2Income)
    ├──▶ TASK-003 (InterestIncome, DividendIncome, CapitalGainLoss)
    ├──▶ TASK-004 (BusinessIncome)
    ├──▶ TASK-005 (RentalIncome, RoyaltyIncome)
    ├──▶ TASK-006 (K1Income)
    ├──▶ TASK-007 (FarmIncome)
    ├──▶ TASK-008 (RetirementDistribution, SocialSecurity, Unemployment, Annuity)
    ├──▶ TASK-009 (OtherIncome, HomeSale, Scholarship, Gambling, CancelledDebt, RSU)
    ├──▶ TASK-010 (LikeKind, 529, SavingsBond, ForeignIncome)
    ├──▶ TASK-011 (Medical, SALT, Mortgage, Charity, Casualty)
    ├──▶ TASK-012 (Education, ChildCare, Retirement, HSA, EstimatedTax, Adoption, Elderly)
    ├──▶ TASK-013 (CleanVehicle, Energy, Marketplace, QBI, AMT, EITC, KiddieTax)
    ├──▶ TASK-014 (TaxReturnInput top-level — 75 fields)
    ├──▶ TASK-015 (IncomeComputation, AGIComputation)
    ├──▶ TASK-016 (DeductionComputation, TaxComputation, SelfEmploymentTax)
    └──▶ TASK-017 (CreditComputation, Penalty, Payments, TaxReturnOutput)
```

All 17 annotation tasks run in parallel after TASK-000 completes.

---

## Post-Merge Checklist

After all tasks merge:

1. Run `uv run pytest tests/` — all 147 existing tests must still pass.
2. Run `uv run pytest tests/test_schema.py` — verify description coverage
   thresholds still met (they should *increase*).
3. Regenerate schemas and spot-check:
   ```bash
   uv run python main.py --schema input | python3 -m json.tool | head -100
   ```
4. Verify every field description contains both:
   - A `title26.md:NNNNN` reference (or a Form reference for structural fields)
   - At least one quoted excerpt in `"double quotes"`
5. Have a non-tax-expert read 10 random plain-English descriptions and
   confirm they are understandable.

### Coverage Target

| Metric | Current | Target |
|--------|---------|--------|
| Top-level input fields with description | 98% | 100% |
| All nested fields with description | 41% | ≥95% |
| Descriptions containing `title26.md:` | ~50% | ≥85% |
| Descriptions containing a quoted excerpt | ~0% | ≥90% |