import { h, render } from 'preact';
import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import { html } from 'htm/preact';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STORAGE_KEY = 'tax-wizard-state';

function saveState(state) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch {}
}
function loadState() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch { return null; }
}
function clearSaved() {
  try { localStorage.removeItem(STORAGE_KEY); } catch {}
}

const fmt = (n) => {
  if (n == null || isNaN(n)) return '$0.00';
  const abs = Math.abs(n);
  const s = abs.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return n < 0 ? `-$${s}` : `$${s}`;
};

const US_STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'];

const FORM_NAMES = {
  f1040: 'Form 1040', f1040s1: 'Schedule 1', f1040s2: 'Schedule 2',
  f1040s3: 'Schedule 3', f1040sa: 'Schedule A', f1040sb: 'Schedule B',
  f1040sc: 'Schedule C', f1040sd: 'Schedule D', f1040se: 'Schedule E',
  f1040sf: 'Schedule F', f1040sse: 'Schedule SE', f8949: 'Form 8949',
  f2441: 'Form 2441',
};

// ─── Default State ────────────────────────────────────────────────────────────

function defaultState() {
  return {
    stepIndex: 0,
    tax_year: 2025,
    filing_status: 'single',
    personal_info: { first_name: '', last_name: '', ssn: '', date_of_birth: '', is_blind: false, occupation: '' },
    spouse_info: { first_name: '', last_name: '', ssn: '', date_of_birth: '', is_blind: false, occupation: '' },
    address: { street: '', city: '', state: '', zip_code: '' },
    hasDependents: false,
    dependents: [],
    incomeTypes: {
      w2: false, interest: false, dividends: false, capitalGains: false,
      business: false, rental: false, retirement: false,
      socialSecurity: false, unemployment: false, other: false,
    },
    w2_income: [],
    interest_income: [],
    dividend_income: [],
    capital_gains_losses: [],
    business_income: [],
    rental_income: [],
    retirement_distributions: [],
    social_security: { total_benefits: 0 },
    unemployment: { amount: 0 },
    other_income: [],
    // Adjustments
    educator_expenses: 0,
    student_loan_interest_paid: 0,
    hasHSA: false,
    hsa: { is_self_only_coverage: true, taxpayer_contributions: 0, employer_contributions: 0, distributions: 0, qualified_medical_expenses_from_hsa: 0 },
    // Deductions
    deduction_method: 'standard',
    medical_expenses: { total_medical_dental: 0, health_insurance_premiums: 0, prescription_drugs: 0, medical_travel: 0 },
    state_local_taxes: { state_income_tax_paid: 0, real_property_tax: 0, personal_property_tax: 0 },
    mortgage_interest: [],
    charitable_contributions: [],
    // Credits
    hasEducationCredits: false,
    education_expenses: [],
    hasChildCare: false,
    child_care_expenses: [],
    // Payments
    estimated_tax_payments: { q1_amount: 0, q2_amount: 0, q3_amount: 0, q4_amount: 0 },
    prior_year_agi: 0,
    prior_year_tax: 0,
    // Results
    results: null,
    errors: null,
    calculating: false,
  };
}

// ─── Reusable Field Components ────────────────────────────────────────────────

function TextField({ label, hint, value, onChange, type = 'text', placeholder, required, ...rest }) {
  return html`<div class="field">
    <label>${label}${required ? html` <span style="color:var(--danger)">*</span>` : ''}</label>
    ${hint ? html`<div class="hint">${hint}</div>` : ''}
    <input type=${type} value=${value} placeholder=${placeholder}
      onInput=${e => onChange(type === 'number' ? (e.target.value === '' ? '' : parseFloat(e.target.value) || 0) : e.target.value)}
      ...${rest} />
  </div>`;
}

function MoneyField({ label, hint, value, onChange, ...rest }) {
  return html`<div class="field">
    <label>${label}</label>
    ${hint ? html`<div class="hint">${hint}</div>` : ''}
    <div class="currency-input">
      <input type="number" step="0.01" min="0" value=${value || ''}
        placeholder="0.00"
        onInput=${e => onChange(e.target.value === '' ? 0 : parseFloat(e.target.value) || 0)}
        ...${rest} />
    </div>
  </div>`;
}

function SelectField({ label, hint, value, onChange, options }) {
  return html`<div class="field">
    <label>${label}</label>
    ${hint ? html`<div class="hint">${hint}</div>` : ''}
    <select value=${value} onChange=${e => onChange(e.target.value)}>
      ${options.map(o => html`<option value=${o.value}>${o.label}</option>`)}
    </select>
  </div>`;
}

function Toggle({ label, checked, onChange }) {
  return html`<div class="toggle-row">
    <label class="toggle">
      <input type="checkbox" checked=${checked} onChange=${e => onChange(e.target.checked)} />
      <span class="toggle-slider" />
    </label>
    <span style="font-size:0.9rem">${label}</span>
  </div>`;
}

function RadioGroup({ label, options, value, onChange }) {
  return html`<div class="field">
    <label>${label}</label>
    <div class="radio-group">
      ${options.map(o => html`
        <label class="radio-option ${value === o.value ? 'selected' : ''}" onClick=${() => onChange(o.value)}>
          <input type="radio" name=${label} value=${o.value} checked=${value === o.value} />
          <div>
            <div class="option-label">${o.label}</div>
            ${o.desc ? html`<div class="option-desc">${o.desc}</div>` : ''}
          </div>
        </label>
      `)}
    </div>
  </div>`;
}

// ─── Step Definitions ─────────────────────────────────────────────────────────

function isMarried(s) {
  return s.filing_status === 'married_filing_jointly' || s.filing_status === 'married_filing_separately';
}

const STEPS = [
  { id: 'filing',      title: 'Filing Status',     show: () => true },
  { id: 'personal',    title: 'Personal Info',     show: () => true },
  { id: 'dependents',  title: 'Dependents',        show: () => true },
  { id: 'income-sel',  title: 'Income Sources',    show: () => true },
  { id: 'w2',          title: 'W-2 Income',        show: s => s.incomeTypes.w2 },
  { id: 'int-div',     title: 'Interest & Dividends', show: s => s.incomeTypes.interest || s.incomeTypes.dividends },
  { id: 'capgains',    title: 'Capital Gains',     show: s => s.incomeTypes.capitalGains },
  { id: 'business',    title: 'Business Income',   show: s => s.incomeTypes.business },
  { id: 'rental',      title: 'Rental Income',     show: s => s.incomeTypes.rental },
  { id: 'retirement',  title: 'Retirement & SS',   show: s => s.incomeTypes.retirement || s.incomeTypes.socialSecurity },
  { id: 'other-inc',   title: 'Other Income',      show: s => s.incomeTypes.unemployment || s.incomeTypes.other },
  { id: 'adjustments', title: 'Adjustments',       show: () => true },
  { id: 'deductions',  title: 'Deductions',        show: () => true },
  { id: 'credits',     title: 'Credits',           show: () => true },
  { id: 'payments',    title: 'Payments',          show: () => true },
  { id: 'review',      title: 'Review & Calculate', show: () => true },
];

// ─── STEP: Filing Status ──────────────────────────────────────────────────────

function StepFiling({ state, update }) {
  return html`
    <div class="card">
      <h2>Filing Status</h2>
      <p class="subtitle">Select your filing status for tax year ${state.tax_year}</p>
      <${RadioGroup} label="" value=${state.filing_status} onChange=${v => update({ filing_status: v })}
        options=${[
          { value: 'single', label: 'Single', desc: 'Unmarried or legally separated' },
          { value: 'married_filing_jointly', label: 'Married Filing Jointly', desc: 'Married and filing a combined return with your spouse' },
          { value: 'married_filing_separately', label: 'Married Filing Separately', desc: 'Married but filing your own separate return' },
          { value: 'head_of_household', label: 'Head of Household', desc: 'Unmarried and paying more than half the cost of keeping up a home for a qualifying person' },
          { value: 'qualifying_surviving_spouse', label: 'Qualifying Surviving Spouse', desc: 'Spouse died in the prior 2 years and you have a dependent child' },
        ]} />
    </div>
  `;
}

// ─── STEP: Personal Info ──────────────────────────────────────────────────────

function PersonFields({ title, info, onChange }) {
  const set = (k, v) => onChange({ ...info, [k]: v });
  return html`
    <h3 style="margin-bottom:12px;font-size:1rem">${title}</h3>
    <div class="input-row">
      <${TextField} label="First name" value=${info.first_name} onChange=${v => set('first_name', v)} required />
      <${TextField} label="Last name" value=${info.last_name} onChange=${v => set('last_name', v)} required />
    </div>
    <div class="input-row">
      <${TextField} label="SSN" value=${info.ssn} onChange=${v => set('ssn', v)} placeholder="XXX-XX-XXXX" required />
      <${TextField} label="Date of birth" value=${info.date_of_birth} onChange=${v => set('date_of_birth', v)} type="date" required />
    </div>
    <div class="input-row">
      <${TextField} label="Occupation" value=${info.occupation} onChange=${v => set('occupation', v)} />
      <div class="field" style="padding-top:22px">
        <${Toggle} label="Legally blind" checked=${info.is_blind} onChange=${v => set('is_blind', v)} />
      </div>
    </div>
  `;
}

