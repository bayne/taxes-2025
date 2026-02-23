"""
Tax return data models for federal individual income tax.

Input model (TaxReturnInput) captures all information a filer provides.
Output model (TaxReturnOutput) captures all computed/validated results.

Both models are composed of @dataclass types using standard Python types
(str, int, float, bool, list, Optional) so they can be described as JSON Schema.
All monetary amounts are in US dollars (float).

References are to IRC (Internal Revenue Code) sections as documented in NOTES.md.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import re
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Optional, Union, get_args, get_origin, get_type_hints

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FilingStatus(str, Enum):
    """IRC §2 (title26.md:10051) — Filing status definitions."""

    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_SURVIVING_SPOUSE = "qualifying_surviving_spouse"


class DependentRelationship(str, Enum):
    """IRC §152 (title26.md:112887) — Qualifying child or qualifying relative."""

    QUALIFYING_CHILD = "qualifying_child"
    QUALIFYING_RELATIVE = "qualifying_relative"


class CapitalGainTerm(str, Enum):
    """IRC §1222 (title26.md:351190) — Short-term vs long-term."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class EducationCreditType(str, Enum):
    """IRC §25A (title26.md:16106) — AOTC or Lifetime Learning."""

    AOTC = "aotc"
    LIFETIME_LEARNING = "lifetime_learning"


class RetirementAccountType(str, Enum):
    """IRC §219 (title26.md:149106), §408A (title26.md:206057)."""

    TRADITIONAL_IRA = "traditional_ira"
    ROTH_IRA = "roth_ira"
    EMPLOYER_401K = "401k"
    ROTH_401K = "roth_401k"
    SEP_IRA = "sep_ira"
    SIMPLE_IRA = "simple_ira"


class DeductionMethod(str, Enum):
    """IRC §63 (title26.md:72402) — Standard vs itemized deductions."""

    STANDARD = "standard"
    ITEMIZED = "itemized"


class K1EntityType(str, Enum):
    """Entity type for Schedule K-1 income.

    IRC §702/§704 (partnerships), §1366 (S-Corps), §652/§662 (estates/trusts).
    """

    PARTNERSHIP = "partnership"
    S_CORP = "s_corp"
    ESTATE_TRUST = "estate_trust"


# ---------------------------------------------------------------------------
# Input Model — Information provided by the tax filer
# ---------------------------------------------------------------------------


@dataclass
class PersonalInfo:
    """Basic taxpayer identification.

    Required for all returns per IRC §6012 (title26.md:498203).
    SSN/ITIN required per IRC §6109.
    """

    # Your legal first name as it appears on your Social Security card.
    # IRC §6012(a) (title26.md:498203): "Returns with respect to income taxes
    # under subtitle A shall be made by the following"
    first_name: str
    # Your legal last name as it appears on your Social Security card.
    # IRC §6012(a) (title26.md:498203): "Returns with respect to income taxes
    # under subtitle A shall be made by the following"
    last_name: str
    # Your Social Security Number or Individual Taxpayer Identification Number.
    # This is the 9-digit number the IRS uses to identify you.
    # IRC §6109(a) (title26.md:525311): "any person required under the authority
    # of this title to make a return... shall include in such form... such
    # identifying number as may be prescribed"
    ssn: str
    # Your date of birth in YYYY-MM-DD format. Used to determine eligibility
    # for age-based benefits like the additional standard deduction at age 65+.
    # IRC §63(f) (title26.md:72598): "additional standard deduction for the aged
    # and the blind"
    date_of_birth: str
    # Whether you are legally blind. If so, you qualify for an additional
    # standard deduction amount.
    # IRC §63(f)(4) (title26.md:72640): "an individual is blind only if his
    # central visual acuity does not exceed 20/200 in the better eye with
    # correcting lenses"
    is_blind: bool = False
    # Whether the taxpayer is deceased (filing a return on behalf of a decedent).
    # IRC §6012(b)(1) (title26.md:498310): "If an individual is deceased, the
    # return of such individual... shall be made by his executor"
    is_deceased: bool = False
    # Your primary occupation or job title, as reported on Form 1040.
    # Form 1040, page 1 — informational field.
    occupation: str = ""


@dataclass
class Address:
    """Mailing address for the return."""

    # Your street address including apartment or unit number.
    # Form 1040, page 1 — required mailing address for the return.
    street: str
    # Your city or town name.
    # Form 1040, page 1 — required mailing address for the return.
    city: str
    # Your two-letter state abbreviation (e.g. "CA", "NY").
    # Form 1040, page 1 — required mailing address for the return.
    state: str
    # Your 5-digit or 9-digit ZIP code.
    # Form 1040, page 1 — required mailing address for the return.
    zip_code: str
    # Your country code. Defaults to "US" for domestic filers.
    # IRC §6012(a) (title26.md:498203): filing requirement applies to all
    # citizens and residents.
    country: str = "US"


@dataclass
class Dependent:
    """Dependent claimed on the return.

    IRC §152 (title26.md:112887) — qualifying child or qualifying relative.
    IRC §24 (title26.md:13963) — child tax credit eligibility.
    """

    # The dependent's legal first name as shown on their Social Security card.
    # IRC §6109 (title26.md:525311): identifying number required for dependents.
    first_name: str
    # The dependent's legal last name as shown on their Social Security card.
    # IRC §6109 (title26.md:525311): identifying number required for dependents.
    last_name: str
    # The dependent's Social Security Number. Required to claim the child tax
    # credit and other dependent-related benefits.
    # IRC §24(h)(7) (title26.md:14190): "No credit shall be allowed... with
    # respect to any qualifying child unless... the taxpayer includes the...
    # social security number of such qualifying child"
    ssn: str
    # The dependent's date of birth (YYYY-MM-DD). Used to determine if they
    # meet the age tests for qualifying child status.
    # IRC §152(c)(3) (title26.md:112980): "meets the age requirements... has
    # not attained age 19... or is a student who has not attained age 24"
    date_of_birth: str
    # Whether this person is your qualifying child or qualifying relative.
    # The tests are different — qualifying children must live with you and
    # meet age requirements; qualifying relatives must earn below a threshold.
    # IRC §152(a) (title26.md:112887): "the term 'dependent' means (1) a
    # qualifying child, or (2) a qualifying relative"
    relationship: DependentRelationship
    # The number of months (0-12) this dependent lived in your home during
    # the tax year. Qualifying children must live with you more than half
    # the year (more than 6 months).
    # IRC §152(c)(1)(B) (title26.md:112948): "who has the same principal
    # place of abode as the taxpayer for more than one-half of such taxable year"
    months_lived_with_taxpayer: int
    # Whether the dependent was a full-time student for at least 5 months
    # of the year. Students can qualify as a dependent up to age 24.
    # IRC §152(c)(3) (title26.md:112980): "is a student who has not attained
    # age 24 as of the close of such calendar year"
    is_full_time_student: bool = False
    # Whether the dependent is permanently and totally disabled. Disabled
    # dependents have no age limit for qualifying child status.
    # IRC §152(c)(3)(B) (title26.md:112980): "subparagraph (A) shall not
    # apply in the case of an individual who is permanently and totally disabled"
    is_permanently_disabled: bool = False
    # The dependent's gross income for the year. For qualifying relatives,
    # their income must be below the exemption amount.
    # IRC §152(d)(1)(B) (title26.md:113040): "the gross income of such
    # individual for the calendar year... is less than the exemption amount"
    gross_income: float = 0.0
    # The percentage of the dependent's total support that you provided
    # (0.0 to 1.0). For qualifying relatives, you must provide over half.
    # IRC §152(d)(1)(C) (title26.md:113044): "the taxpayer provides over
    # one-half of the individual's support for the calendar year"
    support_provided_by_taxpayer_pct: float = 0.0


@dataclass
class W2Income:
    """Wage and salary income from Form W-2.

    IRC §61(a)(1) (title26.md:70854) — compensation for services.
    IRC §31 (title26.md:22615) — tax withheld on wages.
    """

    # The name of the company or person who paid you. This is your employer
    # as shown in Box c of your W-2 form.
    # Form W-2, Box c; IRC §6051(a) (title26.md:513787): "Every person required
    # to deduct and withhold... shall furnish to each such employee... a written
    # statement showing the name... of such person"
    employer_name: str
    # Your employer's federal Employer Identification Number (EIN), a 9-digit
    # number the IRS assigns to businesses. Shown in Box b of your W-2.
    # Form W-2, Box b; IRC §6109(a) (title26.md:525311): "any person required
    # under the authority of this title to make a return... shall include...
    # such identifying number as may be prescribed"
    employer_ein: str
    # Your total taxable wages, salary, tips, and other compensation from this
    # employer before any deductions. This is Box 1 of your W-2.
    # IRC §61(a)(1) (title26.md:70854): "Compensation for services, including
    # fees, commissions, fringe benefits, and similar items"
    wages: float
    # The amount of federal income tax your employer withheld from your
    # paychecks during the year. This is Box 2 of your W-2 and counts as a
    # payment toward your tax bill.
    # IRC §31(a) (title26.md:22615): "The amount withheld as tax under chapter
    # 24 shall be allowed to the recipient of the income as a credit against
    # the tax imposed by this subtitle"
    federal_income_tax_withheld: float
    # The amount of your wages subject to Social Security tax (Box 3 of W-2).
    # There is an annual wage cap ($176,100 for 2025) above which no more
    # Social Security tax is owed.
    # IRC §3121(a) (title26.md:406340): "the term 'wages' means all
    # remuneration for employment"
    social_security_wages: float = 0.0
    # The Social Security tax withheld from your pay (Box 4 of W-2). The
    # employee rate is 6.2% of Social Security wages.
    # IRC §3101(a) (title26.md:403879): "there is hereby imposed on the income
    # of every individual a tax equal to 6.2 percent of the wages... received
    # by the individual with respect to employment"
    social_security_tax_withheld: float = 0.0
    # The amount of your wages subject to Medicare tax (Box 5 of W-2). Unlike
    # Social Security, there is no wage cap for Medicare.
    # IRC §3121(a) (title26.md:406340): "the term 'wages' means all
    # remuneration for employment"
    medicare_wages: float = 0.0
    # The Medicare tax withheld from your pay (Box 6 of W-2). The base
    # employee rate is 1.45% of all Medicare wages.
    # IRC §3101(b)(1) (title26.md:403879): "there is hereby imposed on the
    # income of every individual a tax equal to 1.45 percent of the wages...
    # received by the individual with respect to employment"
    medicare_tax_withheld: float = 0.0
    # The portion of your wages subject to state income tax (Box 16 of W-2).
    # This may differ from federal wages due to state-specific rules.
    # Form W-2, Box 16 — state-specific; not governed by IRC.
    state_wages: float = 0.0
    # The amount of state income tax withheld from your pay (Box 17 of W-2).
    # This is deductible on Schedule A if you itemize (subject to SALT cap).
    # IRC §164(a)(3) (title26.md:119312): "State and local, and foreign,
    # income, war profits, and excess profits taxes"
    state_income_tax_withheld: float = 0.0
    # The amount of local income tax withheld from your pay (Box 19 of W-2).
    # This is deductible on Schedule A if you itemize (subject to SALT cap).
    # IRC §164(a)(3) (title26.md:119312): "State and local, and foreign,
    # income, war profits, and excess profits taxes"
    local_income_tax_withheld: float = 0.0
    # The Additional Medicare Tax (0.9%) withheld by your employer on wages
    # over $200,000. Your employer must withhold once wages exceed $200k
    # regardless of filing status; you reconcile on your return.
    # IRC §3101(b)(2) (title26.md:403879): "a tax equal to 0.9 percent of
    # the wages... received by the individual... which are in excess of...
    # $200,000"
    additional_medicare_tax_withheld: float = 0.0


@dataclass
class InterestIncome:
    """Interest income from Form 1099-INT.

    IRC §61(a)(4) (title26.md:70861) — interest included in gross income.
    IRC §103 (title26.md:83090) — tax-exempt municipal bond interest.
    """

    # The name of the bank, brokerage, or other institution that paid you
    # interest. Shown on Form 1099-INT, Box — Payer's name.
    # Form 1099-INT; IRC §6049 (title26.md:509730): "every person... who makes
    # payments of interest... aggregating $10 or more... shall make a return"
    payer_name: str
    # The total taxable interest you earned from this payer during the year.
    # This includes interest from savings accounts, CDs, bonds, and similar
    # investments. Shown on Form 1099-INT, Box 1.
    # IRC §61(a)(4) (title26.md:70861): "gross income means all income from
    # whatever source derived, including... Interest"
    amount: float
    # Interest from state and local government bonds (municipal bonds) that is
    # exempt from federal income tax. This is still reported on your return but
    # not included in taxable income. Form 1099-INT, Box 8.
    # IRC §103(a) (title26.md:83090): "gross income does not include interest
    # on any State or local bond"
    tax_exempt_amount: float = 0.0
    # Interest earned on U.S. Series EE or Series I savings bonds. This may be
    # excludable from income if you used the proceeds to pay for qualified
    # higher education expenses.
    # IRC §135(a) (title26.md:96620): "gross income shall not include income
    # from the redemption of any United States savings bond... if qualified
    # higher education expenses were paid"
    us_savings_bond_interest: float = 0.0


@dataclass
class DividendIncome:
    """Dividend income from Form 1099-DIV.

    IRC §61(a)(7) (title26.md:70867) — dividends included in gross income.
    IRC §1(h)(11) (title26.md:5895) — qualified dividends at capital gains rates.
    """

    # The name of the company or fund that paid you dividends. Shown on
    # Form 1099-DIV, Payer's name.
    # Form 1099-DIV; IRC §6042 (title26.md:507261): "every person who makes
    # payments of dividends aggregating $10 or more... shall make a return"
    payer_name: str
    # The total ordinary dividends you received from this payer during the year.
    # This includes both qualified and non-qualified dividends. Form 1099-DIV, Box 1a.
    # IRC §61(a)(7) (title26.md:70867): "gross income means all income from
    # whatever source derived, including... Dividends"
    ordinary_dividends: float
    # The portion of your dividends that qualifies for the lower long-term
    # capital gains tax rate (0%, 15%, or 20%) instead of your ordinary rate.
    # Most dividends from U.S. corporations held for at least 61 days qualify.
    # Form 1099-DIV, Box 1b.
    # IRC §1(h)(11)(B) (title26.md:5895): "the term 'qualified dividend income'
    # means dividends received during the taxable year from domestic corporations
    # and qualified foreign corporations"
    qualified_dividends: float = 0.0
    # Long-term capital gain distributions from mutual funds or REITs. These
    # are taxed at the favorable long-term capital gains rate even though you
    # didn't sell shares yourself. Form 1099-DIV, Box 2a.
    # IRC §852(b)(3) (title26.md:296912): "A capital gain dividend shall be
    # treated by the shareholders... as a gain from the sale or exchange of a
    # capital asset held for more than 1 year"
    capital_gain_distributions: float = 0.0


@dataclass
class CapitalGainLoss:
    """Individual capital gain or loss transaction.

    IRC §1001 (title26.md:339459) — gain/loss determination.
    IRC §1221 (title26.md:350914) — capital asset definition.
    IRC §1222 (title26.md:351190) — short-term vs long-term.
    """

    # A brief description of the asset you sold — such as 100 sh AAPL
    # or Rental property at 123 Main St. Reported on Form 8949 column (a).
    # IRC §1001(a) (title26.md:339459): "The gain from the sale or other
    # disposition of property shall be the excess of the amount realized
    # therefrom over the adjusted basis"
    description: str
    # The date you originally acquired (bought) the asset, in YYYY-MM-DD
    # format, or VARIOUS if acquired over multiple dates. This determines
    # whether the gain is short-term or long-term. Form 8949 column (b).
    # IRC §1222(1) (title26.md:351195): "gain from the sale or exchange of
    # a capital asset held for not more than 1 year"
    date_acquired: str
    # The date you sold or disposed of the asset (YYYY-MM-DD).
    # Form 8949 column (c).
    # IRC §1001(a) (title26.md:339459): "The gain from the sale or other
    # disposition of property"
    date_sold: str
    # The total amount you received from the sale, including cash and fair
    # market value of any property received. Form 8949 column (d).
    # IRC §1001(b) (title26.md:339470): "The amount realized from the sale
    # or other disposition of property shall be the sum of any money received
    # plus the fair market value of the property (other than money) received"
    proceeds: float
    # Your cost basis — generally what you originally paid for the asset plus
    # any improvements, minus depreciation. Form 8949 column (e).
    # IRC §1012(a) (title26.md:339700): "The basis of property shall be the
    # cost of such property"
    cost_basis: float
    # Whether the asset was held for more than one year (long-term) or one
    # year or less (short-term). Long-term gains are taxed at lower rates.
    # IRC §1222(3) (title26.md:351200): "the term long-term capital gain
    # means gain from the sale or exchange of a capital asset held for more
    # than 1 year"
    term: CapitalGainTerm
    # Whether this is a collectible (art, coins, stamps, antiques, gems,
    # precious metals). Collectible gains are taxed at a maximum 28% rate
    # instead of the usual 0%/15%/20%.
    # IRC §1(h)(4) (title26.md:5760): "the term 'collectibles gain' means gain
    # from the sale or exchange of a collectible... which is a capital asset
    # held for more than 1 year"
    is_collectible: bool = False
    # Whether this gain is from depreciable real estate (Section 1250 property).
    # The portion of the gain attributable to depreciation is taxed at a
    # maximum 25% rate ("unrecaptured Section 1250 gain").
    # IRC §1(h)(1)(E) (title26.md:5748): "25 percent of the excess (if any)
    # of... the unrecaptured section 1250 gain"
    is_section_1250: bool = False
    # The amount of loss disallowed under the wash sale rule. If you sold at
    # a loss and bought substantially identical securities within 30 days
    # before or after, the loss is not deductible — it's added to your basis
    # in the replacement shares instead. Form 8949 column (g).
    # IRC §1091(a) (title26.md:347794): "In the case of any loss claimed to
    # have been sustained from any sale or other disposition of shares of
    # stock or securities where it appears that... substantially identical
    # stock or securities... were acquired... no deduction shall be allowed"
    wash_sale_loss_disallowed: float = 0.0


@dataclass
class BusinessIncome:
    """Self-employment / sole proprietor income (Schedule C).

    IRC §162 (title26.md:114102) — trade or business expenses.
    IRC §1401 (title26.md:377596) — self-employment tax.
    """

    # The name of your business or "sole proprietorship" if you operate
    # under your own name. Reported on Schedule C, Line A.
    # Form 1040 Schedule C, Line A; IRC §162(a) (title26.md:114102).
    business_name: str
    # Your business's Employer Identification Number (EIN), if you have one.
    # Not required for sole proprietors with no employees.
    # Form 1040 Schedule C, Line D; IRC §6109 (title26.md:525311).
    business_ein: str = ""
    # The six-digit NAICS code that best describes your business activity
    # (e.g. 541511 for custom software). Schedule C, Line B.
    # Form 1040 Schedule C, Line B; IRS Instructions for Schedule C.
    principal_business_code: str = ""
    # Total money your business took in from sales or services before any
    # expenses. This is your business's top-line revenue (Schedule C, Line 1).
    # IRC §61(a)(2) (title26.md:70857): "Gross income derived from business"
    gross_receipts: float = 0.0
    # Refunds, rebates, or allowances you gave to customers. Subtracted from
    # gross receipts to get net revenue (Schedule C, Line 2).
    # IRC §162(a) (title26.md:114102): adjustment to arrive at gross profit.
    returns_and_allowances: float = 0.0
    # The direct cost of materials and labor used to produce the goods you
    # sold. Only applies if your business sells products (Schedule C, Line 4).
    # IRC §263A (title26.md:157789): "proper costs... shall be taken into
    # account in... inventory costs"
    cost_of_goods_sold: float = 0.0
    # What you spent on advertising and marketing your business, such as
    # online ads, business cards, or print campaigns (Schedule C, Line 8).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses
    # paid or incurred during the taxable year in carrying on any trade or business"
    advertising: float = 0.0
    # Business-related vehicle expenses — either actual costs (gas, repairs,
    # insurance) or the standard mileage rate (Schedule C, Line 9).
    # IRC §162(a)(2) (title26.md:114110): "traveling expenses... while away
    # from home in the pursuit of a trade or business"
    car_and_truck: float = 0.0
    # Fees paid to other businesses or individuals for sales commissions or
    # professional service fees (Schedule C, Line 10).
    # IRC §162(a)(1) (title26.md:114108): "a reasonable allowance for salaries
    # or other compensation for personal services actually rendered"
    commissions_and_fees: float = 0.0
    # Payments to independent contractors (non-employees) who performed
    # services for your business. You must issue a 1099-NEC if you paid
    # $600 or more (Schedule C, Line 11).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    contract_labor: float = 0.0
    # The annual write-off for wear and tear on business assets like equipment,
    # machinery, or vehicles. Includes Section 179 expensing and bonus
    # depreciation (Schedule C, Line 13).
    # IRC §167(a) (title26.md:121827): "There shall be allowed as a depreciation
    # deduction a reasonable allowance for the exhaustion, wear and tear...
    # of property used in the trade or business"
    depreciation: float = 0.0
    # Premiums for business insurance such as liability, malpractice, or
    # property insurance. Does not include health insurance (that goes on
    # Form 1040, not Schedule C) (Schedule C, Line 15).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    insurance: float = 0.0
    # Interest paid on a mortgage for business property (not your home).
    # Schedule C, Line 16a.
    # IRC §163(a) (title26.md:116508): "There shall be allowed as a deduction
    # all interest paid or accrued within the taxable year on indebtedness"
    interest_mortgage: float = 0.0
    # Interest paid on other business debts such as credit lines, equipment
    # loans, or business credit cards (Schedule C, Line 16b).
    # IRC §163(a) (title26.md:116508): "There shall be allowed as a deduction
    # all interest paid or accrued within the taxable year on indebtedness"
    interest_other: float = 0.0
    # Fees paid to lawyers, accountants, bookkeepers, tax preparers, or other
    # professionals for business-related services (Schedule C, Line 17).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    legal_and_professional: float = 0.0
    # Costs for office supplies, postage, stationery, and other small items
    # used in your business (Schedule C, Line 18).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    office_expense: float = 0.0
    # Rent or lease payments for business property, office space, equipment,
    # or vehicles used in your business (Schedule C, Line 20).
    # IRC §162(a)(3) (title26.md:114116): "rentals or other payments required
    # to be made as a condition to the continued use or possession... of
    # property to which the taxpayer has not taken or is not taking title"
    rent_lease: float = 0.0
    # What you spent to fix or maintain business property and equipment,
    # not including improvements that add value (Schedule C, Line 21).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    repairs_maintenance: float = 0.0
    # Cost of materials and supplies consumed and used during the year in
    # your business (Schedule C, Line 22).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    supplies: float = 0.0
    # State and local business taxes, licenses, and regulatory fees. Does not
    # include federal income tax or self-employment tax (Schedule C, Line 23).
    # IRC §164(a) (title26.md:119300): "the following taxes shall be allowed
    # as a deduction for the taxable year within which paid or accrued"
    taxes_licenses: float = 0.0
    # Costs of business travel away from your tax home — airfare, hotels,
    # car rentals, and similar expenses. Must be overnight and not lavish
    # (Schedule C, Line 24a).
    # IRC §162(a)(2) (title26.md:114110): "traveling expenses (including amounts
    # expended for meals and lodging other than amounts which are lavish or
    # extravagant under the circumstances) while away from home"
    travel: float = 0.0
    # Business meals — dining with clients, customers, or employees for
    # business purposes. Only 50% of the cost is deductible
    # (Schedule C, Line 24b).
    # IRC §274(n)(1) (title26.md:162543): "The amount allowable as a deduction
    # under this chapter for any expense for food or beverages shall not exceed
    # 50 percent of the amount of such expense"
    meals: float = 0.0
    # Cost of electricity, gas, water, phone, and internet for your business
    # location (Schedule C, Line 25).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    utilities: float = 0.0
    # Wages and salaries paid to your employees (not to yourself if you are
    # the sole proprietor). Does not include amounts paid to independent
    # contractors (Schedule C, Line 26).
    # IRC §162(a)(1) (title26.md:114108): "a reasonable allowance for salaries
    # or other compensation for personal services actually rendered"
    wages: float = 0.0
    # Any other ordinary and necessary business expenses not listed above.
    # You must attach a statement describing these expenses
    # (Schedule C, Line 27a).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses
    # paid or incurred during the taxable year in carrying on any trade or business"
    other_expenses: float = 0.0
    # The deduction for using part of your home regularly and exclusively for
    # business. Calculated on Form 8829 or using the simplified method ($5
    # per square foot, up to 300 sq ft) (Schedule C, Line 30).
    # IRC §280A(c)(1) (title26.md:164290): "Subsection (a) shall not apply to
    # any item to the extent such item is allocable to a portion of the dwelling
    # unit which is exclusively used on a regular basis as the principal place
    # of business for any trade or business of the taxpayer"
    home_office_deduction: float = 0.0


