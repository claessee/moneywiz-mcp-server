# Implementation and validation report

Date: 2026-10-03. Classification: **READY FOR READ-ONLY RECONCILIATION**.

## Executive summary and provenance

Implemented a local, permanently read-only, deterministic MoneyWiz MCP adapter.
Financial output uses decimal strings and explicit currencies. Entity IDs and
relationships are inspected centrally, errors remain explicit, list completeness
is visible, and the official MCP SDK 2.3.0 is pinned. No real MoneyWiz database
was opened and no balances or totals were independently compared with its UI.

- Repository: https://github.com/jcvalerio/moneywiz-mcp-server
- Starting main SHA: `d113a11df8ea475f50b5d118585c763bb4f5ba72`
- Local checkout: `/Users/macmini2/Scripts/Codex-files/moneywiz-mcp-server`
- Local branch: `local/read-only-hardening`
- Local package version: `2.0.0.dev0` (breaking tool/configuration contracts).
- Changes remain uncommitted and local. No push, upstream merge, PR, publication,
  client registration, tunnel or Codex configuration edit was performed.
- Original MIT license and author attribution are preserved. Git retains the
  original source, retired functionality and tests for review or recovery.

## Architectural decisions

1. Preserve the existing Python package, async SQLite manager, service/module
   separation, Pydantic models and local stdio architecture. Replace unsafe
   query/conversion internals rather than introduce another application/platform.
2. Central `Schema` resolves `Z_PRIMARYKEY`, validates mappings, inheritance,
   required columns and populated entity families, and discovers generated tag
   joins/scheduled category columns. SQL values are bound; inspected identifiers
   are validated and quoted, including embedded quotes. The map is scoped to one
   connection/snapshot and discarded on close; there is no stale global mapping.
3. Permanent SQLite URI `mode=ro`, `query_only=ON`, `trusted_schema=OFF` and a
   deny-by-default authorizer. Only controlled reads, validation PRAGMAs and
   BEGIN/ROLLBACK are permitted. There is no commit/write helper or raw-SQL tool.
   An attempted writable legacy configuration is rejected. All reads in a tool
   share one snapshot. WAL is respected without `immutable=1`; SQLite may use
   normal shared-memory locking metadata but never writes financial rows/WAL.
4. Exact path configuration is the default. Opt-in discovery searches known
   MoneyWiz roots, rejects sidecars/shared/empty/invalid stores, requires actual
   account rows, and refuses zero/multiple plausible candidates. No discovery
   was run against this user's installation.
5. Decimal conversion and sufficient-precision arithmetic replace float/SQL SUM
   calculations. Amounts serialize as strings with currency; all aggregation is
   per currency, with no FX, inferred primary currency or nominal currency ranking.
   Existing precision loss in SQLite REAL cannot be recovered.
6. Retain factual retrieval and deterministic complete cashflow/type/category
   aggregation. Remove subjective financial-health, importance, recommendations,
   approximate recurrence forecasts and unsafe balance/budget guesses, along with
   their obsolete models, investigation scripts and mock-heavy tests. Payees and
   tags remain factual references, with standalone listing tools.
7. Eleven MCP tools use structured data/error envelopes and read-only,
   non-destructive, idempotent, closed-world annotations. Controls enforce safety
   independently of metadata. SDK validation errors use MCP error status; service
   failures use `data: null` and structured `error`, which clients must inspect.
8. ISO intervals are [start, end), local dates use explicit Europe/Lisbon by
   default, datetimes require offsets, and resolved endpoints are returned.
   Lists have stable ordering/counts/pagination. Complete aggregates stream every
   match; the bounded category breakdown has separate completeness metadata.
9. Balances remain provisional with opening amount, type sums/counts and warnings.
   Credit cards expose competing candidates with/without the credit limit; no
   authoritative formula is asserted. Investment/forex/loan valuation is explicitly
   unsupported. Budgets expose verified stored fields/currency without inferred
   limit/spending/rollover. Schedules expose stored recurrence, including salary,
   disabled and one-off entries, without projecting future executions.
10. Locked dependencies, blocking lint/format/typing/security/tests, and per-module
    critical coverage gates replace permissive CI. The SDK's default OpenTelemetry
    middleware is removed with its documented pinned-version opt-out; no exporter
    or server network transport is added. Connected clients still control whether
    requested tool results are sent to a model provider.

## Confirmed upstream defects addressed

- Fixed numeric entity IDs across accounts, transactions, classifications, tags,
  budgets and schedules could select the wrong entities or omit legitimate rows.
- `search_transactions.transaction_type` was metadata rather than an applied query
  filter. It now reaches bound SQL and is tested through the actual MCP protocol.
- Discovery omitted the reported iCloud application-support location and could
  consider sidecars/shared stores; it now validates each candidate and ambiguity.