function StepPersonal({ state, update }) {
  const married = isMarried(state);
  return html`
    <div class="card">
      <h2>Personal Information</h2>
      <p class="subtitle">Enter your details as they appear on your Social Security card</p>
      <${PersonFields} title="Your Information" info=${state.personal_info}
        onChange=${v => update({ personal_info: v })} />

      ${married ? html`
        <hr class="section-divider" />
        <${PersonFields} title="Spouse Information" info=${state.spouse_info}
          onChange=${v => update({ spouse_info: v })} />
      ` : ''}

      <hr class="section-divider" />
      <h3 style="margin-bottom:12px;font-size:1rem">Mailing Address</h3>
      <${TextField} label="Street address" value=${state.address.street}
        onChange=${v => update({ address: { ...state.address, street: v } })} />
      <div class="input-row-3">
        <${TextField} label="City" value=${state.address.city}
          onChange=${v => update({ address: { ...state.address, city: v } })} />
        <${SelectField} label="State" value=${state.address.state}
          onChange=${v => update({ address: { ...state.address, state: v } })}
          options=${[{ value: '', label: 'Select...' }, ...US_STATES.map(s => ({ value: s, label: s }))]} />
        <${TextField} label="ZIP" value=${state.address.zip_code}
          onChange=${v => update({ address: { ...state.address, zip_code: v } })} placeholder="00000" />
      </div>
    </div>
  `;
}

// ─── STEP: Dependents ─────────────────────────────────────────────────────────

function defaultDependent() {
  return { first_name: '', last_name: '', ssn: '', date_of_birth: '', relationship: 'qualifying_child',
    months_lived_with_taxpayer: 12, is_full_time_student: false, is_permanently_disabled: false, gross_income: 0, support_provided_by_taxpayer_pct: 1.0 };
}

function StepDependents({ state, update }) {
  const deps = state.dependents;
  const setDep = (i, k, v) => {
    const next = [...deps];
    next[i] = { ...next[i], [k]: v };
    update({ dependents: next });
  };
  const addDep = () => update({ dependents: [...deps, defaultDependent()] });
  const removeDep = (i) => update({ dependents: deps.filter((_, j) => j !== i) });

  return html`
    <div class="card">
      <h2>Dependents</h2>
      <p class="subtitle">People you financially support who qualify for tax benefits</p>

      <${Toggle} label="I have dependents to claim" checked=${state.hasDependents}
        onChange=${v => update({ hasDependents: v, dependents: v ? (deps.length ? deps : [defaultDependent()]) : [] })} />

      ${state.hasDependents ? html`
        ${deps.map((d, i) => html`
          <div class="item-card" key=${i}>
            <div class="item-card-header">
              <h4>Dependent ${i + 1}</h4>
              <button class="btn btn-danger btn-sm" onClick=${() => removeDep(i)}>Remove</button>
            </div>
            <div class="input-row">
              <${TextField} label="First name" value=${d.first_name} onChange=${v => setDep(i, 'first_name', v)} />
              <${TextField} label="Last name" value=${d.last_name} onChange=${v => setDep(i, 'last_name', v)} />
            </div>
            <div class="input-row">
              <${TextField} label="SSN" value=${d.ssn} onChange=${v => setDep(i, 'ssn', v)} placeholder="XXX-XX-XXXX" />
              <${TextField} label="Date of birth" value=${d.date_of_birth} onChange=${v => setDep(i, 'date_of_birth', v)} type="date" />
            </div>
            <div class="input-row">
              <${SelectField} label="Relationship" value=${d.relationship}
                onChange=${v => setDep(i, 'relationship', v)}
                options=${[
                  { value: 'qualifying_child', label: 'Qualifying Child' },
                  { value: 'qualifying_relative', label: 'Qualifying Relative' },
                ]} />
              <${TextField} label="Months lived with you" value=${d.months_lived_with_taxpayer}
                onChange=${v => setDep(i, 'months_lived_with_taxpayer', parseInt(v) || 0)} type="number" />
            </div>
            <div style="display:flex;gap:16px;flex-wrap:wrap">
              <${Toggle} label="Full-time student" checked=${d.is_full_time_student}
                onChange=${v => setDep(i, 'is_full_time_student', v)} />
              <${Toggle} label="Permanently disabled" checked=${d.is_permanently_disabled}
                onChange=${v => setDep(i, 'is_permanently_disabled', v)} />
            </div>
          </div>
        `)}
        <button class="add-btn" onClick=${addDep}>+ Add another dependent</button>
      ` : ''}
    </div>
  `;
}

// ─── STEP: Income Source Selection ────────────────────────────────────────────

function StepIncomeSelect({ state, update }) {
  const types = state.incomeTypes;
  const toggle = (k) => update({ incomeTypes: { ...types, [k]: !types[k] } });

  const options = [
    { key: 'w2', label: 'W-2 Wages', desc: 'Employment income' },
    { key: 'interest', label: 'Interest', desc: '1099-INT, savings, CDs' },
    { key: 'dividends', label: 'Dividends', desc: '1099-DIV, stocks, funds' },
    { key: 'capitalGains', label: 'Capital Gains/Losses', desc: 'Stock sales, property sales' },
    { key: 'business', label: 'Self-Employment', desc: 'Schedule C, 1099-NEC' },
    { key: 'rental', label: 'Rental Income', desc: 'Schedule E rental property' },
    { key: 'retirement', label: 'Retirement', desc: '1099-R, IRA, 401(k), pension' },
    { key: 'socialSecurity', label: 'Social Security', desc: 'SSA-1099 benefits' },
    { key: 'unemployment', label: 'Unemployment', desc: '1099-G compensation' },
    { key: 'other', label: 'Other Income', desc: 'Prizes, jury duty, etc.' },
  ];

  return html`
    <div class="card">
      <h2>Income Sources</h2>
      <p class="subtitle">Select all types of income you received in ${state.tax_year}</p>
      <div class="checkbox-grid">
        ${options.map(o => html`
          <label class="check-option ${types[o.key] ? 'selected' : ''}" key=${o.key}>
            <input type="checkbox" checked=${types[o.key]} onChange=${() => toggle(o.key)} />
            <div>
              <div class="option-label">${o.label}</div>
              <div class="option-desc">${o.desc}</div>
            </div>
          </label>
        `)}
      </div>
    </div>
  `;
}

// ─── STEP: W-2 Income ─────────────────────────────────────────────────────────

function defaultW2() {
  return { employer_name: '', employer_ein: '', wages: 0, federal_income_tax_withheld: 0,
    social_security_wages: 0, social_security_tax_withheld: 0, medicare_wages: 0, medicare_tax_withheld: 0,
    state_wages: 0, state_income_tax_withheld: 0 };
}

function StepW2({ state, update }) {
  const items = state.w2_income;
  const set = (i, k, v) => {
    const next = [...items]; next[i] = { ...next[i], [k]: v }; update({ w2_income: next });
  };
  const add = () => update({ w2_income: [...items, defaultW2()] });
  const remove = (i) => update({ w2_income: items.filter((_, j) => j !== i) });

  const displayItems = items.length ? items : [defaultW2()];
  useEffect(() => { if (!items.length) add(); }, []);

  return html`
    <div class="card">
      <h2>W-2 Wage Income</h2>
      <p class="subtitle">Enter information from each W-2 you received</p>
      ${displayItems.map((w, i) => html`
        <div class="item-card" key=${i}>
          <div class="item-card-header">
            <h4>${w.employer_name || `W-2 #${i + 1}`}</h4>
            ${items.length > 1 ? html`<button class="btn btn-danger btn-sm" onClick=${() => remove(i)}>Remove</button>` : ''}
          </div>
          <div class="input-row">
            <${TextField} label="Employer name" value=${w.employer_name} onChange=${v => set(i, 'employer_name', v)} />
            <${TextField} label="EIN" value=${w.employer_ein} onChange=${v => set(i, 'employer_ein', v)} placeholder="XX-XXXXXXX" />
          </div>
          <div class="input-row">
            <${MoneyField} label="Box 1: Wages, tips, compensation" value=${w.wages} onChange=${v => set(i, 'wages', v)} />
            <${MoneyField} label="Box 2: Federal tax withheld" value=${w.federal_income_tax_withheld} onChange=${v => set(i, 'federal_income_tax_withheld', v)} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Box 3: Social Security wages" value=${w.social_security_wages} onChange=${v => set(i, 'social_security_wages', v)} />
            <${MoneyField} label="Box 4: SS tax withheld" value=${w.social_security_tax_withheld} onChange=${v => set(i, 'social_security_tax_withheld', v)} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Box 5: Medicare wages" value=${w.medicare_wages} onChange=${v => set(i, 'medicare_wages', v)} />
            <${MoneyField} label="Box 6: Medicare tax withheld" value=${w.medicare_tax_withheld} onChange=${v => set(i, 'medicare_tax_withheld', v)} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Box 16: State wages" value=${w.state_wages} onChange=${v => set(i, 'state_wages', v)} />
            <${MoneyField} label="Box 17: State tax withheld" value=${w.state_income_tax_withheld} onChange=${v => set(i, 'state_income_tax_withheld', v)} />
          </div>
        </div>
      `)}
      <button class="add-btn" onClick=${add}>+ Add another W-2</button>
    </div>
  `;
}