@dataclass
class RentalIncome:
    """Rental real estate income (Schedule E).

    IRC §61(a)(5) (title26.md:70863) — rents included in gross income.
    IRC §280A (title26.md:164272) — vacation rental / personal use rules.
    """

    # A brief description of the rental property (e.g. "123 Oak St duplex").
    # Schedule E, Part I — column (a); IRC §61(a)(5) (title26.md:70863).
    property_description: str
    # The type of rental property — e.g. "single_family", "multi_family",
    # "commercial", "vacation". Schedule E, Part I — property type.
    # IRC §61(a)(5) (title26.md:70863): "gross income means all income from
    # whatever source derived, including... Rents"
    property_type: str = ""
    # The number of days the property was rented at fair rental value during
    # the year. If rented fewer than 15 days, the income is completely
    # excluded and no rental expense deductions are allowed.
    # IRC §280A(g) (title26.md:164460): "If a dwelling unit is used during
    # the taxable year by the taxpayer as a residence and such dwelling unit
    # is actually rented for less than 15 days during the taxable year, then
    # the income derived from such use... shall not be included in the gross
    # income of such taxpayer"
    days_rented: int = 0
    # The number of days you or your family personally used the property
    # during the year. If personal use exceeds the greater of 14 days or
    # 10% of rental days, your deductions may be limited.
    # IRC §280A(d)(1) (title26.md:164380): "a taxpayer shall be treated as
    # using a dwelling unit as a residence if he uses such unit... for
    # personal purposes for a number of days which exceeds the greater of
    # 14 days, or 10 percent of the number of days during such year for
    # which such unit is rented at a fair rental"
    days_personal_use: int = 0
    # Gross rental income received from tenants during the year (Schedule E,
    # Part I, Line 3).
    # IRC §61(a)(5) (title26.md:70863): "gross income means all income from
    # whatever source derived, including... Rents"
    rental_income: float = 0.0
    # Amount spent advertising the rental to prospective tenants, such as
    # online listings or newspaper ads (Schedule E, Part I, Line 5).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses
    # paid or incurred during the taxable year in carrying on any trade or business"
    advertising: float = 0.0
    # Travel costs to manage, maintain, or collect rent on the property,
    # including mileage to visit the property (Schedule E, Part I, Line 6).
    # IRC §162(a)(2) (title26.md:114110): "traveling expenses... while away
    # from home in the pursuit of a trade or business"
    auto_and_travel: float = 0.0
    # Costs to clean the property between tenants and ongoing maintenance
    # such as landscaping, pest control, and janitorial services
    # (Schedule E, Part I, Line 7).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    cleaning_and_maintenance: float = 0.0
    # Commissions paid to property managers or rental agents for finding
    # tenants or managing the property (Schedule E, Part I, Line 8).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    commissions: float = 0.0
    # Premiums for landlord, fire, liability, or flood insurance on the
    # rental property (Schedule E, Part I, Line 9).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    insurance: float = 0.0
    # Fees paid to lawyers, accountants, or other professionals for rental
    # property matters such as tenant disputes or tax preparation
    # (Schedule E, Part I, Line 10).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    legal_and_professional: float = 0.0
    # Fees paid to a property management company for managing the rental
    # (Schedule E, Part I, Line 11).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    management_fees: float = 0.0
    # Interest paid on the mortgage for the rental property. Fully deductible
    # against rental income (unlike personal home mortgage limits)
    # (Schedule E, Part I, Line 12).
    # IRC §163(a) (title26.md:116508): "There shall be allowed as a deduction
    # all interest paid or accrued within the taxable year on indebtedness"
    mortgage_interest: float = 0.0
    # Costs to fix things that are broken or worn out, restoring them to
    # their original condition — not improvements that add value
    # (Schedule E, Part I, Line 14).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    repairs: float = 0.0
    # Cost of materials and supplies used for the rental property, such as
    # cleaning supplies, light bulbs, or small tools
    # (Schedule E, Part I, Line 15).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    supplies: float = 0.0
    # Real estate property taxes paid on the rental property during the year
    # (Schedule E, Part I, Line 16).
    # IRC §164(a)(1) (title26.md:119308): "State and local, and foreign, real
    # property taxes"
    taxes: float = 0.0
    # Cost of electricity, gas, water, sewer, and trash removal for the
    # rental property, if paid by the landlord
    # (Schedule E, Part I, Line 17).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    utilities: float = 0.0
    # The annual depreciation deduction for the rental building and
    # improvements. Residential rental property is depreciated over 27.5
    # years using the straight-line method (Schedule E, Part I, Line 18).
    # IRC §167(a) (title26.md:121827): "There shall be allowed as a depreciation
    # deduction a reasonable allowance for the exhaustion, wear and tear...
    # of property used in the trade or business"
    depreciation: float = 0.0
    # Any other ordinary and necessary rental expenses not listed in the
    # categories above (Schedule E, Part I, Line 19).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses
    # paid or incurred during the taxable year in carrying on any trade or business"
    other_expenses: float = 0.0


@dataclass
class RetirementDistribution:
    """Retirement plan distribution from Form 1099-R.

    IRC §72 (title26.md:74051) — annuity/pension taxation and early distribution penalty.
    IRC §408A (title26.md:206057) — Roth IRA distributions.
    """

    # The name of the retirement plan, pension fund, or financial institution
    # that made the distribution. Shown on Form 1099-R, Payer's name.
    # Form 1099-R, Payer's name; IRC §6047 (title26.md:509085): "every person
    # who... makes payments of designated distributions shall make a return"
    payer_name: str
    # The total amount distributed to you from the retirement plan during
    # the year, before any taxes were withheld. Form 1099-R, Box 1.
    # IRC §72(a)(1) (title26.md:74051): "gross income includes any amount
    # received as an annuity... under an annuity, endowment, or life
    # insurance contract"
    gross_distribution: float
    # The portion of the distribution that is subject to income tax. For
    # traditional retirement accounts, this is usually the full amount
    # (since contributions were tax-deductible). For Roth accounts, qualified
    # distributions are $0 taxable. Form 1099-R, Box 2a.
    # IRC §72(a) (title26.md:74051): "gross income includes any amount received
    # as an annuity"
    taxable_amount: float
    # Federal income tax your plan withheld from the distribution.
    # Form 1099-R, Box 4. This counts as a payment toward your tax bill.
    # IRC §31(a) (title26.md:22615): "The amount withheld as tax... shall be
    # allowed to the recipient of the income as a credit against the tax"
    federal_income_tax_withheld: float = 0.0
    # Whether you received this distribution before reaching age 59½. Early
    # distributions are generally subject to a 10% additional tax penalty
    # on top of regular income tax. Form 1099-R, Box 7 distribution code.
    # IRC §72(t)(1) (title26.md:75384): "the taxpayer's tax... shall be
    # increased by an amount equal to 10 percent of the portion of such
    # amount which is includible in gross income"
    is_early_distribution: bool = False
    # The IRS distribution code from Form 1099-R, Box 7, that indicates
    # whether an exception to the 10% early withdrawal penalty applies
    # (e.g. code 2 for disability, code 4 for death, code 1 for no exception).
    # IRC §72(t)(2)(A) (title26.md:75400): "paragraph (1) shall not apply to
    # any of the following distributions: Distributions which are made on or
    # after the date on which the employee attains age 59, made to a
    # beneficiary on or after the death of the employee"
    early_distribution_exception_code: str = ""
    # Whether this distribution came from a Roth IRA or Roth 401(k). Roth
    # contributions were made with after-tax dollars, so qualified distributions
    # are tax-free.
    # IRC §408A(d)(1) (title26.md:206057): "any qualified distribution from a
    # Roth IRA shall not be includible in gross income"
    is_roth: bool = False
    # Whether this Roth distribution meets the requirements to be completely
    # tax-free — made after age 59½, death, or disability AND after the
    # 5-year holding period from your first Roth contribution.
    # IRC §408A(d)(2) (title26.md:206057): "the term 'qualified distribution'
    # means any payment or distribution... made on or after the date on which
    # the individual attains age 59½... and... meets the 5-taxable-year period"
    is_qualified_roth_distribution: bool = False


@dataclass
class SocialSecurityIncome:
    """Social Security benefits from Form SSA-1099.

    IRC §86 (title26.md:80658) — taxation of Social Security benefits.
    Up to 85% may be taxable depending on provisional income.
    """

    # Your total Social Security benefits received during the year, as shown
    # on Form SSA-1099, Box 5. Depending on your other income, up to 85%
    # of this amount may be taxable.
    # IRC §86(a) (title26.md:80658): "gross income for the taxable year of
    # any taxpayer described in subsection (b)... includes social security
    # benefits in an amount equal to the lesser of (A) one-half of the social
    # security benefits received during the taxable year"
    total_benefits: float
    # Any Social Security benefits you repaid during the year (e.g. because
    # of an overpayment). These reduce the amount subject to tax.
    # IRC §86(d)(2)(A) (title26.md:80750): "the term 'social security benefit'
    # means any amount received by the taxpayer by reason of entitlement to
    # a monthly benefit under title II of the Social Security Act"
    repayments: float = 0.0


@dataclass
class UnemploymentIncome:
    """Unemployment compensation from Form 1099-G.

    IRC §85 (title26.md:80444) — all unemployment is gross income.
    """

    # The total unemployment compensation you received during the year,
    # as shown on Form 1099-G, Box 1. All unemployment benefits are
    # taxable as ordinary income.
    # IRC §85(a) (title26.md:80444): "In the case of an individual, gross
    # income includes unemployment compensation"
    amount: float
    # Federal income tax withheld from your unemployment payments, as
    # shown on Form 1099-G, Box 4 (if you elected voluntary withholding).
    # IRC §31(a) (title26.md:22615): "The amount withheld as tax... shall
    # be allowed to the recipient of the income as a credit"
    federal_income_tax_withheld: float = 0.0


@dataclass
class OtherIncome:
    """Other income not captured in specific categories.

    IRC §61 (title26.md:70846) — gross income from whatever source.
    Includes prizes/awards (§74), gambling winnings, jury duty pay, etc.
    """

    # A brief description of the income source — e.g. "jury duty pay",
    # "prize from contest", "hobby income".
    # IRC §61(a) (title26.md:70846): "gross income means all income from
    # whatever source derived"
    description: str
    # The dollar amount of this income item received during the tax year.
    # IRC §61(a) (title26.md:70846): "gross income means all income from
    # whatever source derived"
    amount: float
    # Whether this income is from an activity that qualifies as a trade or
    # business, making it subject to self-employment tax (15.3%). Most
    # "other income" items like prizes and jury duty pay are NOT SE income.
    # IRC §1402(a) (title26.md:378900): "the term 'net earnings from
    # self-employment' means the gross income derived by an individual
    # from any trade or business carried on by such individual"
    is_subject_to_se_tax: bool = False


@dataclass
class HomeSale:
    """Sale of principal residence.

    IRC §121 (title26.md:90818) — exclusion of gain up to $250k/$500k.
    """

    # The date you sold or closed on the home (YYYY-MM-DD format).
    # IRC §121(a) (title26.md:90818): "Gross income shall not include gain
    # from the sale or exchange of property if, during the 5-year period
    # ending on the date of the sale or exchange, such property has been
    # owned and used by the taxpayer as the taxpayer's principal residence"
    date_sold: str
    # The total price the buyer paid for your home (the contract sale price).
    # IRC §1001(b) (title26.md:339470): "The amount realized from the sale
    # or other disposition of property shall be the sum of any money received
    # plus the fair market value of the property... received"
    selling_price: float
    # Costs you paid to sell the home, such as real estate agent commissions,
    # title insurance, advertising, and legal fees. These reduce your gain.
    # IRC §1001(a) (title26.md:339459): "The gain from the sale... shall be
    # the excess of the amount realized therefrom over the adjusted basis"
    selling_expenses: float = 0.0
    # What you originally paid for the home (the purchase price), plus
    # certain settlement or closing costs from when you bought it.
    # IRC §1012(a) (title26.md:339700): "The basis of property shall be the
    # cost of such property"
    cost_basis: float = 0.0
    # The total cost of capital improvements you made to the home that added
    # value, extended its life, or adapted it to a new use — such as a new
    # roof, addition, or remodeled kitchen. Routine maintenance doesn't count.
    # IRC §1016(a)(1) (title26.md:340604): "Proper adjustment... shall in all
    # cases be made... for expenditures... properly chargeable to capital account"
    improvements: float = 0.0
    # Depreciation you claimed on the home after May 6, 1997 (e.g. for a
    # home office or rental use). This portion of gain cannot be excluded
    # and is taxed as "unrecaptured Section 1250 gain" at up to 25%.
    # IRC §121(d)(6) (title26.md:91061): "the amount of gain excluded...
    # shall not include so much of such gain as does not exceed the portion
    # of the depreciation adjustments... attributable to periods after
    # May 6, 1997"
    depreciation_after_may_1997: float = 0.0
    # The number of years you owned the home. You must have owned it for
    # at least 2 of the last 5 years to qualify for the exclusion.
    # IRC §121(a) (title26.md:90818): "such property has been owned... by
    # the taxpayer as the taxpayer's principal residence for periods
    # aggregating 2 years or more"
    years_owned: float = 0.0
    # The number of years (out of the 5-year period ending on the sale date)
    # you actually lived in the home as your main residence. You need at
    # least 2 years of use to qualify for the gain exclusion.
    # IRC §121(a) (title26.md:90818): "such property has been... used by
    # the taxpayer as the taxpayer's principal residence for periods
    # aggregating 2 years or more"
    years_used_as_residence: float = 0.0
    # Whether you already used the home sale exclusion on a different home
    # within the last 2 years. You can only use it once every 2 years.
    # IRC §121(b)(3) (title26.md:90864): "Subsection (a) shall not apply
    # to any sale or exchange by the taxpayer if, during the 2-year period
    # ending on the date of such sale or exchange, there was any other sale
    # or exchange by the taxpayer to which subsection (a) applied"
    exclusion_used_in_prior_2_years: bool = False


@dataclass
class EducationExpense:
    """Education expenses for credits.

    IRC §25A (title26.md:16106) — AOTC and Lifetime Learning credits.
    From Form 1098-T.
    """

    # The name of the student for whom you paid education expenses. Can be
    # yourself, your spouse, or a dependent listed on your return.
    # IRC §25A(b)(3) (title26.md:16170): "the term 'eligible student' means,
    # with respect to any academic period, a student who meets the
    # requirements of section 484(a)(1) of the Higher Education Act of 1965"
    student_name: str
    # The student's Social Security Number. Required to claim education credits.
    # IRC §25A(g)(1) (title26.md:16326): "No credit shall be allowed... unless
    # the taxpayer includes... the TIN of the... student"
    student_ssn: str
    # The name of the college, university, or vocational school the student
    # attended. Must be an eligible educational institution that participates
    # in federal student aid programs.
    # IRC §25A(f)(2) (title26.md:16310): "the term 'eligible educational
    # institution' means an institution described in section 481 of the
    # Higher Education Act of 1965"
    institution_name: str
    # The school's Employer Identification Number, shown on Form 1098-T, Box 5.
    # Form 1098-T; IRC §6050S (title26.md:512524).
    institution_ein: str = ""
    # The amount of qualified tuition and required enrollment fees paid to the
    # institution for the student during the year. Room, board, insurance,
    # and transportation do NOT qualify. Form 1098-T, Box 1.
    # IRC §25A(f)(1)(A) (title26.md:16106): "The term 'qualified tuition and
    # related expenses' means tuition and fees required for the enrollment or
    # attendance of the taxpayer, the taxpayer's spouse, or any dependent"
    qualified_tuition_and_fees: float = 0.0
    # Scholarships, grants, and other tax-free educational assistance the
    # student received. These reduce the amount of expenses eligible for the
    # credit. Form 1098-T, Box 5.
    # IRC §25A(g)(2) (title26.md:16162): "qualified tuition and related
    # expenses... shall be reduced by the amount of such expenses which were
    # taken into account... under section 117"
    scholarships_and_grants: float = 0.0
    # Which education credit you are claiming — the American Opportunity Tax
    # Credit (AOTC, up to $2,500 per student for first 4 years) or the
    # Lifetime Learning Credit (LLC, up to $2,000 per return, any year).
    # IRC §25A(a) (title26.md:16106): "there shall be allowed as a credit...
    # the American Opportunity Tax Credit, plus the Lifetime Learning Credit"
    credit_type: EducationCreditType = EducationCreditType.AOTC
    # Which year of college or post-secondary education the student is in
    # (1 through 4). The AOTC is only available for the first 4 years.
    # IRC §25A(b)(2)(C) (title26.md:16160): "An election... may not be made
    # for any taxable year if such an election has been made... for any 4
    # prior taxable years"
    year_in_postsecondary: int = 1
    # Whether the student was enrolled at least half-time for at least one
    # academic period during the year. Required for the AOTC.
    # IRC §25A(b)(3)(B) (title26.md:16180): "The term 'eligible student'...
    # means a student who... is carrying at least ½ the normal full-time
    # work load for the course of study the student is pursuing"
    is_at_least_half_time: bool = True
    # Whether the student has been convicted of a federal or state felony
    # drug offense. If so, the AOTC cannot be claimed for that student.
    # IRC §25A(b)(2)(D) (title26.md:16170): "The American Opportunity Tax
    # Credit... shall not be allowed... with respect to a student for the
    # taxable year if the student has been convicted of a Federal or State
    # felony offense consisting of the possession or distribution of a
    # controlled substance"
    has_felony_drug_conviction: bool = False


@dataclass
class ChildCareExpense:
    """Child and dependent care expenses.

    IRC §21 (title26.md:12007) — credit for care of qualifying individuals.
    """

    # The name of the person or organization that provided the care — such
    # as a daycare center, nanny, babysitter, or after-school program.
    # Form 2441, Part I; IRC §21(a) (title26.md:12007): "there shall be
    # allowed as a credit... an amount equal to the applicable percentage
    # of the employment-related expenses paid by such individual"
    provider_name: str
    # The care provider's Social Security Number (for individuals) or EIN
    # (for organizations). You must include this to claim the credit.
    # Form 2441, Part I — Provider's TIN; IRC §21(e)(9) (title26.md:12214):
    # "no credit shall be allowed... unless the taxpayer includes... the
    # name, address, and TIN of each person to whom an amount was paid"
    provider_tin: str
    # The mailing address of the care provider.
    # Form 2441, Part I — Provider's address.
    provider_address: str = ""
    # The total amount you paid to this care provider during the year for
    # care of qualifying individuals so you (and your spouse) could work.
    # Limited to $3,000 for one qualifying individual or $6,000 for two
    # or more.
    # IRC §21(c) (title26.md:12114): "The aggregate amount of
    # employment-related expenses... shall not exceed $3,000 if there is 1
    # qualifying individual... or $6,000 if there are 2 or more"
    amount_paid: float = 0.0
    # The name of the child or dependent who received the care. Must be a
    # qualifying individual: your child under age 13, your disabled spouse,
    # or another disabled dependent.
    # IRC §21(b)(1) (title26.md:12042): "qualifying individual... a dependent
    # of the taxpayer... who has not attained age 13... or is physically or
    # mentally incapable of caring for himself"
    care_recipient_name: str = ""
    # The Social Security Number of the child or dependent who received care.
    # IRC §21(e)(10) (title26.md:12110): identification requirements.
    care_recipient_ssn: str = ""


@dataclass
class CharitableContribution:
    """Charitable contributions detail.

    IRC §170 (title26.md:132628) — deduction for charitable contributions.
    """

    # The name of the charity or nonprofit organization you donated to.
    # Must be a qualified tax-exempt organization under §501(c)(3).
    # IRC §170(c) (title26.md:132700): "the term 'charitable contribution'
    # means a contribution or gift to or for the use of... a corporation,
    # trust, or community chest, fund, or foundation... organized and
    # operated exclusively for religious, charitable, scientific, literary,
    # or educational purposes"
    organization_name: str
    # The total cash (including checks, credit card charges, and electronic
    # payments) you donated to this organization during the year. Cash
    # contributions to public charities are deductible up to 60% of AGI.
    # IRC §170(b)(1)(G) (title26.md:132740): "the aggregate amount of
    # contributions allowed... shall not exceed 60 percent of the taxpayer's
    # contribution base"
    cash_amount: float = 0.0
    # The fair market value of non-cash property you donated — such as
    # clothing, household items, vehicles, or stocks. Non-cash donations
    # over $500 require Form 8283.
    # IRC §170(a)(1) (title26.md:132628): "There shall be allowed as a
    # deduction any charitable contribution... payment of which is made
    # within the taxable year"
    noncash_amount: float = 0.0
    # A description of the non-cash property donated (e.g. "used clothing",
    # "2018 Honda Civic", "100 shares of AAPL stock"). Required for
    # non-cash donations.
    # Form 8283; IRC §170(f)(8) (title26.md:132900): "no deduction shall be
    # allowed for any contribution of $250 or more unless the taxpayer
    # substantiates the contribution by a contemporaneous written
    # acknowledgment of the contribution by the donee organization"
    # requirements for charitable contributions.
    noncash_description: str = ""
    # Whether the donated property would have produced long-term capital gain
    # if sold. Capital gain property donations to public charities are limited
    # to 30% of AGI instead of the usual 60%.
    # IRC §170(b)(1)(C) (title26.md:132774): "contributions of capital gain
    # property to which subparagraph (A) applies shall be allowed... to the
    # extent of the amount of such contributions which does not exceed 30
    # percent of the taxpayer's contribution base"
    is_capital_gain_property: bool = False
    # Whether the organization is a public charity (vs. a private foundation).
    # Public charities have higher AGI limits for deductions. Most well-known
    # charities, churches, schools, and hospitals are public charities.
    # IRC §170(b)(1)(A) (title26.md:132738): higher limits for contributions
    # "to a church or a convention or association of churches... an educational
    # organization... a hospital"
    is_public_charity: bool = True


