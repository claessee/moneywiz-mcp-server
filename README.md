# MoneyWiz MCP Server — local read-only reconciliation fork

This fork provides factual MoneyWiz retrieval and exact, deterministic aggregation
through the official Python MCP SDK 2.3.0. It is **READY FOR READ-ONLY
RECONCILIATION**, not RECONCILED. No real MoneyWiz database/UI has been compared
in this implementation session. Original author/license attribution is retained.

## Safety and scope

SQLite always opens with `mode=ro`, `query_only=ON`, `trusted_schema=OFF` and a
read-only authorizer. There is no writable setting, transaction/commit helper,
third-party database API, raw-SQL tool, network transport or backup-before-write
path. `MONEYWIZ_READ_ONLY=false` is rejected rather than interpreted as permission.
Each tool opens one read transaction, validates SQLite with `quick_check`, builds
its schema map, reads a consistent snapshot and closes it. WAL data is read;
`immutable=1` is intentionally avoided because it can ignore WAL changes.
SQLite may use its normal WAL/shared-memory locking metadata; no financial rows,
schema, main database bytes or WAL records are written by this server.

Core Data SQLite is private implementation detail, not a supported MoneyWiz API.
The adapter covers entity/column observations from upstream source and PR #44,
tested with fabricated stores with two substantially different entity maps,
TEXT/REAL monetary values and WAL. This does not demonstrate universal
MoneyWiz 2/3/iCloud compatibility. Missing/ambiguous relationships, unknown
populated transaction/account descendants and invalid references fail explicitly.
Unused abstract entity definitions are allowed. Missing optional capabilities
are disclosed in `schema_info` and fail explicitly when requested.

## Install the local working copy

This branch has breaking tool/configuration changes and version `2.0.0.dev0`.
It has not been published. Do not install the upstream PyPI release expecting
these guarantees. With uv installed:

```sh
cd /Users/macmini2/Scripts/Codex-files/moneywiz-mcp-server
uv sync --frozen --all-extras --python 3.12.15
```

The session also leaves an installed `.venv`. Python 3.12.15 is the local tested
runtime; Python 3.10/3.14 and Linux/macOS are configured in CI but only executed
locally if recorded in the validation report. CI checks are blocking.

## Exact database path

Set `MONEYWIZ_DB_PATH` in your MCP client's environment to the absolute primary
SQLite file. The server deliberately does not load `.env`, inspect arbitrary
home directories or pick the first candidate. A reported iCloud location is:

```text
~/Library/Containers/com.moneywiz.personalfinance/Data/Library/Application Support/MoneyWiz_iCloud.sqlite
```

Expand `~` to your actual home directory in JSON/TOML client configuration. This
path is a documented candidate, not proof of your installation's actual path.
Legacy container `Data/Documents` stores, including `.AppData`, remain discovery
candidates. Explicit paths must be regular, readable, nonempty, valid SQLite with
required Core Data/MoneyWiz tables and entities. Symlink targets are validated.
`-wal`, `-shm`, `-journal` and `_shared.sqlite` are intentionally rejected as
primary inputs. Adjacent valid SQLite WAL/SHM files remain necessary for reading
a live WAL-mode store; never select them or discard them from a live snapshot.

`MONEYWIZ_AUTO_DISCOVER=true` explicitly opts into searching only known MoneyWiz
container/application-support roots. Every candidate undergoes the same
validation and must have account rows. Zero or multiple plausible candidates
produce an error; neither directory order nor modification time chooses a store.
Prefer explicit configuration for all real use.

## Local MCP client setup

