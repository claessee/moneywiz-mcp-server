# Security and privacy

MoneyWiz MCP Server is designed for local, read-only access to a MoneyWiz SQLite database.

## Security boundary

The database layer enforces read-only behavior structurally:

- SQLite URI `mode=ro`
- `PRAGMA query_only=ON`
- `trusted_schema=OFF`
- restrictive SQLite authorizer
- no commit/write helper
- no raw-SQL MCP tool
- no writable configuration mode

The server exposes local stdio transport only. It does not add a network listener or telemetry exporter.

SQLite may still use normal locking/shared-memory metadata while reading a live WAL-backed database. The security guarantee is that this server does not modify MoneyWiz financial rows, schema, or WAL records.

## Data handling

Routine logs are designed not to include transaction records, SQL parameters, raw SQL, full database paths, balances, or other private financial content.

The server sends requested tool results over stdio to the connected MCP client. The client may forward those results to its model provider according to the client's own configuration and privacy policy. That behavior is outside this server's process boundary.

Never post a real MoneyWiz database, reconciliation output, account balances, transaction descriptions, credentials, or other private financial material in a public GitHub issue.

## Reporting a vulnerability

Use GitHub's private security reporting feature if it is enabled for this repository. If private reporting is not available, open a minimal public issue asking the maintainer for a private reporting channel without including exploit details or private financial data.

Useful reports should include the affected version/commit, platform, Python version, a minimal synthetic reproduction, and the expected versus observed security behavior.

## Supported versions

The maintained line is 2.x. Security fixes are applied to the current 2.x branch unless a release note states otherwise.

## Schema compatibility reports

MoneyWiz uses a private Core Data SQLite schema. Compatibility reports should use sanitized schema/entity names and synthetic fixtures where possible. Do not attach a personal database.