@dataclass
class MortgageInterest:
    """Mortgage interest from Form 1098.

    IRC §163(h) (title26.md:116508) — qualified residence interest deduction.
    Limit: $750,000 acquisition debt ($375,000 MFS) for post-Dec 15, 2017 debt.
    """

    # The name of the bank, credit union, or mortgage company that holds your
    # loan. Shown on Form 1098, Recipient/Lender field.
    # Form 1098; IRC §6050H (title26.md:511071): "any person who is engaged
    # in a trade or business and who... receives from an individual interest
    # aggregating $600 or more... shall make a return"
    lender_name: str
    # The lender's Employer Identification Number (EIN), shown on Form 1098.
    # Form 1098, Recipient's TIN; IRC §6109 (title26.md:525311).
    lender_ein: str = ""
    # The total mortgage interest you paid during the year on your home loan.
    # Deductible on Schedule A for loans up to $750,000 ($375,000 MFS) taken
    # out after December 15, 2017. Form 1098, Box 1.
    # IRC §163(h)(3)(B) (title26.md:116550): "The term 'acquisition
    # indebtedness' means any indebtedness which is incurred in acquiring,
    # constructing, or substantially improving any qualified residence of
    # the taxpayer, and is secured by such residence"
    mortgage_interest_paid: float = 0.0
    # Private mortgage insurance (PMI) premiums you paid during the year,
    # if your lender required PMI because your down payment was less than
    # 20%. Form 1098, Box 5.
    # IRC §163(h)(3)(E) (title26.md:117071): "premiums paid or accrued...
    # for qualified mortgage insurance... shall be treated as mortgage
    # interest"
    mortgage_insurance_premiums: float = 0.0
    # Mortgage points (prepaid interest) you paid to lower your interest
    # rate. Generally deductible in full in the year paid for a home
    # purchase, or amortized over the loan term for a refinance. Form 1098,
    # Box 6.
    # IRC §461(g)(2) (title26.md:245042): "In the case of any amount paid
    # as points... to any financial institution... such amount shall be
    # allowed as a deduction in the taxable year in which paid"
    points_paid: float = 0.0
    # The remaining principal balance on your mortgage as of the end of the
    # year. Used to determine if your total mortgage debt exceeds the
    # deduction limit. Form 1098, Box 2.
    # IRC §163(h)(3)(B)(ii) (title26.md:116555): acquisition indebtedness
    # limited to $750,000 ($375,000 MFS).
    outstanding_mortgage_principal: float = 0.0
    # The date the mortgage loan was originated (YYYY-MM-DD format). Loans
    # taken out on or before December 15, 2017 have a higher $1,000,000
    # limit; loans after that date are limited to $750,000.
    # IRC §163(h)(3)(F)(i) (title26.md:116996): "$1,000,000 limitation...
    # shall be applied by substituting '$750,000'"
    mortgage_origination_date: str = ""
    # Whether this loan was used to buy, build, or substantially improve
    # your home (acquisition debt). Only acquisition debt interest is
    # deductible; home equity loan interest for other purposes generally
    # is not deductible after 2017.
    # IRC §163(h)(3)(B)(i) (title26.md:116550): "The term 'acquisition
    # indebtedness' means any indebtedness which is incurred in acquiring,
    # constructing, or substantially improving any qualified residence"
    is_acquisition_debt: bool = True


@dataclass
class StateLocalTaxes:
    """State and local taxes paid.

    IRC §164 (title26.md:119300) — SALT deduction.
    Subject to SALT cap per IRC §164(b)(6).
    """

    # State income taxes you paid during the year — from paycheck withholding,
    # estimated payments, or a balance due on your prior-year state return.
    # Combined with other SALT items, subject to the $40,000 cap ($20,000 MFS)
    # for 2025.
    # IRC §164(a)(3) (title26.md:119312): "State and local, and foreign,
    # income, war profits, and excess profits taxes"
    state_income_tax_paid: float = 0.0
    # Local (city/county) income taxes you paid during the year. Some
    # localities impose their own income tax in addition to the state tax.
    # IRC §164(a)(3) (title26.md:119312): "State and local... income...
    # taxes"
    local_income_tax_paid: float = 0.0
    # Real estate property taxes you paid on property you own, such as your
    # home, land, or other real property. Does not include taxes on rental
    # or business property (those go on Schedule E or C).
    # IRC §164(a)(1) (title26.md:119308): "State and local, and foreign,
    # real property taxes"
    real_property_tax: float = 0.0
    # Personal property taxes you paid — taxes assessed based on the value
    # of personal property like vehicles, boats, or RVs. Must be based on
    # the value of the property to be deductible.
    # IRC §164(a)(2) (title26.md:119310): "State and local personal
    # property taxes"
    personal_property_tax: float = 0.0
    # State and local general sales taxes you paid during the year. You can
    # deduct either income taxes OR sales taxes, but not both. The IRS
    # provides optional tables based on income and state of residence.
    # IRC §164(b)(5)(I) (title26.md:119376): "an individual may elect to
    # deduct... State and local general sales taxes... in lieu of the taxes
    # described in paragraph (3)"
    sales_tax_paid: float = 0.0
    # Whether you choose to deduct state/local sales taxes instead of
    # state/local income taxes. This may benefit you if you live in a state
    # with no income tax or if you made large purchases.
    # IRC §164(b)(5)(I) (title26.md:119376): "an individual may elect to
    # deduct... State and local general sales taxes... in lieu of the taxes
    # described in paragraph (3)"
    elect_sales_tax: bool = False


@dataclass
class MedicalExpense:
    """Medical and dental expenses.

    IRC §213 (title26.md:147452) — deductible above 7.5% of AGI.
    """

    # Your total out-of-pocket medical and dental expenses for the year —
    # doctor visits, surgeries, hospital stays, dental work, vision care,
    # hearing aids, etc. Only the amount exceeding 7.5% of your AGI is
    # deductible.
    # IRC §213(a) (title26.md:147452): "There shall be allowed as a deduction
    # the expenses paid during the taxable year, not compensated for by
    # insurance or otherwise, for medical care of the taxpayer, his spouse,
    # or a dependent... to the extent that such expenses exceed 7.5 percent
    # of adjusted gross income"
    total_medical_dental: float = 0.0
    # Premiums you paid for health insurance out of your own pocket (not
    # through pre-tax payroll deductions or an employer plan). Includes
    # premiums for medical, dental, and vision coverage.
    # IRC §213(d)(1)(D) (title26.md:147530): "The term 'medical care' means
    # amounts paid... for insurance... covering medical care"
    health_insurance_premiums: float = 0.0
    # Premiums paid for qualified long-term care insurance. Deductible amounts
    # are capped based on your age at the end of the tax year.
    # IRC §213(d)(1)(D) (title26.md:147530): "amounts paid for insurance...
    # covering medical care" including "qualified long-term care services"
    # IRC §213(d)(10) (title26.md:147570): age-based limits on deductible
    # long-term care premiums.
    long_term_care_premiums: float = 0.0
    # Cost of prescription medications and insulin. Over-the-counter
    # medicines are NOT deductible unless prescribed by a doctor.
    # IRC §213(b) (title26.md:147465): "An amount paid during the taxable
    # year for medicine or a drug shall be taken into account under
    # subsection (a) only if such medicine or drug is a prescribed drug
    # or is insulin"
    prescription_drugs: float = 0.0
    # Transportation costs to and from medical appointments — mileage,
    # parking, tolls, ambulance fees, bus/taxi fare. Also includes lodging
    # away from home for medical treatment (up to $50 per night).
    # IRC §213(d)(1)(B) (title26.md:147510): "amounts paid for transportation
    # primarily for and essential to medical care"
    medical_travel: float = 0.0


@dataclass
class RetirementContribution:
    """Retirement account contributions.

    IRC §219 (title26.md:149106) — IRA deduction.
    IRC §408A (title26.md:206057) — Roth IRA contributions.
    """

    # The type of retirement account — Traditional IRA, Roth IRA, 401(k),
    # Roth 401(k), SEP IRA, or SIMPLE IRA. Each has different tax treatment
    # for contributions and withdrawals.
    # IRC §219 (title26.md:149106): "there shall be allowed as a deduction an
    # amount equal to the qualified retirement contributions"
    # IRC §408A (title26.md:206057): Roth IRA rules — no deduction, but
    # qualified distributions are tax-free.
    account_type: RetirementAccountType
    # The total amount you contributed to this retirement account during the
    # year. For 2025, the IRA limit is $7,000 ($8,000 if age 50+); 401(k)
    # limit is $23,500 ($31,000 if age 50+).
    # IRC §219(b)(1) (title26.md:149120): "The amount allowable as a
    # deduction... shall not exceed the lesser of the deductible amount, or
    # an amount equal to the compensation includible in the individual's
    # gross income"
    contribution_amount: float = 0.0
    # The amount your employer contributed (matched) on your behalf. Employer
    # contributions do not count against your personal contribution limit.
    # IRC §402(g) (title26.md:192780): elective deferral limits.
    employer_match: float = 0.0
    # Whether you (or your spouse) are an active participant in an
    # employer-sponsored retirement plan (e.g. 401(k), pension, 403(b)).
    # If so, your Traditional IRA deduction may be reduced or eliminated
    # based on your income.
    # IRC §219(g)(1) (title26.md:149340): "If the taxpayer or the taxpayer's
    # spouse is an active participant... the deductible amount shall be...
    # reduced (but not below zero)"
    is_active_participant_in_employer_plan: bool = False


@dataclass
class HSAInfo:
    """Health Savings Account information.

    IRC §223 (title26.md:152303) — HSA deduction and rules.
    """

    # Whether your high-deductible health plan (HDHP) covers only yourself
    # (self-only) or your family. The contribution limit is different for
    # each: $4,300 self-only / $8,550 family for 2025.
    # IRC §223(b)(2) (title26.md:152324): "the monthly limitation... shall
    # be 1/12 of the annual limitation for such coverage"
    is_self_only_coverage: bool = True
    # The amount you personally contributed to your HSA during the year
    # (not through payroll deduction). This is an above-the-line deduction
    # that reduces your AGI.
    # IRC §223(a) (title26.md:152303): "there shall be allowed as a deduction
    # for the taxable year an amount equal to the aggregate amount paid in
    # cash during such taxable year by or on behalf of such individual to
    # a health savings account"
    taxpayer_contributions: float = 0.0
    # The amount your employer contributed to your HSA. Employer contributions
    # are excluded from your income but count toward the annual limit.
    # IRC §223(b)(4) (title26.md:152360): "The limitation... shall be reduced
    # by the aggregate amount paid by the employer... to all health savings
    # accounts of such individual"
    employer_contributions: float = 0.0
    # The total amount you withdrew from your HSA during the year, for any
    # purpose. Distributions used for non-medical expenses are taxable income
    # plus a 20% penalty (unless you're 65+ or disabled).
    # IRC §223(f)(2) (title26.md:152430): "Any amount paid or distributed out
    # of a health savings account which is not used exclusively to pay
    # qualified medical expenses... shall be includible in the gross income"
    distributions: float = 0.0
    # The total amount of your HSA distributions that were used to pay for
    # qualified medical expenses. These withdrawals are completely tax-free.
    # IRC §223(f)(1) (title26.md:152420): "Any amount paid or distributed out
    # of a health savings account shall not be includible in gross income if
    # such amount is used exclusively to pay qualified medical expenses"
    qualified_medical_expenses_from_hsa: float = 0.0


@dataclass
class ForeignIncomeInfo:
    """Foreign earned income and taxes paid.

    IRC §911 (title26.md:325314) — foreign earned income exclusion.
    IRC §27 / §901 (title26.md:19867) — foreign tax credit.
    """

    # The name of the foreign country where you earned income or paid taxes.
    # IRC §911(d)(1) (title26.md:325360): "the term 'qualified individual'
    # means an individual whose tax home is in a foreign country"
    country: str
    # The total income you earned while working in this foreign country.
    # You may be able to exclude up to ~$130,000 (2025, inflation-adjusted)
    # if you qualify as a bona fide resident or meet the physical presence test.
    # IRC §911(a)(1) (title26.md:325314): "there shall be excluded from the
    # gross income of such individual... the foreign earned income of such
    # individual"
    foreign_earned_income: float = 0.0
    # Income taxes you paid to the foreign country's government. You can claim
    # a credit on your U.S. return to avoid being taxed twice on the same
    # income. You choose either the foreign earned income exclusion OR the
    # foreign tax credit, not both on the same income.
    # IRC §901(a) (title26.md:319129): "the tax imposed by this chapter shall
    # be credited with the amounts provided in the applicable paragraph of
    # subsection (b)"
    foreign_taxes_paid: float = 0.0
    # The number of days you were physically present in the foreign country
    # during the tax year. You need at least 330 full days in any 12-month
    # period to qualify under the physical presence test.
    # IRC §911(d)(1)(B) (title26.md:325370): "during any period of 12
    # consecutive months, such individual is present in a foreign country...
    # during at least 330 full days"
    days_in_foreign_country: int = 0
    # Whether you were a bona fide resident of a foreign country for an
    # uninterrupted period that includes the entire tax year. This is an
    # alternative to the 330-day physical presence test.
    # IRC §911(d)(1)(A) (title26.md:325364): "an individual whose tax home
    # is in a foreign country and who is a bona fide resident of a foreign
    # country... for an uninterrupted period which includes an entire
    # taxable year"
    is_bona_fide_resident: bool = False
    # Your housing expenses in the foreign country — rent, utilities,
    # insurance, and similar costs (but not extravagant expenses). A portion
    # may be excludable beyond the base foreign earned income exclusion.
    # IRC §911(c)(1) (title26.md:325330): "the term 'housing cost amount'
    # means an amount equal to the excess of the housing expenses...
    # of such individual... over 16 percent of the amount... of the
    # exclusion amount"
    housing_expenses: float = 0.0


@dataclass
class EstimatedTaxPayment:
    """Estimated tax payments made during the year.

    IRC §6654 (title26.md:568042) — estimated tax requirements.
    """

    # Your first quarter estimated tax payment, due April 15 of the tax year.
    # You make estimated payments if you expect to owe $1,000 or more after
    # subtracting withholding and credits. Form 1040-ES.
    # IRC §6654(c)(2) (title26.md:566360): "the amount of the required
    # installment... shall be 25 percent of the required annual payment"
    q1_amount: float = 0.0
    # Your second quarter estimated tax payment, due June 15.
    # IRC §6654(c)(2) (title26.md:566360): "25 percent of the required
    # annual payment"
    q2_amount: float = 0.0
    # Your third quarter estimated tax payment, due September 15.
    # IRC §6654(c)(2) (title26.md:566360): "25 percent of the required
    # annual payment"
    q3_amount: float = 0.0
    # Your fourth quarter estimated tax payment, due January 15 of the
    # following year.
    # IRC §6654(c)(2) (title26.md:566360): "25 percent of the required
    # annual payment"
    q4_amount: float = 0.0
    # Any amount you elected to apply from your prior year's tax overpayment
    # toward this year's estimated tax instead of receiving a refund.
    # Form 1040, Line 36 of prior year; IRC §6402(b) (title26.md:542923):
    # "the Secretary... may credit the amount of such overpayment... against
    # any liability... of such person"
    amount_applied_from_prior_year: float = 0.0


@dataclass
class CleanVehicleCredit:
    """Clean vehicle credit information.

    IRC §30D (title26.md:21693) — new clean vehicle credit (up to $7,500).
    IRC §25E (title26.md:18698) — previously-owned clean vehicle credit (up to $4,000).
    """

    # Whether this is a new clean vehicle (§30D, up to $7,500 credit) or a
    # previously-owned clean vehicle (§25E, up to $4,000 credit).
    # IRC §30D(a) (title26.md:21693): "There shall be allowed as a credit...
    # with respect to each new clean vehicle placed in service by the taxpayer"
    # IRC §25E(a) (title26.md:18698): "there shall be allowed as a credit...
    # a previously-owned clean vehicle"
    is_new_vehicle: bool = True
    # The Vehicle Identification Number (VIN) of the clean vehicle. Required
    # for claiming the credit on your return.
    # IRC §30D(d)(1)(H) (title26.md:21780): VIN reporting requirement.
    vehicle_vin: str = ""
    # The price you paid for the vehicle. For previously-owned vehicles (§25E),
    # the sale price must be $25,000 or less. The credit is 30% of the price,
    # up to $4,000.
    # IRC §25E(a)(2) (title26.md:18700): "the amount equal to 30 percent of
    # the sale price with respect to such vehicle"
    purchase_price: float = 0.0
    # The date you purchased the vehicle (YYYY-MM-DD format). Credits under
    # §30D and §25E were terminated after September 30, 2025.
    # IRC §30D(h) (title26.md:21850): termination date provisions.
    purchase_date: str = ""
    # The manufacturer's suggested retail price (MSRP) of the vehicle. For
    # new vehicles (§30D), there are MSRP caps: $80,000 for vans, SUVs, and
    # pickups; $55,000 for all other vehicles.
    # IRC §30D(f)(11) (title26.md:21965): "no credit shall be allowed...
    # if the manufacturer's suggested retail price... exceeds... $80,000
    # in the case of a van, sport utility vehicle, or pickup truck, and
    # $55,000 in the case of any other vehicle"
    vehicle_msrp: float = 0.0
    # Whether the vehicle meets the critical minerals requirement — that a
    # specified percentage of the battery's critical minerals were extracted
    # or processed in the U.S. or a free trade partner. Worth $3,750 of the
    # credit.
    # IRC §30D(e)(1)(A) (title26.md:21750): "the percentage of the value of
    # the applicable critical minerals... extracted or processed in the
    # United States, or in any country with which the United States has a
    # free trade agreement"
    meets_critical_minerals_requirement: bool = False
    # Whether the vehicle meets the battery component requirement — that a
    # specified percentage of battery components were manufactured or
    # assembled in North America. Worth $3,750 of the credit.
    # IRC §30D(e)(2)(A) (title26.md:21760): "the percentage of the value of
    # the components contained in the battery... manufactured or assembled
    # in North America"
    meets_battery_component_requirement: bool = False
    # Whether the vehicle was made by a qualified manufacturer whose vehicles
    # are eligible for the credit.
    # IRC §30D(d)(1)(C) (title26.md:21730): "the final assembly of which
    # occurs within North America" and other manufacturer requirements.
    is_qualified_manufacturer: bool = False


@dataclass
class EnergyCredit:
    """Residential energy credits.

    IRC §25C (title26.md:17281) — energy efficient home improvement credit (30%).
    IRC §25D (title26.md:18115) — residential clean energy credit (30%).
    """

    # Amounts you spent on energy-efficient home improvements — insulation,
    # exterior doors, windows, skylights, and certain central air systems.
    # 30% credit, up to $1,200 total per year (with $600-per-item sub-caps).
    # IRC §25C(a)(1) (title26.md:17287): "30 percent of the sum of the amount
    # paid or incurred by the taxpayer for qualified energy efficiency
    # improvements installed during such taxable year"
    home_improvement_expenditures: float = 0.0
    # Amounts you spent on qualifying heat pumps, heat pump water heaters,
    # or biomass stoves/boilers. These have a separate $2,000 annual cap.
    # IRC §25C(b)(6) (title26.md:17330): "in the case of any qualified energy
    # property described in subparagraph (A)... $2,000"
    heat_pump_expenditures: float = 0.0
    # Amount paid for a home energy audit conducted by a qualified auditor.
    # 30% credit with a $150 cap per year.
    # IRC §25C(a)(3) (title26.md:17295): "the amount paid or incurred by the
    # taxpayer during the taxable year for home energy audits"
    # IRC §25C(b)(5) (title26.md:17338): "$150 with respect to home energy
    # audits"
    home_energy_audit: float = 0.0
    # Amounts you spent on solar electric (photovoltaic) panels for your home.
    # 30% credit with no dollar cap. Part of the Residential Clean Energy
    # Credit (§25D).
    # IRC §25D(a)(1) (title26.md:18120): "the qualified solar electric
    # property expenditures"
    solar_electric_expenditures: float = 0.0
    # Amounts you spent on solar water heating systems for your home. The
    # system must provide at least half the energy for water heating. 30%
    # credit with no dollar cap.
    # IRC §25D(a)(2) (title26.md:18122): "the qualified solar water heating
    # property expenditures"
    solar_water_heating_expenditures: float = 0.0
    # Amounts you spent on battery storage technology for your home (capacity
    # of at least 3 kilowatt hours). 30% credit with no dollar cap.
    # IRC §25D(a)(6) (title26.md:18132): "the qualified battery storage
    # technology expenditures"
    battery_storage_expenditures: float = 0.0
    # Amounts you spent on geothermal heat pump systems for your home.
    # 30% credit with no dollar cap.
    # IRC §25D(a)(5) (title26.md:18130): "the qualified geothermal heat pump
    # property expenditures"
    geothermal_expenditures: float = 0.0
    # Amounts you spent on small residential wind energy systems (wind
    # turbines) for your home. 30% credit with no dollar cap.
    # IRC §25D(a)(4) (title26.md:18128): "the qualified small wind energy
    # property expenditures"
    wind_expenditures: float = 0.0


@dataclass
class CancelledDebt:
    """Cancelled / discharged debt from Form 1099-C.

    IRC §108 (title26.md:86700) — income from discharge of indebtedness.
    """

    # The name of the lender or creditor who cancelled or forgave the debt.
    # Shown on Form 1099-C, Box — Creditor's name.
    # Form 1099-C; IRC §6050P (title26.md:512210): "any applicable entity
    # which discharges... indebtedness of any person... shall make a return"
    creditor_name: str
    # The total amount of debt that was cancelled, forgiven, or discharged.
    # Generally, this counts as taxable income unless an exclusion applies.
    # Form 1099-C, Box 2.
    # IRC §61(a)(11) (title26.md:70875): "gross income means all income from
    # whatever source derived, including... Income from discharge of
    # indebtedness"
    amount_discharged: float = 0.0
    # Whether the cancelled debt was a mortgage on your main home (qualified
    # principal residence indebtedness). If so, it may be excluded from
    # income for discharges before January 1, 2026.
    # IRC §108(a)(1)(E) (title26.md:86720): "the indebtedness discharged is
    # qualified principal residence indebtedness which is discharged before
    # January 1, 2026"
    is_principal_residence_debt: bool = False
    # Whether this is a qualifying student loan discharge — such as for
    # working in certain public service professions, NHSC loan repayment,
    # or state loan repayment programs. These are excluded from income.
    # IRC §108(f)(1) (title26.md:86900): "gross income does not include any
    # amount which... would be includible in gross income by reason of the
    # discharge... of any student loan if such discharge was pursuant to a
    # provision of such loan under which all or part of the indebtedness...
    # would be discharged if the individual worked for a certain period of
    # time in certain professions"
    is_student_loan_qualifying: bool = False
    # The amount by which your total debts exceeded the fair market value of
    # your total assets immediately before the debt was cancelled. Cancelled
    # debt is excluded from income to the extent you were insolvent.
    # IRC §108(a)(1)(B) (title26.md:86710): "the discharge occurs when the
    # taxpayer is insolvent"
    # IRC §108(a)(3) (title26.md:86740): "the amount excluded... shall not
    # exceed the amount by which the taxpayer is insolvent"
    taxpayer_insolvent_amount: float = 0.0
    # Whether the debt was discharged as part of a Title 11 bankruptcy case.
    # Debt cancelled in bankruptcy is fully excluded from income.
    # IRC §108(a)(1)(A) (title26.md:86708): "the discharge occurs in a
    # title 11 case"
    is_bankruptcy: bool = False


