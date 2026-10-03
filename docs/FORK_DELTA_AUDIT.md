# Fork Delta Audit

## Baseline

Audited on **2026-10-03** against original upstream
[`jcvalerio/moneywiz-mcp-server`](https://github.com/jcvalerio/moneywiz-mcp-server)
at exact SHA **`d113a11df8ea475f50b5d118585c763bb4f5ba72`**.

Our starting checkout was branch **`main`**, HEAD
**`666d332825c34a19a394fa81e6e5a2e6f1b6e637`** (`Docs: restore MoneyWiz architecture image`), with a clean
tracked/untracked working tree. Comparisons below use our current source,
including the authorized Task 1 category fix. No fork was cherry-picked.

Method: read the live GitHub baseline-to-main comparisons, all twelve listed
commit patches, and the pinned final versions of every added/modified production
module in both fork deltas. Also inspect their changed test assertions and
fixture construction, configuration/packaging patches, and documentation deltas.
Compare the actual functions with our schema, database, service, model, MCP and
validation layers. Merge comparisons distinguish integration from new behavior.
Neither fork's tests were executed, and this audit did not open a real financial
database. Independent acceptance checks should use MoneyWiz-produced exports locally;
[RECONCILIATION.md](RECONCILIATION.md) documents the generic procedure.

Each table row has exactly one classification. Multiple rows for one commit
separate behaviors with different dispositions. Source links pin immutable
fork heads; commit links identify the introducing change. Our evidence names
repository-relative files and exact functions so it remains inspectable locally.
New optional reporting/filter features are distinguished from missing fixes in
our existing tool contracts.

## Forks examined

| Fork | Live main SHA | Divergence from baseline | Examination |
| --- | --- | --- | --- |
| HigorLoren/moneywiz-mcp-server | `077d7337d2f011023d81de7517d9024bed753a19` | 9 ahead, 0 behind | All nine commits and the complete 20-file net delta. [Comparison](https://github.com/HigorLoren/moneywiz-mcp-server/compare/d113a11df8ea475f50b5d118585c763bb4f5ba72...077d7337d2f011023d81de7517d9024bed753a19). |
| dengxuhui/moneywiz-mcp-server | `bd96a1593671a50b0d3df510ead3b548c0eff566` | 3 ahead, 0 behind | Both implementation commits and their merge; complete 87-file net delta. [Comparison](https://github.com/dengxuhui/moneywiz-mcp-server/compare/d113a11df8ea475f50b5d118585c763bb4f5ba72...bd96a1593671a50b0d3df510ead3b548c0eff566). |
| wokoman/moneywiz-mcp-server | Not refreshed | Previously reported identical to upstream main | No substantive audit; supplied prior inventory only. |
| prepfinders/moneywiz-mcp-server | Not refreshed | Previously reported behind upstream | No substantive audit; supplied prior inventory only. |
| iflow-mcp/jcvalerio-moneywiz-mcp-server | Not refreshed | Previously reported behind upstream | No substantive audit; supplied prior inventory only. |

The two meaningful forks' live heads and ahead counts still match the supplied
inventory. No claim is made that the three other forks were freshly verified.

## HigorLoren delta

| Commit | Change | Classification | Our status | Action |
| --- | --- | --- | --- | --- |
| [5603a83267cc66465716ee812124763b169c5c72](https://github.com/HigorLoren/moneywiz-mcp-server/commit/5603a83267cc66465716ee812124763b169c5c72) | [Connection][H-connection] `get_entity_name_map()` reads/caches `Z_PRIMARYKEY`; transaction queries and model conversion use entity names rather than fixed IDs. Fork mapping accepts duplicates/invalid names without validation; unknown model types become `UNKNOWN`. | OUR IMPLEMENTATION IS STRONGER | `database/schema.py::Schema.inspect/entity/family` validates IDs, uniqueness, object keys, inheritance and populated unknown account/transaction descendants. `transaction_service.py::predicate/convert` includes withdrawals and all ten supported types using that same map; `test_remapped_full_schema` exercises two fully different ID generations. | Retain our central validated adapter. |
| [5603a83267cc66465716ee812124763b169c5c72](https://github.com/HigorLoren/moneywiz-mcp-server/commit/5603a83267cc66465716ee812124763b169c5c72) | [Connection][H-connection] `resolve_join_table()` scans generated tag tables/columns, returns the first candidate or `None`, and interpolates unquoted schema identifiers. | OUR IMPLEMENTATION IS STRONGER | `Schema.tag_join` checks both runtime entity IDs and relationship suffixes, accepts numeric generated suffixes, and requires one unambiguous table/column triple. `Schema.identifier/quote_identifier` verifies and quotes identifiers; `CategoryClassificationService.tags_for` rejects missing/dangling relationships rather than returning fabricated empty tags. | Keep discovery, ambiguity rejection and quoting. Do not adopt first-match fallback. |
| [5603a83267cc66465716ee812124763b169c5c72](https://github.com/HigorLoren/moneywiz-mcp-server/commit/5603a83267cc66465716ee812124763b169c5c72) | [Transactions][H-transactions] `_enhance_transaction/_enhance_category_hierarchy` resolve Category, Payee, Tag and account entity IDs dynamically; external account-ID lookup also uses dynamic families. Enhancement retains first-category, unknown-name/USD fallback and caught row errors. | OUR IMPLEMENTATION IS STRONGER | `CategoryClassificationService.rows/reference/category/categories_for/payee/tags_for` uses runtime IDs, returns all assigned categories, validates references and hierarchy, and preserves names. `AccountService.resolve_ids` requires exactly one PK/ZGID match and deduplicates IDs. Transaction currency must come from a valid account. | Retain our resolution paths and explicit errors. |
| [41b1cf54926946ac92b08add8769ae80317516d0](https://github.com/HigorLoren/moneywiz-mcp-server/commit/41b1cf54926946ac92b08add8769ae80317516d0) | [Accounts][H-accounts] `list_accounts` resolves account and all transaction subtype IDs before computing opening balance plus SQL `SUM(ZAMOUNT1)`. | OUR IMPLEMENTATION IS STRONGER | `account_service.py::list_accounts` uses the same central account/transaction maps, streams amounts with `decimal_value/exact_add`, exposes per-type components and credit limit separately, and rejects unavailable account references. Investment/loan/forex valuation remains unsupported. Supported balances expose their components for independent local checks. | Keep our Decimal and valuation semantics; no new balance formula is supplied by this commit. |
| [1b1232bef6535723e7a2e04098833b1f9e82f9ac](https://github.com/HigorLoren/moneywiz-mcp-server/commit/1b1232bef6535723e7a2e04098833b1f9e82f9ac) | [Budgets][H-budgets] `_get_budget_entity_id/get_budgets` remove fixed Budget ID, including the output model's entity-type field. | ALREADY COVERED | `budget_service.py::get_budgets` uses `schema.entity("Budget")`. `test_remapped_full_schema` verifies budgets under remapped IDs. | No further change. |
| [1b1232bef6535723e7a2e04098833b1f9e82f9ac](https://github.com/HigorLoren/moneywiz-mcp-server/commit/1b1232bef6535723e7a2e04098833b1f9e82f9ac) | [Classification][H-classification] category hierarchy/root lookups replace fixed Category ID with runtime resolution. | OUR IMPLEMENTATION IS STRONGER | `CategoryClassificationService.category` resolves every ancestor dynamically and raises on cycles, invalid parents and dangling references. The fork stops/returns fallback information on those failures. | Keep validated hierarchy traversal. |
| [1b1232bef6535723e7a2e04098833b1f9e82f9ac](https://github.com/HigorLoren/moneywiz-mcp-server/commit/1b1232bef6535723e7a2e04098833b1f9e82f9ac) | [Classification][H-classification] `_get_classification_entity_roles` makes dominant-type, fallback and learned-pattern category classification independent of numeric entity IDs. | DELIBERATELY EXCLUDED | Our category model contains factual IDs/names/ancestors only. `TransactionService.convert` takes the transaction type from the entity map, not inferred category income/importance or learned usage patterns. | Do not restore heuristic category classification. |
| [1b1232bef6535723e7a2e04098833b1f9e82f9ac](https://github.com/HigorLoren/moneywiz-mcp-server/commit/1b1232bef6535723e7a2e04098833b1f9e82f9ac) | [Schedules][H-schedules] adds scheduled deposit handlers and dynamically resolves scheduled types, categories/payees/tags and tag joins. Deposit and withdrawal share `REGULAR`; the returned transaction type is still inferred from amount sign. | OUR IMPLEMENTATION IS STRONGER | `Schema.SCHEDULED_TYPES` distinguishes deposit, withdraw and transfer by entity name. `ScheduledTransactionService.get_scheduled_transactions` uses that map and common relationship validation; lists disabled and one-off rows too. `test_remapped_full_schema` verifies salary category and tags on a scheduled deposit. | Keep entity-based schedule classification and all-row completeness. |
| [1b1232bef6535723e7a2e04098833b1f9e82f9ac](https://github.com/HigorLoren/moneywiz-mcp-server/commit/1b1232bef6535723e7a2e04098833b1f9e82f9ac) | [Schedules][H-schedules] `calculate_salary_breakdown` skips deposits when counting outgoing commitments. | DELIBERATELY EXCLUDED | There is no salary-coverage/commitment projection tool. Scheduled salary remains a factual `deposit`; recurrence fields are returned without estimated future occurrences, salary or recommendations. | No salary-analysis service to patch. Preserve factual scheduled deposits. |
| [d7dfd67fc0a57e7946f2450f8bac9952a5925084](https://github.com/HigorLoren/moneywiz-mcp-server/commit/d7dfd67fc0a57e7946f2450f8bac9952a5925084) | Architecture/change-log edits describe numeric IDs as model-dependent, replacing fixed examples with placeholders. | NOT RELEVANT | Our `ARCHITECTURE.md`, `Schema` and implementation report already document dynamic schema resolution. No production behavior changes here. | No code import. |
| [a0114e55d1e6edc1922b6c23bf4d1971bcf9635f](https://github.com/HigorLoren/moneywiz-mcp-server/commit/a0114e55d1e6edc1922b6c23bf4d1971bcf9635f) | [Accounts][H-accounts]/[transactions][H-transactions] guard empty entity lists, returning no transactions/opening-only balances or rejecting missing account mappings. | OUR IMPLEMENTATION IS STRONGER | `Schema.inspect` requires integrity-critical mappings; `Schema.family` and `account_service.py::placeholders` reject unresolved empty families. Explicit empty user filters instead match zero rows. A valid mapped family with no records naturally returns empty data. | Retain distinction between unavailable schema and valid empty results. SQLite itself permits `IN ()`; do not import an empty-success fallback. |
| [903b2e5faeccae0885a5ee74b8592b31471de400](https://github.com/HigorLoren/moneywiz-mcp-server/commit/903b2e5faeccae0885a5ee74b8592b31471de400) | [Dates][H-dates] parses arbitrary relative counts, calendar years and month/year phrases; rejects unrecognized text instead of defaulting to three months. Still uses naive `now`, 30-day months and inclusive calendar endings at `23:59:59`. | DELIBERATELY EXCLUDED | `utils/date_utils.py::parse_iso/interval` accepts explicit ISO inputs and valid IANA zones only; malformed/naive inputs raise. Queries use inclusive start/exclusive end in UTC, preventing overlaps and lost end-of-day fractions. There is no natural-language period API. | Retain deterministic ISO contract. This NLP repair is unnecessary in an API that never interprets NLP. |
| [ad4410dd1fbdc737c94baf0813e480d5f0faa671](https://github.com/HigorLoren/moneywiz-mcp-server/commit/ad4410dd1fbdc737c94baf0813e480d5f0faa671) | Merge integrates the preceding date parser; compared with `a0114e5`, only `date_utils.py` and its tests change, matching the parser patch. | NOT RELEVANT | Parser disposition is recorded above; no additional merge-specific correction. | Do not double-count the merged NLP work. |
| [1eeb7f10da645ddf28d7076a08c10ea9ca273de7](https://github.com/HigorLoren/moneywiz-mcp-server/commit/1eeb7f10da645ddf28d7076a08c10ea9ca273de7) | Adds `.dual-graph/` to `.gitignore`. | NOT RELEVANT | Local tooling cache exclusion does not change our MCP behavior. | No import needed. |
| [077d7337d2f011023d81de7517d9024bed753a19](https://github.com/HigorLoren/moneywiz-mcp-server/commit/077d7337d2f011023d81de7517d9024bed753a19) | [Text helper][H-text] collapses Unicode whitespace with `" ".join(name.split())`; transaction leaf/ancestor, budget and scheduled filters compare normalized values without rewriting output. Fork budget matching retains its pre-existing lowercasing. | ALREADY COVERED | **Implemented in Task 1.** Our reusable `utils/text_utils.py::normalize_category_name` uses the same expression. `TransactionService.predicate` normalizes requested names, valid stored names and every hierarchy comparison before resolving category IDs. It does not lowercase. Budgets/schedules accept no category-name filters in our API; classification resolves IDs, so those three services require no edits. | Retain the scoped fix and regression tests. This commit is the engineering source that identified the MoneyWiz NBSP compatibility issue. |
| [5603a8](https://github.com/HigorLoren/moneywiz-mcp-server/commit/5603a83267cc66465716ee812124763b169c5c72), [1b1232b](https://github.com/HigorLoren/moneywiz-mcp-server/commit/1b1232bef6535723e7a2e04098833b1f9e82f9ac), [a0114e5](https://github.com/HigorLoren/moneywiz-mcp-server/commit/a0114e55d1e6edc1922b6c23bf4d1971bcf9635f), [903b2e5](https://github.com/HigorLoren/moneywiz-mcp-server/commit/903b2e5faeccae0885a5ee74b8592b31471de400), [077d733](https://github.com/HigorLoren/moneywiz-mcp-server/commit/077d7337d2f011023d81de7517d9024bed753a19) | Associated tests update mocked entity maps/tag joins, add parser assertions, and add NBSP tests, including a real-store test that skips if no NBSP category exists. | OUR IMPLEMENTATION IS STRONGER | Fabricated real SQLite stores cover two ID generations, relationship ambiguity, malformed schema, signs, empty filters, hierarchy and MCP protocol behavior. New NBSP tests cannot skip and need no personal database. | Keep our tests; no foreign real-store fixtures or private printouts imported. |

### Task 1 implementation and regression evidence

The helper is exactly:

```python
def normalize_category_name(name: str) -> str:
    return " ".join(name.split())
```

This trims leading/trailing Unicode whitespace and collapses internal runs to
one ASCII space. It changes neither case nor punctuation; U+200B zero-width
space is not treated as whitespace by Python and is not removed. Stored
`Category.name`, hierarchy strings and echoed requested filters remain intact.
Normalized names are used only to validate requested names and select matching
category IDs/descendants. SQL still uses bound IDs and applies the complete
predicate before count, ordering and pagination. No substring/fuzzy matching
was introduced. Equal normalized names use the existing all-matching-category
ID semantics; no arbitrary first category is selected.

Material architectural difference from Higor: our transaction filtering occurs
in `predicate`, before SQL count/pagination, whereas Higor enhances fetched
rows and then filters them in Python. Higor also patches budget and scheduled
filters that our factual listing tools do not expose. We therefore changed only
the actual comparison path and did not import those services or lowercasing.

Added regressions:

- `tests/unit/test_text_utils.py`: seven parameter cases for NBSP, ASCII spaces,
  mixed NBSP/em-space/tab/newline runs, empty text, case and punctuation
  preservation, zero-width-space preservation, and idempotence.
- `tests/unit/test_hardening.py::test_category_whitespace_matching_preserves_names`:
  six SQLite cases (parent/leaf crossed with NBSP/ASCII/mixed stored spelling),
  matching `Food & Dining`, preserving the original hierarchy/leaf name,
  counting all matches before a one-row page, isolating unrelated Salary,
  rejecting case/punctuation/prefix/missing alternatives, and preserving
  empty-filter behavior.
- `tests/integration/test_mcp_v2.py::test_category_nbsp_filter_over_mcp_preserves_stored_name`:
  real SDK request/response with mixed-whitespace and duplicate-equivalent user
  filters; validates original stored spelling, hierarchy, echoed filters and
  complete match count.

## dengxuhui delta

| Commit | Change | Classification | Our status | Action |
| --- | --- | --- | --- | --- |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Registry][D-schema] resolves names/IDs and counts, including withdrawals, with canonical transaction/account kinds. Mapping/count failures become warnings; unfamiliar transactions become `UNKNOWN`. | OUR IMPLEMENTATION IS STRONGER | `Schema.inspect` validates map/inheritance/objects and fails closed on populated unknown financial descendants, rather than continuing incomplete. `TRANSACTION_TYPES` also supports `InvestmentExchangeTransaction`, omitted from Deng's final registry. | Keep our map, strict validation and complete supported family. Generic `InvestmentTransaction` support in Deng is not independently proven valuation semantics. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Registry][D-schema] `_discover_tag_link` scans table/column text for TRANSACTION/TAG, returns a first candidate (possibly scheduled as fallback), and interpolates unquoted PRAGMA identifiers. | OUR IMPLEMENTATION IS STRONGER | `Schema.tag_join/identifier` verifies exact runtime entity IDs, relationship patterns and uniqueness, quotes identifiers, and distinguishes transaction from scheduled ownership. | Retain strict generated-join discovery. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Accounts][D-accounts] sums individual signed transactions with Decimal and adds opening balance; account detail and ID resolution use runtime IDs. Missing amounts/openings/currencies default to zero/USD; all account types receive calculated balances. | OUR IMPLEMENTATION IS STRONGER | `AccountService` exposes exact validated components, rejects dangling/ambiguous account references and missing currency, preserves null opening as unknown, and does not claim investment/loan/forex valuation. `exact_add` prevents context rounding. Credit limit is separate; the calculated formula and its components are explicit for local comparison. | Keep our verified formula and explicit unsupported states. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Transactions][D-transactions] includes canonical types and actual account currencies; [category][D-categories]/[payee][D-payees] services resolve names/ancestors. Category assignments are collapsed to one entry per transaction; unresolved paths stop early and names/currencies use defaults. | OUR IMPLEMENTATION IS STRONGER | `TransactionService.convert` retains all assigned categories, exact type/sign and valid account currency. `CategoryClassificationService` rejects dangling references/cycles/conflicting name fields and returns complete factual hierarchy. Split amounts stay in totals but are explicitly unallocated in category breakdown. | Do not import lossy split-category or fallback conversion. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Categories][D-categories] `resolve_category_ids` matches lowercased leaf/ancestor names, scanning at most 1,000 categories; whitespace is not normalized. | OUR IMPLEMENTATION IS STRONGER | `TransactionService.predicate` resolves the full stored category population before pagination, normalizes whitespace only, requires every requested name to exist and preserves exact case. | Retain current matching semantics and Task 1 fix. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Payees][D-payees]/[transactions][D-transactions] add case-insensitive payee-name filtering and category/payee substring search; transaction search also adds account-type/direction/multi-kind filters. | NOT RELEVANT | Our accepted filter surface is explicit account IDs, category names and one exact transaction type. Payees/tags are factual returned/listed names resolved by row IDs; no payee/tag-name filter exists to normalize. Extra filter APIs are product extensions, not repairs to currently accepted inputs. | Consider only under a separately scoped feature request; do not silently broaden matching or add filters here. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Transactions][D-transactions] stable date/PK cursor pagination and `has_more/next_cursor`; fetches/enhances all remaining rows, and `total_count` shrinks after the cursor. `get_all_transactions` imposes a one-million-record limit. | OUR IMPLEMENTATION IS STRONGER | `get_transactions` counts the complete predicate in the same snapshot and uses SQL `ORDER BY ZDATE1 DESC,Z_PK DESC LIMIT/OFFSET`; `Page` includes matched/returned counts, truncation and next offset. `summarize_cashflow` streams all matches in batches without an arbitrary transaction cap. Across changing stores, our page warns to use a frozen copy. | Keep existing completeness guarantees; cursor transport alone is not a missing correctness fix. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Transactions][D-transactions] adds original amounts, counterpart-account and constructed transfer-pair IDs from optional sender/recipient fields; [cashflow][D-cashflow] counts pairs by two present legs. | NOT RELEVANT | Current transaction output promises factual type/account/money/categories, not transfer pairing, original-currency conversion or counterpart metadata. Transfer-in/out legs and signed sums are already included; pair validation is a separate local acceptance check. Deng does not validate reciprocal links/account references or cross-currency pair semantics. | Optional metadata extension requires separate relationship validation and tests; no missing fix in the current output contract. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Cashflow][D-cashflow] per-currency income/expense/refund/reconcile/transfer buckets with balance-delta diagnostics. Uses canonical kinds, but folds investment sales/buys into income/expenses and puts refunds into net cashflow. | OUR IMPLEMENTATION IS STRONGER | `TransactionService.summarize_cashflow` returns per-currency signed deposits and negated withdrawals, and separate stored sums for transfers, refunds, reconciliations and investment types. Reversals retain sign and split categories are explicit. Every matched row is processed. | Preserve our stated financial semantics and exact streaming totals. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Cashflow][D-cashflow] adds monthly/payee grouping and built-in opening/closing balance-discrepancy reporting. | NOT RELEVANT | Our MCP offers complete currency/type totals and category breakdown; `validate.py::reconcile` supports local control totals. Extra grouping and automatic balance-delta report are additional report APIs, not missing fixes. | Keep as possible separately designed features, with our boundary and currency rules. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Amounts][D-amounts]/[money][D-money] replace float aggregates with Decimal and currency dictionaries/string money. `None` becomes zero, additions use default Decimal precision, and every output is quantized to two cents before some downstream sums. | OUR IMPLEMENTATION IS STRONGER | `models/currency_types.py::decimal_value/exact_add/Money` validates finite bounded values, adds with sufficient local precision and serializes stored Decimal precision unchanged. Currency codes are mandatory; no currency mixing or implicit FX. | Do not import null-to-zero, universal two-decimal rounding or default-context arithmetic. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Dates][D-dates] makes NSDate epoch UTC and rejects naive datetime-to-timestamp conversion. Transaction/balance query end is inclusive; invalid IANA zones silently fall back to Shanghai, while ISO parsing localizes naive inputs. | OUR IMPLEMENTATION IS STRONGER | `date_utils.py` uses aware UTC NSDate conversion, rejects malformed/naive ISO datetimes and invalid zones, and enforces `[start,end)` with strict ordering. Date validation prevents malformed rows silently disappearing behind interval filters. DST/offset/boundary tests are in `test_hardening.py`. | Retain strict ISO/timezone/boundary handling. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Dates][D-dates]/[config][D-config] add English/Chinese natural-language periods and configurable default timezone. | DELIBERATELY EXCLUDED | Tools accept explicit ISO start/end and an explicit IANA timezone (UTC default). No relative-language parser, clock-dependent period defaults or silent zone fallback. | Let the caller express explicit dates; do not add NLP to the data layer. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Net worth][D-networth] adds snapshots and history by account/currency, using opening plus transactions for every account type, default inclusion flags and date endpoints. | DELIBERATELY EXCLUDED | Investment, forex and loan calculated valuations are explicitly unsupported in `AccountService`. The MCP does not claim comprehensive net worth from unverified component sums or approximate calendar history. | Do not add an authoritative net-worth tool without independently proven account/valuation semantics. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | [Registry][D-schema]/[MCP][D-main] add entity/count/currency/latest-date diagnosis and metadata models. Mapping failures can still leave `_loaded=True`; diagnostic warnings accompany service output. | OUR IMPLEMENTATION IS STRONGER | `schema_info/server_status`, `Schema.diagnostics`, structured errors and `validate.py::reconcile` expose adapter status and explicit unsupported sections. Integrity-critical schema failure prevents financial success output. No raw-SQL tool is exposed. | Retain fail-closed diagnostics; counts/latest-date display alone is an optional extension. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | Removes savings/trend/advice/heuristic services, their response/formatter/validator models and obsolete tests; new domain models support factual tools. | ALREADY COVERED | Our source tree and eleven-tool inventory exclude subjective advice, savings prescriptions, inferred category importance and forecasting. `models/responses.py` supplies only current factual outputs. | Keep factual tool inventory; no legacy service restoration. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | Synthetic SQLite fixture and golden-number tests assert account, cashflow, category/payee, tags, cursor and transfer results. Uses one principal schema and expected numbers from fabricated fixtures. | OUR IMPLEMENTATION IS STRONGER | `tests/conftest.py` builds remapped schemas; hardening tests cover malformed/ambiguous data, Decimal/currency/boundaries, read-only attacks and completeness. MCP v2 protocol tests run the real SDK. Independent MoneyWiz-produced exports remain a separate local acceptance requirement, not a synthetic-test claim. | Keep synthetic adversarial coverage and independent-export acceptance requirements. |
| [58a49c1a81e9f382a0766b83ab8973871c6110aa](https://github.com/dengxuhui/moneywiz-mcp-server/commit/58a49c1a81e9f382a0766b83ab8973871c6110aa) | Rewrites README/architecture/roadmap/change log, bumps project version, adjusts lock/Makefile/config examples/cache ignore, removes investigation scripts and bundled sample database. | NOT RELEVANT | These are packaging/documentation/local-tool deltas. Our pinned MCP Python SDK v2, strict checks and public privacy rules govern this checkout. Deng's product version `2.0.0` does not imply MCP SDK v2: its final main still uses `FastMCP`. | No dependency/config/tooling import. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [Budgets][D-budgets] resolves Budget, account and category links and lists budget records. | OUR IMPLEMENTATION IS STRONGER | `BudgetService.get_budgets` uses dynamic entities, validates account/category references, resolves exactly one explicit/direct or referenced Currency code, preserves zero/negative stored monetary fields and lists all records with `Page` metadata. Deng silently defaults currency to USD and returns sliced lists. | Keep our factual budget components and completeness. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [Budgets][D-budgets] treats `ZOPENINGBALANCE1` as budget limit, sums absolute transaction-budget-linked amounts, and derives remaining/percentage/period status; category filters use substrings. | DELIBERATELY EXCLUDED | No proven budget limit/rollover/spending allocation contract is claimed. Stored monetary/duration fields are returned under their observed names; no expense/refund/sign or currency inference is substituted. | Do not import guessed budget analysis or broaden category matching. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [Schedules][D-schedules]/[registry][D-schema] dynamically maps deposit/withdraw/transfer handlers and stored account/payee/category fields. Includes salary deposits with their canonical kind. | OUR IMPLEMENTATION IS STRONGER | Our `SCHEDULED_TYPES` and scheduled service already do this with reference, flag, direct/assigned category and currency validation, all assigned categories, disabled/one-off rows and pagination metadata. Missing handler types are reported explicitly. | Preserve current schedule semantics. No missing salary-deposit fix. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [Schedules][D-schedules] `_load_tags` still uses fixed `Z_32TAGS`, `Z_36TAGS2`, `Z_32SCHEDULEDTRANSACTIONS1` and returns empty on errors. Category links use only `ZSCHEDULEDTRANSACITION`. | OUR IMPLEMENTATION IS STRONGER | `Schema.tag_join("ScheduledTransactionHandler")` resolves generated IDs dynamically; `category_links("scheduled")` discovers both ordinary and numeric `Z\d+_SCHEDULEDTRANSACITION` variants. Dangling tags and ambiguous joins raise. | Do not copy remaining hardcoded scheduled relationships. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [Schedules][D-schedules] adds recipient account, autopay, first/last execution fields and recurrence labels; supports account/category/date filters. | NOT RELEVANT | These are additional metadata/filter fields outside the present stored-handler tool contract. Our output already carries raw recurrence fields without asserting unit-label meaning. Fork skips schedules without an account, defaults missing money/currency and guesses recurrence labels. | Optional fields require separately validated semantics; no compatibility fix to import here. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [Transactions][D-transactions] tag names now prefer `ZNAME6` and fall back to `ZNAME2`. | OUR IMPLEMENTATION IS STRONGER | `CategoryClassificationService.tags_for/required_name` already checks `ZNAME6`, `ZNAME2`, `ZNAME`, requires a valid referenced Tag row and rejects contradictory populated names. Both transaction/scheduled tags use it. | No further fix. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [Statistics][D-stats] adds all-time/yearly statistics and current account totals by currency. Reuses investment-inclusive income/expense buckets and the one-million-row transaction cap. | NOT RELEVANT | Complete explicit-period currency/type totals already exist. An all-time/yearly convenience endpoint is outside the intended current MCP surface; fork current totals additionally inherit unsupported valuation assumptions. | No new endpoint. Any future design must keep completeness and supported valuation boundaries. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [Registry][D-schema]/[config][D-config] add `MONEYWIZ_SCHEMA_PROFILE` override; profile names derive from Category/Payee numeric ID pairs and an override changes the label. | DELIBERATELY EXCLUDED | `Schema.inspect` validates actual mappings/columns/relationships for every opened store. No caller-selected profile bypass or model-version guess governs financial interpretation. Deng's override changes diagnostic labeling, not a validated alternate adapter. | Keep schema-based compatibility, not numeric-ID-derived version labels or unverified profile overrides. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [Dates][D-dates] adds next/future English/Chinese periods with inferred calendar month shifts. | DELIBERATELY EXCLUDED | Deterministic ISO intervals are the sole date input contract. Stored schedules are listed without a relative-time projection service. | No NLP or clock-dependent period extension. |
| [bfd3e4696c64fabe31cebe0de73fe88baa69de64](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bfd3e4696c64fabe31cebe0de73fe88baa69de64) | [MCP][D-main] `run_diagnose` CLI exposes registry report; `run_print_config` emits client config. Adds OpenClaw example/schema docs and schedule/budget/statistics fixture/tests. | NOT RELEVANT | Local `moneywiz-validate`, `schema_info` and existing client examples cover supported operations. Product docs/client generation and tests for excluded extra endpoints are not runtime corrections. Synthetic new schedule/budget tests do not independently prove recurrence/budget/valuation meanings. | Keep existing CLI/client guidance and factual test contracts. |
| [bd96a1593671a50b0d3df510ead3b548c0eff566](https://github.com/dengxuhui/moneywiz-mcp-server/commit/bd96a1593671a50b0d3df510ead3b548c0eff566) | Merge of both v2 implementation commits. GitHub comparison from `bfd3e4696c64fabe31cebe0de73fe88baa69de64` to this merge has **no changed files**. | NOT RELEVANT | All substantive changes are accounted for above; no merge-only implementation. | No additional action. |

### Cross-cutting checks and retained guarantees

- **Read-only/privacy/MCP:** both forks retain the inherited optional
  `read_only=False` connection and `transaction()` commit helper. Deng's final
  main passes that flag from config and uses `FastMCP`; its config/main logs
  database paths, and inherited `execute_query` debug logging includes SQL and
  parameters. Higor also logs query parameters/classification data and uses
  the same inherited writable design. These are retained baseline properties,
  not new fork fixes. Our `DatabaseManager` uses URI `mode=ro`, `query_only=ON`,
  `trusted_schema=OFF`, a restrictive authorizer and one read snapshot per
  operation; no commit helper/raw-SQL tool/writable config exists. `main.py`
  uses MCP SDK v2 `MCPServer`, removes default tracing middleware, and returns
  sanitized errors without private arguments/raw exceptions.
- **Empty/missing/unknown entities:** valid empty records are not conflated
  with unresolved families. Optional Tag absence has an explicit warning in
  transaction results, and tag relationships without a Tag mapping fail.
  Missing Budget/scheduled families produce explicit errors, while missing
  individual scheduled types appear as warnings. Populated unknown financial
  descendants fail even when their names do not follow conventional suffixes.
- **Text:** only category-name filters exist in our current MCP. Category
  matching now normalizes Unicode whitespace symmetrically; no case folding,
  punctuation edits, substring search or normalization of output names occurs.
  Payee/tag resolution is by stored IDs, with conflicting name fields rejected.
  Neither fork supplies a separate Unicode payee/tag matching repair that
  applies to an accepted filter in our API.
- **Schedules/relationships:** Higor's retained scheduled category resolution
  tries `ZSCHEDULEDTRANSACITION` and fixed `Z31_SCHEDULEDTRANSACITION`, then
  falls back to direct category fields and returns only one assignment.
  Our numeric-column discovery and direct/assigned consistency checks are
  stricter. Neither fork supplies a validated relationship variant missed by
  our adapter; arbitrary unproven variants appropriately fail closed.
- **Money/signs/credit cards:** account totals include all supported stored
  transaction kinds. Income/expense reporting preserves signed reversals;
  transfers/refunds/reconciliations/investments stay separately classified.
  Credit limit never becomes cash or automatic debt correction. Calculated
  supported account balances use explicit opening-plus-transactions components
  for local comparison; correctness is not asserted universally across stores.
  Both forks provide no independently proven alternative card formula. Investment/loan/forex component sums are
  diagnostic, not market/net-worth valuations.
- **iCloud/live stores:** neither post-baseline delta fixes WAL discovery or
  introduces a safer primary-store selector. Our explicit path validation
  rejects sidecars/shared stores (including symlink aliases); opt-in discovery
  requires exactly one schema-validated nonempty store. URI escaping handles
  special filename characters; `immutable=1` is deliberately avoided so WAL
  content remains visible. A consistent SQLite snapshot protects each call;
  changing live stores still require a frozen copy for multi-call pagination.
- **Precision/currency/dates/completeness:** exact context-sized Decimal
  addition, original amount precision, mandatory explicit currencies, no
  implicit FX, strict ISO/IANA validation, half-open UTC query boundaries,
  total match counts and stable ID tie-breaks remain intact. Subjective
  analytics and guessed financial defaults were not imported.

## Missing fixes discovered

**None remain after Task 1.** The genuine category-whitespace compatibility gap
identified by Higor's `077d7337d2f011023d81de7517d9024bed753a19` was implemented
before the delta audit and is therefore classified ALREADY COVERED in the final
table. No additional item meets USEFUL MISSING FIX: observed extra endpoints or
metadata are scope extensions, and fallback/valuation/NLP semantics contradict
the accepted design or are handled more safely by our current code.

No additional source fix was implemented during the audit. This conclusion is
limited to the inspected fork deltas and supported current tool contracts; it
does not certify universal compatibility with the private MoneyWiz schema.

## Deliberately excluded fork functionality

- Higor's category-pattern income/importance inference and salary commitment
  coverage/recommendations: infer financial meaning rather than return stored
  facts. Scheduled salary deposits are already retained and correctly typed.
- Relative-language date parsers in both forks, including Deng's future phrases:
  clock-dependent interpretations, approximated calendar shifts and fallback
  timezones would weaken explicit deterministic ISO interval semantics.
- Deng's comprehensive net-worth/history valuations: opening plus transactions
  is not independently proven investment/loan/forex valuation. Unsupported
  components must remain visible as unsupported.
- Deng's budget spending/remaining/status: assumed opening-as-limit, absolute
  transaction amounts, fallback currencies and inferred period semantics are
  not an established budget allocation/rollover contract.
- Deng's schema profile override/version label: caller-selected labels and
  numeric-ID pairs do not establish a valid Core Data semantic adapter.
- Inherited optional writes/commit helpers, third-party database access and
  private SQL/path/argument logging in either fork: incompatible with permanent
  read-only access and privacy. They were not newly introduced corrections.

Optional payee filters, counterpart metadata, monthly/payee grouping and
all-time statistics are classified NOT RELEVANT to current scope, rather than
being mislabeled inherently subjective or unsafe features. They can be
considered separately with appropriate bounded factual contracts.

## Publication impact

**No outstanding fork correctness delta blocks v2.0.0.** Task 1 is implemented
and verified. The audit found no additional USEFUL MISSING FIX to schedule.

The first validation exposed a separate release-check blocker: the editable
root package in `uv.lock` was `2.0.0.dev0` while `pyproject.toml` was `2.0.0`.
The subsequent explicit instruction to fix, commit and publish authorized its
repair. The sole lock diff is that version entry; dependencies did not change.
The inherited release-triggered PyPI workflow was also removed because this
derivative must not publish under the upstream PyPI identity. GitHub artifact
builds now use Python 3.12.15, validate the lock and use frozen tools; CI checks
the lock too. These were release repairs, not missing fork fixes.

Actual validation (Python 3.12.15; temporary `uv` 0.12.22 runtime): Task 1 first
passed its full 186-test suite before the audit. After the later authorized
timezone/privacy changes, the final full suite passed 187 tests. Checks below
describe the final source unless explicitly identified as the Task 1 subset.

| Command | Result |
| --- | --- |
| Task 1 focused pytest selection, with coverage disabled only for the subset | **25 passed**, 160 deselected. Full-suite coverage gates below remained unchanged. |
| Timezone/CLI focused pytest selection, with coverage disabled only for the subset | **22 passed**, 157 deselected; explicit DST boundaries, UTC defaults, MCP output and validation CLI. |
| `uv lock --check` | **PASS** after the authorized root-version repair described above. |
| `uv run --frozen pytest` | **PASS**, 187 tests, **94.21%** overall coverage; unchanged 85% total gate. |
| `uv run --frozen python scripts/check_critical_coverage.py` | **PASS**, all ten designated critical modules exceed unchanged 90% gate (lowest: main 90.91%; schema 93.33%; new helper 100% in overall report). |
| `uv run --frozen ruff check .` | **PASS**. |
| `uv run --frozen ruff format --check .` | **PASS**, 29 files already formatted. |
| `uv run --frozen mypy src/` | **PASS**, 21 source files. |
| `uv run --frozen bandit -r src/` | **PASS**, no reported issues. Existing reviewed SQL-assembly annotations retained; no checks suppressed for this change. |
| `uv run --frozen pip-audit --local --skip-editable` | **PASS**, no known vulnerabilities; editable project skipped as requested. |
| `uv build --no-sources` | **PASS**, 2.0.0 wheel and sdist. |
| `uv run --frozen twine check dist/*` | **PASS**, built 2.0.0 wheel/sdist and existing dev0 artifacts checked. |
| `git diff --check` | **PASS**. |

`uv` was absent from PATH initially, so it was installed into a temporary tools
directory; the dependency manifest is unchanged and the lock repair changes
only the root project version. Sandbox DNS
prevented initial package-index calls; approved network access completed the
package/build/vulnerability checks. These environment failures are distinct
from the initial reproducible version mismatch. No thresholds or tests were weakened.

The additionally requested hero correction replaces the former SVG with the
user-supplied PNG, updates README and the publishing asset list, and preserves
the PNG bytes exactly. The additionally requested README validation edit removes
the explicit timezone argument from its example. The subsequent privacy cleanup
sets the MCP, interval helper and validation defaults to UTC, removes personal
validation narratives from public documentation, and retains explicit IANA-zone
support with DST regression tests using an unrelated example zone. A scan of
72 tracked/new files found no personal reference matches against the local
canonical profile and personal-name/path/zone patterns. After release repairs,
a final 71-file scan again found no personal-name/home-path/zone matches. Images contained no
private home-path strings; the supplied PNG bytes remain unchanged. The sole
tracked SQLite sample is byte-identical to the original upstream baseline,
not a locally supplied store. No financial export files are tracked. Public
repository ownership/attribution remains intact. The original category-fix/audit
phase did not commit or publish. The subsequent explicit instruction authorized
committing these changes and publishing v2.0.0 through GitHub. No additional
fork functionality was imported, no MoneyWiz database was modified, and no PR
or merge is part of this work.

[H-connection]: https://github.com/HigorLoren/moneywiz-mcp-server/blob/077d7337d2f011023d81de7517d9024bed753a19/src/moneywiz_mcp_server/database/connection.py
[H-transactions]: https://github.com/HigorLoren/moneywiz-mcp-server/blob/077d7337d2f011023d81de7517d9024bed753a19/src/moneywiz_mcp_server/services/transaction_service.py
[H-accounts]: https://github.com/HigorLoren/moneywiz-mcp-server/blob/077d7337d2f011023d81de7517d9024bed753a19/src/moneywiz_mcp_server/services/account_service.py
[H-budgets]: https://github.com/HigorLoren/moneywiz-mcp-server/blob/077d7337d2f011023d81de7517d9024bed753a19/src/moneywiz_mcp_server/services/budget_service.py
[H-classification]: https://github.com/HigorLoren/moneywiz-mcp-server/blob/077d7337d2f011023d81de7517d9024bed753a19/src/moneywiz_mcp_server/services/category_classification_service.py
[H-schedules]: https://github.com/HigorLoren/moneywiz-mcp-server/blob/077d7337d2f011023d81de7517d9024bed753a19/src/moneywiz_mcp_server/services/scheduled_transaction_service.py
[H-dates]: https://github.com/HigorLoren/moneywiz-mcp-server/blob/077d7337d2f011023d81de7517d9024bed753a19/src/moneywiz_mcp_server/utils/date_utils.py
[H-text]: https://github.com/HigorLoren/moneywiz-mcp-server/blob/077d7337d2f011023d81de7517d9024bed753a19/src/moneywiz_mcp_server/utils/text_utils.py
[D-schema]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/database/schema_registry.py
[D-accounts]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/services/account_service.py
[D-transactions]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/services/transaction_service.py
[D-categories]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/services/category_service.py
[D-payees]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/services/payee_service.py
[D-cashflow]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/services/cashflow_service.py
[D-amounts]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/utils/amounts.py
[D-money]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/models/money.py
[D-dates]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/utils/date_utils.py
[D-config]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/config.py
[D-networth]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/services/net_worth_service.py
[D-main]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/main.py
[D-budgets]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/services/budget_service.py
[D-schedules]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/services/scheduled_transaction_service.py
[D-stats]: https://github.com/dengxuhui/moneywiz-mcp-server/blob/bd96a1593671a50b0d3df510ead3b548c0eff566/src/moneywiz_mcp_server/services/financial_stats_service.py

NO BLOCKING FORK DELTAS FOUND