- Read-only mode could be disabled; write/commit and optional third-party database
  API paths existed. They are removed and mutation probes verify structural denial.
- Swallowed conversion/relationship failures, assumed USD/CRC, fallback dates and
  unresolved-name defaults made incomplete/incorrect output look valid. Integrity
  failures now produce structured errors, including unreferenced classifications
  checked by the reconciliation harness.
- Float SQL totals, mixed-currency sums and nominal rankings were invalid financial
  arithmetic. Aggregation now preserves each currency and exact decimal values.
- Scheduled salary/deposit handling was incomplete; scheduled date filtering was
  accepted without reliably being applied. The new surface returns factual stored
  schedules without an ignored period/projection parameter.
- Budget filtering/inferred semantics could drop zero/negative definitions and
  present guessed currency/status. Stored fields and unsupported states are explicit.
- Locale/naive/fallback date handling, misleading limited counts and missing stable
  pagination are replaced by tested ISO/timezone/boundary and completeness contracts.
- Private SQL/parameters/records could enter logging/investigation output. Routine
  server errors are sanitized and the default harness omits individual transactions,
  notes and payees. No real financial records were used in implementation.

Additional regressions found while implementing: malformed stored dates could
silently disappear behind date predicates, identical category leaf names could
merge unrelated categories, and in-process MCP calls could overlook an environment
MAX_RESULTS cap. Dedicated checks now cover all three. The harness also flags
truncated category groups without truncating currency totals.

## Suspicions corrected or left unproven

- SQLite permits `IN ()`; the suspected syntax error is disproven. Unresolved empty
  entity mappings still error, while an intentionally empty user filter matches
  nothing. These are different correctness conditions.
- Upstream already had `mode=ro` and query_only in its read-only branch; their
  optional nature and retained write paths were the defect.
- PR #44 was open/unmerged with mergeable_state `blocked`, head
  `a0114e55d1e6edc1922b6c23bf4d1971bcf9635f`. Check-runs returned no runs; commit
  status was pending with no individual statuses. No completed failing or green
  CI result was established. The PR was evaluated, not merged/cherry-picked.
- #48's credit-limit-sized discrepancy does not establish a general formula.
  Net-of-limit opening balance, conditional opening offset and different UI
  balance meanings remain competing explanations requiring real reconciliation.
- Reporter counts of 13,355 versus 2,497 transactions and 9 versus 0 budgets are
  upstream evidence, not measurements of this user's store.
- Synthetic remapping proves the implementation does not depend on those numeric
  IDs; it does not prove universal MoneyWiz/Core Data version compatibility.

Primary research links and the pre-implementation assessment are in
[ENGINEERING_AUDIT.md](ENGINEERING_AUDIT.md).

## Actual validation results

Local execution: macOS arm64, Python **3.12.15**. All test data was fabricated.
The baseline unit/non-integration run before editing was **119 passed, 29
integration tests deselected**, in 1.14s. Unsafe real-store-oriented integration
paths were not run. The replacement suite tests actual async SQLite and MCP
protocol behavior; its count is not directly comparable to retired mock tests.

| Check actually run | Result |
| --- | --- |
| `.venv/bin/pytest -q` (all current tests) | **171 passed**, no deselection/skip, 2.74s |
| Coverage from that run | **94.17%**, 944 statements / 55 missing; 85% global gate passed |
| `.venv/bin/python scripts/check_critical_coverage.py` | All 10 critical modules passed their individual 90% gate |
| `.venv/bin/ruff check .` | Passed with obsolete global unused-import/argument/path ignores removed |
| `.venv/bin/ruff format --check .` | Passed, 27 Python files |
| `.venv/bin/mypy src/` | Passed, strict configuration, 20 source files |
| `.venv/bin/bandit -r src/ -q -f json -o /private/tmp/moneywiz-bandit-final.json` | Zero unsuppressed findings, zero analysis errors; 12 locally annotated B608 SQL-assembly checks skipped, no global B608 skip |
| `.venv/bin/pip-audit --local --skip-editable --format=json --output=/private/tmp/moneywiz-dependency-audit.json` | 85 installed packages audited, zero known vulnerabilities; one editable local package skipped (86 inventory entries) |
| `/private/tmp/moneywiz-tooling/bin/uv lock --check` | Passed; 99 cross-platform lock records resolved |
| `/private/tmp/moneywiz-tooling/bin/uv sync --frozen --all-extras` | Passed, locked local package version 2.0.0.dev0 |
| `/private/tmp/moneywiz-tooling/bin/uv build --no-sources` | Wheel and source archive built successfully |
| `.venv/bin/twine check dist/moneywiz_mcp_server-2.0.0.dev0*` | Both artifacts passed |
| Clean wheel installation into `/private/tmp/moneywiz-wheel-smoke` | Installed and imported from its own site-packages, outside the checkout |
| Installed-wheel MCP/CLI smoke using the official Client | Eleven-tool inventory; status/schema/accounts; applied type filter, count/pagination/truncation and decimal strings; reconciliation CLI all passed; fabricated database SHA256 unchanged |
| Wheel/sdist archive inspection | License/schema/harness included; source archive includes lock/tests/docs; no database/sidecar artifacts or retired services |
| `git diff --check` | Passed |
| Workflow/pre-commit YAML and JSON/TOML examples parsing | Passed |