@dataclass
class QualifiedBusinessIncome:
    """Qualified business income for §199A deduction.

    IRC §199A (title26.md:146337) — QBI deduction up to 20%.
    """

    # The name of the business generating the qualified business income.
    # IRC §199A(b)(2) (title26.md:146370): "20 percent of the taxpayer's
    # qualified business income with respect to the qualified trade or business"
    business_name: str
    # Your share of the net income from a qualified trade or business. This
    # is eligible for a deduction of up to 20% — a major tax break for
    # pass-through business owners (sole proprietors, partnerships, S-Corps).
    # IRC §199A(a) (title26.md:146337): "there shall be allowed as a
    # deduction... an amount equal to the lesser of the combined qualified
    # business income amount... or 20 percent of the excess... of the taxable
    # income... over the net capital gain"
    qualified_business_income: float = 0.0
    # Total W-2 wages the business paid to its employees during the year.
    # For high-income taxpayers, the QBI deduction is limited by a formula
    # that considers wages paid: 50% of W-2 wages, or 25% of wages + 2.5%
    # of qualified property basis.
    # IRC §199A(b)(2)(B) (title26.md:146380): "the greater of 50 percent
    # of the W-2 wages... or the sum of 25 percent of the W-2 wages... plus
    # 2.5 percent of the unadjusted basis... of all qualified property"
    w2_wages_paid: float = 0.0
    # The unadjusted basis (original cost) of depreciable business property
    # still within its recovery period. Used in the alternative wage/property
    # limitation for the QBI deduction at higher incomes.
    # IRC §199A(b)(6) (title26.md:146460): "the term qualified property
    # means, with respect to any qualified trade or business for a taxable
    # year, tangible property of a character subject to the allowance for
    # depreciation under section 167"
    qualified_property_basis: float = 0.0
    # Whether this is a "specified service trade or business" — including
    # health, law, accounting, consulting, athletics, financial services, or
    # any business where the principal asset is the reputation or skill of
    # employees. Above the income threshold, the QBI deduction for these
    # businesses phases out entirely.
    # IRC §199A(d)(2) (title26.md:146440): "the term 'specified service trade
    # or business' means any trade or business involving the performance of
    # services in the fields of health, law, engineering, architecture,
    # accounting, actuarial science, performing arts, consulting, athletics,
    # financial services, brokerage services"
    is_specified_service_business: bool = False
    # Qualified REIT dividends you received. These get their own 20% QBI
    # deduction regardless of the W-2 wage limitation.
    # IRC §199A(b)(1)(B) (title26.md:146361): "20 percent of the aggregate
    # amount of the qualified REIT dividends and qualified publicly traded
    # partnership income"
    reit_dividends: float = 0.0
    # Your share of income from a publicly traded partnership (PTP). Like
    # REIT dividends, PTP income gets a 20% QBI deduction without the W-2
    # wage limitation.
    # IRC §199A(b)(1)(B) (title26.md:146361): "qualified publicly traded
    # partnership income of the taxpayer for the taxable year"
    ptp_income: float = 0.0


@dataclass
class K1Income:
    """Schedule K-1 income from partnerships, S-Corps, or estates/trusts.

    IRC §702/§704 (title26.md:283000) — partnership distributive share.
    IRC §1366 — S-Corp income passthrough.
    IRC §652/§662 (title26.md:283395) — estate/trust income.
    """

    # The legal name of the partnership, S-Corp, or trust that issued the K-1.
    # Form 1065 / 1120-S / 1041 Schedule K-1, Box A.
    entity_name: str
    # The entity's federal Employer Identification Number (EIN), shown on
    # Schedule K-1, Box B.
    # Form K-1, Box B; IRC §6109 (title26.md:525311).
    entity_ein: str = ""
    # The type of entity that issued the K-1 — partnership (Form 1065),
    # S-Corporation (Form 1120-S), or estate/trust (Form 1041).
    # IRC §702 (title26.md:283000): partnership income;
    # IRC §1366 (title26.md:370392): S-Corp income;
    # IRC §652 (title26.md:278228): trust/estate income.
    entity_type: K1EntityType = K1EntityType.PARTNERSHIP
    # Your share of the entity's ordinary business income or loss (K-1,
    # Box 1 for partnerships/S-Corps). This is the main profit or loss
    # figure from the business operations.
    # IRC §702(a)(8) (title26.md:283000): "each partner shall take into
    # account separately... the partner's distributive share of the
    # partnership's taxable income or loss"
    ordinary_business_income: float = 0.0
    # Your share of net rental real estate income or loss from the entity
    # (K-1, Box 2). Reported on your Schedule E, Part II.
    # IRC §702(a)(8) (title26.md:283000): partner's distributive share.
    net_rental_income: float = 0.0
    # Your share of interest income earned by the entity (K-1, Box 5).
    # Flows to your Schedule B.
    # IRC §702(a)(4) (title26.md:283000): "gains and losses from sales or
    # exchanges of capital assets... dividends... and interest income"
    interest_income: float = 0.0
    # Your share of ordinary dividends earned by the entity (K-1, Box 6a).
    # Flows to your Schedule B.
    # IRC §702(a)(4) (title26.md:283000): partner's share of dividends.
    ordinary_dividends: float = 0.0
    # Your share of qualified dividends earned by the entity (K-1, Box 6b).
    # These are taxed at the lower long-term capital gains rate.
    # IRC §1(h)(11) (title26.md:5895): "qualified dividend income shall be
    # treated as adjusted net capital gain"
    qualified_dividends: float = 0.0
    # Your share of net short-term capital gains or losses from the entity
    # (K-1, Box 8). Combined with your other short-term gains/losses on
    # Schedule D.
    # IRC §702(a)(1) (title26.md:283000): "gains and losses from sales or
    # exchanges of capital assets held for not more than 1 year"
    net_short_term_capital_gain: float = 0.0
    # Your share of net long-term capital gains or losses from the entity
    # (K-1, Box 9a). Combined with your other long-term gains/losses on
    # Schedule D.
    # IRC §702(a)(2) (title26.md:283000): "gains and losses from sales or
    # exchanges of capital assets held for more than 1 year"
    net_long_term_capital_gain: float = 0.0
    # Your share of net Section 1231 gain or loss from the entity (K-1,
    # Box 10). Section 1231 gains from business property held over a year
    # are generally treated as long-term capital gains.
    # IRC §1231(a) (title26.md:352018): "the section 1231 gains... shall be
    # treated as long-term capital gains"
    net_section_1231_gain: float = 0.0
    # Your share of any other income items from the entity not reported in
    # the specific boxes above (K-1, Box 11 or other code items).
    # IRC §702(a)(8) (title26.md:283000): partner's distributive share of
    # the partnership's taxable income or loss.
    other_income: float = 0.0
    # Your share of the entity's Section 179 expense deduction — the
    # immediate write-off for business equipment purchases (K-1, Box 12).
    # IRC §179(a) (title26.md:141033): "A taxpayer may elect to treat the
    # cost of any section 179 property as an expense... and not as a
    # capital expenditure"
    section_179_deduction: float = 0.0
    # Fixed payments to a partner for services or capital use, regardless
    # of partnership profit. Guaranteed payments are always subject to
    # self-employment tax. Partnerships only (K-1, Box 4).
    # IRC §707(c) (title26.md:284243): "payments to a partner for services
    # or the use of capital shall be considered as made to one who is not
    # a member of the partnership... to the extent such payments are
    # determined without regard to the income of the partnership"
    guaranteed_payments: float = 0.0
    # Your net earnings from the entity that are subject to self-employment
    # tax. For partnerships, this includes your share of ordinary income
    # plus guaranteed payments.
    # IRC §1402(a) (title26.md:378900): "net earnings from self-employment
    # means the gross income derived by an individual from any trade or
    # business carried on by such individual"
    self_employment_earnings: float = 0.0
    # Your share of income taxes the entity paid to foreign countries
    # (K-1, Box 16). You may claim these as a foreign tax credit.
    # IRC §901(a) (title26.md:319129): "the tax imposed by this chapter shall
    # be credited with the amounts... of taxes paid or accrued... to any
    # foreign country"
    foreign_taxes_paid: float = 0.0
    # Your share of tax-exempt income earned by the entity (K-1, Box 18).
    # Not taxable, but increases your basis in the entity.
    # IRC §103(a) (title26.md:83090): "gross income does not include interest
    # on any State or local bond"
    tax_exempt_income: float = 0.0
    # Cash and property distributions you received from the entity (K-1,
    # Box 19). Distributions are generally not taxable until they exceed
    # your basis in the entity.
    # IRC §731(a) (title26.md:285050): "gain shall not be recognized to such
    # partner, except to the extent that any money distributed exceeds the
    # adjusted basis of such partner's interest"
    distributions: float = 0.0
    # Your share of qualified business income from the entity for the §199A
    # deduction (K-1, Box 20, Code Z).
    # IRC §199A(c)(1) (title26.md:146337): "for purposes of this section,
    # for any taxable year, the net amount of qualified items of income,
    # gain, deduction, and loss with respect to any qualified trade or
    # business of the taxpayer"
    qualified_business_income: float = 0.0
    # W-2 wages paid by the entity, used for the §199A wage limitation
    # (K-1, Box 20, Code Z attachment).
    # IRC §199A(b)(4) (title26.md:146337): "the amounts described in
    # paragraphs (3) and (8) of section 6051(a) paid by such person with
    # respect to employment of employees"
    w2_wages: float = 0.0
    # Unadjusted basis of qualified property held by the entity, used for
    # the §199A property limitation (K-1, Box 20, Code Z attachment).
    # IRC §199A(b)(6) (title26.md:146460): "the term qualified property
    # means, with respect to any qualified trade or business for a taxable
    # year, tangible property of a character subject to the allowance for
    # depreciation under section 167"
    qualified_property_basis: float = 0.0
    # Whether the entity's trade or business is a specified service business,
    # which limits or eliminates the §199A deduction at higher incomes.
    # IRC §199A(d)(2) (title26.md:146440): "specified service trade or
    # business means any trade or business involving the performance of
    # services in the fields of health, law, accounting, consulting..."
    is_specified_service_business: bool = False


@dataclass
class RoyaltyIncome:
    """Royalty income reported on Schedule E Part I.

    IRC §61(a)(6) (title26.md:70865) — royalties included in gross income.
    IRC §62(a)(4) (title26.md:71305) — above-the-line deductions for royalties.
    """

    # A brief description of the type of royalty — e.g. oil/gas, book,
    # patent, music. Schedule E, Part I — description of property.
    # IRC §61(a)(6) (title26.md:70846): "gross income means all income from
    # whatever source derived, including but not limited to... Royalties"
    description: str
    # The name of the company, publisher, or person paying you royalties.
    # Shown on Form 1099-MISC, Box 2 or payer's name field.
    # Form 1099-MISC, Box 2; IRC §6041 (title26.md:506653).
    payer_name: str = ""
    # The total royalty payments you received during the year before
    # subtracting any expenses. Reported on Schedule E, Part I.
    # IRC §61(a)(6) (title26.md:70865): "gross income means all income from
    # whatever source derived, including... Royalties"
    gross_royalties: float = 0.0
    # Expenses related to earning the royalty income, such as depletion
    # (for oil/gas/mining), depreciation, or production costs.
    # IRC §611(a) (title26.md:272949): "In the case of mines, oil and gas
    # wells... there shall be allowed as a deduction... a reasonable allowance
    # for depletion"
    expenses: float = 0.0
    # Whether this royalty income is subject to self-employment tax. Generally,
    # royalties are passive and not subject to SE tax, but royalties from a
    # trade or business in which you materially participate may be.
    # IRC §1402(a) (title26.md:378900): "the term 'net earnings from
    # self-employment' means the gross income derived by an individual from
    # any trade or business carried on by such individual"
    is_subject_to_se_tax: bool = False


@dataclass
class FarmIncome:
    """Farm income reported on Schedule F.

    IRC §162 (title26.md:114102) — trade or business expenses.
    IRC §1401 (title26.md:377596) — self-employment tax.
    IRC §172(b)(1)(B) (title26.md:137742) — farm NOL 2-year carryback.
    """

    # The name of your farm or ranch operation (Schedule F, Line A).
    # Form 1040 Schedule F, Line A; IRC §162(a) (title26.md:114102).
    farm_name: str
    # The primary crop or livestock you produce — e.g. "corn", "cattle",
    # "soybeans", "poultry" (Schedule F, Line B).
    # Form 1040 Schedule F, Line B; IRS Instructions for Schedule F.
    principal_product: str = ""
    # Total income from selling livestock, produce, grains, and other farm
    # products you raised, plus any commodity credit loans and agricultural
    # program payments (Schedule F, Lines 1-4 combined).
    # IRC §61(a)(2) (title26.md:70857): "Gross income derived from business"
    gross_farm_income: float = 0.0
    # Cost of livestock or other items you purchased for resale (not raised)
    # and sold during the year (Schedule F, Line 2).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses
    # paid or incurred during the taxable year in carrying on any trade or business"
    cost_of_livestock_purchased: float = 0.0
    # Expenses for soil and water conservation on farmland, including
    # terracing, contour farming, and waterway construction. Deductible up
    # to 25% of gross farm income (Schedule F, Line 12).
    # IRC §175(a) (title26.md:140200): "A taxpayer engaged in the business
    # of farming may treat expenditures which are paid or incurred by him
    # during the taxable year for the purpose of soil or water conservation"
    conservation_expenses: float = 0.0
    # Amounts paid to others for custom hire of machines or equipment to
    # perform farm work — such as custom harvesting, baling, or spraying
    # (Schedule F, Line 13).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    custom_hire: float = 0.0
    # Cost of feed for your livestock during the year (Schedule F, Line 14).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    feed: float = 0.0
    # Cost of fertilizers and lime applied to your farmland during the year
    # (Schedule F, Line 15).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    fertilizers: float = 0.0
    # Shipping and trucking costs for hauling your farm products to market,
    # or transporting supplies to the farm (Schedule F, Line 16).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    freight: float = 0.0
    # Cost of gasoline, diesel, and other fuels used for farming operations,
    # including fuel for tractors, trucks, and irrigation pumps
    # (Schedule F, Line 17).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    gasoline_fuel: float = 0.0
    # Wages and salaries paid to farm employees (not to yourself). Does not
    # include amounts paid to independent contractors (Schedule F, Line 18).
    # IRC §162(a)(1) (title26.md:114108): "a reasonable allowance for salaries
    # or other compensation for personal services actually rendered"
    labor_hired: float = 0.0
    # Contributions to pension, profit-sharing, or retirement plans for your
    # farm employees (Schedule F, Line 19).
    # IRC §404(a) (title26.md:198645): "contributions paid by an employer
    # to... a pension trust... shall be allowed as a deduction"
    pension_plans: float = 0.0
    # Rent or lease payments for farmland used in your farming operation
    # (Schedule F, Line 20a).
    # IRC §162(a)(3) (title26.md:114116): "rentals or other payments required
    # to be made as a condition to the continued use or possession... of
    # property to which the taxpayer has not taken or is not taking title"
    rent_lease_land: float = 0.0
    # Rent or lease payments for machinery, equipment, and vehicles used in
    # farming (Schedule F, Line 20b).
    # IRC §162(a)(3) (title26.md:114116): "rentals or other payments"
    rent_lease_equipment: float = 0.0
    # Cost of seeds and plants purchased for planting during the year
    # (Schedule F, Line 21).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    seeds_plants: float = 0.0
    # Cost of storing crops, grain, or other farm products in warehouses or
    # grain elevators (Schedule F, Line 22).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    storage: float = 0.0
    # Cost of supplies consumed in your farming operation — such as tools,
    # fencing materials, veterinary supplies, and small equipment items
    # (Schedule F, Line 23).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    supplies: float = 0.0
    # State, local, and real property taxes paid on farm property and farm
    # operations (Schedule F, Line 24). Does not include self-employment tax.
    # IRC §164(a) (title26.md:119300): "the following taxes shall be allowed
    # as a deduction for the taxable year within which paid or accrued"
    taxes: float = 0.0
    # Cost of electricity, gas, water, phone, and internet for the farm
    # (Schedule F, Line 25).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    utilities: float = 0.0
    # Veterinary, breeding, and medicine expenses for your livestock
    # (Schedule F, Line 26).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    vet_fees: float = 0.0
    # Any other ordinary and necessary farm expenses not listed above. You
    # must list these on a separate statement (Schedule F, Line 27).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses
    # paid or incurred during the taxable year in carrying on any trade or business"
    other_expenses: float = 0.0
    # Depreciation and Section 179 expense deduction for farm buildings,
    # equipment, and vehicles (Schedule F, Line 14 of Form 4562).
    # IRC §167(a) (title26.md:121827): "There shall be allowed as a depreciation
    # deduction a reasonable allowance for the exhaustion, wear and tear...
    # of property used in the trade or business"
    depreciation: float = 0.0
    # Business-related vehicle expenses for farm trucks and cars — either
    # actual costs or the standard mileage rate (Schedule F, Line 10).
    # IRC §162(a)(2) (title26.md:114110): "traveling expenses... while away
    # from home in the pursuit of a trade or business"
    car_and_truck: float = 0.0
    # Premiums for farm insurance — property, liability, crop insurance,
    # and worker's compensation (Schedule F, Line 11).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    insurance: float = 0.0
    # Interest paid on a mortgage for farm property — land, buildings, and
    # improvements (Schedule F, Line 18a).
    # IRC §163(a) (title26.md:116508): "There shall be allowed as a deduction
    # all interest paid or accrued within the taxable year on indebtedness"
    interest_mortgage: float = 0.0
    # Interest on other farm debts — equipment loans, operating lines of
    # credit, and other farm financing (Schedule F, Line 18b).
    # IRC §163(a) (title26.md:116508): "There shall be allowed as a deduction
    # all interest paid or accrued within the taxable year on indebtedness"
    interest_other: float = 0.0
    # Costs to fix or maintain farm buildings, fences, equipment, and
    # machinery — restoring them to their original condition, not
    # improvements that add value (Schedule F, Line 19).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary expenses"
    repairs_maintenance: float = 0.0
    # Crop insurance proceeds or federal crop disaster payments received
    # during the year (Schedule F, Lines 6a-6d).
    # IRC §451(d) (title26.md:238288): election to defer crop insurance
    # proceeds to the following year in certain circumstances.
    crop_insurance_proceeds: float = 0.0
    # Commodity Credit Corporation (CCC) loans reported as income. Farmers
    # may elect to report CCC loan proceeds as income in the year received
    # (Schedule F, Line 5a).
    # IRC §77(a) (title26.md:78902): "Amounts received as loans from the
    # Commodity Credit Corporation shall, at the election of the taxpayer,
    # be considered as income"
    ccc_loans_reported_as_income: float = 0.0
    # Whether you materially participated in the farming operation. If not,
    # losses may be limited under the passive activity rules. Also determines
    # SE tax treatment — material participants owe SE tax on farm income.
    # IRC §469(h)(1) (title26.md:249250): "A taxpayer shall be treated as
    # materially participating in an activity only if the taxpayer is involved
    # in the operations of the activity on a basis which is regular,
    # continuous, and substantial"
    is_material_participant: bool = True


@dataclass
class AnnuityIncome:
    """Annuity income (non-retirement-plan).

    IRC §72 (title26.md:74051) — annuity taxation.
    IRC §72(b) — exclusion ratio.
    IRC §72(d)(1) — simplified method for employer plans.
    """

    # The name of the insurance company or financial institution making
    # the annuity payments. Shown on Form 1099-R, Payer's name.
    # Form 1099-R, Payer's name; IRC §72(a) (title26.md:74051).
    payer_name: str
    # The type of annuity contract — "commercial" for annuities purchased
    # from an insurance company, or "employer_plan" for pension/employer
    # annuities eligible for the simplified method.
    # IRC §72(d)(1) (title26.md:74210): "In the case of any amount received as an annuity
    # amounts received as an annuity under... a qualified employer plan"
    contract_type: str = ""
    # The total annuity payment you received this year (before taxes).
    # A portion of each payment is a tax-free return of your own money
    # (your "investment in the contract"); the rest is taxable.
    # IRC §72(a)(1) (title26.md:74051): "gross income includes any amount
    # received as an annuity... under an annuity, endowment, or life
    # insurance contract"
    gross_payment: float = 0.0
    # Your after-tax investment in the annuity contract — the total amount
    # you paid using money that was already taxed. This is recovered
    # tax-free over the life of the annuity.
    # IRC §72(c)(1)(A) (title26.md:74051): "the aggregate amount of premiums
    # or other consideration paid for the contract, minus the aggregate amount
    # received under the contract before the annuity starting date, to the
    # extent that such amount was excludable from gross income"
    investment_in_contract: float = 0.0
    # The total expected return from the annuity, used with the exclusion
    # ratio method to calculate the tax-free portion of each payment.
    # Exclusion ratio = investment / expected return.
    # IRC §72(b)(1) (title26.md:74080): "Gross income does not include that
    # part of any amount received as an annuity... which bears the same ratio
    # to such amount as the investment in the contract... bears to the
    # expected return under the contract"
    expected_return: float = 0.0
    # The cumulative amount of your investment already recovered tax-free
    # in prior years. Once you've recovered your full investment, all
    # remaining payments are fully taxable.
    # IRC §72(b)(2) (title26.md:74090): "if the annuitant dies before the
    # entire investment... is recovered... the amount of such... unrecovered
    # investment... shall be allowed as a deduction"
    amount_previously_recovered: float = 0.0
    # Whether to use the IRS Simplified Method (for employer-plan annuities)
    # instead of the general exclusion ratio. The simplified method divides
    # your investment by a fixed number of anticipated payments based on age.
    # IRC §72(d)(1)(A) (title26.md:74210): "In the case of any amount
    # received as an annuity under a qualified employer retirement plan,
    # paragraph 2 of subsection (b) shall be applied by determining the
    # investment in the contract by using the simplified method"
    use_simplified_method: bool = False
    # Your age when annuity payments began. Used with the simplified method
    # to look up the number of anticipated payments: age ≤55→360, 56-60→310,
    # 61-65→260, 66-70→210, 71+→160.
    # IRC §72(d)(1)(B)(iv) (title26.md:74220): table of anticipated payments
    # by age at the annuity starting date.
    annuitant_age_at_start: int = 0
    # Federal income tax withheld from your annuity payments during the year.
    # Shown on Form 1099-R, Box 4.
    # IRC §31(a) (title26.md:22615): "The amount withheld as tax... shall be
    # allowed to the recipient of the income as a credit against the tax"
    federal_income_tax_withheld: float = 0.0


@dataclass
class ScholarshipIncome:
    """Scholarship and fellowship income.

    IRC §117 (title26.md:89656) — qualified scholarships excluded.
    Amounts for room/board or services rendered are taxable.
    """

    # The name of the college, university, or educational institution that
    # awarded the scholarship or fellowship.
    # Form 1098-T; IRC §117(a) (title26.md:89656).
    institution_name: str
    # The total amount of the scholarship or fellowship grant you received,
    # including both qualified (tax-free) and non-qualified (taxable) portions.
    # IRC §117(a) (title26.md:89656): "Gross income does not include any
    # amount received as a qualified scholarship by an individual who is a
    # candidate for a degree"
    total_scholarship: float = 0.0
    # The portion of your scholarship used for tuition and required fees,
    # books, supplies, and equipment. This part is excluded from income.
    # IRC §117(b)(2) (title26.md:89680): "the term 'qualified tuition and
    # related expenses' means tuition and fees required for the enrollment
    # or attendance of a student at an educational organization"
    qualified_tuition_and_fees: float = 0.0
    # Scholarship money used for room and board (housing and meals). This
    # portion does NOT qualify for the exclusion and is taxable income.
    # IRC §117(b) (title26.md:89670): only "qualified tuition and related
    # expenses" are excluded; room, board, and personal expenses are not.
    room_board_stipend: float = 0.0
    # Payments received for teaching, research, or other services required
    # as a condition of the scholarship. These are taxable as compensation.
    # IRC §117(c) (title26.md:89700): "Subsection (a) shall not exclude from
    # gross income any amount received... which represents payment for
    # teaching, research, or other services"
    service_compensation: float = 0.0


