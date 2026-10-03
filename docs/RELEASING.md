# Local fork versioning and upgrades

`2.0.0.dev0` identifies breaking local changes, not a published release. The MCP
SDK is independently pinned to 2.3.0. No release/push/PR is authorized here.
Old upstream 1.x tools, float response contracts, natural-language defaults and
.env/write-mode settings are intentionally incompatible. Keep a validated local
branch/snapshot before an upgrade, review the change report, sync the hash-bearing
lock, run all blocking checks, repeat real UI reconciliation and restart the MCP
client. Use a previously validated branch/snapshot to roll back. Never modify a
MoneyWiz store to accommodate the adapter; unsupported observations need schema
regressions and explicit review.