The Bandit annotations cover only reviewed bound-value/validated-identifier query
assembly. Its notices about nosec on nonfinding AST nodes are scanner notices,
not extra findings. No claim of an unconditional security proof is made.
Dependency auditing transmitted public package/version metadata only.

Relevant statement coverage:

| Module | Coverage |
| --- | --- |
| database/connection.py | 98.55% |
| database/schema.py | 93.33% |
| models/currency_types.py | 97.14% |
| services/account_service.py | 95.71% |
| services/transaction_service.py | 98.04% |
| services/category_classification_service.py | 96.49% |
| services/budget_service.py | 97.14% |
| services/scheduled_transaction_service.py | 100.00% |
| utils/date_utils.py | 97.67% |
| main.py | 90.91% |

Config coverage is 96.92%, response models 100%, harness 76.83%. The subprocess
CLI/stdio smoke is not included in in-process coverage, explaining unobserved
entry-point branches. Python 3.10/3.14 and Linux/macOS are configured in CI;
those extra matrix environments and hosted CI have **not** been executed here.
UV_PYTHON is explicitly assigned per matrix job so uv run retains that interpreter.

Tests cover two full schemas with different entity numbering; required/optional
mappings and malformed inheritance; dynamic hostile identifiers; missing/dangling
references and category cycles; discovery rejection/ambiguity; helper, authorizer,
query_only and mode=ro mutation denial; live WAL visibility/snapshot refresh and
unchanged main/WAL data; all supported type/account/category/date filters; stable
pagination; schedules/budgets/classifiers; Decimal precision/signs/zero/currencies;
provisional balances; NSDate UTC epoch; month boundaries and Lisbon 23/25-hour DST;
all eleven tools over the real SDK; sanitized errors/logs; and harness partial errors
and category truncation while totals remain complete.

## Remaining uncertainty and real-store acceptance

Core Data SQLite is a private implementation detail. The adapter uses observed
upstream entity names/columns and fabricated schema variants. An unobserved real
schema must error or report unsupported capability; it must be inspected before
extending the adapter. No claim of MoneyWiz 2/3/iCloud universal support is made.

Before routine use, independently compare the same store/interval with MoneyWiz:
account names/types/currencies/counts, each balance and its components, per-account
transaction counts, type/sign conventions, transfer legs/pairs, categories and
hierarchies, payee/tag relationships, per-currency income/expenses, budgets and
scheduled salary/expenses/transfers including disabled/one-off entries.
Resolve or explicitly document discrepancies before calling the deployment RECONCILED.

Credit-card balances, null opening balances, investment/forex/loan valuation,
budget limit/rollover/spending meaning, refund/reconciliation inclusion in UI
cashflow, stored schedule next-date/recurrence meaning and split-category amounts
remain explicit uncertainties. Split expenses are included in complete totals
but left unallocated by category. No FX or recurrence forecasting is implemented.

Per-call snapshots are consistent; offset pages across live updates are not a
frozen export. Use a consistent backup/copy for multi-page comparisons. The
server's output is local stdio, but a connected model client can transmit requested
financial output under its own settings. Reconciliation should be local first.

## Exact macOS reconciliation commands and configuration

This session leaves the installed environment ready. The reported iCloud path
below is a **candidate**, not a verified path on this Mac. Substitute the actual
primary store or a consistent MoneyWiz backup if necessary:

```sh
cd /Users/macmini2/Scripts/Codex-files/moneywiz-mcp-server
.venv/bin/python -m moneywiz_mcp_server.validate \
  --db "$HOME/Library/Containers/com.moneywiz.personalfinance/Data/Library/Application Support/MoneyWiz_iCloud.sqlite" \
  --start 2026-09-01 --end 2026-10-01 --timezone Europe/Lisbon
```

A second selected period covers the spring DST change:

```sh
.venv/bin/python -m moneywiz_mcp_server.validate \
  --db "/absolute/path/to/your/consistent/MoneyWiz.sqlite" \
  --start 2026-03-01 --end 2026-04-01 --timezone Europe/Lisbon
```

