# Engineering assessment (2026-10-03)

Starting main: d113a11df8ea475f50b5d118585c763bb4f5ba72.

Evidence reviewed: all production modules, repository tree/configuration/lock,
fixture and test structures, CI/security/local check scripts, README/architecture,
open issue/PR inventory and PR #44 files, reviews and discussion.

Confirmed in source: fixed entity IDs in every service and transaction model;
unapplied MCP transaction_type filter; ignored scheduled time_period;
missing scheduled deposit handler; limits reported as complete counts; swallowed
row/relationship errors; assumed USD and CRC currencies; SQL floating-point SUM;
cross-currency sums/ranking; fallback dates and naive NSDate epoch; unsafe
identifier interpolation proposed in PR #44; configurable writable connection,
write context manager and optional third-party database API; private parameters,
identifiers/paths and SQL logged. Budget amount/currency semantics conflict even
within upstream investigation scripts and service. Recurrence projection guesses
end conditions and uses approximate months. Classification uses heuristics rather
than factual relationships. These algorithms cannot be retained as authoritative.

PR #44 is open, unmerged, mergeable_state=blocked at review; head
 a0114e55d1e6edc1922b6c23bf4d1971bcf9635f. Check-runs API returned no check runs;
the commit-status API returned pending with no individual statuses. This is not
a verified green-check result. Reviews flag unresolved-entity fallbacks,
unquoted schema identifiers and empty mappings. Independent reporter describes
13,355 vs 2,497 transactions and 9 vs 0 budgets on another generation, with a
remaining credit-limit offset after the PR. These are reports, not our own real
MoneyWiz validation. No open tags/budget/schedule-specific issues other than
these findings were returned; other open PRs are dependency updates and #47.
Issues #46/#49 confirm discovery path and sidecar concerns; #48 does not prove a
general credit-card formula. Candidate hypotheses: opening balance net of limit,
conditional offset on nonzero opening balance, or different UI balance meaning.
Keep components and candidate calculations as diagnostics only.

Official MCP Python SDK documentation identifies v2 as stable; PyPI reports
2.3.0. Migration requires MCPServer, mcp_types and snake_case annotations/results.
Default OpenTelemetry middleware is avoidable; install no exporter and remove
that middleware. Preserve local stdio, async SQLite database manager, service
separation, packaging and metadata. Replace unsafe query/conversion internals,
retire subjective analytics and their obsolete response models/tests (Git retains
originals). Preserve factual retrieval, cashflow aggregation and per-currency
category breakdown; payees remain factual row references. No FX or recurrence forecasting.

Core Data SQLite is an undocumented private Apple implementation (Apple warns
against direct manipulation). Entity names/columns observed in upstream are a
bounded adapter, not universal semantics. Unknown account/transaction descendants,
unresolvable mappings/relationships, split categories and missing references must
be errors or explicit unsupported states, never a fabricated default.

Validation plan: fabricated full SQLite schemas with remapped entity IDs and
real async reads, malformed/ambiguous stores, authorizer/ro/query_only mutation
probes, relationship and reference failures, all types/filter/pagination,
exact decimal/currency tests, UTC and explicit-zone boundaries and DST, MCP v2 protocol
roundtrips, read-only reconciliation CLI, lint/format/strict typing/full Bandit,
locked dependency vulnerability audit and wheel/sdist validation. Financial
acceptance still requires independent MoneyWiz UI reconciliation.

## Findings corrected after investigation

SQLite explicitly accepts an empty `IN ()` list and defines its result as false;
the suspected SQLite syntax error is disproven. Empty entity sets are still
rejected before query assembly because unresolved schema mappings must not look
like valid empty results. An intentionally empty user filter instead matches
zero rows without broadening the query.

PR #44's blocked merge state is not evidence of a currently failing CI run:
neither the check-runs nor commit-status API supplied a completed green or failed
run. Likewise, the credit-limit-sized discrepancy in #48 is evidence to reconcile,
not proof of a universal balance formula. Read-only mode itself existed upstream;
the confirmed problem was its optional nature and retained write capability.

Primary sources used (accessed 2026-10-03):

- [Upstream source](https://github.com/jcvalerio/moneywiz-mcp-server/tree/d113a11df8ea475f50b5d118585c763bb4f5ba72)
- [PR #44](https://github.com/jcvalerio/moneywiz-mcp-server/pull/44)
- [Issue #46](https://github.com/jcvalerio/moneywiz-mcp-server/issues/46),
  [#48](https://github.com/jcvalerio/moneywiz-mcp-server/issues/48),
  [#49](https://github.com/jcvalerio/moneywiz-mcp-server/issues/49)
- [Official MCP v2 migration](https://py.sdk.modelcontextprotocol.io/migration/)
- [Official OpenTelemetry opt-out](https://py.sdk.modelcontextprotocol.io/run/opentelemetry/)
- [SQLite URI read-only mode](https://www.sqlite.org/uri.html)
- [SQLite IN semantics](https://www.sqlite.org/lang_expr.html)
- [Apple Core Data persistent-store guidance](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/CoreData/PersistentStoreFeatures.html)
- [Codex local MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

The final implementation and actual results are recorded in
[IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md).
