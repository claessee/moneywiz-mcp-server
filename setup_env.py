"""Print explicit configuration instructions; never inspect or overwrite .env."""

print("Set MONEYWIZ_DB_PATH to the exact primary SQLite store in your MCP client env.")
print(
    "For iCloud: ~/Library/Containers/com.moneywiz.personalfinance/Data/Library/Application Support/MoneyWiz_iCloud.sqlite"
)
print(
    "Expand ~ in client configuration. Run moneywiz-validate --db PATH --start YYYY-MM-DD --end YYYY-MM-DD first."
)
