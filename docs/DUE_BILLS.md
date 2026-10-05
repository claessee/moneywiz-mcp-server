# Bills due in a week or month

`list_due_bills` answers questions about **remaining scheduled payments**. It does not reconstruct bills already paid/skipped earlier in a calendar period, discover invoices outside MoneyWiz, or prove bank settlement.

## Parameters

| Parameter | Contract |
| --- | --- |
| `start`, `end` | ISO dates or offset-aware datetimes, `[start, end)`, at most 366 elapsed days |
| `timezone` | IANA timezone, defaults to UTC; pass the user's timezone explicitly |
| `account_ids` | Returned account IDs or exact stored ZGIDs; omitted means all, empty means none |
| `include_overdue` | Defaults to true; additionally includes stored next dates before the period that precede `as_of` |
| `as_of` | Optional offset-aware datetime for deterministic overdue classification; defaults to current UTC |
| `limit`, `offset` | Standard bounded pagination, applied independently to payment and unresolved-schedule pages |

For this week use local Monday midnight through next Monday midnight. For this month use the first day through the first day of the following month. The client resolves relative periods; the server validates explicit dates. For example:

```json
{
  "start": "2026-10-05",
  "end": "2026-10-12",
  "timezone": "Europe/Lisbon"
}
```

```json
{
  "start": "2026-10-01",
  "end": "2026-11-01",
  "timezone": "Europe/Lisbon",
  "account_ids": ["returned-account-id"]
}
```

## Results and completeness

`page` contains active expense and transfer occurrences sorted by UTC due instant, then numeric schedule ID. Income and disabled definitions are excluded. Each occurrence includes its local due date/time, account name/ID, signed stored money/currency, payee, description, and whether it falls inside the requested interval.

- `basis=stored_next_execution` is a date read from MoneyWiz.
- `basis=projected` is a future calendar estimate using the current stored amount.
- `status=overdue` means a stored next date precedes `as_of`. It is schedule state, not an assertion about an unpaid invoice or bank settlement.
- `status=scheduled` is another stored next date. Projected occurrences have `status=projected`.

`totals` contains positive magnitudes per currency in four disjoint buckets: `bills_in_interval`, `transfers_in_interval`, `overdue_bills_before_interval`, and `overdue_transfers_before_interval`. No nominal cross-currency total or FX conversion is performed. Period totals include stored overdue payments **inside** that period exactly once; earlier overdue totals are separate. Totals cover every known occurrence before pagination, even when `page.truncated` is true.

`unresolved_schedules` is a separately paginated list of schedule IDs and unsupported-rule reasons. Both pages use the same input limit/offset but each has its own matched count and next offset. Follow both next offsets until exhausted.

`projection_complete` and `totals_complete` are false whenever a relevant schedule cannot be projected reliably, or a schedule handler family is absent. In that case amounts are **known scheduled amounts only**, not complete commitments. Completeness always concerns remaining schedules in this source, not all historical bills or all invoices in the world.

## Supported recurrence and evidence

Local read-only reconciliation on 2026-10-05 compared existing MoneyWiz recurrence forms with their corresponding Core Data rows. No schedule was saved or changed. Only schema-level observations are recorded here; private financial data is not included.

| Stored field/value | Observed MoneyWiz setting |
| --- | --- |
| `ZDURATION1=1`, `ZDURATIONUNITS1=8` | Every month |
| `ZDURATION1=1`, `ZDURATIONUNITS1=4` | Every year |
| `ZWEEKENDSHANDLER=0`, `ZWEEKENDOPTION=NULL` | Weekends: No change |
| `ZENDDATE=NULL` on those rows | End: Never |

The vendor's [MoneyWiz guide](https://assets.wiz.money/MoneyWiz_Guide.pdf), chapter 4, describes scheduled date/time, repeat frequency, end conditions, and the distinction between schedules and posted payments. It does **not** document the private SQLite numeric fields; those mappings come from the local UI comparison above. The guide is dated 2021-12-14, so it provides background rather than current schema proof.

Projection supports positive integer multiples of the verified monthly/yearly units, unchanged weekends, an available unchanged original day anchor at day 1–28, and a known unbounded end. Local wall time is preserved in the caller's timezone. Choose the timezone MoneyWiz uses to schedule payments; a UTC timestamp alone cannot establish the original recurrence timezone. Daylight-saving gaps/folds are explicitly unsupported. The first stored next date is retained even when projection is unsupported.

Limits remain explicit for daily/weekly or unknown units, changed/missing anchors, month-end/leap-day rules, weekend shifts, finite/unknown endings, or overdue repeating schedules requiring reconciliation. No occurrences before the stored next date are invented. When no additional occurrence can fall in the requested period under the known unshifted monthly/yearly interval, the stored date suffices.

## Balance questions

Use `list_accounts` to resolve the exact account, then `get_account` by returned ID. The existing opening-balance-plus-stored-transactions formula and provisional status are unchanged. Reconcile against MoneyWiz and verify the configured source is current before treating a value as authoritative. The due-bill tool does not subtract scheduled commitments from an account balance.
