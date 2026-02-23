# AGENTS.md — AI Coding Agent Guide

Guidelines for AI coding agents working on the taxes-bot codebase.

## Project Overview

Federal individual income tax calculator for tax year 2025. The system has four layers:

- **CLI** (`main.py`) — JSON in, JSON out via stdin or file argument
- **Web UI** (`server.py` + `static/`) — Preact single-page app with a multi-step wizard
- **BDD tests** (`tests/features/` + `tests/step_defs/`) — pytest-bdd Gherkin scenarios
- **Playwright e2e tests** (`tests/e2e/`) — Browser tests with video recording

Zero external runtime dependencies. Python 3.14+, stdlib only. Dev dependencies are pytest, pytest-bdd, and pytest-playwright.

## Architecture

### Core Files

| File | Lines | Purpose |
|------|-------|---------|
| `models.py` | ~4000 | Dataclass-based input/output models. `TaxReturnInput` and `TaxReturnOutput` with all sub-models. Enums for filing status, account types, etc. All monetary amounts are `float` in USD. |
| `calculator.py` | ~2400 | Tax computation engine. Takes `TaxReturnInput`, returns `TaxReturnOutput`. References IRC sections in comments. Has `_deserialize_enum()` for JSON-to-dataclass conversion. |
| `main.py` | ~48 | CLI entry point. Reads JSON from file or stdin, prints result JSON. Also supports `--schema input` and `--schema output`. |
| `server.py` | ~106 | Stdlib `http.server` HTTP server. `GET /` serves static files. `POST /api/calculate` runs the calculator. `GET /api/schema` returns JSON Schema. No dependencies. |

### Web UI

| File | Lines | Purpose |
|------|-------|---------|
| `static/index.html` | ~130 | HTML shell with embedded CSS |
| `static/js/app.js` | ~1300 | Preact SPA wizard. Multi-step form with conditional branching. State persisted to `localStorage`. Uses Preact + htm via CDN (no build step). |

Key concepts in `app.js`:
- `defaultState()` defines the full wizard state shape
- `STEPS` array controls wizard navigation; each step has a `show` function for conditional visibility
- `buildPayload()` converts wizard state into the API request body
- `incomeTypes` flags control which income entry steps are shown
- State is saved to `localStorage` under key `tax-wizard-state`

### Tests

| Path | Purpose |
|------|---------|
| `tests/conftest.py` (~1900 lines) | BDD test fixtures and all shared step implementations (`@given`, `@when`, `@then`) |
| `tests/features/` (15 files) | Gherkin `.feature` files, one per tax scenario category |
| `tests/step_defs/` (15 files) | Thin `@scenario(...)` wrappers that bind feature files to pytest |
| `tests/test_schema.py` | Validates JSON Schema generation |
| `tests/test_schema_references.py` | Validates schema cross-references |
| `tests/e2e/conftest.py` (~436 lines) | Server fixture, `Wizard` helper class, `run_scenario()`, assertion helpers |
| `tests/e2e/test_wizard_flow.py` (9 tests) | Full wizard navigation tests — step-by-step form filling |
| `tests/e2e/test_*.py` (15 files, 59 tests) | State-injection tests — one file per feature/scenario group |

## Key Patterns

### Data Models

- All models are Python `@dataclass` types with default values
- Optional lists use `field(default_factory=list)`; optional scalars use `None`
- Enums inherit from `(str, Enum)` so they serialize as strings
- `_deserialize_enum()` in `calculator.py` recursively converts JSON dicts into proper dataclass instances with enum values

### Calculator

- References IRC sections in comments (e.g., `# IRC §1(j)`)
- Tax brackets, thresholds, and phase-outs are 2025 inflation-adjusted constants at the top of the file
- Raises `ValidationError` for invalid inputs
- Returns a fully-populated `TaxReturnOutput` with sub-objects for income, AGI, deductions, tax, credits, and payments

### Web UI State

The wizard state shape in `app.js defaultState()` must stay in sync with `tests/e2e/conftest.py _default_wizard_state()`. When adding UI fields, update both.

`buildPayload()` in `app.js` only extracts data the UI has forms for. Features without UI forms cannot be tested through normal form filling — use the state-injection pattern instead.

### E2E Test Patterns

**Pattern 1: State injection (fast, used for all scenarios)**

```python
from .conftest import run_scenario, get_results_json, wizard_state, person, w2, assert_json_field

def test_some_scenario(page, server_url):
    state = wizard_state(
        filing_status="single",
        personal_info=person("Alice", "Smith", "111-22-3333", "1990-03-15"),
        income_types={"w2": True},
        w2_income=[w2("Acme", "11-1111111", 75000, 9000)],
    )
    payload = {
        "tax_year": 2025,
        "filing_status": "single",
        "personal_info": {...},
        "address": {...},
        "w2_income": [{...}],
        "deduction_method": "standard",
    }
    run_scenario(page, server_url, state, payload)
    r = get_results_json(page)
    assert_json_field(r, "income", "total_wages", expected=75000)
```