@dataclass
class GamblingIncome:
    """Gambling/wagering income and losses.

    IRC §61 (title26.md:70846) — winnings are gross income.
    IRC §165(d) (title26.md:120131) — losses limited to 90%, capped at gains.
    """

    # Gambling winnings reported on Form W-2G. Casinos and other payers must
    # issue a W-2G for certain types of winnings above reporting thresholds
    # (e.g. slot machine jackpots of $1,200+, poker tournaments of $5,000+).
    # IRC §61(a) (title26.md:70846): "gross income means all income from
    # whatever source derived"
    w2g_winnings: float = 0.0
    # Other gambling winnings not reported on a W-2G — such as casino table
    # games, lottery tickets, or sports bets below reporting thresholds.
    # You are still required to report all gambling income.
    # IRC §61(a) (title26.md:70846): "gross income means all income from
    # whatever source derived"
    other_winnings: float = 0.0
    # Federal income tax withheld from your gambling winnings, as shown on
    # Form W-2G, Box 4 (typically 24% for reportable winnings).
    # IRC §31(a) (title26.md:22615): "The amount withheld as tax... shall
    # be allowed to the recipient of the income as a credit"
    federal_income_tax_withheld: float = 0.0
    # Your total gambling losses for the year. Losses are only deductible
    # if you itemize, and only up to the amount of your gambling winnings.
    # You cannot deduct more in losses than you won.
    # IRC §165(d) (title26.md:120200): "Losses from wagering transactions
    # shall be allowed only to the extent of the gains from such transactions"
    losses: float = 0.0


@dataclass
class CasualtyLossEvent:
    """Individual casualty/disaster loss event.

    IRC §165(c)(3) (title26.md:120131) — casualty losses.
    IRC §165(h)(1) — $500 per-event floor.
    IRC §165(h)(2) — 10% AGI threshold.
    IRC §165(h)(5) — disaster-only limitation (post-2017).
    """

    # A brief description of the casualty event — e.g. "Hurricane damage to
    # home", "Wildfire destroyed garage", "Tornado damage to vehicle".
    # IRC §165(c)(3) (title26.md:120155): "losses of property not connected
    # with a trade or business... if such losses arise from fire, storm,
    # shipwreck, or other casualty, or from theft"
    description: str
    # The FEMA disaster declaration number (e.g. "DR-4999"). After 2017,
    # personal casualty losses are only deductible if the loss is attributable
    # to a federally declared disaster.
    # IRC §165(h)(5) (title26.md:120250): "any personal casualty loss shall
    # be allowed... for any taxable year only to the extent that such loss
    # is attributable to a Federally declared disaster"
    fema_disaster_declaration_number: str = ""
    # The date the casualty event occurred (YYYY-MM-DD format).
    # IRC §165(a) (title26.md:120131): "There shall be allowed as a deduction
    # any loss sustained during the taxable year and not compensated for
    # by insurance or otherwise"
    date_of_loss: str = ""
    # The type of property damaged or destroyed — e.g. "main home",
    # "personal vehicle", "household contents".
    # Form 4684; IRC §165(c)(3) (title26.md:120155).
    property_type: str = ""
    # The fair market value of the property immediately before the casualty.
    # The loss is the lesser of (FMV before − FMV after) or the adjusted
    # basis, minus any reimbursements.
    # IRC §165(b) (title26.md:120140): "the basis for determining the amount
    # of the deduction for any loss shall be the adjusted basis provided in
    # section 1011"
    fair_market_value_before: float = 0.0
    # The fair market value of the property immediately after the casualty.
    # The decline in value (before minus after) measures the economic loss.
    # IRC §165(b) (title26.md:120140): "the adjusted basis provided in
    # section 1011 for determining the loss from the sale or other
    # disposition of property"
    fair_market_value_after: float = 0.0
    # Your adjusted basis in the property — generally what you paid for it
    # plus improvements, minus depreciation. The deductible loss cannot
    # exceed your basis.
    # IRC §1011(a) (title26.md:339650): "The adjusted basis for determining
    # the gain or loss from the sale or other disposition of property...
    # shall be the basis (determined under section 1012... ), adjusted as
    # provided in section 1016"
    adjusted_basis: float = 0.0
    # The amount you received (or expect to receive) from your insurance
    # company for the loss. Subtracted from the loss before the $500 floor
    # and 10% AGI threshold are applied.
    # IRC §165(a) (title26.md:120131): "any loss sustained during the taxable
    # year and not compensated for by insurance or otherwise"
    insurance_reimbursement: float = 0.0
    # Any other reimbursement you received for the loss — such as from
    # FEMA disaster relief, employer assistance, or a lawsuit settlement.
    # IRC §165(a) (title26.md:120131): "any loss sustained during the taxable
    # year and not compensated for by insurance or otherwise"
    other_reimbursement: float = 0.0


@dataclass
class RestrictedStockEvent:
    """Restricted stock / §83(b) compensation event.

    IRC §83 (title26.md:79675) — property transferred for services.
    IRC §83(b) — election to include at grant date.
    """

    # A brief description of the equity award — e.g. "RSU vesting from
    # TechCo" or "Restricted stock grant with §83(b) election".
    # IRC §83(a) (title26.md:79675): "the excess of... the fair market value
    # of such property... over the amount (if any) paid for such property,
    # shall be included in the gross income"
    description: str
    # The date you were originally granted the restricted stock or RSUs
    # (YYYY-MM-DD format). Relevant for §83(b) elections.
    # IRC §83(b) (title26.md:79698): "any person who performs services...
    # may elect to include in gross income... the excess... of the fair
    # market value... at the time of such transfer"
    grant_date: str = ""
    # The date the stock vested (restrictions lapsed) and you gained full
    # ownership (YYYY-MM-DD format). This is when tax is owed unless you
    # made a §83(b) election at grant time.
    # IRC §83(a) (title26.md:79675): "at the first time the rights of the
    # person having the beneficial interest in such property are transferable
    # or are not subject to a substantial risk of forfeiture"
    vesting_date: str = ""
    # The fair market value per share on the date the stock vested. The
    # taxable income is (FMV at vesting × shares) minus what you paid.
    # IRC §83(a) (title26.md:79675): "the excess of the fair market value
    # of such property... over the amount (if any) paid for such property,
    # shall be included in the gross income"
    fmv_at_vesting: float = 0.0
    # The total amount you paid for the shares (often $0 for RSUs, or a
    # small exercise price for restricted stock). Subtracted from FMV to
    # determine taxable compensation.
    # IRC §83(a) (title26.md:79675): "the excess of... the fair market value
    # ... over the amount (if any) paid for such property"
    amount_paid: float = 0.0
    # Whether you filed a Section 83(b) election within 30 days of receiving
    # the stock to be taxed on the grant-date value instead of waiting for
    # vesting. This locks in a lower value if the stock appreciates, but you
    # get no deduction if you forfeit the shares later.
    # IRC §83(b) (title26.md:79698): "any person who performs services... may
    # elect to include in gross income... the excess of the fair market value
    # of the property at the time of transfer over the amount (if any) paid"
    section_83b_election: bool = False
    # The fair market value per share on the grant date. Only needed if you
    # made a §83(b) election — this is the value used to compute income
    # instead of the vesting-date value.
    # IRC §83(b) (title26.md:79698): "the fair market value of the property
    # at the time of transfer"
    fmv_at_grant: float = 0.0
    # The number of shares that vested (or were granted if §83(b)). Multiplied
    # by the per-share FMV to determine total compensation income.
    # IRC §83(a) (title26.md:79675).
    shares: int = 0


@dataclass
class LikeKindExchange:
    """Like-kind exchange of real property.

    IRC §1031 (title26.md:342673) — gain deferral on like-kind exchanges.
    Limited to real property only since TCJA 2017.
    """

    # A description of the property you gave up in the exchange — e.g.
    # "Commercial building at 456 Elm St". Must be real property held for
    # business or investment.
    # IRC §1031(a)(1) (title26.md:342673): "No gain or loss shall be
    # recognized on the exchange of real property held for productive use
    # in a trade or business or for investment"
    property_relinquished_description: str
    # A description of the replacement property you received in the exchange.
    # Must be real property of "like kind" — broadly, any real estate for
    # any other real estate.
    # IRC §1031(a)(1) (title26.md:342673): "if such real property is exchanged
    # solely for real property of like kind which is to be held either for
    # productive use in a trade or business or for investment"
    property_received_description: str = ""
    # The date you transferred (gave up) the relinquished property
    # (YYYY-MM-DD format). You must identify the replacement property
    # within 45 days of this date.
    # IRC §1031(a)(3)(A) (title26.md:342700): "such property is... identified
    # as property to be received in the exchange on or before the day which
    # is 45 days after the date on which the taxpayer transfers the property"
    date_relinquished: str = ""
    # The date you received the replacement property (YYYY-MM-DD format).
    # Must be within 180 days of the transfer date (or your tax return
    # due date, whichever is earlier).
    # IRC §1031(a)(3)(B) (title26.md:342699): "such property is received...
    # not later than... 180 days after the date on which the taxpayer
    # transfers the property relinquished"
    date_received: str = ""
    # The fair market value of the property you gave up at the time of
    # the exchange.
    # IRC §1031(d) (title26.md:342750): basis of property acquired in
    # like-kind exchange.
    fmv_relinquished: float = 0.0
    # Your adjusted basis in the property you gave up — generally what you
    # paid for it plus improvements minus depreciation.
    # IRC §1011(a) (title26.md:339650): "the adjusted basis for determining
    # the gain or loss"
    adjusted_basis_relinquished: float = 0.0
    # The fair market value of the replacement property you received in
    # the exchange.
    # IRC §1031(d) (title26.md:342750): basis of property acquired.
    fmv_received: float = 0.0
    # Cash or non-like-kind property ("boot") you received in the exchange.
    # Any boot received triggers immediate gain recognition up to the amount
    # of boot received.
    # IRC §1031(b) (title26.md:342715): "the gain, if any, to the recipient
    # shall be recognized, but in an amount not in excess of the sum of such
    # money and the fair market value of such other property"
    boot_received: float = 0.0
    # Cash or non-like-kind property you paid as part of the exchange (to
    # equalize values). Boot paid increases your basis in the replacement
    # property.
    # IRC §1031(d) (title26.md:342750): basis adjustments for boot.
    boot_paid: float = 0.0
    # The amount of debt (e.g. mortgage) on the relinquished property that
    # the buyer assumed or that was paid off at closing. Treated as boot
    # received.
    # IRC §1031(d) (title26.md:342750): "liabilities assumed treated as
    # money received"
    liabilities_relieved: float = 0.0
    # The amount of debt on the replacement property that you assumed.
    # Treated as boot paid, offsetting liabilities relieved.
    # IRC §1031(d) (title26.md:342750): liabilities assumed offset.
    liabilities_assumed: float = 0.0
    # Whether the exchange is between related parties (family members or
    # controlled entities). If either party disposes of the property within
    # 2 years, the tax-free treatment is revoked.
    # IRC §1031(f)(1) (title26.md:342780): "If... any related person disposes
    # of any property... before the date 2 years after the date of the last
    # transfer which was part of such exchange... no nonrecognition... shall
    # apply to such exchange"
    is_related_party: bool = False


@dataclass
class Section529Distribution:
    """Section 529 qualified tuition program distribution.

    IRC §529 (title26.md:263347) — tax-free distributions for qualified expenses.
    10% penalty on earnings portion of non-qualified distributions.
    """

    # The name of the 529 qualified tuition savings plan.
    # IRC §529(b)(1) (title26.md:263360): "a program established and
    # maintained by a State or agency or instrumentality thereof"
    plan_name: str
    # The name of the person for whose education the funds were distributed.
    # IRC §529(e)(1) (title26.md:263500): "the term 'designated beneficiary'
    # means the individual designated at the commencement of participation"
    beneficiary_name: str = ""
    # The Social Security Number of the beneficiary.
    # IRC §529 — identification requirements for 529 beneficiaries.
    beneficiary_ssn: str = ""
    # The total amount withdrawn from the 529 plan during the year.
    # Qualified withdrawals for education expenses are tax-free; non-qualified
    # withdrawals are taxable (on the earnings portion) plus a 10% penalty.
    # IRC §529(c)(3)(A) (title26.md:263420): "Distributions shall be
    # includible in the gross income of the distributee"
    gross_distribution: float = 0.0
    # The portion of the distribution that represents investment earnings
    # (as opposed to your original contributions). Only the earnings portion
    # of non-qualified distributions is taxable.
    # IRC §529(c)(3)(A) (title26.md:263420): earnings portion taxable on
    # non-qualified distributions.
    earnings_portion: float = 0.0
    # The amount of qualified higher education expenses the beneficiary
    # incurred — tuition, fees, books, supplies, equipment, room and board
    # (if at least half-time), and computer equipment.
    # IRC §529(e)(3) (title26.md:263520): "the term 'qualified higher
    # education expenses' means tuition, fees, books, supplies, and equipment
    # required for the enrollment or attendance of a designated beneficiary
    # at an eligible educational institution"
    qualified_education_expenses: float = 0.0
    # Whether this distribution was used for K-12 (elementary or secondary
    # school) tuition. Capped at $10,000 per year per beneficiary.
    # IRC §529(c)(7) (title26.md:263560): "expenses for tuition in connection
    # with enrollment or attendance at an elementary or secondary public,
    # private, or religious school... shall not exceed $10,000"
    is_k12_tuition: bool = False
    # Amount used to repay qualified student loans of the beneficiary or their
    # sibling. Subject to a $10,000 lifetime cap per individual.
    # IRC §529(c)(9) (title26.md:263580): "any reference to qualified higher
    # education expenses shall include a reference to amounts paid as
    # principal or interest on any qualified education loan... which shall
    # not exceed $10,000"
    student_loan_repayment: float = 0.0
    # Amount rolled over from the 529 plan to a Roth IRA for the beneficiary.
    # The 529 account must have been open for 15+ years and the rollover is
    # subject to annual IRA contribution limits and a $35,000 lifetime cap.
    # IRC §529(c)(3)(C)(iv) (title26.md:263450): rollover to Roth IRA
    # provisions; "aggregate amount... shall not exceed $35,000"
    rollover_to_roth: float = 0.0


@dataclass
class SavingsBondEducationExclusion:
    """U.S. Savings Bond education interest exclusion.

    IRC §135 (title26.md:96620) — Series EE/I bond interest exclusion.
    Subject to MAGI phase-out.
    """

    # The total proceeds from redeeming the savings bonds — principal plus
    # interest combined. The excludable interest is prorated if the proceeds
    # exceed your qualified education expenses.
    # IRC §135(b)(1) (title26.md:96620): "the amount of interest excludable
    # under subsection (a)... shall not exceed the amount which bears the
    # same ratio to such interest as the qualified higher education expenses
    # ... bear to such proceeds"
    total_bond_proceeds: float = 0.0
    # The interest portion of the bond proceeds. This is the amount that
    # may be partially or fully excluded from income if used for qualified
    # education expenses (subject to income phase-out).
    # IRC §135(a) (title26.md:96620): "gross income shall not include income
    # from the redemption of any United States savings bond... if qualified
    # higher education expenses were paid by the taxpayer"
    bond_interest: float = 0.0
    # Qualified higher education expenses — tuition and required fees at
    # an eligible institution for you, your spouse, or your dependent.
    # Room and board do NOT qualify for this exclusion.
    # IRC §135(c)(2) (title26.md:96620): "the term 'qualified higher
    # education expenses' means tuition and fees required for the enrollment
    # or attendance of the taxpayer, the taxpayer's spouse, or any dependent"
    qualified_education_expenses: float = 0.0
    # Scholarships, fellowships, and other tax-free educational assistance
    # the student received. These reduce your qualified education expenses
    # before computing the bond interest exclusion.
    # IRC §135(c)(2)(B) (title26.md:96620): "reduced by the amount of
    # scholarships, fellowships, employer-provided educational assistance,
    # and veterans' educational assistance"
    scholarships_and_grants: float = 0.0


@dataclass
class MarketplaceCoverage:
    """ACA marketplace health insurance coverage.

    IRC §36B (title26.md:27167) — Premium Tax Credit.
    Advance payments must be reconciled on the return.
    """

    # The name of the health insurance plan you enrolled in through the
    # ACA marketplace (e.g. "Blue Cross Silver 70").
    # IRC §36B(b)(2)(A) (title26.md:26669): "qualified health plans offered
    # in the individual market within a State... enrolled in through an
    # Exchange established by the State"
    marketplace_plan_name: str = ""
    # The state marketplace/exchange where you enrolled (e.g. "healthcare.gov"
    # or a state-based exchange like "Covered California").
    # IRC §36B(b)(2)(A) (title26.md:26669): "Exchange established by the State"
    state_exchange: str = ""
    # The number of months during the year you were enrolled in marketplace
    # coverage. The credit is calculated on a monthly basis.
    # IRC §36B(b)(1) (title26.md:26660): "the sum of the premium assistance
    # amounts determined... with respect to all coverage months"
    coverage_months: int = 12
    # The total annual premium for your marketplace health plan — the full
    # price before any subsidies or advance payments.
    # IRC §36B(b)(2)(A) (title26.md:26669): "the monthly premiums for such
    # month for 1 or more qualified health plans"
    annual_premium: float = 0.0
    # The annual premium for the second-lowest-cost Silver plan available to
    # you in your area (the "benchmark plan"). This is used to calculate
    # your credit amount — you don't need to enroll in this plan.
    # IRC §36B(b)(3)(B) (title26.md:26700): "the term 'applicable second
    # lowest cost silver plan' means the second lowest cost silver plan of
    # the individual market in the rating area"
    annual_slcsp_premium: float = 0.0
    # Advance premium tax credit payments the government sent directly to
    # your insurance company during the year to reduce your monthly premiums.
    # These must be reconciled on your return — if you got too much, you
    # repay the excess; if too little, you get the difference as a credit.
    # IRC §36B(f)(1) (title26.md:27167): "If the advance payments... for a
    # taxable year exceed the credit allowed... the tax imposed... shall be
    # increased by the amount of such excess"
    advance_ptc_received: float = 0.0
    # The number of people in your tax household — yourself, your spouse (if
    # filing jointly), and anyone you claim as a dependent. Used to determine
    # the Federal Poverty Line (FPL) threshold for your household size.
    # IRC §36B(d)(1) (title26.md:26800): "the term 'household income' means
    # the modified adjusted gross income of the taxpayer... and all other
    # individuals... taken into account in determining the family size"
    household_size: int = 1


@dataclass
class AMTPreferenceItems:
    """Alternative Minimum Tax preference items and adjustments.

    IRC §55 (title26.md:64924) — AMT imposed.
    IRC §56 — AMTI adjustments.
    IRC §57 — AMT preference items.
    IRC §53 — prior year minimum tax credit.
    """

    # The difference between the fair market value of shares received and
    # the exercise price when you exercised Incentive Stock Options (ISOs).
    # ISOs are not taxed for regular income tax, but the spread IS added
    # to income for AMT purposes.
    # IRC §56(b)(19) (title26.md:65200): adjustments for incentive stock
    # options; IRC §422 (title26.md:226910): "an incentive stock option
    # shall be treated as an option... and the share transferred... shall
    # not be treated as a transfer of property"
    iso_exercise_spread: float = 0.0
    # Tax-exempt interest you received from private activity municipal bonds.
    # While exempt from regular tax, this interest IS a preference item for
    # the Alternative Minimum Tax.
    # IRC §57(a)(5)(A) (title26.md:68558): "Interest on specified private
    # activity bonds reduced by any deduction... which would have been
    # allowable if such interest were includible in gross income"
    private_activity_bond_interest: float = 0.0
    # The excess of percentage depletion over the adjusted basis of the
    # property at year-end. Applies to owners of mining, oil/gas, or other
    # natural resource properties.
    # IRC §57(a)(1) (title26.md:65350): "The excess of the deduction for
    # depletion allowable under section 611 over the adjusted basis of
    # the property"
    depletion_excess: float = 0.0
    # The excess of intangible drilling costs deducted in the current year
    # over the amount that would have been deductible if amortized over
    # 10 years. Applies to oil, gas, and geothermal well investments.
    # IRC §57(a)(2) (title26.md:65360): "With respect to all productive
    # properties of the taxpayer, the amount... by which the amount of the
    # deductions... exceeds the amount which would have been allowable...
    # if such costs had been amortized ratably over the 120-month period"
    intangible_drilling_costs_excess: float = 0.0
    # Any other AMT adjustments not captured in the specific fields above —
    # such as tax-exempt interest from certain bonds, installment sale
    # adjustments, or passive activity differences.
    # IRC §56 (title26.md:65150): various AMT adjustments to taxable income.
    other_adjustments: float = 0.0
    # Minimum tax credit carried forward from prior years when you paid AMT.
    # You can use this credit in later years when your regular tax exceeds
    # the tentative minimum tax, effectively getting back the excess AMT you
    # paid previously.
    # IRC §53(a) (title26.md:64700): "There shall be allowed as a credit
    # against the tax imposed... an amount equal to the minimum tax credit
    # for such taxable year"
    prior_year_amt_credit: float = 0.0


@dataclass
class EITCEligibility:
    """Earned Income Tax Credit eligibility details.

    IRC §32 (title26.md:22751) — EITC requirements.
    """

    # Whether you have a valid Social Security Number that authorizes you
    # to work in the United States. ITINs do not qualify for the EITC.
    # IRC §32(m) (title26.md:22872): "No credit shall be allowed under this
    # section to an eligible individual who does not include on the return...
    # such individual's taxpayer identification number"
    has_valid_ssn_for_employment: bool = True
    # Your total investment income for the year — interest, dividends,
    # capital gains, rental income, and royalties. If this exceeds the
    # limit ($11,950 for 2025), you cannot claim the EITC.
    # IRC §32(i) (title26.md:23033): "No credit shall be allowed... if the
    # aggregate amount of disqualified income of the taxpayer for the
    # taxable year exceeds $10,000"
    investment_income: float = 0.0
    # Whether your main home was in the United States (including DC and
    # military bases overseas) for more than half the year. Required for
    # EITC eligibility (with limited exceptions for military).
    # IRC §32(c)(1)(A)(ii)(I) (title26.md:22840): "who has a principal place
    # of abode in the United States... for more than one-half of such
    # taxable year"
    lived_in_us_more_than_half_year: bool = True
    # Whether you can be claimed as a qualifying child of another taxpayer.
    # If so, you cannot claim the EITC on your own return.
    # IRC §32(c)(1)(A) (title26.md:22835): an "eligible individual" must not
    # be a "qualifying child" (as defined in §152(c)) of another taxpayer.
    is_qualifying_child_of_another: bool = False
    # The year of any prior EITC disqualification due to reckless or
    # intentional disregard of the rules. Results in a 2-year ban from
    # claiming the EITC.
    # IRC §32(k)(1)(B)(ii) (title26.md:23127): "the period of 2 taxable years
    # after the most recent taxable year for which there was a final
    # determination that the taxpayer's claim of credit under this section
    # was due to reckless or intentional disregard of rules and regulations"
    prior_eitc_disqualification_year: Optional[int] = None
    # Whether you were previously disqualified from claiming the EITC due to
    # fraud. Fraud results in a 10-year ban from claiming the credit.
    # IRC §32(k)(1)(B)(i) (title26.md:23122): "the period of 10 taxable years
    # after the most recent taxable year for which there was a final
    # determination that the taxpayer's claim of credit under this section
    # was due to fraud"
    prior_eitc_fraud: bool = False


