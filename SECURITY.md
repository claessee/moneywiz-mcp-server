# Read-only and privacy boundary

The server has no financial-data network calls, telemetry exporter or write tools.
SQLite connections are unconditionally URI mode=ro/query_only, with a read
snapshot and authorizer. SQL values are parameterized and dynamic identifiers
are validated/quoted. Routine logs omit records, parameters, raw SQL and paths.
MCP responses necessarily reach the connected client; its model/provider data
handling is outside this process. Keep real database/report artifacts local.

Unit/integration checks never auto-discover or read a personal store. Packages
exclude database files and reconciliation artifacts. Security checks include full
Bandit and locked installed-package pip-audit; scoped B608 suppressions correspond
to inspected bound-value/quoted-identifier query assembly, not arbitrary SQL.
Untrusted schemas/records fail explicitly rather than returning partial facts.

This is a local reconciliation fork, not a public release. Do not enable automatic
publishing, remote transports or tunnels as part of setup. Upstream vulnerability
reporting remains subject to the upstream project's policy; no message or report
is sent automatically by this package.