Exit 0 means adapter checks completed with UI comparison pending; exit 1 is a
fundamental validation failure; exit 2 retains successful sections and explicit
errors. The JSON report includes schema/missing capabilities/warnings, masked path,
account components/types/currencies, all-period type counts and per-currency totals,
transfer leg count, classifier/schedule/budget counts and truncation warnings.
It does not dump individual transactions. See [RECONCILIATION.md](RECONCILIATION.md)
for the comparison and consistent-store procedure. Keep any captured output private.

After reconciliation, the provided Codex TOML example is:

```toml
[mcp_servers.moneywiz]
command = "/Users/macmini2/Scripts/Codex-files/moneywiz-mcp-server/.venv/bin/python"
args = ["-m", "moneywiz_mcp_server"]

[mcp_servers.moneywiz.env]
MONEYWIZ_DB_PATH = "/absolute/path/to/your/verified/primary/MoneyWiz.sqlite"
MAX_RESULTS = "500"
```

Use a literal absolute path in client configuration. `.env.example` is documentation;
the process does not automatically read `.env`. Do not set a writable option.
Nothing in this task applied this configuration or selected a real database.

## Exact changed-file manifest

Paths below are relative to the local checkout above. M = modified, A = newly
added, D = retired/deleted from this working copy. Deleted originals remain in
Git at the starting SHA. Ignored environment/build/coverage outputs are generated
artifacts, not source changes.

```text
M .env.example
M .github/workflows/ci.yml
M .github/workflows/security.yml
M .gitignore
M .pre-commit-config.yaml
M .python-version
M ARCHITECTURE.md
M CHANGELOG.md
M CONTRIBUTING.md
A MANIFEST.in
M Makefile
M README.md
M SECURITY.md
A docs/ENGINEERING_AUDIT.md
A docs/IMPLEMENTATION_REPORT.md
A docs/RECONCILIATION.md
M docs/RELEASING.md
M docs/ROADMAP.md
M examples/claude_code_config.json
M examples/claude_desktop_config.json
M examples/claude_desktop_config_venv.json
A examples/codex_config.toml
D final_scheduled_investigation.py
D focused_scheduled_investigation.py
D investigate_budgets.py
D investigate_budgets_deep.py
D investigate_scheduled_transactions.py
M pyproject.toml
M scripts/check-ci.sh
A scripts/check_critical_coverage.py
M setup_env.py
M src/moneywiz_mcp_server/__init__.py
M src/moneywiz_mcp_server/config.py
M src/moneywiz_mcp_server/database/connection.py
A src/moneywiz_mcp_server/database/schema.py
A src/moneywiz_mcp_server/errors.py
M src/moneywiz_mcp_server/main.py
M src/moneywiz_mcp_server/models/__init__.py
D src/moneywiz_mcp_server/models/analytics_result.py
D src/moneywiz_mcp_server/models/base.py
D src/moneywiz_mcp_server/models/budget.py
M src/moneywiz_mcp_server/models/currency_types.py
M src/moneywiz_mcp_server/models/responses.py
D src/moneywiz_mcp_server/models/savings_responses.py
D src/moneywiz_mcp_server/models/scheduled_transaction.py
D src/moneywiz_mcp_server/models/transaction.py
M src/moneywiz_mcp_server/services/__init__.py
M src/moneywiz_mcp_server/services/account_service.py
M src/moneywiz_mcp_server/services/budget_service.py
M src/moneywiz_mcp_server/services/category_classification_service.py
D src/moneywiz_mcp_server/services/savings_service.py
M src/moneywiz_mcp_server/services/scheduled_transaction_service.py
M src/moneywiz_mcp_server/services/transaction_service.py
D src/moneywiz_mcp_server/services/trend_service.py
M src/moneywiz_mcp_server/utils/__init__.py
M src/moneywiz_mcp_server/utils/date_utils.py
D src/moneywiz_mcp_server/utils/env_loader.py
D src/moneywiz_mcp_server/utils/formatters.py
D src/moneywiz_mcp_server/utils/validators.py
A src/moneywiz_mcp_server/validate.py
M tests/conftest.py
D tests/fixtures/create_test_db.py
D tests/integration/test_budgets_integration.py
D tests/integration/test_category_resolution.py
D tests/integration/test_fastmcp_tools.py
A tests/integration/test_mcp_v2.py
D tests/integration/test_scheduled_transactions_integration.py
D tests/integration/test_service_compatibility.py
D tests/test_analytics_basic.py
D tests/unit/test_budget_models.py
D tests/unit/test_budget_service.py
D tests/unit/test_category_classification_data_driven.py
D tests/unit/test_currency_types.py
D tests/unit/test_database_connection.py
A tests/unit/test_hardening.py
D tests/unit/test_savings_service.py
D tests/unit/test_scheduled_transaction_models.py
D tests/unit/test_scheduled_transaction_service.py
D tests/unit/test_transaction_tags.py
D tests/unit/test_trend_service.py
M uv.lock
```