@dataclass
class AdoptionExpense:
    """Qualified adoption expenses for the adoption credit.

    IRC §23 (title26.md:13227) — adoption credit up to ~$17,280 (2025).
    """

    # The name of the child you adopted or are in the process of adopting.
    # IRC §23(d)(1) (title26.md:13290): "the term 'eligible child' means
    # any individual who has not attained age 18"
    child_name: str
    # The child's Social Security Number, or Adoption Taxpayer Identification
    # Number (ATIN) if an SSN has not yet been issued.
    # IRC §23(f)(1) (title26.md:13320): identifying number requirements.
    child_ssn: str = ""
    # Whether the child has special needs — meaning the state has determined
    # the child cannot or should not be returned to their parents and the
    # child has a condition that makes placement difficult. If so, you are
    # deemed to have paid the maximum adoption expenses regardless of actual
    # costs.
    # IRC §23(a)(3) (title26.md:13252): "In the case of an adoption of a
    # child with special needs which becomes final during a taxable year,
    # the taxpayer shall be treated as having paid during such year qualified
    # adoption expenses... in an amount equal to the excess (if any) of
    # $10,000 over the aggregate qualified adoption expenses actually paid"
    is_special_needs: bool = False
    # Whether this is an international (foreign) adoption. For foreign
    # adoptions, the credit can only be claimed in the year the adoption
    # becomes final.
    # IRC §23(e) (title26.md:13310): timing rules for foreign adoptions.
    is_foreign_adoption: bool = False
    # The total qualified adoption expenses you paid — including adoption
    # fees, attorney fees, court costs, travel expenses, and other costs
    # directly related to the legal adoption. Subject to the per-child
    # maximum (~$17,280 for 2025).
    # IRC §23(d)(1) (title26.md:13290): "the term 'qualified adoption
    # expenses' means reasonable and necessary adoption fees, court costs,
    # attorney fees, and other expenses which are directly related to, and
    # the principal purpose of which is for, the legal adoption"
    qualified_expenses: float = 0.0
    # The tax year in which you paid or incurred the adoption expenses.
    # For domestic adoptions not yet final, the credit is allowed the year
    # after the expense is paid.
    # IRC §23(a)(2)(A) (title26.md:13240): "in the case of any expense paid
    # or incurred before the taxable year in which such adoption becomes
    # final, for the taxable year following the taxable year during which
    # such expense is paid or incurred"
    year_expenses_paid: int = 0
    # The tax year in which the adoption was legally finalized (or None if
    # still in progress).
    # IRC §23(a)(2)(B) (title26.md:13245): "in the case of an expense paid
    # or incurred during or after the taxable year in which such adoption
    # becomes final, for the taxable year in which such expense is paid"
    adoption_finalized_year: Optional[int] = None
    # Unused adoption credit carried forward from prior years. The
    # nonrefundable portion can be carried forward for up to 5 years.
    # IRC §23(c) (title26.md:13317): "If the credit allowable... for any
    # taxable year exceeds the limitation... such excess shall be carried
    # to the succeeding taxable year... but not for more than 5 taxable
    # years"
    prior_year_carryforward: float = 0.0


@dataclass
class ElderlyDisabledInfo:
    """Credit for the elderly or permanently disabled.

    IRC §22 (title26.md:12756) — 15% nonrefundable credit.
    """

    # Whether you are permanently and totally disabled — meaning you cannot
    # engage in any substantial gainful activity due to a medically
    # determinable physical or mental condition that is expected to last
    # continuously for at least 12 months or result in death.
    # IRC §22(e)(3) (title26.md:12860): "An individual is permanently and
    # totally disabled if he is unable to engage in any substantial gainful
    # activity by reason of any medically determinable physical or mental
    # impairment which can be expected to result in death or which has
    # lasted or can be expected to last for a continuous period of not less
    # than 12 months"
    is_permanently_totally_disabled: bool = False
    # Taxable disability income you received during the year (if you are
    # under 65 and retired on disability). Used to calculate the initial
    # Section 22 amount for disabled individuals under 65.
    # IRC §22(c)(2)(B) (title26.md:12810): "the initial amount shall be the
    # lesser of... the section 22 amount, or the taxable disability income"
    disability_income: float = 0.0
    # Nontaxable Social Security benefits you received. These reduce the
    # initial Section 22 amount dollar-for-dollar.
    # IRC §22(c)(3)(A) (title26.md:12872): "the section 22 amount shall be
    # reduced by... the amount of any pension, annuity, or disability benefit
    # excluded from gross income under... section 86 (relating to social
    # security and tier 1 railroad retirement benefits)"
    nontaxable_social_security: float = 0.0
    # Nontaxable Veterans Affairs (VA) pension or disability payments you
    # received. These also reduce the initial Section 22 amount.
    # IRC §22(c)(3)(A) (title26.md:12872): "any pension, annuity, or
    # disability benefit... excluded from gross income... under any
    # provision of law administered by the Department of Veterans Affairs"
    nontaxable_va_pension: float = 0.0


@dataclass
class KiddieTaxInfo:
    """Kiddie tax information for children with unearned income.

    IRC §1(g) (title26.md:5520) — child's unearned income taxed at parent's rate.
    """

    # The child's total unearned income for the year — interest, dividends,
    # capital gains, and other investment income. The amount above the
    # threshold ($2,500 for 2025) is taxed at the parent's marginal rate.
    # IRC §1(g)(4) (title26.md:5570): "the net unearned income of such child
    # for the taxable year"
    child_unearned_income: float = 0.0
    # The child's earned income (wages, salary, self-employment) for the
    # year. Earned income is taxed at the child's own rate, not the parent's.
    # IRC §1(g)(4)(A) (title26.md:5575): "net unearned income means the
    # excess of... the portion of the adjusted gross income... which is not
    # attributable to earned income (as defined in section 911(d)(2))"
    child_earned_income: float = 0.0
    # The parent's taxable income, used to determine the parent's marginal
    # tax rate that applies to the child's excess unearned income.
    # IRC §1(g)(3) (title26.md:5555): "the allocable parental tax... the
    # tax which would be imposed... on the parent's taxable income"
    parent_taxable_income: float = 0.0
    # The parent's filing status, needed to look up the correct tax brackets
    # when computing the parent's marginal rate for the kiddie tax.
    # IRC §1(g)(3)(A) (title26.md:5555): "the tax which would be imposed
    # by this section on the sum of the parent's taxable income"
    parent_filing_status: FilingStatus = FilingStatus.MARRIED_FILING_JOINTLY
    # The parent's marginal tax rate, if known. If provided, this rate is
    # used directly instead of computing it from parent_taxable_income.
    # IRC §1(g)(1)(B)(ii) (title26.md:5530): "such child's share of the
    # allocable parental tax"
    parent_marginal_rate: float = 0.0
    # Whether the child is a full-time student. The kiddie tax can apply to
    # students aged 19-23 whose earned income is not more than half their
    # support. Without this flag, the kiddie tax only applies to those
    # under 18.
    # IRC §1(g)(2)(A)(ii)(I) (title26.md:5545): "has attained age 18 before
    # the close of the taxable year and meets the age requirements of section
    # 152(c)(3)... and whose earned income... does not exceed one-half of the
    # amount of the individual's support"
    child_is_full_time_student: bool = False
    # Whether the child provides more than half of their own support for the
    # year. If so, the kiddie tax does NOT apply (even if the child is under
    # 18) because they are self-supporting.
    # IRC §1(g)(2)(A)(ii)(II) (title26.md:5550): "whose earned income...
    # does not exceed one-half of the amount of the individual's support"
    child_provides_over_half_support: bool = False


# ---------------------------------------------------------------------------
# Top-level Input Model
# ---------------------------------------------------------------------------


@dataclass
class TaxReturnInput:
    """Complete input for a federal individual income tax return.

    This model captures all information needed to compute a Form 1040
    and associated schedules. All fields reference the applicable IRC sections.

    IRC §6012 (title26.md:498203) — filing requirements.
    IRC §6072 (title26.md:516367) — filing deadline (April 15).
    """

    tax_year: int
    filing_status: FilingStatus
    personal_info: PersonalInfo
    address: Address
    spouse_info: Optional[PersonalInfo] = None

    # IRC §152 (title26.md:112887)
    dependents: list[Dependent] = field(default_factory=list)

    # Income sources — IRC §61 (title26.md:70846)
    w2_income: list[W2Income] = field(default_factory=list)
    interest_income: list[InterestIncome] = field(default_factory=list)
    dividend_income: list[DividendIncome] = field(default_factory=list)
    capital_gains_losses: list[CapitalGainLoss] = field(default_factory=list)
    capital_loss_carryforward: float = (
        0.0  # IRC §1212 (title26.md:350269) — legacy single value
    )
    capital_loss_carryforward_short_term: float = (
        0.0  # IRC §1212(b) — retains ST character
    )
    capital_loss_carryforward_long_term: float = (
        0.0  # IRC §1212(b) — retains LT character
    )
    business_income: list[BusinessIncome] = field(default_factory=list)
    rental_income: list[RentalIncome] = field(default_factory=list)
    retirement_distributions: list[RetirementDistribution] = field(default_factory=list)
    social_security: Optional[SocialSecurityIncome] = None
    unemployment: Optional[UnemploymentIncome] = None
    other_income: list[OtherIncome] = field(default_factory=list)
    home_sale: Optional[HomeSale] = None
    cancelled_debt: list[CancelledDebt] = field(default_factory=list)
    k1_income: list[K1Income] = field(default_factory=list)  # IRC §702/§1366/§652
    royalty_income: list[RoyaltyIncome] = field(default_factory=list)  # IRC §61(a)(6)
    farm_income: list[FarmIncome] = field(default_factory=list)  # Schedule F
    annuity_income: list[AnnuityIncome] = field(default_factory=list)  # IRC §72
    scholarship_income: list[ScholarshipIncome] = field(
        default_factory=list
    )  # IRC §117
    gambling: Optional[GamblingIncome] = None  # IRC §61, §165(d)
    restricted_stock_events: list[RestrictedStockEvent] = field(
        default_factory=list
    )  # IRC §83
    section_529_distributions: list[Section529Distribution] = field(
        default_factory=list
    )  # IRC §529
    like_kind_exchanges: list[LikeKindExchange] = field(
        default_factory=list
    )  # IRC §1031
    alimony_received: float = 0.0  # Pre-2019 instruments — former §71
    alimony_payer_ssn: str = ""
    alimony_instrument_date: str = ""  # ISO 8601 — must be pre-2019 for inclusion

    # Adjustments to income — IRC §62 (title26.md:71233)
    educator_expenses: float = 0.0  # Up to $250, IRC §62(a)(2)(D)
    ira_contributions: list[RetirementContribution] = field(default_factory=list)
    student_loan_interest_paid: float = 0.0  # IRC §221 (title26.md:151853)
    hsa: Optional[HSAInfo] = None  # IRC §223 (title26.md:152303)
    alimony_paid: float = 0.0  # Pre-2019 instruments only
    alimony_recipient_ssn: str = ""
    qualified_tips: float = 0.0  # IRC §224 (title26.md:153381)
    qualified_overtime: float = 0.0  # IRC §225 (title26.md:153525)
    early_withdrawal_penalty: float = 0.0
    savings_bond_education: Optional[SavingsBondEducationExclusion] = None  # IRC §135

    # NOL carryforward — IRC §172 (title26.md:137742)
    nol_carryforward: float = 0.0  # Post-2017 NOLs (80% limitation)
    nol_carryforward_pre_2018: float = 0.0  # Pre-2018 NOLs (no percentage limit)

    # Deduction preference — IRC §63 (title26.md:72402)
    deduction_method: DeductionMethod = DeductionMethod.STANDARD

    # Itemized deduction details — IRC §63(d)
    medical_expenses: Optional[MedicalExpense] = None  # IRC §213
    state_local_taxes: Optional[StateLocalTaxes] = None  # IRC §164
    mortgage_interest: list[MortgageInterest] = field(default_factory=list)  # IRC §163
    charitable_contributions: list[CharitableContribution] = field(
        default_factory=list
    )  # IRC §170
    charitable_contribution_carryforward: float = (
        0.0  # IRC §170(d) — 5-year carryforward
    )
    casualty_loss_from_disaster: float = 0.0  # IRC §165(h)(5) — legacy simple field
    casualty_losses: list[CasualtyLossEvent] = field(
        default_factory=list
    )  # IRC §165(h) — detailed
    investment_interest_expense: float = 0.0  # IRC §163(d)
    investment_interest_carryforward: float = 0.0  # IRC §163(d) — prior year excess
    elect_to_include_qualified_dividends_in_nii: bool = False  # §163(d)(4)(B)

    # Credits
    education_expenses: list[EducationExpense] = field(default_factory=list)  # IRC §25A
    child_care_expenses: list[ChildCareExpense] = field(default_factory=list)  # IRC §21
    retirement_savings_contributions: list[RetirementContribution] = field(
        default_factory=list
    )  # IRC §25B
    clean_vehicle: Optional[CleanVehicleCredit] = None  # IRC §30D / §25E
    energy_credits: Optional[EnergyCredit] = None  # IRC §25C / §25D
    energy_credit_carryforward: float = 0.0  # IRC §25D(c) — prior year unused credit
    foreign_income: list[ForeignIncomeInfo] = field(
        default_factory=list
    )  # IRC §911 / §27
    qbi: list[QualifiedBusinessIncome] = field(default_factory=list)  # IRC §199A
    adoption_expenses: list[AdoptionExpense] = field(default_factory=list)  # IRC §23
    elderly_disabled_info: Optional[ElderlyDisabledInfo] = None  # IRC §22
    marketplace_coverage: Optional[MarketplaceCoverage] = None  # IRC §36B
    amt_preferences: Optional[AMTPreferenceItems] = None  # IRC §55/§56/§57
    eitc_eligibility: Optional[EITCEligibility] = None  # IRC §32
    kiddie_tax: Optional[KiddieTaxInfo] = None  # IRC §1(g)
    net_investment_income_override: Optional[float] = None  # §1411 manual NII

    # Payments — IRC §31, §6654
    estimated_tax_payments: Optional[EstimatedTaxPayment] = None
    other_federal_withholding: float = 0.0  # Backup withholding, etc.

    # Prior year info (for safe harbor, carryforwards)
    prior_year_agi: float = 0.0
    prior_year_tax: float = 0.0


# ---------------------------------------------------------------------------
# Output Model — Computed tax return results
# ---------------------------------------------------------------------------


@dataclass
class IncomeComputation:
    """Computed income totals.

    IRC §61 (title26.md:70846) — gross income.
    """

    # Sum of all wages, salaries, and tips from every W-2 you received.
    # IRC §61(a)(1) (title26.md:70854): "Compensation for services, including
    # fees, commissions, fringe benefits, and similar items"
    total_wages: float = 0.0
    # Sum of all taxable interest income from banks, brokerages, and bonds.
    # IRC §61(a)(4) (title26.md:70861): "Interest"
    total_interest: float = 0.0
    # Interest from state/local bonds — reported but NOT included in taxable
    # income. May affect other calculations like Social Security taxation.
    # IRC §103(a) (title26.md:83090): "gross income does not include interest
    # on any State or local bond"
    tax_exempt_interest: float = 0.0
    # Sum of all ordinary dividends from stocks, mutual funds, and REITs.
    # IRC §61(a)(7) (title26.md:70867): "Dividends"
    total_ordinary_dividends: float = 0.0
    # Portion of ordinary dividends that qualify for the lower long-term
    # capital gains tax rate instead of your ordinary income rate.
    # IRC §1(h)(11) (title26.md:5895): "qualified dividend income shall be
    # treated as adjusted net capital gain"
    total_qualified_dividends: float = 0.0
    # Net gain or loss from selling assets held one year or less, after
    # applying any short-term capital loss carryforward from prior years.
    # IRC §1222(1) (title26.md:351190): "the term short-term capital gain means gain
    # from the sale or exchange of a capital asset held for not more than
    # 1 year"
    net_short_term_capital_gain_loss: float = 0.0
    # Net gain or loss from selling assets held more than one year, after
    # applying any long-term capital loss carryforward from prior years.
    # IRC §1222(3) (title26.md:351200): "long-term capital gain means gain
    # from the sale or exchange of a capital asset held for more than 1 year"
    net_long_term_capital_gain_loss: float = 0.0
    # Your overall net capital gain or loss after combining short-term and
    # long-term results and applying the $3,000 loss limitation ($1,500 MFS).
    # IRC §1211(b) (title26.md:350190): "losses from sales or exchanges of
    # capital assets shall be allowed only to the extent of the gains...
    # plus... the lower of $3,000... or the excess of such losses over
    # such gains"
    net_capital_gain_loss: float = 0.0
    # Capital losses that exceed the current-year $3,000 limit, carried
    # forward to future years. Capital loss carryforwards never expire.
    # IRC §1212(b) (title26.md:350269): "a short-term capital loss... shall
    # be treated as a short-term capital loss... in the succeeding taxable
    # year"
    capital_loss_carryforward_to_next_year: float = 0.0
    # The short-term portion of the capital loss carryforward. Retains its
    # short-term character in future years.
    # IRC §1212(b)(1) (title26.md:350269): carried forward as short-term.
    capital_loss_carryforward_remaining_short: float = 0.0
    # The long-term portion of the capital loss carryforward. Retains its
    # long-term character in future years.
    # IRC §1212(b)(2) (title26.md:350280): carried forward as long-term.
    capital_loss_carryforward_remaining_long: float = 0.0
    # Net profit or loss from all self-employment businesses (Schedule C).
    # IRC §162(a) (title26.md:114102): "all the ordinary and necessary
    # expenses paid or incurred during the taxable year in carrying on
    # any trade or business"
    total_business_income: float = 0.0
    # Net rental income or loss from all rental properties (Schedule E).
    # IRC §61(a)(5) (title26.md:70863): "Rents"
    total_rental_income: float = 0.0
    # Total gross distributions received from all retirement plans (401(k),
    # IRA, pension), before determining the taxable portion.
    # IRC §72(a)(1) (title26.md:74051): "gross income includes any amount
    # received as an annuity"
    total_retirement_distributions: float = 0.0
    # The taxable portion of your retirement distributions — excludes
    # qualified Roth distributions and the tax-free return of after-tax
    # contributions.
    # IRC §72(a) (title26.md:74051): "gross income includes any amount
    # received as an annuity"
    taxable_retirement_distributions: float = 0.0
    # Total Social Security benefits received during the year (from Form
    # SSA-1099). Not all of this is necessarily taxable.
    # IRC §86(d)(1) (title26.md:80750): "the term 'social security benefit'
    # means any amount received by the taxpayer by reason of entitlement to
    # a monthly benefit under title II of the Social Security Act"
    total_social_security: float = 0.0
    # The taxable portion of your Social Security benefits — between 0% and
    # 85% depending on your other income (provisional income test).
    # IRC §86(a) (title26.md:80658): "gross income... includes social security
    # benefits in an amount equal to the lesser of (A) one-half of the social
    # security benefits received during the taxable year"
    taxable_social_security: float = 0.0
    # Total unemployment compensation received during the year. All
    # unemployment benefits are fully taxable as ordinary income.
    # IRC §85(a) (title26.md:80444): "gross income includes unemployment
    # compensation"
    unemployment_compensation: float = 0.0
    # Taxable gain from selling your main home, after applying the §121
    # exclusion ($250k single / $500k joint) and adding back depreciation.
    # IRC §121(a) (title26.md:90818): "Gross income shall not include gain
    # from the sale or exchange of property if... such property has been
    # owned and used by the taxpayer as the taxpayer's principal residence
    # for periods aggregating 2 years or more"
    taxable_home_sale_gain: float = 0.0
    # Total other income not captured in specific categories — prizes,
    # jury duty pay, hobby income, and similar items.
    # IRC §61(a) (title26.md:70846): "gross income means all income from
    # whatever source derived"
    total_other_income: float = 0.0
    # Taxable cancelled debt income after applying exclusions for
    # bankruptcy, insolvency, principal residence debt, and student loans.
    # IRC §108(a)(1) (title26.md:86700): "Gross income does not include any
    # amount which... would be includible in gross income by reason of the
    # discharge... of indebtedness of the taxpayer if (A) the discharge
    # occurs in a title 11 case, (B) the discharge occurs when the taxpayer
    # is insolvent"
    total_cancelled_debt_income: float = 0.0
    # Your share of ordinary business income from partnerships, S-Corps,
    # and trusts reported on Schedule K-1.
    # IRC §702(a)(8) (title26.md:283000): "each partner shall take into
    # account separately the partner's distributive share"
    total_k1_ordinary_income: float = 0.0
    # Guaranteed payments received from partnerships for services or use
    # of capital, regardless of partnership profit. Always SE income.
    # IRC §707(c) (title26.md:284243): "payments to a partner for services
    # or the use of capital shall be considered as made to one who is not
    # a member of the partnership"
    total_k1_guaranteed_payments: float = 0.0
    # Net royalty income after deducting expenses like depletion and
    # depreciation. Reported on Schedule E, Part I.
    # IRC §61(a)(6) (title26.md:70865): "Royalties"
    total_royalty_income: float = 0.0
    # Net farm profit or loss from all farming operations (Schedule F).
    # IRC §61(a)(2) (title26.md:70857): "Gross income derived from business"
    total_farm_income: float = 0.0
    # Whether the farm generated a net operating loss eligible for the
    # special 2-year carryback rule available only to farming losses.
    # IRC §172(b)(1)(B)(iv) (title26.md:137800): "in the case of any portion
    # of a net operating loss... which is a farming loss... the 2-year
    # carryback"
    farm_nol_carryback_eligible: bool = False
    # Alimony included in gross income under pre-2019 divorce instruments.
    # Post-2018 instruments: alimony is not income to the recipient.
    # Former IRC §71 (title26.md:70897): alimony income inclusion repealed
    # for instruments executed after Dec. 31, 2018.
    alimony_income: float = 0.0
    # Total gambling and wagering winnings included in gross income.
    # IRC §61(a) (title26.md:70846): "gross income means all income from
    # whatever source derived"
    gambling_income: float = 0.0
    # The taxable portion of annuity payments after excluding the tax-free
    # return of your investment, computed via the exclusion ratio or
    # simplified method.
    # IRC §72(b)(1) (title26.md:74080): "Gross income does not include that
    # part of any amount received as an annuity... which bears the same
    # ratio to such amount as the investment in the contract... bears to
    # the expected return"
    annuity_taxable_amount: float = 0.0
    # Scholarship amounts used for non-qualified expenses (room, board,
    # services) that are included in taxable income.
    # IRC §117(a) (title26.md:89656): "Gross income does not include any
    # amount received as a qualified scholarship" — amounts not qualifying
    # are taxable.
    taxable_scholarship_income: float = 0.0
    # Taxable earnings from non-qualified 529 plan distributions. Only the
    # earnings portion of non-qualified withdrawals is taxable.
    # IRC §529(c)(3)(A) (title26.md:263420): "Distributions shall be
    # includible in the gross income of the distributee"
    taxable_529_income: float = 0.0
    # Gain recognized on like-kind exchanges due to boot (cash or unlike
    # property) received. The remainder of the gain is deferred.
    # IRC §1031(b) (title26.md:342715): "the gain... shall be recognized...
    # in an amount not in excess of the sum of such money and the fair
    # market value of such other property"
    like_kind_recognized_gain: float = 0.0
    # Gain deferred (not currently taxed) on like-kind exchanges. This
    # reduces the basis of the replacement property.
    # IRC §1031(a)(1) (title26.md:342673): "No gain or loss shall be
    # recognized on the exchange of real property held for productive use"
    like_kind_deferred_gain: float = 0.0
    # Compensation income from restricted stock vesting or §83(b) elections.
    # Included in gross income as ordinary compensation.
    # IRC §83(a) (title26.md:79675): "the excess of the fair market value
    # of such property... over the amount (if any) paid for such property,
    # shall be included in the gross income"
    restricted_stock_income: float = 0.0
    # Your total gross income — the sum of all taxable income items before
    # any deductions or adjustments. This is the starting point for
    # computing your tax.
    # IRC §61(a) (title26.md:70846): "gross income means all income from
    # whatever source derived"
    gross_income: float = 0.0