// ─── STEP: Interest & Dividends ───────────────────────────────────────────────

function StepInterestDividends({ state, update }) {
  const ints = state.interest_income;
  const divs = state.dividend_income;

  const setInt = (i, k, v) => { const next = [...ints]; next[i] = { ...next[i], [k]: v }; update({ interest_income: next }); };
  const addInt = () => update({ interest_income: [...ints, { payer_name: '', amount: 0, tax_exempt_amount: 0 }] });
  const removeInt = (i) => update({ interest_income: ints.filter((_, j) => j !== i) });

  const setDiv = (i, k, v) => { const next = [...divs]; next[i] = { ...next[i], [k]: v }; update({ dividend_income: next }); };
  const addDiv = () => update({ dividend_income: [...divs, { payer_name: '', ordinary_dividends: 0, qualified_dividends: 0, capital_gain_distributions: 0 }] });
  const removeDiv = (i) => update({ dividend_income: divs.filter((_, j) => j !== i) });

  return html`
    <div class="card">
      <h2>Interest & Dividend Income</h2>
      <p class="subtitle">From 1099-INT and 1099-DIV forms</p>

      ${state.incomeTypes.interest ? html`
        <h3 style="margin:16px 0 8px;font-size:1rem">Interest Income (1099-INT)</h3>
        ${ints.map((item, i) => html`
          <div class="item-card" key=${'int-' + i}>
            <div class="item-card-header">
              <h4>${item.payer_name || `Interest #${i + 1}`}</h4>
              <button class="btn btn-danger btn-sm" onClick=${() => removeInt(i)}>Remove</button>
            </div>
            <${TextField} label="Payer name" value=${item.payer_name} onChange=${v => setInt(i, 'payer_name', v)} />
            <div class="input-row">
              <${MoneyField} label="Box 1: Interest income" value=${item.amount} onChange=${v => setInt(i, 'amount', v)} />
              <${MoneyField} label="Box 8: Tax-exempt interest" value=${item.tax_exempt_amount} onChange=${v => setInt(i, 'tax_exempt_amount', v)} />
            </div>
          </div>
        `)}
        <button class="add-btn" onClick=${addInt}>+ Add interest income</button>
        <hr class="section-divider" />
      ` : ''}

      ${state.incomeTypes.dividends ? html`
        <h3 style="margin:16px 0 8px;font-size:1rem">Dividend Income (1099-DIV)</h3>
        ${divs.map((item, i) => html`
          <div class="item-card" key=${'div-' + i}>
            <div class="item-card-header">
              <h4>${item.payer_name || `Dividend #${i + 1}`}</h4>
              <button class="btn btn-danger btn-sm" onClick=${() => removeDiv(i)}>Remove</button>
            </div>
            <${TextField} label="Payer name" value=${item.payer_name} onChange=${v => setDiv(i, 'payer_name', v)} />
            <div class="input-row">
              <${MoneyField} label="Box 1a: Ordinary dividends" value=${item.ordinary_dividends} onChange=${v => setDiv(i, 'ordinary_dividends', v)} />
              <${MoneyField} label="Box 1b: Qualified dividends" value=${item.qualified_dividends} onChange=${v => setDiv(i, 'qualified_dividends', v)} />
            </div>
            <${MoneyField} label="Box 2a: Capital gain distributions" value=${item.capital_gain_distributions} onChange=${v => setDiv(i, 'capital_gain_distributions', v)} />
          </div>
        `)}
        <button class="add-btn" onClick=${addDiv}>+ Add dividend income</button>
      ` : ''}
    </div>
  `;
}

// ─── STEP: Capital Gains ──────────────────────────────────────────────────────

function StepCapitalGains({ state, update }) {
  const items = state.capital_gains_losses;
  const set = (i, k, v) => { const next = [...items]; next[i] = { ...next[i], [k]: v }; update({ capital_gains_losses: next }); };
  const add = () => update({ capital_gains_losses: [...items, { description: '', date_acquired: '', date_sold: '', proceeds: 0, cost_basis: 0, term: 'long_term' }] });
  const remove = (i) => update({ capital_gains_losses: items.filter((_, j) => j !== i) });

  return html`
    <div class="card">
      <h2>Capital Gains & Losses</h2>
      <p class="subtitle">Stock sales, property sales, and other capital transactions</p>
      ${items.map((item, i) => html`
        <div class="item-card" key=${i}>
          <div class="item-card-header">
            <h4>${item.description || `Transaction #${i + 1}`}</h4>
            <button class="btn btn-danger btn-sm" onClick=${() => remove(i)}>Remove</button>
          </div>
          <${TextField} label="Description" value=${item.description} onChange=${v => set(i, 'description', v)} placeholder="e.g. 100 sh AAPL" />
          <div class="input-row-3">
            <${TextField} label="Date acquired" value=${item.date_acquired} onChange=${v => set(i, 'date_acquired', v)} type="date" />
            <${TextField} label="Date sold" value=${item.date_sold} onChange=${v => set(i, 'date_sold', v)} type="date" />
            <${SelectField} label="Holding period" value=${item.term} onChange=${v => set(i, 'term', v)}
              options=${[{ value: 'short_term', label: 'Short-term (≤1 yr)' }, { value: 'long_term', label: 'Long-term (>1 yr)' }]} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Sale proceeds" value=${item.proceeds} onChange=${v => set(i, 'proceeds', v)} />
            <${MoneyField} label="Cost basis" value=${item.cost_basis} onChange=${v => set(i, 'cost_basis', v)} />
          </div>
        </div>
      `)}
      <button class="add-btn" onClick=${add}>+ Add transaction</button>
    </div>
  `;
}

// ─── STEP: Business Income ────────────────────────────────────────────────────

function StepBusiness({ state, update }) {
  const items = state.business_income;
  const set = (i, k, v) => { const next = [...items]; next[i] = { ...next[i], [k]: v }; update({ business_income: next }); };
  const add = () => update({ business_income: [...items, { business_name: '', gross_receipts: 0, cost_of_goods_sold: 0,
    advertising: 0, car_and_truck: 0, insurance: 0, legal_and_professional: 0, office_expense: 0,
    rent_lease: 0, supplies: 0, utilities: 0, other_expenses: 0, home_office_deduction: 0 }] });
  const remove = (i) => update({ business_income: items.filter((_, j) => j !== i) });

  return html`
    <div class="card">
      <h2>Self-Employment / Business Income</h2>
      <p class="subtitle">Schedule C — profit or loss from business</p>
      ${items.map((b, i) => html`
        <div class="item-card" key=${i}>
          <div class="item-card-header">
            <h4>${b.business_name || `Business #${i + 1}`}</h4>
            ${items.length > 1 ? html`<button class="btn btn-danger btn-sm" onClick=${() => remove(i)}>Remove</button>` : ''}
          </div>
          <${TextField} label="Business name" value=${b.business_name} onChange=${v => set(i, 'business_name', v)} />
          <${MoneyField} label="Gross receipts / revenue" value=${b.gross_receipts} onChange=${v => set(i, 'gross_receipts', v)} />
          <${MoneyField} label="Cost of goods sold" value=${b.cost_of_goods_sold} onChange=${v => set(i, 'cost_of_goods_sold', v)} />
          <h4 style="margin:12px 0 8px;font-size:0.9rem;color:var(--text-muted)">Expenses</h4>
          <div class="input-row">
            <${MoneyField} label="Advertising" value=${b.advertising} onChange=${v => set(i, 'advertising', v)} />
            <${MoneyField} label="Car & truck" value=${b.car_and_truck} onChange=${v => set(i, 'car_and_truck', v)} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Insurance" value=${b.insurance} onChange=${v => set(i, 'insurance', v)} />
            <${MoneyField} label="Legal & professional" value=${b.legal_and_professional} onChange=${v => set(i, 'legal_and_professional', v)} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Office expense" value=${b.office_expense} onChange=${v => set(i, 'office_expense', v)} />
            <${MoneyField} label="Rent / lease" value=${b.rent_lease} onChange=${v => set(i, 'rent_lease', v)} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Supplies" value=${b.supplies} onChange=${v => set(i, 'supplies', v)} />
            <${MoneyField} label="Utilities" value=${b.utilities} onChange=${v => set(i, 'utilities', v)} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Other expenses" value=${b.other_expenses} onChange=${v => set(i, 'other_expenses', v)} />
            <${MoneyField} label="Home office deduction" value=${b.home_office_deduction} onChange=${v => set(i, 'home_office_deduction', v)} />
          </div>
        </div>
      `)}
      <button class="add-btn" onClick=${add}>+ Add business</button>
    </div>
  `;
}

// ─── STEP: Rental Income ──────────────────────────────────────────────────────

function StepRental({ state, update }) {
  const items = state.rental_income;
  const set = (i, k, v) => { const next = [...items]; next[i] = { ...next[i], [k]: v }; update({ rental_income: next }); };
  const add = () => update({ rental_income: [...items, { property_description: '', rental_income: 0,
    advertising: 0, cleaning_and_maintenance: 0, insurance: 0, mortgage_interest: 0, repairs: 0,
    taxes: 0, utilities: 0, depreciation: 0, other_expenses: 0 }] });
  const remove = (i) => update({ rental_income: items.filter((_, j) => j !== i) });

  return html`
    <div class="card">
      <h2>Rental Income</h2>
      <p class="subtitle">Schedule E — rental real estate income and expenses</p>
      ${items.map((r, i) => html`
        <div class="item-card" key=${i}>
          <div class="item-card-header">
            <h4>${r.property_description || `Property #${i + 1}`}</h4>
            ${items.length > 1 ? html`<button class="btn btn-danger btn-sm" onClick=${() => remove(i)}>Remove</button>` : ''}
          </div>
          <${TextField} label="Property description" value=${r.property_description} onChange=${v => set(i, 'property_description', v)} placeholder="e.g. 123 Oak St duplex" />
          <${MoneyField} label="Gross rental income" value=${r.rental_income} onChange=${v => set(i, 'rental_income', v)} />
          <h4 style="margin:12px 0 8px;font-size:0.9rem;color:var(--text-muted)">Expenses</h4>
          <div class="input-row">
            <${MoneyField} label="Insurance" value=${r.insurance} onChange=${v => set(i, 'insurance', v)} />
            <${MoneyField} label="Mortgage interest" value=${r.mortgage_interest} onChange=${v => set(i, 'mortgage_interest', v)} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Repairs" value=${r.repairs} onChange=${v => set(i, 'repairs', v)} />
            <${MoneyField} label="Taxes" value=${r.taxes} onChange=${v => set(i, 'taxes', v)} />
          </div>
          <div class="input-row">
            <${MoneyField} label="Utilities" value=${r.utilities} onChange=${v => set(i, 'utilities', v)} />
            <${MoneyField} label="Depreciation" value=${r.depreciation} onChange=${v => set(i, 'depreciation', v)} />
          </div>
          <${MoneyField} label="Other expenses" value=${r.other_expenses} onChange=${v => set(i, 'other_expenses', v)} />
        </div>
      `)}
      <button class="add-btn" onClick=${add}>+ Add rental property</button>
    </div>
  `;
}

// ─── STEP: Retirement & Social Security ───────────────────────────────────────

function StepRetirement({ state, update }) {
  const dists = state.retirement_distributions;
  const setDist = (i, k, v) => { const next = [...dists]; next[i] = { ...next[i], [k]: v }; update({ retirement_distributions: next }); };
  const addDist = () => update({ retirement_distributions: [...dists, { payer_name: '', gross_distribution: 0, taxable_amount: 0,
    federal_income_tax_withheld: 0, is_early_distribution: false, is_roth: false }] });
  const removeDist = (i) => update({ retirement_distributions: dists.filter((_, j) => j !== i) });

  return html`
    <div class="card">
      <h2>Retirement & Social Security</h2>
      <p class="subtitle">Retirement plan distributions (1099-R) and Social Security benefits (SSA-1099)</p>

      ${state.incomeTypes.retirement ? html`
        <h3 style="margin:16px 0 8px;font-size:1rem">Retirement Distributions (1099-R)</h3>
        ${dists.map((d, i) => html`
          <div class="item-card" key=${i}>
            <div class="item-card-header">
              <h4>${d.payer_name || `Distribution #${i + 1}`}</h4>
              <button class="btn btn-danger btn-sm" onClick=${() => removeDist(i)}>Remove</button>
            </div>
            <${TextField} label="Payer name" value=${d.payer_name} onChange=${v => setDist(i, 'payer_name', v)} />
            <div class="input-row">
              <${MoneyField} label="Box 1: Gross distribution" value=${d.gross_distribution} onChange=${v => setDist(i, 'gross_distribution', v)} />
              <${MoneyField} label="Box 2a: Taxable amount" value=${d.taxable_amount} onChange=${v => setDist(i, 'taxable_amount', v)} />
            </div>
            <${MoneyField} label="Box 4: Federal tax withheld" value=${d.federal_income_tax_withheld} onChange=${v => setDist(i, 'federal_income_tax_withheld', v)} />
            <div style="display:flex;gap:16px;flex-wrap:wrap">
              <${Toggle} label="Early distribution (before 59½)" checked=${d.is_early_distribution}
                onChange=${v => setDist(i, 'is_early_distribution', v)} />
              <${Toggle} label="Roth distribution" checked=${d.is_roth}
                onChange=${v => setDist(i, 'is_roth', v)} />
            </div>
          </div>
        `)}
        <button class="add-btn" onClick=${addDist}>+ Add distribution</button>
      ` : ''}

      ${state.incomeTypes.socialSecurity ? html`
        ${state.incomeTypes.retirement ? html`<hr class="section-divider" />` : ''}
        <h3 style="margin:16px 0 8px;font-size:1rem">Social Security Benefits (SSA-1099)</h3>
        <${MoneyField} label="Box 5: Total benefits received" value=${state.social_security.total_benefits}
          onChange=${v => update({ social_security: { ...state.social_security, total_benefits: v } })} />
      ` : ''}
    </div>
  `;
}

// ─── STEP: Other Income ───────────────────────────────────────────────────────

function StepOtherIncome({ state, update }) {
  const others = state.other_income;
  const setOther = (i, k, v) => { const next = [...others]; next[i] = { ...next[i], [k]: v }; update({ other_income: next }); };
  const addOther = () => update({ other_income: [...others, { description: '', amount: 0 }] });
  const removeOther = (i) => update({ other_income: others.filter((_, j) => j !== i) });

  return html`
    <div class="card">
      <h2>Other Income</h2>
      <p class="subtitle">Unemployment, prizes, jury duty pay, and other income</p>

      ${state.incomeTypes.unemployment ? html`
        <h3 style="margin:16px 0 8px;font-size:1rem">Unemployment Compensation (1099-G)</h3>
        <${MoneyField} label="Unemployment benefits received" value=${state.unemployment.amount}
          onChange=${v => update({ unemployment: { ...state.unemployment, amount: v } })} />
        <hr class="section-divider" />
      ` : ''}

      ${state.incomeTypes.other ? html`
        <h3 style="margin:16px 0 8px;font-size:1rem">Other Income</h3>
        ${others.map((item, i) => html`
          <div class="item-card" key=${i}>
            <div class="item-card-header">
              <h4>${item.description || `Other #${i + 1}`}</h4>
              <button class="btn btn-danger btn-sm" onClick=${() => removeOther(i)}>Remove</button>
            </div>
            <div class="input-row">
              <${TextField} label="Description" value=${item.description} onChange=${v => setOther(i, 'description', v)} placeholder="e.g. jury duty pay" />
              <${MoneyField} label="Amount" value=${item.amount} onChange=${v => setOther(i, 'amount', v)} />
            </div>
          </div>
        `)}
        <button class="add-btn" onClick=${addOther}>+ Add other income</button>
      ` : ''}
    </div>
  `;
}

// ─── STEP: Adjustments ────────────────────────────────────────────────────────

function StepAdjustments({ state, update }) {
  return html`
    <div class="card">
      <h2>Adjustments to Income</h2>
      <p class="subtitle">Above-the-line deductions that reduce your adjusted gross income</p>

      <${MoneyField} label="Educator expenses" hint="Up to $250 for K-12 teachers" value=${state.educator_expenses}
        onChange=${v => update({ educator_expenses: v })} />

      <${MoneyField} label="Student loan interest paid" hint="Up to $2,500 deduction" value=${state.student_loan_interest_paid}
        onChange=${v => update({ student_loan_interest_paid: v })} />

      <hr class="section-divider" />
      <${Toggle} label="I have a Health Savings Account (HSA)" checked=${state.hasHSA}
        onChange=${v => update({ hasHSA: v })} />

      ${state.hasHSA ? html`
        <div style="margin-top:8px">
          <${SelectField} label="Coverage type" value=${state.hsa.is_self_only_coverage ? 'self' : 'family'}
            onChange=${v => update({ hsa: { ...state.hsa, is_self_only_coverage: v === 'self' } })}
            options=${[{ value: 'self', label: 'Self-only' }, { value: 'family', label: 'Family' }]} />
          <div class="input-row">
            <${MoneyField} label="Your HSA contributions" value=${state.hsa.taxpayer_contributions}
              onChange=${v => update({ hsa: { ...state.hsa, taxpayer_contributions: v } })} />
            <${MoneyField} label="Employer contributions" value=${state.hsa.employer_contributions}
              onChange=${v => update({ hsa: { ...state.hsa, employer_contributions: v } })} />
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

// ─── STEP: Deductions ─────────────────────────────────────────────────────────

function StepDeductions({ state, update }) {
  const isItemized = state.deduction_method === 'itemized';
  const mort = state.mortgage_interest;
  const setMort = (i, k, v) => { const next = [...mort]; next[i] = { ...next[i], [k]: v }; update({ mortgage_interest: next }); };
  const addMort = () => update({ mortgage_interest: [...mort, { lender_name: '', mortgage_interest_paid: 0, mortgage_insurance_premiums: 0, points_paid: 0, outstanding_mortgage_principal: 0 }] });
  const removeMort = (i) => update({ mortgage_interest: mort.filter((_, j) => j !== i) });

  const char = state.charitable_contributions;
  const setChar = (i, k, v) => { const next = [...char]; next[i] = { ...next[i], [k]: v }; update({ charitable_contributions: next }); };
  const addChar = () => update({ charitable_contributions: [...char, { organization_name: '', cash_amount: 0, noncash_amount: 0 }] });
  const removeChar = (i) => update({ charitable_contributions: char.filter((_, j) => j !== i) });

  return html`
    <div class="card">
      <h2>Deductions</h2>
      <p class="subtitle">Choose standard deduction or itemize your deductions</p>

      <${RadioGroup} label="" value=${state.deduction_method} onChange=${v => update({ deduction_method: v })}
        options=${[
          { value: 'standard', label: 'Standard Deduction', desc: `Take the standard deduction amount for your filing status` },
          { value: 'itemized', label: 'Itemized Deductions', desc: 'List individual deductions (medical, taxes, mortgage interest, charitable)' },
        ]} />

      ${isItemized ? html`
        <hr class="section-divider" />

        <h3 style="margin:0 0 12px;font-size:1rem">Medical & Dental Expenses</h3>
        <div class="hint" style="margin-bottom:12px">Only the amount exceeding 7.5% of your AGI is deductible</div>
        <div class="input-row">
          <${MoneyField} label="Medical & dental expenses" value=${state.medical_expenses.total_medical_dental}
            onChange=${v => update({ medical_expenses: { ...state.medical_expenses, total_medical_dental: v } })} />
          <${MoneyField} label="Health insurance premiums" value=${state.medical_expenses.health_insurance_premiums}
            onChange=${v => update({ medical_expenses: { ...state.medical_expenses, health_insurance_premiums: v } })} />
        </div>

        <hr class="section-divider" />
        <h3 style="margin:0 0 12px;font-size:1rem">State & Local Taxes (SALT)</h3>
        <div class="hint" style="margin-bottom:12px">Capped at $40,000 ($20,000 if married filing separately)</div>
        <div class="input-row">
          <${MoneyField} label="State income tax paid" value=${state.state_local_taxes.state_income_tax_paid}
            onChange=${v => update({ state_local_taxes: { ...state.state_local_taxes, state_income_tax_paid: v } })} />
          <${MoneyField} label="Real property tax" value=${state.state_local_taxes.real_property_tax}
            onChange=${v => update({ state_local_taxes: { ...state.state_local_taxes, real_property_tax: v } })} />
        </div>
        <${MoneyField} label="Personal property tax" value=${state.state_local_taxes.personal_property_tax}
          onChange=${v => update({ state_local_taxes: { ...state.state_local_taxes, personal_property_tax: v } })} />

        <hr class="section-divider" />
        <h3 style="margin:0 0 12px;font-size:1rem">Mortgage Interest</h3>
        ${mort.map((m, i) => html`
          <div class="item-card" key=${i}>
            <div class="item-card-header">
              <h4>${m.lender_name || `Mortgage #${i + 1}`}</h4>
              ${mort.length > 1 ? html`<button class="btn btn-danger btn-sm" onClick=${() => removeMort(i)}>Remove</button>` : ''}
            </div>
            <${TextField} label="Lender name" value=${m.lender_name} onChange=${v => setMort(i, 'lender_name', v)} />
            <div class="input-row">
              <${MoneyField} label="Interest paid" value=${m.mortgage_interest_paid} onChange=${v => setMort(i, 'mortgage_interest_paid', v)} />
              <${MoneyField} label="PMI premiums" value=${m.mortgage_insurance_premiums} onChange=${v => setMort(i, 'mortgage_insurance_premiums', v)} />
            </div>
            <${MoneyField} label="Outstanding principal" value=${m.outstanding_mortgage_principal} onChange=${v => setMort(i, 'outstanding_mortgage_principal', v)} />
          </div>
        `)}
        <button class="add-btn" onClick=${addMort}>+ Add mortgage</button>

        <hr class="section-divider" />
        <h3 style="margin:0 0 12px;font-size:1rem">Charitable Contributions</h3>
        ${char.map((c, i) => html`
          <div class="item-card" key=${i}>
            <div class="item-card-header">
              <h4>${c.organization_name || `Contribution #${i + 1}`}</h4>
              <button class="btn btn-danger btn-sm" onClick=${() => removeChar(i)}>Remove</button>
            </div>
            <${TextField} label="Organization name" value=${c.organization_name} onChange=${v => setChar(i, 'organization_name', v)} />
            <div class="input-row">
              <${MoneyField} label="Cash contributions" value=${c.cash_amount} onChange=${v => setChar(i, 'cash_amount', v)} />
              <${MoneyField} label="Non-cash contributions" value=${c.noncash_amount} onChange=${v => setChar(i, 'noncash_amount', v)} />
            </div>
          </div>
        `)}
        <button class="add-btn" onClick=${addChar}>+ Add contribution</button>
      ` : ''}
    </div>
  `;
}

// ─── STEP: Credits ────────────────────────────────────────────────────────────

function StepCredits({ state, update }) {
  const edus = state.education_expenses;
  const setEdu = (i, k, v) => { const next = [...edus]; next[i] = { ...next[i], [k]: v }; update({ education_expenses: next }); };
  const addEdu = () => update({ education_expenses: [...edus, { student_name: '', student_ssn: '', institution_name: '',
    qualified_tuition_and_fees: 0, scholarships_and_grants: 0, credit_type: 'aotc', year_in_postsecondary: 1 }] });
  const removeEdu = (i) => update({ education_expenses: edus.filter((_, j) => j !== i) });

  const cares = state.child_care_expenses;
  const setCare = (i, k, v) => { const next = [...cares]; next[i] = { ...next[i], [k]: v }; update({ child_care_expenses: next }); };
  const addCare = () => update({ child_care_expenses: [...cares, { provider_name: '', provider_tin: '', amount_paid: 0, care_recipient_name: '' }] });
  const removeCare = (i) => update({ child_care_expenses: cares.filter((_, j) => j !== i) });

  return html`
    <div class="card">
      <h2>Tax Credits</h2>
      <p class="subtitle">Credits directly reduce the tax you owe</p>

      <${Toggle} label="I have education expenses (AOTC / Lifetime Learning)" checked=${state.hasEducationCredits}
        onChange=${v => update({ hasEducationCredits: v })} />

      ${state.hasEducationCredits ? html`
        ${edus.map((e, i) => html`
          <div class="item-card" key=${i}>
            <div class="item-card-header">
              <h4>${e.student_name || `Student #${i + 1}`}</h4>
              <button class="btn btn-danger btn-sm" onClick=${() => removeEdu(i)}>Remove</button>
            </div>
            <div class="input-row">
              <${TextField} label="Student name" value=${e.student_name} onChange=${v => setEdu(i, 'student_name', v)} />
              <${TextField} label="Student SSN" value=${e.student_ssn} onChange=${v => setEdu(i, 'student_ssn', v)} />
            </div>
            <${TextField} label="Institution name" value=${e.institution_name} onChange=${v => setEdu(i, 'institution_name', v)} />
            <div class="input-row">
              <${MoneyField} label="Tuition & fees paid" value=${e.qualified_tuition_and_fees} onChange=${v => setEdu(i, 'qualified_tuition_and_fees', v)} />
              <${MoneyField} label="Scholarships/grants received" value=${e.scholarships_and_grants} onChange=${v => setEdu(i, 'scholarships_and_grants', v)} />
            </div>
            <div class="input-row">
              <${SelectField} label="Credit type" value=${e.credit_type} onChange=${v => setEdu(i, 'credit_type', v)}
                options=${[{ value: 'aotc', label: 'American Opportunity (AOTC)' }, { value: 'lifetime_learning', label: 'Lifetime Learning' }]} />
              <${TextField} label="Year in school" value=${e.year_in_postsecondary} onChange=${v => setEdu(i, 'year_in_postsecondary', parseInt(v) || 1)} type="number" />
            </div>
          </div>
        `)}
        <button class="add-btn" onClick=${addEdu}>+ Add student</button>
      ` : ''}

      <hr class="section-divider" />

      <${Toggle} label="I have child/dependent care expenses" checked=${state.hasChildCare}
        onChange=${v => update({ hasChildCare: v })} />

      ${state.hasChildCare ? html`
        ${cares.map((c, i) => html`
          <div class="item-card" key=${i}>
            <div class="item-card-header">
              <h4>${c.provider_name || `Provider #${i + 1}`}</h4>
              <button class="btn btn-danger btn-sm" onClick=${() => removeCare(i)}>Remove</button>
            </div>
            <div class="input-row">
              <${TextField} label="Provider name" value=${c.provider_name} onChange=${v => setCare(i, 'provider_name', v)} />
              <${TextField} label="Provider SSN/EIN" value=${c.provider_tin} onChange=${v => setCare(i, 'provider_tin', v)} />
            </div>
            <div class="input-row">
              <${MoneyField} label="Amount paid" value=${c.amount_paid} onChange=${v => setCare(i, 'amount_paid', v)} />
              <${TextField} label="Child/dependent name" value=${c.care_recipient_name} onChange=${v => setCare(i, 'care_recipient_name', v)} />
            </div>
          </div>
        `)}
        <button class="add-btn" onClick=${addCare}>+ Add care provider</button>
      ` : ''}
    </div>
  `;
}

// ─── STEP: Payments ───────────────────────────────────────────────────────────

function StepPayments({ state, update }) {
  const est = state.estimated_tax_payments;
  return html`
    <div class="card">
      <h2>Estimated Tax Payments</h2>
      <p class="subtitle">Quarterly estimated tax payments you made during the year</p>

      <div class="input-row">
        <${MoneyField} label="Q1 (Apr 15)" value=${est.q1_amount}
          onChange=${v => update({ estimated_tax_payments: { ...est, q1_amount: v } })} />
        <${MoneyField} label="Q2 (Jun 15)" value=${est.q2_amount}
          onChange=${v => update({ estimated_tax_payments: { ...est, q2_amount: v } })} />
      </div>
      <div class="input-row">
        <${MoneyField} label="Q3 (Sep 15)" value=${est.q3_amount}
          onChange=${v => update({ estimated_tax_payments: { ...est, q3_amount: v } })} />
        <${MoneyField} label="Q4 (Jan 15)" value=${est.q4_amount}
          onChange=${v => update({ estimated_tax_payments: { ...est, q4_amount: v } })} />
      </div>

      <hr class="section-divider" />
      <h3 style="margin:0 0 12px;font-size:1rem">Prior Year Information</h3>
      <div class="hint" style="margin-bottom:12px">Used for safe harbor and penalty calculations</div>
      <div class="input-row">
        <${MoneyField} label="Prior year AGI" value=${state.prior_year_agi}
          onChange=${v => update({ prior_year_agi: v })} />
        <${MoneyField} label="Prior year total tax" value=${state.prior_year_tax}
          onChange=${v => update({ prior_year_tax: v })} />
      </div>
    </div>
  `;
}

// ─── STEP: Review & Calculate ─────────────────────────────────────────────────

function buildPayload(state) {
  const payload = {
    tax_year: state.tax_year,
    filing_status: state.filing_status,
    personal_info: { ...state.personal_info },
    address: { ...state.address },
    deduction_method: state.deduction_method,
    educator_expenses: state.educator_expenses || 0,
    student_loan_interest_paid: state.student_loan_interest_paid || 0,
    prior_year_agi: state.prior_year_agi || 0,
    prior_year_tax: state.prior_year_tax || 0,
  };

  // Spouse
  if (isMarried(state) && state.spouse_info.first_name) {
    payload.spouse_info = { ...state.spouse_info };
  }

  // Dependents
  if (state.hasDependents && state.dependents.length) {
    payload.dependents = state.dependents.filter(d => d.first_name);
  }

  // Income
  if (state.incomeTypes.w2 && state.w2_income.length) {
    payload.w2_income = state.w2_income.filter(w => w.employer_name || w.wages);
  }
  if (state.incomeTypes.interest && state.interest_income.length) {
    payload.interest_income = state.interest_income.filter(i => i.payer_name || i.amount);
  }
  if (state.incomeTypes.dividends && state.dividend_income.length) {
    payload.dividend_income = state.dividend_income.filter(d => d.payer_name || d.ordinary_dividends);
  }
  if (state.incomeTypes.capitalGains && state.capital_gains_losses.length) {
    payload.capital_gains_losses = state.capital_gains_losses.filter(c => c.description || c.proceeds);
  }
  if (state.incomeTypes.business && state.business_income.length) {
    payload.business_income = state.business_income.filter(b => b.business_name || b.gross_receipts);
  }
  if (state.incomeTypes.rental && state.rental_income.length) {
    payload.rental_income = state.rental_income.filter(r => r.property_description || r.rental_income);
  }
  if (state.incomeTypes.retirement && state.retirement_distributions.length) {
    payload.retirement_distributions = state.retirement_distributions.filter(d => d.payer_name || d.gross_distribution);
  }
  if (state.incomeTypes.socialSecurity && state.social_security.total_benefits) {
    payload.social_security = { ...state.social_security };
  }
  if (state.incomeTypes.unemployment && state.unemployment.amount) {
    payload.unemployment = { ...state.unemployment };
  }
  if (state.incomeTypes.other && state.other_income.length) {
    payload.other_income = state.other_income.filter(o => o.description || o.amount);
  }

  // HSA
  if (state.hasHSA && state.hsa.taxpayer_contributions) {
    payload.hsa = { ...state.hsa };
  }

  // Estimated payments
  const est = state.estimated_tax_payments;
  if (est.q1_amount || est.q2_amount || est.q3_amount || est.q4_amount) {
    payload.estimated_tax_payments = { ...est };
  }

  // Deductions
  if (state.deduction_method === 'itemized') {
    const med = state.medical_expenses;
    if (med.total_medical_dental || med.health_insurance_premiums) {
      payload.medical_expenses = { ...med };
    }
    const salt = state.state_local_taxes;
    if (salt.state_income_tax_paid || salt.real_property_tax || salt.personal_property_tax) {
      payload.state_local_taxes = { ...salt };
    }
    if (state.mortgage_interest.length) {
      payload.mortgage_interest = state.mortgage_interest.filter(m => m.lender_name || m.mortgage_interest_paid);
    }
    if (state.charitable_contributions.length) {
      payload.charitable_contributions = state.charitable_contributions.filter(c => c.organization_name || c.cash_amount);
    }
  }

  // Credits
  if (state.hasEducationCredits && state.education_expenses.length) {
    payload.education_expenses = state.education_expenses.filter(e => e.student_name);
  }
  if (state.hasChildCare && state.child_care_expenses.length) {
    payload.child_care_expenses = state.child_care_expenses.filter(c => c.provider_name);
  }

  return payload;
}

function ReviewSummary({ state }) {
  const lines = [];
  lines.push(['Filing status', state.filing_status.replace(/_/g, ' ')]);
  lines.push(['Taxpayer', `${state.personal_info.first_name} ${state.personal_info.last_name}`]);
  if (isMarried(state) && state.spouse_info.first_name) {
    lines.push(['Spouse', `${state.spouse_info.first_name} ${state.spouse_info.last_name}`]);
  }
  if (state.hasDependents) lines.push(['Dependents', state.dependents.length]);

  const incomes = Object.entries(state.incomeTypes).filter(([_, v]) => v).map(([k]) => k);
  if (incomes.length) lines.push(['Income sources', incomes.join(', ')]);

  if (state.incomeTypes.w2) {
    const total = state.w2_income.reduce((s, w) => s + (w.wages || 0), 0);
    if (total) lines.push(['W-2 wages', fmt(total)]);
  }

  lines.push(['Deduction method', state.deduction_method]);

  return html`
    <div style="font-size:0.9rem">
      ${lines.map(([label, val]) => html`
        <div class="result-row" key=${label}>
          <span>${label}</span>
          <span style="font-weight:500;text-transform:capitalize">${val}</span>
        </div>
      `)}
    </div>
  `;
}

function ResultsDisplay({ results }) {
  if (!results) return null;
  const r = results;
  const inc = r.income || {};
  const agi = r.agi || {};
  const ded = r.deductions || {};
  const tax = r.tax || {};
  const credits = r.credits || {};
  const se = r.se_tax || {};
  const pay = r.payments || {};

  const isRefund = r.overpayment > 0;
  const bannerAmount = isRefund ? r.overpayment : r.amount_owed;

  return html`
    <div>
      <div class="refund-banner ${isRefund ? 'refund' : 'owed'}">
        ${isRefund ? `Refund: ${fmt(bannerAmount)}` : `Amount Owed: ${fmt(bannerAmount)}`}
      </div>

      <div style="display:flex;justify-content:center;gap:24px;margin-bottom:16px;font-size:0.85rem;color:var(--text-muted)">
        <span>Effective rate: ${(r.effective_tax_rate * 100).toFixed(1)}%</span>
        <span>Marginal rate: ${(r.marginal_tax_rate * 100).toFixed(0)}%</span>
      </div>

      <div class="result-section">
        <h3>Income</h3>
        ${inc.total_wages ? html`<div class="result-row"><span>Wages</span><span class="amount">${fmt(inc.total_wages)}</span></div>` : ''}
        ${inc.total_interest ? html`<div class="result-row"><span>Interest</span><span class="amount">${fmt(inc.total_interest)}</span></div>` : ''}
        ${inc.total_ordinary_dividends ? html`<div class="result-row"><span>Dividends</span><span class="amount">${fmt(inc.total_ordinary_dividends)}</span></div>` : ''}
        ${inc.net_capital_gain_loss ? html`<div class="result-row"><span>Capital gains/losses</span><span class="amount">${fmt(inc.net_capital_gain_loss)}</span></div>` : ''}
        ${inc.total_business_income ? html`<div class="result-row"><span>Business income</span><span class="amount">${fmt(inc.total_business_income)}</span></div>` : ''}
        ${inc.total_rental_income ? html`<div class="result-row"><span>Rental income</span><span class="amount">${fmt(inc.total_rental_income)}</span></div>` : ''}
        ${inc.taxable_retirement_distributions ? html`<div class="result-row"><span>Retirement distributions</span><span class="amount">${fmt(inc.taxable_retirement_distributions)}</span></div>` : ''}
        ${inc.taxable_social_security ? html`<div class="result-row"><span>Social Security (taxable)</span><span class="amount">${fmt(inc.taxable_social_security)}</span></div>` : ''}
        ${inc.unemployment_compensation ? html`<div class="result-row"><span>Unemployment</span><span class="amount">${fmt(inc.unemployment_compensation)}</span></div>` : ''}
        ${inc.total_other_income ? html`<div class="result-row"><span>Other income</span><span class="amount">${fmt(inc.total_other_income)}</span></div>` : ''}
        <div class="result-row total"><span>Gross Income</span><span class="amount">${fmt(inc.gross_income)}</span></div>
      </div>

      <div class="result-section">
        <h3>Adjusted Gross Income</h3>
        ${agi.total_adjustments ? html`<div class="result-row"><span>Total adjustments</span><span class="amount">-${fmt(agi.total_adjustments)}</span></div>` : ''}
        <div class="result-row total"><span>AGI</span><span class="amount">${fmt(agi.agi)}</span></div>
      </div>

      <div class="result-section">
        <h3>Deductions</h3>
        <div class="result-row">
          <span>${ded.deduction_method_used === 'itemized' ? 'Itemized deductions' : 'Standard deduction'}</span>
          <span class="amount">${fmt(ded.deduction_amount)}</span>
        </div>
        ${ded.qbi_deduction ? html`<div class="result-row"><span>QBI deduction</span><span class="amount">${fmt(ded.qbi_deduction)}</span></div>` : ''}
        ${ded.senior_deduction ? html`<div class="result-row"><span>Senior deduction</span><span class="amount">${fmt(ded.senior_deduction)}</span></div>` : ''}
        <div class="result-row total"><span>Taxable Income</span><span class="amount">${fmt(ded.taxable_income)}</span></div>
      </div>

      <div class="result-section">
        <h3>Tax</h3>
        <div class="result-row"><span>Income tax</span><span class="amount">${fmt(tax.total_income_tax)}</span></div>
        ${tax.amt ? html`<div class="result-row"><span>Alternative minimum tax</span><span class="amount">${fmt(tax.amt)}</span></div>` : ''}
        ${se.total_se_tax ? html`<div class="result-row"><span>Self-employment tax</span><span class="amount">${fmt(se.total_se_tax)}</span></div>` : ''}
        ${tax.additional_medicare_tax ? html`<div class="result-row"><span>Additional Medicare tax</span><span class="amount">${fmt(tax.additional_medicare_tax)}</span></div>` : ''}
        ${tax.niit_amount ? html`<div class="result-row"><span>Net investment income tax</span><span class="amount">${fmt(tax.niit_amount)}</span></div>` : ''}
        <div class="result-row total"><span>Total Tax</span><span class="amount">${fmt(r.total_tax)}</span></div>
      </div>

      <div class="result-section">
        <h3>Credits</h3>
        ${credits.child_tax_credit_nonrefundable ? html`<div class="result-row"><span>Child tax credit</span><span class="amount positive">${fmt(credits.child_tax_credit_nonrefundable)}</span></div>` : ''}
        ${credits.additional_child_tax_credit ? html`<div class="result-row"><span>Additional child tax credit</span><span class="amount positive">${fmt(credits.additional_child_tax_credit)}</span></div>` : ''}
        ${credits.education_credits ? html`<div class="result-row"><span>Education credits</span><span class="amount positive">${fmt(credits.education_credits)}</span></div>` : ''}
        ${credits.aotc_refundable ? html`<div class="result-row"><span>AOTC (refundable)</span><span class="amount positive">${fmt(credits.aotc_refundable)}</span></div>` : ''}
        ${credits.earned_income_credit ? html`<div class="result-row"><span>Earned income credit</span><span class="amount positive">${fmt(credits.earned_income_credit)}</span></div>` : ''}
        ${credits.child_dependent_care_credit ? html`<div class="result-row"><span>Child/dependent care credit</span><span class="amount positive">${fmt(credits.child_dependent_care_credit)}</span></div>` : ''}
        ${credits.savers_credit ? html`<div class="result-row"><span>Saver's credit</span><span class="amount positive">${fmt(credits.savers_credit)}</span></div>` : ''}
        ${credits.foreign_tax_credit ? html`<div class="result-row"><span>Foreign tax credit</span><span class="amount positive">${fmt(credits.foreign_tax_credit)}</span></div>` : ''}
        ${credits.total_credits ? html`<div class="result-row total"><span>Total Credits</span><span class="amount positive">${fmt(credits.total_credits)}</span></div>` : ''}
      </div>

      <div class="result-section">
        <h3>Payments</h3>
        ${pay.federal_income_tax_withheld ? html`<div class="result-row"><span>Federal tax withheld</span><span class="amount">${fmt(pay.federal_income_tax_withheld)}</span></div>` : ''}
        ${pay.estimated_tax_payments ? html`<div class="result-row"><span>Estimated tax payments</span><span class="amount">${fmt(pay.estimated_tax_payments)}</span></div>` : ''}
        ${pay.excess_social_security_withheld ? html`<div class="result-row"><span>Excess SS tax withheld</span><span class="amount">${fmt(pay.excess_social_security_withheld)}</span></div>` : ''}
        <div class="result-row total"><span>Total Payments</span><span class="amount">${fmt(r.total_payments)}</span></div>
      </div>

      <div class="result-section">
        <div class="result-row total" style="font-size:1.1rem">
          <span>${isRefund ? 'Your Refund' : 'Amount You Owe'}</span>
          <span class="amount ${isRefund ? 'positive' : 'negative'}">${fmt(bannerAmount)}</span>
        </div>
      </div>
    </div>
  `;
}

// Forms that currently have a mapping file on the server
const MAPPED_FORMS = new Set([
  'f1040','f1040s1','f1040s2','f1040s3','f1040sa','f1040sb',
  'f1040sc','f1040sd','f1040se','f1040sf','f1040sse','f8949','f2441',
]);

function applicableFormIds(output) {
  const income = output.income || {};
  const agi    = output.agi || {};
  const ded    = output.deductions || {};
  const tax    = output.tax || {};
  const cr     = output.credits || {};
  const se     = output.se_tax || {};

  const forms = ['f1040'];

  const anyNonZero = (...vals) => vals.some(v => v && v !== 0);

  if (anyNonZero(income.total_business_income, income.total_rental_income,
                 income.unemployment_compensation, income.alimony_income,
                 income.total_farm_income, income.total_royalty_income,
                 income.total_k1_ordinary_income, income.taxable_home_sale_gain,
                 agi.educator_expenses_deduction, agi.ira_deduction,
                 agi.student_loan_interest_deduction, agi.hsa_deduction,
                 agi.se_tax_deduction, agi.alimony_deduction))
    forms.push('f1040s1');

  if (anyNonZero(tax.amt, tax.niit_amount, tax.additional_medicare_tax, se.total_se_tax))
    forms.push('f1040s2');

  if (anyNonZero(cr.education_credits, cr.foreign_tax_credit,
                 cr.child_dependent_care_credit, cr.savers_credit,
                 cr.energy_home_improvement_credit, cr.residential_clean_energy_credit,
                 cr.elderly_disabled_credit))
    forms.push('f1040s3');

  if (ded.deduction_method_used === 'ITEMIZED')  forms.push('f1040sa');
  if (anyNonZero(income.total_business_income))  forms.push('f1040sc');
  if (anyNonZero(income.net_capital_gain_loss))  { forms.push('f1040sd'); forms.push('f8949'); }
  if (anyNonZero(income.total_rental_income, income.total_k1_ordinary_income,
                 income.total_royalty_income))    forms.push('f1040se');
  if (anyNonZero(income.total_farm_income))       forms.push('f1040sf');
  if (anyNonZero(se.total_se_tax))               forms.push('f1040sse');

  return forms.filter(id => MAPPED_FORMS.has(id));
}

function StepReview({ state, update }) {
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [pdfError, setPdfError] = useState(null);
  const [pdfFormIds, setPdfFormIds] = useState(null);
  const [pdfOpeningFormId, setPdfOpeningFormId] = useState(null);

  const doCalculate = async () => {
    update({ calculating: true, errors: null, results: null });
    setPdfError(null);
    setPdfFormIds(null);
    try {
      const payload = buildPayload(state);
      const resp = await fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) {
        update({ calculating: false, errors: data.errors || [data.error || 'Calculation failed'] });
      } else {
        update({ calculating: false, results: data });
        setPdfFormIds(applicableFormIds(data));
      }
    } catch (err) {
      update({ calculating: false, errors: [err.message] });
    }
  };

  const doDownloadPDF = async () => {
    setPdfDownloading(true);
    setPdfError(null);
    try {
      const payload = buildPayload(state);
      const resp = await fetch('/api/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const data = await resp.json();
        setPdfError((data.errors || ['PDF generation failed']).join('; '));
      } else {
        const formIdsHeader = resp.headers.get('X-Form-Ids');
        if (formIdsHeader) setPdfFormIds(formIdsHeader.split(',').filter(id => MAPPED_FORMS.has(id)));
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'tax_return_forms.zip';
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      setPdfError(err.message);
    } finally {
      setPdfDownloading(false);
    }
  };

  const openFormInTab = async (formId) => {
    // Open the window synchronously (before any awaits) to avoid popup blockers
    const win = window.open('', '_blank');
    if (!win) {
      setPdfError('Popup blocked — please allow popups for this site and try again.');
      return;
    }
    setPdfOpeningFormId(formId);
    setPdfError(null);
    try {
      const payload = { ...buildPayload(state), _form_id: formId };
      const resp = await fetch('/api/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        win.close();
        const data = await resp.json();
        setPdfError((data.errors || ['PDF generation failed']).join('; '));
      } else {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        win.location.href = url;
      }
    } catch (err) {
      win.close();
      setPdfError(err.message);
    } finally {
      setPdfOpeningFormId(null);
    }
  };

  return html`
    <div class="card">
      <h2>Review & Calculate</h2>
      <p class="subtitle">Review your information, then calculate your tax</p>

      <${ReviewSummary} state=${state} />

      ${state.errors ? html`
        <div class="alert alert-error" style="margin-top:16px">
          ${state.errors.map(e => html`<div key=${e}>${e}</div>`)}
        </div>
      ` : ''}

      <div style="text-align:center;margin-top:20px">
        <button class="btn btn-success" onClick=${doCalculate} disabled=${state.calculating}
          style="padding:14px 48px;font-size:1.1rem">
          ${state.calculating ? html`<span class="spinner" /> Calculating...` : 'Calculate My Tax'}
        </button>
      </div>

      ${state.results ? html`
        <hr class="section-divider" />
        <${ResultsDisplay} results=${state.results} />

        <div style="text-align:center;margin-top:24px">
          <button class="btn btn-primary" onClick=${doDownloadPDF} disabled=${pdfDownloading}
            style="padding:12px 36px;font-size:1rem">
            ${pdfDownloading
              ? html`<span class="spinner" /> Generating PDFs...`
              : '⬇ Download Filled IRS Forms (ZIP)'}
          </button>

          ${pdfFormIds && pdfFormIds.length > 0 ? html`
            <div style="margin-top:14px">
              <div style="font-size:0.8rem;color:#666;margin-bottom:6px">Open individual forms in a new tab:</div>
              <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px">
                ${pdfFormIds.map(id => html`
                  <button key=${id} class="btn btn-secondary"
                    onClick=${() => openFormInTab(id)}
                    disabled=${pdfOpeningFormId === id}
                    style="font-size:0.85rem;padding:6px 14px">
                    ${pdfOpeningFormId === id
                      ? html`<span class="spinner" />`
                      : html`${FORM_NAMES[id] || id} ↗`}
                  </button>
                `)}
              </div>
            </div>
          ` : ''}

          ${pdfError ? html`
            <div class="alert alert-error" style="margin-top:10px;text-align:left">
              ${pdfError}
            </div>
          ` : ''}
        </div>
      ` : ''}
    </div>
  `;
}

// ─── Step Component Map ───────────────────────────────────────────────────────

const STEP_COMPONENTS = {
  'filing': StepFiling,
  'personal': StepPersonal,
  'dependents': StepDependents,
  'income-sel': StepIncomeSelect,
  'w2': StepW2,
  'int-div': StepInterestDividends,
  'capgains': StepCapitalGains,
  'business': StepBusiness,
  'rental': StepRental,
  'retirement': StepRetirement,
  'other-inc': StepOtherIncome,
  'adjustments': StepAdjustments,
  'deductions': StepDeductions,
  'credits': StepCredits,
  'payments': StepPayments,
  'review': StepReview,
};

// ─── App ──────────────────────────────────────────────────────────────────────

function App() {
  const [state, setState] = useState(() => loadState() || defaultState());

  const update = useCallback((partial) => {
    setState(prev => {
      const next = { ...prev, ...partial };
      saveState(next);
      return next;
    });
  }, []);

  // Compute visible steps based on current state
  const visibleSteps = useMemo(() => STEPS.filter(s => s.show(state)), [state]);
  const currentVisibleIndex = Math.min(state.stepIndex, visibleSteps.length - 1);
  const currentStep = visibleSteps[currentVisibleIndex];
  const StepComponent = STEP_COMPONENTS[currentStep?.id];

  const goNext = () => {
    if (currentVisibleIndex < visibleSteps.length - 1) {
      update({ stepIndex: currentVisibleIndex + 1 });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };
  const goPrev = () => {
    if (currentVisibleIndex > 0) {
      update({ stepIndex: currentVisibleIndex - 1 });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };
  const goToStep = (i) => {
    update({ stepIndex: i });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const startOver = () => {
    clearSaved();
    setState(defaultState());
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return html`
    <header>
      <h1>Federal Tax Calculator</h1>
      <p>Tax Year ${state.tax_year}</p>
    </header>

    <div class="progress-label">
      Step ${currentVisibleIndex + 1} of ${visibleSteps.length}: ${currentStep?.title}
    </div>
    <div class="progress-bar">
      ${visibleSteps.map((s, i) => html`
        <div key=${s.id}
          class="progress-segment ${i < currentVisibleIndex ? 'done' : i === currentVisibleIndex ? 'current' : ''}"
          style="cursor:pointer" onClick=${() => goToStep(i)}
          title=${s.title} />
      `)}
    </div>

    ${StepComponent ? html`<${StepComponent} state=${state} update=${update} />` : ''}

    <div class="nav-buttons">
      <div>
        ${currentVisibleIndex > 0 ? html`
          <button class="btn btn-secondary" onClick=${goPrev}>Back</button>
        ` : html`
          <button class="btn btn-secondary" onClick=${startOver} style="font-size:0.85rem">Start Over</button>
        `}
      </div>
      <div>
        ${currentVisibleIndex < visibleSteps.length - 1 ? html`
          <button class="btn btn-primary" onClick=${goNext}>Continue</button>
        ` : ''}
      </div>
    </div>

    <div style="text-align:center;margin:24px 0;font-size:0.75rem;color:var(--text-muted)">
      All data is stored locally in your browser. Nothing is sent to the server until you calculate.
      <br />
      <button onClick=${startOver} style="color:var(--danger);background:none;border:none;cursor:pointer;font-size:0.75rem;text-decoration:underline;margin-top:4px">
        Clear all data and start over
      </button>
    </div>
  `;
}

// ─── Mount ────────────────────────────────────────────────────────────────────

render(html`<${App} />`, document.getElementById('app'));
