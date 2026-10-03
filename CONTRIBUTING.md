# Working on the local reconciliation fork

Preserve permanent read-only safety, exact decimal/currency semantics, explicit
schema errors and bounded completeness metadata. Use fabricated SQLite fixtures
only. Do not add writable helpers, raw-SQL tools, financial telemetry or defaults
that manufacture missing data. Do not widen support claims without real UI
reconciliation evidence. Test new entity/relationship observations under multiple
numeric maps and include malformed-schema failures.

Run `uv sync --frozen --all-extras` and `./scripts/check-ci.sh`. All checks block.
Use `uv run --frozen pip-audit --local --skip-editable` for dependency audit. Update
pins/lock deliberately and rerun schema/SDK/transport tests after changes. Private
MoneyWiz stores and reconciliation output must never be committed or packaged.
No push, publication or pull request is authorized by this implementation task.