@dataclass
class AGIComputation:
    """Adjusted gross income computation.

    IRC §62 (title26.md:71233) — above-the-line deductions.
    """

    # Your total gross income, carried forward from IncomeComputation.
    # IRC §61(a) (title26.md:70846): "gross income means all income from
    # whatever source derived"
    gross_income: float = 0.0
    # Deduction for qualified K-12 teacher expenses — up to $250 for
    # classroom supplies, books, and professional development.
    # IRC §62(a)(2)(D) (title26.md:71272): "The deductions allowed by
    # section 162 which consist of expenses, not in excess of $250, paid
    # or incurred by an eligible educator"
    educator_expenses_deduction: float = 0.0
    # Deduction for contributions to a Traditional IRA. May be limited if
    # you or your spouse participate in an employer retirement plan.
    # IRC §219(a) (title26.md:149106): "there shall be allowed as a
    # deduction an amount equal to the qualified retirement contributions"
    ira_deduction: float = 0.0
    # Deduction for interest paid on qualified student loans, up to $2,500.
    # Phases out at higher income levels.
    # IRC §221(a) (title26.md:151853): "there shall be allowed as a
    # deduction... an amount equal to the interest paid by the taxpayer
    # during the taxable year on any qualified education loan"
    student_loan_interest_deduction: float = 0.0
    # Deduction for your personal contributions to a Health Savings Account.
    # IRC §223(a) (title26.md:152303): "there shall be allowed as a
    # deduction for the taxable year an amount equal to the aggregate
    # amount paid in cash... to a health savings account"
    hsa_deduction: float = 0.0
    # Deduction equal to 50% of your self-employment tax. This accounts
    # for the fact that employees only pay half of FICA while the employer
    # pays the other half.
    # IRC §164(f) (title26.md:119500): "one-half of the taxes imposed by
    # section 1401 for the taxable year shall be allowed as a deduction"
    se_tax_deduction: float = 0.0
    # Deduction for alimony payments under pre-2019 divorce instruments.
    # Not available for instruments executed after Dec. 31, 2018.
    # Former IRC §215 (title26.md:71757): "In the case of an individual,
    # there shall be allowed as a deduction an amount equal to the alimony
    # or separate maintenance payments paid during such individual's
    # taxable year"
    alimony_deduction: float = 0.0
    # Deduction for qualified tips received in tipped occupations, up to
    # $25,000. Effective 2025-2028. Phases out at higher incomes.
    # IRC §224(a) (title26.md:153381): "There shall be allowed as a
    # deduction an amount equal to the qualified tips received during
    # the taxable year"
    qualified_tips_deduction: float = 0.0
    # Deduction for qualified overtime compensation above the regular rate,
    # up to $12,500 ($25,000 joint). Effective 2025-2028.
    # IRC §225(a) (title26.md:153525): "There shall be allowed as a
    # deduction an amount equal to the qualified overtime compensation
    # received during the taxable year"
    qualified_overtime_deduction: float = 0.0
    # Penalty charged by a financial institution for withdrawing funds from
    # a time deposit (e.g. CD) before maturity. Deductible above the line.
    # IRC §62(a)(9) (title26.md:71331): "The deductions allowed by part VII
    # of subchapter B (relating to... penalties forfeited because of
    # premature withdrawal)"
    early_withdrawal_penalty: float = 0.0
    # Interest from U.S. savings bonds excluded from income because the
    # proceeds were used to pay qualified higher education expenses.
    # IRC §135(a) (title26.md:96620): "gross income shall not include income
    # from the redemption of any United States savings bond... if qualified
    # higher education expenses were paid"
    savings_bond_interest_excluded: float = 0.0
    # Sum of all above-the-line deductions (adjustments to income).
    # IRC §62(a) (title26.md:71233): "the term 'adjusted gross income'
    # means, in the case of an individual, gross income minus the following
    # deductions"
    total_adjustments: float = 0.0
    # Your Adjusted Gross Income — gross income minus above-the-line
    # deductions. AGI is the most important intermediate number on your
    # return; it determines eligibility for many credits and deductions.
    # IRC §62(a) (title26.md:71233): "the term 'adjusted gross income'
    # means, in the case of an individual, gross income minus the following
    # deductions"
    agi: float = 0.0


@dataclass
class DeductionComputation:
    """Standard or itemized deduction computation.

    IRC §63 (title26.md:72402) — taxable income.
    """

    # The base standard deduction amount for your filing status — $15,750
    # single, $31,500 joint, $23,625 HoH for 2025.
    # IRC §63(c)(2) (title26.md:72514): "the term 'basic standard deduction'
    # means... $31,500 in the case of a joint return or a surviving spouse,
    # $23,625 in the case of a head of household, $15,750 in any other case"
    basic_standard_deduction: float = 0.0
    # Additional standard deduction for being age 65 or older — $1,600 per
    # qualifying person for married filers, $2,000 for unmarried filers.
    # IRC §63(f)(1) (title26.md:72598): "additional standard deduction for
    # the aged... in the case of an individual who has attained age 65
    # before the close of the taxable year"
    additional_standard_deduction_age: float = 0.0
    # Additional standard deduction for being legally blind — same amounts
    # as the age-based addition ($1,600 married / $2,000 unmarried).
    # IRC §63(f)(2) (title26.md:72620): "additional standard deduction...
    # in the case of an individual who is blind"
    additional_standard_deduction_blind: float = 0.0
    # Sum of basic + additional standard deductions. Compared against
    # itemized deductions to determine which method reduces your taxes more.
    # IRC §63(c)(1) (title26.md:72510): "the term 'standard deduction' means
    # the sum of the basic standard deduction"
    total_standard_deduction: float = 0.0

    # Medical and dental expenses deductible above the 7.5% of AGI floor.
    # IRC §213(a) (title26.md:147452): "expenses paid... for medical care...
    # to the extent that such expenses exceed 7.5 percent of adjusted gross
    # income"
    medical_deduction: float = 0.0
    # State and local tax deduction — income/sales tax + property tax,
    # subject to the SALT cap ($40,000 for 2025, $20,000 MFS).
    # IRC §164(b)(6)(A) (title26.md:119469): "the aggregate amount of taxes
    # taken into account... shall not exceed" the applicable cap.
    salt_deduction: float = 0.0
    # Mortgage interest deduction for acquisition debt on your primary and
    # second home. Limited to interest on the first $750,000 of debt.
    # IRC §163(h)(3)(B) (title26.md:116550): "acquisition indebtedness...
    # incurred in acquiring, constructing, or substantially improving any
    # qualified residence"
    mortgage_interest_deduction: float = 0.0
    # Charitable contribution deduction — cash gifts (up to 60% of AGI) and
    # non-cash donations (up to 30% of AGI for capital gain property).
    # IRC §170(a)(1) (title26.md:132628): "There shall be allowed as a
    # deduction any charitable contribution... payment of which is made
    # within the taxable year"
    charitable_deduction: float = 0.0
    # Amount of prior-year charitable carryforward applied this year.
    # IRC §170(d)(1) (title26.md:132765): excess contributions "shall be
    # treated as a charitable contribution... in each of the 5 succeeding
    # taxable years"
    charitable_carryforward_used: float = 0.0
    # Charitable contributions exceeding this year's AGI limits, carried
    # forward to next year (up to 5 years total).
    # IRC §170(d)(1) (title26.md:132765): "5 succeeding taxable years in
    # order of time"
    charitable_carryforward_remaining: float = 0.0
    # Casualty and theft loss deduction from federally declared disasters,
    # after the $500 per-event floor and 10% of AGI threshold.
    # IRC §165(h)(1) (title26.md:120200): "the amount of the loss... shall
    # be reduced by $500"; IRC §165(h)(2): "only to the extent that the
    # aggregate amount of such losses exceeds 10 percent of... adjusted
    # gross income"
    casualty_loss_deduction: float = 0.0
    # Gambling losses deductible as an itemized deduction, limited to 90%
    # of wagering losses and capped at total gambling winnings.
    # IRC §165(d) (title26.md:120200): "Losses from wagering transactions
    # shall be allowed only to the extent of the gains from such transactions"
    gambling_loss_deduction: float = 0.0
    # Investment interest expense deductible up to the amount of net
    # investment income. Excess carries forward to future years.
    # IRC §163(d)(1) (title26.md:116555): "the amount allowed as a deduction
    # ... for investment interest... shall not exceed the net investment
    # income of the taxpayer"
    investment_interest_deduction: float = 0.0
    # Investment interest expense exceeding net investment income, carried
    # forward to deduct in future years when you have more investment income.
    # IRC §163(d)(2) (title26.md:116560): "the amount not allowed as a
    # deduction... by reason of paragraph (1) shall be treated as investment
    # interest paid or accrued... in the succeeding taxable year"
    investment_interest_carryforward_to_next_year: float = 0.0
    # Sum of all itemized deductions (medical, SALT, mortgage, charity,
    # casualty, gambling losses, and investment interest).
    # IRC §63(d) (title26.md:72560): "the term 'itemized deductions' means
    # the deductions allowable under this chapter other than the deductions
    # allowable in arriving at adjusted gross income and the deduction for
    # personal exemptions"
    total_itemized_deductions: float = 0.0
    # Reduction in itemized deductions under the overall limitation (applies
    # starting 2026). For 2018-2025 this is zero (limitation suspended).
    # IRC §68(a) (title26.md:73738): "the amount of the itemized deductions
    # otherwise allowable for the taxable year shall be reduced"
    itemized_deduction_limitation: float = 0.0

    # Net operating loss deduction applied to reduce taxable income.
    # Post-2017 NOLs limited to 80% of taxable income; pre-2018 NOLs
    # have no percentage limitation.
    # IRC §172(a) (title26.md:137742): "There shall be allowed as a
    # deduction... an amount equal to the aggregate of the net operating
    # loss carryovers... and the net operating loss carrybacks"
    nol_deduction: float = 0.0
    # Unused NOL remaining after this year's deduction, available to carry
    # forward to future tax years (indefinitely for post-2017 NOLs).
    # IRC §172(b)(1)(A)(ii) (title26.md:137760): post-2017 NOLs "shall be
    # a net operating loss carryover to each taxable year following"
    nol_carryforward_remaining: float = 0.0

    # Whether standard or itemized deductions were used on this return.
    # IRC §63(b) (title26.md:72450): "In the case of an individual who does
    # not elect to itemize his deductions... the term 'taxable income' means
    # adjusted gross income, minus the standard deduction"
    deduction_method_used: DeductionMethod = DeductionMethod.STANDARD
    # The actual deduction amount used — either the total standard deduction
    # or total itemized deductions, whichever is greater (or whichever was
    # elected).
    # IRC §63(a) (title26.md:72402): "the term 'taxable income' means gross
    # income minus the deductions allowed by this chapter"
    deduction_amount: float = 0.0
    # The Qualified Business Income deduction — up to 20% of pass-through
    # business income. Taken separately from standard/itemized deductions.
    # IRC §199A(a) (title26.md:146337): "there shall be allowed as a
    # deduction... an amount equal to the lesser of the combined qualified
    # business income amount... or 20 percent of... the taxable income"
    qbi_deduction: float = 0.0
    # Additional deduction for taxpayers age 65 and older — $6,000 per
    # qualifying senior, phasing out at higher incomes. Available through 2028.
    # IRC §151(f) (title26.md:112427): "in addition to the deduction allowed
    # under subsection (d), there shall be allowed as a deduction... $6,000
    # for each qualified individual"
    senior_deduction: float = 0.0
    # Your taxable income — the amount your tax is actually calculated on.
    # Equals AGI minus deductions, QBI deduction, senior deduction, and
    # any NOL deduction.
    # IRC §63(a) (title26.md:72402): "the term 'taxable income' means gross
    # income minus the deductions allowed by this chapter"
    taxable_income: float = 0.0


@dataclass
class TaxComputation:
    """Tax liability computation.

    IRC §1 (title26.md:5292) — tax rates and brackets.
    IRC §55 (title26.md:64924) — alternative minimum tax.
    IRC §1411 — Net Investment Income Tax.
    IRC §3101(b)(2) — Additional Medicare Tax.
    """

    # Tax on your ordinary income (wages, business income, interest, etc.)
    # computed using the progressive tax brackets (10% to 37% for 2025).
    # IRC §1(a)-(d) (title26.md:5292): "There is hereby imposed on the
    # taxable income of every individual... a tax determined in accordance
    # with the following table"
    ordinary_income_tax: float = 0.0
    # Breakdown of how your ordinary income tax was computed across the
    # progressive brackets — a list of {rate, bracket_income, tax} dicts.
    # IRC §1(j) (title26.md:6120): post-2017 bracket structure (10%, 12%,
    # 22%, 24%, 32%, 35%, 37%).
    tax_bracket_details: list[dict] = field(default_factory=list)

    # Total qualified dividends and net long-term capital gains eligible
    # for the preferential 0%/15%/20% tax rates.
    # IRC §1(h) (title26.md:5703): "the tax imposed... shall not exceed the
    # sum of" amounts computed at preferential rates.
    qualified_dividends_and_ltcg: float = 0.0
    # Tax on qualified dividends/LTCG in the 0% bracket (taxable income up
    # to $48,350 single / $96,700 joint for 2025).
    # IRC §1(h)(1)(B) (title26.md:5720): the 0% rate on adjusted net
    # capital gain.
    capital_gains_tax_at_0_pct: float = 0.0
    # Tax on qualified dividends/LTCG in the 15% bracket (the most common
    # rate for long-term gains and qualified dividends).
    # IRC §1(h)(1)(C) (title26.md:5730): "15 percent of the lesser of...
    # so much of the adjusted net capital gain"
    capital_gains_tax_at_15_pct: float = 0.0
    # Tax on qualified dividends/LTCG in the 20% bracket (applies to income
    # above $533,400 single / $600,050 joint for 2025).
    # IRC §1(h)(1)(D) (title26.md:5740): the 20% rate on the highest tier
    # of adjusted net capital gain.
    capital_gains_tax_at_20_pct: float = 0.0
    # Tax on gains from selling collectibles (art, coins, antiques, gems)
    # at the maximum 28% rate.
    # IRC §1(h)(4) (title26.md:5760): "the term 'collectibles gain' means
    # gain from the sale or exchange of a collectible"
    collectibles_gain_tax: float = 0.0
    # Tax on unrecaptured Section 1250 gain (depreciation recapture on real
    # property) at the maximum 25% rate.
    # IRC §1(h)(1)(E) (title26.md:5748): "25 percent of the excess (if
    # any) of the unrecaptured section 1250 gain"
    unrecaptured_1250_gain_tax: float = 0.0

    # Total regular income tax — ordinary tax + capital gains tax at all
    # rate tiers + collectibles + unrecaptured §1250 gain.
    # IRC §1 (title26.md:5292): aggregate tax on all types of income.
    total_income_tax: float = 0.0

    # Alternative Minimum Taxable Income — your taxable income plus AMT
    # preference items (ISO exercises, SALT addback, private activity bond
    # interest, etc.).
    # IRC §55(b)(2) (title26.md:64960): "the term 'alternative minimum
    # taxable income' means the taxable income... determined with the
    # adjustments provided in section 56 and increased by the amount of
    # the items of tax preference described in section 57"
    amti: float = 0.0
    # AMT exemption amount — shields a portion of AMTI from the AMT rates.
    # Phases out at 25 cents per dollar of AMTI above the threshold.
    # IRC §55(d)(1) (title26.md:64960): "the exemption amount... $78,750
    # in the case of a joint return... $50,600 in the case of an individual
    # who is not married"
    amt_exemption: float = 0.0
    # The tentative minimum tax — computed by applying AMT rates (26%/28%)
    # to AMTI minus the exemption. AMT is owed only if this exceeds regular
    # tax.
    # IRC §55(b)(1)(A) (title26.md:64948): "26 percent of so much of the
    # taxable excess as does not exceed $175,000, plus 28 percent of so
    # much of the taxable excess as exceeds $175,000"
    tentative_minimum_tax: float = 0.0
    # The AMT amount — the excess of tentative minimum tax over regular
    # income tax. This additional tax ensures high-income taxpayers with
    # large preference items pay at least a minimum level of tax.
    # IRC §55(a) (title26.md:64924): "a tax equal to the excess (if any)
    # of the tentative minimum tax for the taxable year, over the regular
    # tax for the taxable year"
    amt: float = 0.0
    # Prior-year AMT credit used this year — recovers AMT paid in prior
    # years when your regular tax exceeds the tentative minimum tax.
    # IRC §53(a) (title26.md:64700): "There shall be allowed as a credit
    # against the tax imposed... an amount equal to the minimum tax credit"
    prior_year_amt_credit_used: float = 0.0

    # Your net investment income — interest, dividends, capital gains,
    # rents, royalties, and passive income, minus investment expenses.
    # Used for the 3.8% NIIT calculation.
    # IRC §1411(c)(1) (title26.md:381140): "net investment income means...
    # gross income from interest, dividends, annuities, royalties, and
    # rents... and net gain attributable to the disposition of property"
    net_investment_income: float = 0.0
    # The Net Investment Income Tax — 3.8% of the lesser of your net
    # investment income or MAGI exceeding the threshold ($200k single /
    # $250k joint).
    # IRC §1411(a)(1) (title26.md:381140): "a tax equal to 3.8 percent of
    # the lesser of (A) the net investment income... or (B) the excess...
    # of modified adjusted gross income... over the threshold amount"
    niit_amount: float = 0.0

    # The Additional Medicare Tax on wages exceeding the threshold ($200k
    # single / $250k joint). This 0.9% surtax is in addition to the regular
    # 1.45% Medicare tax.
    # IRC §3101(b)(2) (title26.md:403879): "a tax equal to 0.9 percent of
    # the wages... received by the individual... which are in excess of...
    # $200,000"
    additional_medicare_tax: float = 0.0
    # Additional Medicare Tax already withheld by your employer(s). Your
    # employer must start withholding once wages exceed $200k, regardless
    # of your filing status.
    # IRC §3102(f) (title26.md:404346): employer withholding requirements
    # for the additional Medicare tax.
    additional_medicare_tax_withheld: float = 0.0

    # Extra tax on a child's unearned income (the "kiddie tax") — the
    # difference between the tax at the parent's rate and the child's rate
    # on investment income above the threshold.
    # IRC §1(g)(1) (title26.md:5520): "the tax imposed by this section shall
    # be equal to the greater of (A) the tax imposed... without regard to
    # this subsection, or (B) the sum of the tax which would be imposed...
    # if the taxable income... were reduced by the net unearned income...
    # plus such child's share of the allocable parental tax"
    kiddie_tax_amount: float = 0.0

    # Total tax before credits — the sum of income tax, AMT, NIIT,
    # additional Medicare tax, and kiddie tax. Credits are subtracted
    # from this amount.
    # IRC §1 (title26.md:5292), §55 (title26.md:64924), §1411, §3101(b)(2),
    # §1(g) — combined tax before credit offsets.
    total_tax_before_credits: float = 0.0