`run_scenario()` injects `localStorage` state, intercepts the `/api/calculate` fetch with the exact payload, clicks Calculate, and waits for results. This lets you test calculator features that have no corresponding UI form fields.

**Pattern 2: Full wizard flow (for video demos)**

```python
from .conftest import Wizard, assert_json_field

def test_wizard_scenario(wiz, page):
    wiz.select_filing_status("single")
    wiz.next()
    wiz.fill("First name", "Alice")
    # ... fill all fields step by step ...
    wiz.calculate()
    r = wiz.results()
    assert_json_field(r, "income", "total_wages", expected=75000)
```

The `Wizard` class navigates step-by-step filling real form fields. These tests produce useful video recordings saved to `test-results/videos/`.

### BDD Test Pattern

Feature files use Gherkin syntax. Step definitions in `tests/step_defs/` are thin wrappers:

```python
from pytest_bdd import scenario

@scenario("single_w2_standard.feature", "Single filer with $75,000 W-2 income")
def test_single_w2_standard():
    pass
```

All `@given`, `@when`, and `@then` step implementations live in `tests/conftest.py`. The `TaxScenarioContext` dataclass accumulates inputs across steps, then `@when("the tax return is calculated")` builds `TaxReturnInput` and calls `calculate()`.

## Running Tests

```bash
# BDD tests (unit/integration — no browser needed)
uv run pytest tests/ -k "not e2e"

# E2E tests (starts server automatically, records video)
uv run pytest tests/e2e/ -v

# Full wizard flow tests only
uv run pytest tests/e2e/test_wizard_flow.py -v

# Videos saved to test-results/videos/
```

All commands use `uv run` to ensure the correct virtual environment. The e2e server fixture is session-scoped — it starts once on port 8765 for all tests.

## Adding New Tax Features

1. **Models** — Add dataclass fields to `models.py` for both input and output. Follow existing conventions: `float` for money, `Optional[...]` for nullable, `field(default_factory=list)` for lists.

2. **Calculator** — Add computation logic in `calculator.py`. Reference the IRC section in a comment. Add 2025 constants if needed.

3. **BDD test** — Create a `.feature` file in `tests/features/`. Add step definitions in `tests/step_defs/` (thin `@scenario` wrappers). If you need new `@given`/`@then` steps, add them to `tests/conftest.py`.

4. **E2E test** — Add a test in the appropriate `tests/e2e/test_*.py` file (or create a new one). Use the state-injection pattern with `run_scenario()`.

5. **UI support** (if applicable):
   - Add form fields to the appropriate wizard step in `static/js/app.js`
   - Update `buildPayload()` to include the new fields
   - Update `_default_wizard_state()` in `tests/e2e/conftest.py` to match
   - Add a full wizard flow test in `tests/e2e/test_wizard_flow.py`

6. **No UI support** — Use the state-injection pattern. The `payload` dict sent to `run_scenario()` goes directly to the server via route interception, bypassing `buildPayload()`. This is how features like AMT preferences, K-1 income, and carryforwards are tested.

## Common Pitfalls

- **`buildPayload()` vs full model**: The web UI `buildPayload()` only extracts data the UI has forms for. Many `TaxReturnInput` fields (AMT preferences, K-1 income, carryforwards, kiddie tax, etc.) have no UI. For testing these, you must use route interception in e2e tests to replace the POST body.

- **`_deserialize_enum()` is required**: When constructing `TaxReturnInput` from a JSON dict, call `_deserialize_enum(data, TaxReturnInput)` first. It recursively converts string values to enum instances and nested dicts to dataclass instances. The server and CLI both do this before calling `calculate()`.

- **Wizard step visibility**: Steps appear or hide based on `incomeTypes` flags and each step's `show` function in the `STEPS` array. If a step does not appear during a wizard flow test, check that the corresponding `incomeTypes` flag was toggled on.

- **Session-scoped server**: The e2e server fixture starts once for the entire test session. Do not assume a fresh server per test. State isolation comes from `localStorage` manipulation, not server restarts.

- **Video recording**: Configured via the `browser_context_args` fixture in `tests/e2e/conftest.py`. Videos are saved to `test-results/videos/`. The viewport is 1280x720.

- **Playwright `fill()` needs strings**: Number and money fields in Playwright must receive string values. Always use `str(value)` when calling `wiz.fill()` or `field.fill()`.

- **`server_url` fixture pattern**: State-injection test files define a local `server_url` fixture that just returns the session-scoped `server` fixture value. This is the convention across all e2e test files:
  ```python
  @pytest.fixture()
  def server_url(server):
      return server
  ```

- **Enum string values**: All enums use lowercase snake_case string values (e.g., `"single"`, `"married_filing_jointly"`, `"short_term"`). The wizard state, API payloads, and calculator all use these string representations.

- **Float tolerance in assertions**: `assert_json_field` uses a default tolerance of 1.0 for numeric comparisons. Use the `gt`, `lt`, `gte`, `eq`, and `expected` keyword arguments for different comparison modes.