For Codex, use an STDIO server with an absolute executable, arguments
`["-m", "moneywiz_mcp_server"]`, and the exact database path in `env`.
[Official client configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
supports the following TOML shape (also provided in `examples/codex_config.toml`):

```toml
[mcp_servers.moneywiz]
command = "/Users/macmini2/Scripts/Codex-files/moneywiz-mcp-server/.venv/bin/python"
args = ["-m", "moneywiz_mcp_server"]

[mcp_servers.moneywiz.env]
MONEYWIZ_DB_PATH = "/absolute/path/to/MoneyWiz_iCloud.sqlite"
MAX_RESULTS = "500"
```

This is a configuration example; this task has not changed your Codex settings
or connected any real database. Reload the client and call `server_status`, then
`schema_info`, after completing local reconciliation. Generic local MCP clients
can use the JSON examples in `examples/`.

This server implements local stdio only. A cloud-only ChatGPT connection requires
an explicitly designed additional access mechanism. No tunnel, HTTP listener,
remote database access or publishing is included or authorized here.

## Tool catalogue

All tools carry read-only/non-destructive/closed-world annotations. Database
controls enforce safety independently of these advisory annotations. Successful
responses are `{ "data": ..., "error": null }`; failures contain a structured
`error.code` and fixed operational/schema message, with `data: null`. Inspect the
error field on every call; a normal MCP transport response is not a success
assertion. SDK input-schema failures use MCP `is_error=true`.

| Tool | Meaning |
| --- | --- |
| `server_status` | Connection/SQLite/schema verification, no balances or paths |
| `schema_info` | Observed entity IDs, table columns, missing optional capabilities |
| `list_accounts` | Stored accounts, currency and provisional balance components |
| `get_account` | One returned numeric ID or exact ZGID; ambiguous identifiers fail |
| `search_transactions` | Explicit interval, account/category/type filtering and pagination |
| `list_categories` | Category IDs, names and complete parent hierarchy |
| `list_tags` | Factual stored tag IDs and names |
| `list_payees` | Factual stored payee IDs and names |
| `list_budgets` | All budgets, including zero/negative amounts, stored monetary components |
| `list_scheduled_transactions` | Income/expense/transfer handlers, disabled and one-off schedules included |
| `summarize_cashflow` | Complete per-currency cashflow/type sums and bounded expense-category breakdown |

`search_transactions` supports `deposit`, `withdraw`, `transfer_in`,
`transfer_out`, `investment_buy`, `investment_sell`, `investment_exchange`,
`refund`, `reconcile`, `transfer_budget`. Names map to entity names, never numeric
IDs or guessed signs. Requested types missing from a schema return explicit
errors. `account_ids` accept returned IDs or exact ZGIDs; duplicates deduplicate,
missing/ambiguous references fail. Category names match themselves and descendants;
equal leaf names can select multiple categories, whose identities remain explicit
in output. Empty filter lists match no rows and never widen a query.

## Money and balance semantics

Every amount is `{ "amount": "123.4500", "currency": "EUR" }`. Decimal strings
retain precision. TEXT/INTEGER/REAL values normalize through their deterministic
Python decimal textual representation; precision already lost in SQLite REAL
storage cannot be reconstructed. Arithmetic uses sufficient decimal precision,
never SQLite floating-point SUM or float money calculations. No FX, cross-currency
total, nominal currency ranking or inferred primary currency exists.

Cashflow income is signed `DepositTransaction` amounts; expenses are negated
`WithdrawTransaction` amounts. Reversals keep their signs. Net is income minus
expenses within each currency. Refunds, investments, reconciliations and budget
transfers are separately labelled stored sums, excluded from these narrowly
specified income/expense totals. Transfers count **legs**, not deduplicated transfer
pairs, and never count as income. Expense category breakdown uses category IDs,
not leaf-name merging; split expenses stay in currency totals with an explicit
unallocated count rather than fabricated category allocation.

Balances are **provisional**, opening balance plus all observed account amount
fields, with per-type sums/counts. Null opening balance means no calculated
balance. Investment/forex/loan valuation is not claimed. Credit cards expose
opening balance, transaction sum, credit limit, and candidates with/without the
limit. Neither candidate is labelled authoritative. Issue #48 offers insufficient
evidence to choose a general credit-card formula. Compare components to the UI.

Budgets expose stored `ZOPENINGBALANCE1`/`ZAMOUNT1`, with their own verified
currency code/name or `Currency.ZCODE` reference. No account-derived currency,
assumed CRC, guessed limit, rollover, spent amount or subjective risk label is
returned. Conflicting/unresolved currency fields are explicit unsupported-schema
errors. Scheduled data exposes stored recurrence fields; it does not guess end
conditions, generate executions or treat approximate 30-day months as months.

## Dates, ordering and completeness

Intervals are **[start, end)**. Dates are ISO `YYYY-MM-DD` at midnight in the
explicit IANA timezone (default `Europe/Lisbon`); datetimes require `T` and an
explicit offset/`Z`. Naive datetimes, locale dates and natural-language periods
are rejected. Resolved timezone-aware endpoints are returned. NSDate's epoch is
2001-01-01T00:00:00Z. Stored dates return UTC, preserving their instant rather than
inventing a database timezone. Lisbon DST days are tested at 23 and 25 hours.
Malformed stored dates cannot disappear behind a WHERE interval filter.

Lists accept `limit=1..500` (default 100), `offset=0..10000000` and return
`matched_count`, `returned_count`, `limit`, `offset`, `truncated`, `next_offset`.
`MAX_RESULTS` can impose a lower list limit. Transactions order by date DESC,
ID DESC; schedules by execution date ASC, ID ASC; other lists by ID ASC. Counts
and rows share a snapshot. Offset pagination across separate live-store calls
can change when MoneyWiz edits records; use a consistent frozen copy for a full
multi-page export. A page with an offset is explicitly partial even at the end.

Cashflow streams every matched row; totals are never limited to a transaction
page. The nested expense-category page is bounded at 500 and reports its own
truncation; `truncated=false` at cashflow level describes the complete totals.
Use category-filtered transaction pages to investigate any omitted category
records. Schema diagnostics bound stores at 500 tables/entities and 1000 columns
per table; cashflow has at most 500 currency groups, otherwise explicit errors.

## Reconciliation and privacy

Run the local command before client use; [the procedure](docs/RECONCILIATION.md)
includes exact commands, comparisons and credit-card diagnostics. Exit codes:
0 = adapter checks completed, **UI comparison still pending**;
1 = database/configuration validation failed; 2 = explicit incomplete diagnostic
sections. A zero exit code does not mean RECONCILED. Output omits individual
transactions/payees/notes by default and uses a home-relative or masked path.

The server performs no networking and installs no telemetry exporter. The SDK's
default OpenTelemetry server middleware is removed using its
[documented opt-out](https://py.sdk.modelcontextprotocol.io/run/opentelemetry/).
Requested data travels over stdio to the MCP client; that client may forward
tool results to its model provider under its own policy. Routine server logs
contain no financial records/SQL/arguments/full paths. Keep reconciliation output
local; database files and reconciliation JSON are ignored by Git and excluded
from packages. Tests use fabricated data only and never auto-discover real stores.

## Upgrade and development

Keep a local snapshot/branch of the validated checkout. Read changes to schema,
SDK, money, date and tool contracts before upgrading. Run `uv sync --frozen`,
all checks and UI reconciliation after any change; restart the MCP client.
Pin the SDK/dependencies through `pyproject.toml` and committed hash-bearing
`uv.lock`; do not run an unconstrained install in an MCP startup command.

```sh
uv run --frozen pytest
uv run --frozen python scripts/check_critical_coverage.py
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy src/
uv run --frozen bandit -r src/
uv run --frozen pip-audit --local --skip-editable
uv build --no-sources
uv run --frozen twine check dist/*
```

The full suite enforces 85% global coverage and a separate 90% minimum in each
critical database/schema/money/service/date/MCP module, with regression-heavy critical components
rather than trivial mocks. Full Bandit scanning is enabled; reviewed B608
exemptions cover only dynamically built bound-value/quoted-identifier queries.
No global B608 exemption or nonblocking type/security checks remain.
See [engineering evidence](docs/ENGINEERING_AUDIT.md) and
[implementation/validation report](docs/IMPLEMENTATION_REPORT.md).