@dataclass
class CreditComputation:
    """Tax credit computation.

    Nonrefundable credits reduce tax to zero; refundable credits can produce a refund.
    """

    # Credit for child and dependent care expenses — helps working parents
    # offset the cost of daycare and similar care for children under 13.
    # IRC §21(a) (title26.md:12007): "there shall be allowed as a credit...
    # an amount equal to the applicable percentage of the employment-related
    # expenses paid by such individual"
    child_dependent_care_credit: float = 0.0
    # Credit for taxpayers age 65+ or permanently/totally disabled with low
    # income. Equal to 15% of the Section 22 amount after reductions.
    # IRC §22(a) (title26.md:12756): "there shall be allowed as a credit...
    # an amount equal to 15 percent of such individual's section 22 amount"
    elderly_disabled_credit: float = 0.0
    # Nonrefundable portion of education credits — AOTC (60% nonrefundable)
    # and Lifetime Learning Credit (100% nonrefundable).
    # IRC §25A(a) (title26.md:16106): "there shall be allowed as a credit...
    # the American Opportunity Tax Credit, plus the Lifetime Learning Credit"
    education_credits: float = 0.0
    # Retirement Savings Contributions Credit — up to 50% of retirement
    # contributions (max $2,000) for lower-income workers.
    # IRC §25B(a) (title26.md:16825): "there shall be allowed as a credit...
    # an amount equal to the applicable percentage of so much of the
    # qualified retirement savings contributions... as does not exceed $2,000"
    savers_credit: float = 0.0
    # Nonrefundable portion of the Child Tax Credit — $2,200 per qualifying
    # child under age 17 for 2025.
    # IRC §24(a) (title26.md:13963): "There shall be allowed as a credit...
    # for the taxable year with respect to each qualifying child"
    child_tax_credit_nonrefundable: float = 0.0
    # Credit for other dependents (not qualifying children under 17) — $500
    # per qualifying dependent. Nonrefundable.
    # IRC §24(h)(4) (title26.md:14162): "$500 credit for other dependents"
    other_dependent_credit: float = 0.0
    # Nonrefundable portion of the adoption credit — qualified adoption
    # expenses up to ~$17,280 (2025), minus the $5,000 refundable portion.
    # IRC §23(a) (title26.md:13227): "there shall be allowed as a credit...
    # the amount of the qualified adoption expenses paid or incurred"
    adoption_credit_nonrefundable: float = 0.0
    # Credit for energy-efficient home improvements — 30% of qualifying
    # expenditures with annual caps ($1,200 general / $2,000 heat pumps).
    # IRC §25C(a) (title26.md:17281): "30 percent of the sum of the amount
    # paid or incurred... for qualified energy efficiency improvements"
    energy_home_improvement_credit: float = 0.0
    # Credit for residential clean energy systems — 30% of expenditures for
    # solar, wind, geothermal, and battery storage with no dollar cap.
    # IRC §25D(a) (title26.md:18115): "there shall be allowed as a credit...
    # the applicable percentages of the qualified solar electric property
    # expenditures"
    residential_clean_energy_credit: float = 0.0
    # Prior-year §25D credit carryforward applied this year. Unused
    # residential clean energy credits carry forward to future years.
    # IRC §25D(c) (title26.md:18156): unused credit carryforward provisions.
    energy_credit_carryforward_used: float = 0.0
    # §25D credit remaining unused after this year (carries to next year).
    # IRC §25D(c) (title26.md:18156): credit carryforward.
    energy_credit_carryforward_remaining: float = 0.0
    # Credit for income taxes paid to foreign countries — prevents double
    # taxation on foreign-source income.
    # IRC §27(a) (title26.md:19867): "the amount of taxes imposed by
    # foreign countries and possessions of the United States"
    # IRC §901(a) (title26.md:319129): "the tax imposed by this chapter
    # shall be credited with the amounts... of taxes paid or accrued...
    # to any foreign country"
    foreign_tax_credit: float = 0.0
    # Credit for purchasing a new clean vehicle (§30D, up to $7,500) or
    # previously-owned clean vehicle (§25E, up to $4,000).
    # IRC §30D(a) (title26.md:21693): "There shall be allowed as a credit
    # ... an amount equal to the sum of the credit amounts... with respect
    # to each new clean vehicle placed in service"
    clean_vehicle_credit: float = 0.0
    # Sum of all nonrefundable credits, limited to the tax liability before
    # credits. Nonrefundable credits can reduce your tax to zero but
    # cannot produce a refund.
    # IRC §26(a) (title26.md:19070): limitation on nonrefundable credits.
    total_nonrefundable_credits: float = 0.0

    # Refundable portion of the Child Tax Credit (Additional Child Tax
    # Credit) — up to $1,400 per child, equal to 15% of earned income
    # over $2,500.
    # IRC §24(d) (title26.md:14182): "the credit... shall not exceed the
    # excess of... 15 percent of so much of the taxpayer's earned income...
    # as exceeds $2,500"
    additional_child_tax_credit: float = 0.0
    # The Earned Income Tax Credit — a refundable credit for lower-income
    # workers that can result in a refund even with no tax owed. Amount
    # depends on earned income, filing status, and number of children.
    # IRC §32(a) (title26.md:22751): "there shall be allowed as a credit...
    # an amount equal to the credit percentage of so much of the taxpayer's
    # earned income for the taxable year as does not exceed the earned
    # income amount"
    earned_income_credit: float = 0.0
    # If the EITC was denied, the reason for disqualification — such as
    # excess investment income, missing SSN, or prior fraud.
    # IRC §32(i) (title26.md:23033): "if the aggregate amount of disqualified
    # income of the taxpayer... exceeds $10,000" and other eligibility rules.
    eitc_disqualification_reason: str = ""
    # Refundable portion of the American Opportunity Tax Credit — 40% of the
    # AOTC is refundable, up to $1,000 per student.
    # IRC §25A(i)(1) (title26.md:16422): "40 percent of the credit... shall
    # be treated as a credit allowable under subpart C (and not allowed under
    # subsection (a))" — i.e. refundable.
    aotc_refundable: float = 0.0
    # Net Premium Tax Credit for ACA marketplace coverage — the computed
    # credit minus advance payments already received during the year.
    # IRC §36B(a) (title26.md:27167): "there shall be allowed as a credit
    # against the tax imposed... an amount equal to the premium assistance
    # credit amount"
    premium_tax_credit: float = 0.0
    # Amount of excess advance PTC that must be repaid — when the advance
    # payments your insurer received exceeded the actual credit you qualify
    # for based on your final income. Subject to repayment caps at lower
    # income levels.
    # IRC §36B(f)(1) (title26.md:27167): "If the advance payments... exceed
    # the credit allowed... the tax imposed... shall be increased by the
    # amount of such excess"
    excess_advance_ptc_repayment: float = 0.0
    # Refundable portion of the adoption credit — up to $5,000.
    # IRC §23(a)(4) (title26.md:13261): refundable adoption credit amount.
    adoption_credit_refundable: float = 0.0
    # Unused nonrefundable adoption credit that carries forward to next
    # year (up to 5 years).
    # IRC §23(c) (title26.md:13317): "such excess shall be carried to the
    # succeeding taxable year... but not for more than 5 taxable years"
    adoption_credit_carryforward: float = 0.0
    # Sum of all refundable credits. Refundable credits can exceed your tax
    # liability and result in a refund payment to you.
    # Various IRC sections — refundable credits include EITC (§32), ACTC
    # (§24(d)), refundable AOTC (§25A(i)), PTC (§36B), and adoption (§23).
    total_refundable_credits: float = 0.0

    # Grand total of all credits — nonrefundable (capped at tax liability)
    # plus refundable (can produce a refund).
    total_credits: float = 0.0


@dataclass
class SelfEmploymentTaxComputation:
    """Self-employment tax computation.

    IRC §1401 (title26.md:377596) — SE tax rates.
    """

    # Your total net self-employment earnings from all businesses, farms,
    # and activities subject to SE tax.
    # IRC §1402(a) (title26.md:378900): "the term 'net earnings from
    # self-employment' means the gross income derived by an individual
    # from any trade or business carried on by such individual"
    net_se_earnings: float = 0.0
    # SE tax base — 92.35% of net SE earnings. This reduction mimics the
    # fact that employers pay half of FICA for their employees.
    # IRC §1402(a) (title26.md:378900): "the net earnings from self-employment
    # derived by an individual from any trade or business carried on by
    se_tax_base: float = 0.0
    # Social Security (OASDI) portion of SE tax — 12.4% of the SE tax
    # base, up to the annual wage base ($176,100 for 2025), reduced by
    # any W-2 Social Security wages already taxed.
    # IRC §1401(a) (title26.md:377596): "a tax equal to 12.4 percent of
    # the amount of the self-employment income"
    oasdi_tax: float = 0.0
    # Medicare portion of SE tax — 2.9% of the entire SE tax base with
    # no annual limit.
    # IRC §1401(b)(1) (title26.md:377611): "a tax equal to 2.9 percent of
    # the amount of the self-employment income"
    medicare_tax: float = 0.0
    # Additional Medicare Tax on SE income — 0.9% on SE income exceeding
    # the threshold ($250k joint / $200k single / $125k MFS).
    # IRC §1401(b)(2)(A) (title26.md:377621): "a tax equal to 0.9 percent
    # of the self-employment income... which is in excess of... $250,000
    # in the case of a joint return"
    additional_medicare_tax: float = 0.0
    # Total self-employment tax — OASDI + Medicare + Additional Medicare.
    # IRC §1401 (title26.md:377596): combined SE tax rates.
    total_se_tax: float = 0.0
    # The above-the-line deduction for 50% of your SE tax, which reduces
    # your AGI. This mirrors the employer portion of FICA that W-2
    # employees never see on their returns.
    # IRC §164(f) (title26.md:119500): "one-half of the taxes imposed by
    # section 1401 for the taxable year shall be allowed as a deduction"
    se_tax_deduction: float = 0.0


@dataclass
class PenaltyComputation:
    """Estimated tax penalty computation.

    IRC §6654 (title26.md:568042) — underpayment penalty.
    """

    # The minimum amount you were required to pay during the year through
    # withholding and/or estimated tax payments — the lesser of 90% of
    # current-year tax or 100% of prior-year tax (110% if prior AGI >$150k).
    # IRC §6654(d)(1) (title26.md:566370): "the term 'required annual
    # payment' means the lesser of (A) 90 percent of the tax shown on the
    # return... or (B) 100 percent of the tax shown on the return of the
    # individual for the preceding taxable year"
    required_annual_payment: float = 0.0
    # Total of all federal income tax withholding (from W-2s, 1099s, etc.)
    # plus estimated tax payments actually made during the year.
    # IRC §31(a) (title26.md:22615): withholding credits; IRC §6654(c)
    # (title26.md:566360): required installment payments.
    total_payments_and_withholding: float = 0.0
    # Penalty for underpayment of estimated tax. Charged at the federal
    # short-term rate plus 3% on the underpaid amount for the period of
    # underpayment.
    # IRC §6654(a) (title26.md:568042): "there shall be added to the tax...
    # an amount determined by applying the underpayment rate... to the
    # amount of the underpayment, for the period of the underpayment"
    estimated_tax_penalty: float = 0.0
    # Whether the estimated tax penalty was waived — because the balance
    # due was under $1,000, you had no tax liability last year, or you met
    # the safe harbor by paying enough through withholding/estimated payments.
    # IRC §6654(e)(1) (title26.md:566527): "No addition to tax shall be
    # imposed... if the tax shown on the return... less the amount of the
    # credit... is less than $1,000"
    penalty_waived: bool = False


@dataclass
class PaymentSummary:
    """Summary of all tax payments.

    IRC §31 (title26.md:22615) — withholding credits.
    """

    # Total federal income tax withheld from all sources — W-2 wages,
    # retirement distributions, unemployment, gambling winnings, annuities,
    # and any additional Medicare tax withheld.
    # IRC §31(a) (title26.md:22615): "The amount withheld as tax under
    # chapter 24 shall be allowed to the recipient of the income as a
    # credit against the tax imposed by this subtitle"
    federal_income_tax_withheld: float = 0.0
    # Total quarterly estimated tax payments you made during the year
    # (Form 1040-ES).
    # IRC §6654(c)(2) (title26.md:566360): "25 percent of the required
    # annual payment" for each of the four installment periods.
    estimated_tax_payments: float = 0.0
    # Amount applied from your prior-year tax refund toward this year's
    # estimated tax liability.
    # IRC §6402(b) (title26.md:542923): "the Secretary... may credit the
    # amount of such overpayment... against any liability... of such person"
    amount_applied_from_prior_year: float = 0.0
    # Excess Social Security tax withheld when you had multiple employers
    # and total wages exceeded the SS wage base. Claimed as a credit.
    # IRC §31(b) (title26.md:22636): credit for "special refunds of social
    # security tax" when withholding exceeds the maximum.
    excess_social_security_withheld: float = 0.0
    # Other payments and credits — backup withholding (Form 1099 Box 4),
    # excess advance premium tax credit repayment, and similar.
    # IRC §31(a) (title26.md:22615): withholding credit provisions.
    other_payments: float = 0.0
    # Grand total of all payments toward your tax liability — withholding,
    # estimated payments, prior-year overpayment, SS excess, and other.
    # Form 1040, Line 33 — Total Payments.
    total_payments: float = 0.0


@dataclass
class TaxReturnOutput:
    """Complete computed federal individual income tax return.

    This model contains all calculated fields that would appear on
    Form 1040 and associated schedules.
    """

    # The tax year this return covers (e.g. 2025).
    # IRC §441(a) (title26.md:236260): "Taxable income shall be computed
    # on the basis of the taxpayer's taxable year"
    tax_year: int
    # The filing status used on this return — determines tax brackets,
    # standard deduction, and eligibility for various benefits.
    # IRC §2 (title26.md:10051): filing status definitions.
    filing_status: FilingStatus
    # Detailed breakdown of all income items and how they sum to gross income.
    # IRC §61 (title26.md:70846): "gross income means all income from
    # whatever source derived"
    income: IncomeComputation = field(default_factory=IncomeComputation)
    # Above-the-line deductions and the resulting Adjusted Gross Income.
    # IRC §62 (title26.md:71233): "adjusted gross income means... gross
    # income minus the following deductions"
    agi: AGIComputation = field(default_factory=AGIComputation)
    # Standard or itemized deductions, QBI, and resulting taxable income.
    # IRC §63 (title26.md:72402): "the term 'taxable income' means gross
    # income minus the deductions allowed by this chapter"
    deductions: DeductionComputation = field(default_factory=DeductionComputation)
    # Tax computation including brackets, capital gains rates, AMT, NIIT,
    # and additional Medicare tax.
    # IRC §1 (title26.md:5292): "There is hereby imposed on the taxable
    # income of every individual... a tax"
    tax: TaxComputation = field(default_factory=TaxComputation)
    # All tax credits — nonrefundable and refundable — that reduce your
    # tax liability.
    # Various IRC sections (§21-§36B): credits against income tax.
    credits: CreditComputation = field(default_factory=CreditComputation)
    # Self-employment tax computation for business owners and freelancers.
    # IRC §1401 (title26.md:377596): "there shall be imposed... on the
    # self-employment income of every individual, a tax"
    se_tax: SelfEmploymentTaxComputation = field(
        default_factory=SelfEmploymentTaxComputation
    )
    # Estimated tax penalty computation.
    # IRC §6654 (title26.md:568042): "in the case of any underpayment of
    # estimated tax... there shall be added to the tax... an amount"
    penalty: PenaltyComputation = field(default_factory=PenaltyComputation)
    # Summary of all tax payments (withholding + estimated + other).
    # IRC §31 (title26.md:22615): tax withheld on wages.
    payments: PaymentSummary = field(default_factory=PaymentSummary)

    # Your total tax liability after all credits, plus SE tax, penalties,
    # and surtaxes, minus refundable credits. This is what you owe for the
    # year before comparing to payments made.
    # Form 1040, Line 37 — Total Tax.
    total_tax: float = 0.0
    # Total of all payments made toward your tax (withholding, estimated
    # payments, prior-year overpayment applied, etc.).
    # Form 1040, Line 33 — Total Payments.
    total_payments: float = 0.0
    # If your payments exceeded your tax — this is your refund amount.
    # IRC §6402(a) (title26.md:542923): "In the case of any overpayment,
    # the Secretary... may credit the amount of such overpayment...
    # against any liability... and shall... refund any balance to such
    # person"
    overpayment: float = 0.0
    # If your tax exceeded your payments — this is the additional amount
    # you owe with your return.
    # IRC §6151(a) (title26.md:527517): "the tax... shall... be paid at the
    # time and place fixed for filing the return"
    amount_owed: float = 0.0
    # Your effective tax rate — total tax divided by gross income. Shows
    # the actual percentage of your income that went to federal taxes,
    # accounting for all deductions, credits, and preferential rates.
    # Informational — not defined in IRC; computed as total_tax / gross_income.
    effective_tax_rate: float = 0.0
    # Your marginal tax rate — the rate that applies to the last dollar of
    # your ordinary taxable income. This is the bracket rate you're "in."
    # IRC §1(j) (title26.md:6120): progressive rate brackets from 10% to 37%.
    marginal_tax_rate: float = 0.0

    # Capital losses exceeding this year's $3,000 limit, carried forward
    # to offset future gains. Never expires.
    # IRC §1212(b) (title26.md:350269): "short-term capital loss... shall be
    # treated as a short-term capital loss... in the succeeding taxable year"
    capital_loss_carryforward: float = 0.0
    # Short-term portion of capital loss carryforward — retains character.
    # IRC §1212(b)(1) (title26.md:350269): carried forward as short-term.
    capital_loss_carryforward_short: float = 0.0
    # Long-term portion of capital loss carryforward — retains character.
    # IRC §1212(b)(2) (title26.md:350280): carried forward as long-term.
    capital_loss_carryforward_long: float = 0.0
    # Charitable contributions exceeding this year's AGI limits, carried
    # forward up to 5 years.
    # IRC §170(d)(1) (title26.md:132765): "treated as a charitable
    # contribution... in each of the 5 succeeding taxable years"
    charitable_contribution_carryforward: float = 0.0
    # Unused AMT credit from prior years, available to offset future regular
    # tax in excess of tentative minimum tax.
    # IRC §53(a) (title26.md:64700): "There shall be allowed as a credit...
    # an amount equal to the minimum tax credit for such taxable year"
    amt_credit_carryforward: float = 0.0
    # Net operating loss remaining after this year's deduction, available
    # to carry forward indefinitely (post-2017 NOLs).
    # IRC §172(b) (title26.md:137760): indefinite carryforward for post-2017
    # net operating losses.
    nol_carryforward_remaining: float = 0.0
    # Investment interest expense exceeding net investment income, carried
    # forward to deduct in future years.
    # IRC §163(d)(2) (title26.md:116560): "the amount not allowed... shall
    # be treated as investment interest paid or accrued... in the succeeding
    # taxable year"
    investment_interest_carryforward: float = 0.0
    # Unused residential clean energy credit (§25D) carried forward.
    # IRC §25D(c) (title26.md:18156): unused credit carryforward.
    energy_credit_carryforward: float = 0.0
    # Penalty on the earnings portion of non-qualified 529 plan
    # distributions — 10% of taxable earnings from non-education withdrawals.
    # IRC §529(c)(6) (title26.md:263550): "the tax imposed... shall be
    # increased by an amount equal to 10 percent of the portion of such
    # amount which is includible in gross income"
    section_529_penalty: float = 0.0


# ---------------------------------------------------------------------------
# JSON Schema Generation Utility
# ---------------------------------------------------------------------------

_PYTHON_TO_JSON_TYPE = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _clean_docstring(doc: str) -> str:
    """Clean a Python docstring for use as a JSON Schema description.

    Preserves all content including IRC section references, but normalizes
    indentation and collapses internal whitespace.
    """
    if not doc:
        return ""
    lines = doc.strip().splitlines()
    cleaned: list[str] = []
    for line in lines:
        cleaned.append(line.strip())
    # Join lines, preserving paragraph breaks (blank lines)
    result_parts: list[str] = []
    for line in cleaned:
        if line:
            result_parts.append(line)
        elif result_parts and result_parts[-1] != "":
            result_parts.append("")
    return "\n".join(result_parts).strip()


def _extract_field_comments(cls) -> dict[str, str]:
    """Extract inline and section-header comments for dataclass fields.

    Parses the source code of *cls* to find comments associated with each
    field.  Handles three patterns:

    1. Inline comment on the same line as the field definition::

           wages: float  # IRC §61(a)(1)

    2. Inline comment on a continuation/closing line of a multi-line
       field definition::

           scholarship_income: list[ScholarshipIncome] = field(
               default_factory=list
           )  # IRC §117

    3. Section-header comment preceding a group of fields::

           # Income sources — IRC §61 (title26.md:70846)
           w2_income: list[W2Income] = field(default_factory=list)

    Returns a mapping of ``{field_name: comment_text}``.
    """
    try:
        source = inspect.getsource(cls)
    except (OSError, TypeError):
        return {}

    field_names = {f.name for f in fields(cls)}
    comments: dict[str, str] = {}
    src_lines = source.splitlines()

    # comment_block accumulates consecutive ``#`` lines that precede a
    # field definition.  section_comment is a single-line fallback that
    # persists across multiple fields (backward-compatible with the old
    # "section header" pattern).
    comment_block: list[str] = []
    section_comment = ""

    i = 0
    while i < len(src_lines):
        line = src_lines[i]
        stripped = line.strip()

        # Skip blank lines — do NOT reset comment_block so that a blank
        # line between a comment block and its field is tolerated.
        if not stripped:
            i += 1
            continue

        # Standalone comment line — accumulate into the current block.
        if stripped.startswith("#"):
            comment_block.append(stripped.lstrip("# ").strip())
            i += 1
            continue

        # Docstring lines (triple-quote) — skip entire block.
        if stripped.startswith('"""') or stripped.startswith("'''"):
            quote = stripped[:3]
            # Single-line docstring (open and close on same line)
            if stripped.count(quote) >= 2:
                i += 1
                continue
            # Multi-line docstring — skip until closing triple-quote
            i += 1
            while i < len(src_lines):
                if quote in src_lines[i]:
                    break
                i += 1
            i += 1
            continue

        # Try to match a field definition start: ``  field_name: type``
        m = re.match(r"\s+(\w+)\s*:", line)
        if m and m.group(1) in field_names:
            fname = m.group(1)

            # Collect all source lines that belong to this field
            # definition (may span multiple lines due to parentheses).
            field_lines = [line]
            paren_depth = line.count("(") - line.count(")")
            j = i + 1
            while paren_depth > 0 and j < len(src_lines):
                field_lines.append(src_lines[j])
                paren_depth += src_lines[j].count("(") - src_lines[j].count(")")
                j += 1

            # Search the collected lines for the first ``#`` comment.
            inline_comment = ""
            for fl in field_lines:
                if "#" in fl:
                    inline_comment = fl.split("#", 1)[1].strip()
                    break

            # --- Priority for assigning a description ---
            # 1. Multi-line comment block (2+ lines) — dedicated to this
            #    field; consumed and section_comment reset.
            # 2. Single-line comment block — treated as a section header
            #    (persists for subsequent uncommented fields).
            # 3. Inline comment on the field definition itself.
            # 4. Lingering section_comment from an earlier header.
            if len(comment_block) > 1:
                comments[fname] = " ".join(comment_block)
                comment_block = []
                section_comment = ""
            elif len(comment_block) == 1:
                section_comment = comment_block[0]
                comments[fname] = section_comment
                comment_block = []
            elif inline_comment:
                comments[fname] = inline_comment
            elif section_comment:
                comments[fname] = section_comment

            i = max(i + 1, j)
            continue

        # Non-field, non-comment line (e.g. method/class def) resets
        # both the comment block and section comment.
        if stripped.startswith("def ") or stripped.startswith("class "):
            comment_block = []
            section_comment = ""

        i += 1

    return comments


def _resolve_type(tp, module_globals=None):
    """Convert a Python type annotation to a JSON Schema fragment."""

    origin = get_origin(tp)
    args = get_args(tp)

    # Optional[X] is Union[X, None]
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            inner = _resolve_type(non_none[0], module_globals)
            return {**inner, "nullable": True}
        return {}

    # list[X]
    if origin is list:
        item_type = args[0] if args else str
        return {"type": "array", "items": _resolve_type(item_type, module_globals)}

    # dict (for bracket details etc.)
    if origin is dict or tp is dict:
        return {"type": "object"}

    # Enum — include docstring with IRC references as description
    if isinstance(tp, type) and issubclass(tp, Enum):
        schema: dict = {"type": "string", "enum": [e.value for e in tp]}
        if tp.__doc__:
            schema["description"] = _clean_docstring(tp.__doc__)
        return schema

    # Dataclass — nested object
    if dataclasses.is_dataclass(tp):
        return dataclass_to_json_schema(tp)

    # Primitive types
    if tp in _PYTHON_TO_JSON_TYPE:
        return {"type": _PYTHON_TO_JSON_TYPE[tp]}

    return {"type": "string"}


def dataclass_to_json_schema(cls) -> dict:
    """Generate a JSON Schema dict from a @dataclass class.

    Supports nested dataclasses, Optional, list, Enum, and primitive types.
    Class-level descriptions use the full docstring (including IRC section
    references).  Field-level descriptions are extracted from inline source
    comments and section-header comments.
    """
    if not dataclasses.is_dataclass(cls):
        raise TypeError(f"{cls} is not a dataclass")

    hints = get_type_hints(cls)
    field_comments = _extract_field_comments(cls)
    properties = {}
    required = []

    for f in fields(cls):
        tp = hints[f.name]
        schema = _resolve_type(tp)

        # Determine if required (no default and not Optional)
        origin = get_origin(tp)
        args = get_args(tp)
        is_optional = origin is Union and type(None) in args

        if (
            f.default is dataclasses.MISSING
            and f.default_factory is dataclasses.MISSING
        ):
            if not is_optional:
                required.append(f.name)

        # Attach field-level description from source comments
        if f.name in field_comments:
            schema["description"] = field_comments[f.name]

        properties[f.name] = schema

    result = {
        "type": "object",
        "properties": properties,
    }
    if required:
        result["required"] = required

    # Use the full cleaned docstring (with IRC references) as the
    # class-level description instead of only the first line.
    if cls.__doc__:
        result["description"] = _clean_docstring(cls.__doc__)

    return result


def generate_schema(cls, title: str = "") -> dict:
    """Generate a complete JSON Schema document from a dataclass."""
    schema = dataclass_to_json_schema(cls)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    if title:
        schema["title"] = title
    elif hasattr(cls, "__name__"):
        schema["title"] = cls.__name__
    return schema


if __name__ == "__main__":
    input_schema = generate_schema(TaxReturnInput, "TaxReturnInput")
    output_schema = generate_schema(TaxReturnOutput, "TaxReturnOutput")

    print("=== Input Schema ===")
    print(json.dumps(input_schema, indent=2))
    print("\n=== Output Schema ===")
    print(json.dumps(output_schema, indent=2))
