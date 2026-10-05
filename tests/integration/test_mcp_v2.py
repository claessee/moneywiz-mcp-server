import json
import os
from pathlib import Path
import subprocess
import sys

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters
from mcp.server._otel import OpenTelemetryMiddleware
import pytest

from moneywiz_mcp_server import main


@pytest.fixture(autouse=True)
def configure(synthetic, monkeypatch):
    monkeypatch.setattr(main, "_config", None)
    monkeypatch.setenv("MONEYWIZ_DB_PATH", str(synthetic[0]))


async def test_tool_inventory_annotations_and_structured_models():
    async with Client(main.mcp) as client:
        inventory = await client.list_tools()
        names = {t.name for t in inventory.tools}
        assert names == {
            "server_status",
            "schema_info",
            "list_accounts",
            "get_account",
            "search_transactions",
            "list_categories",
            "list_tags",
            "list_payees",
            "list_budgets",
            "list_scheduled_transactions",
            "list_due_bills",
            "summarize_cashflow",
        }
        for tool in inventory.tools:
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False
            assert tool.annotations.open_world_hint is False
            assert tool.output_schema
        assert not any(
            isinstance(m, OpenTelemetryMiddleware)
            for m in main.mcp._lowlevel_server.middleware
        )


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("server_status", {}),
        ("schema_info", {}),
        ("list_accounts", {}),
        ("get_account", {"account_id": "account-1"}),
        ("list_categories", {}),
        ("list_tags", {}),
        ("list_payees", {}),
        ("list_budgets", {}),
        ("list_scheduled_transactions", {}),
        (
            "list_due_bills",
            {
                "start": "2026-09-14",
                "end": "2026-09-21",
                "timezone": "Europe/Lisbon",
                "as_of": "2026-09-14T00:00:00Z",
            },
        ),
        (
            "search_transactions",
            {
                "start": "2026-09-01T00:00:00Z",
                "end": "2026-10-01T00:00:00Z",
                "transaction_type": "withdraw",
                "limit": 2,
            },
        ),
        (
            "summarize_cashflow",
            {"start": "2026-09-01T00:00:00Z", "end": "2026-10-01T00:00:00Z"},
        ),
    ],
)
async def test_all_tools_over_real_sdk_protocol(name, args):
    async with Client(main.mcp) as client:
        result = await client.call_tool(name, args)
        assert not result.is_error
        assert result.structured_content["error"] is None
        assert result.structured_content["data"] is not None
        if name in ("search_transactions", "summarize_cashflow"):
            assert result.structured_content["data"]["interval"]["timezone"] == "UTC"
        if name == "search_transactions":
            data = result.structured_content["data"]
            assert data["page"]["matched_count"] == 5
            assert data["page"]["returned_count"] == 2
            assert data["page"]["truncated"]
            assert {t["transaction_type"] for t in data["page"]["items"]} == {
                "withdraw"
            }
            assert isinstance(data["page"]["items"][0]["money"]["amount"], str)


async def test_structured_error_and_logs_are_private(caplog):
    async with Client(main.mcp) as client:
        result = await client.call_tool(
            "get_account", {"account_id": "PRIVATE-MISSING-ACCOUNT"}
        )
        assert result.structured_content["error"]["code"] == "INVALID_PARAMETER"
        assert result.structured_content["data"] is None
        result = await client.call_tool(
            "search_transactions",
            {
                "start": "2026-09-01",
                "end": "2026-10-01",
                "transaction_type": "unsupported",
            },
        )
        assert result.structured_content["error"]["code"] == "INVALID_PARAMETER"
    assert "PRIVATE-MISSING-ACCOUNT" not in caplog.text
    assert "Private fabricated" not in caplog.text
    assert "Fabricated employer" not in caplog.text


async def test_category_nbsp_filter_over_mcp_preserves_stored_name(synthetic):
    import sqlite3

    stored_name = "Food\u00a0&\u00a0Dining"
    requested_name = " \tFood &  Dining\n"
    with sqlite3.connect(synthetic[0]) as db:
        db.execute("UPDATE ZSYNCOBJECT SET ZNAME2=? WHERE Z_PK=201", (stored_name,))
    async with Client(main.mcp) as client:
        reply = await client.call_tool(
            "search_transactions",
            {
                "start": "2026-09-01T00:00:00Z",
                "end": "2026-10-01T00:00:00Z",
                "categories": [requested_name, "Food & Dining"],
                "limit": 1,
            },
        )
        assert not reply.is_error
        assert reply.structured_content["error"] is None
        data = reply.structured_content["data"]
        assert data["filters_applied"]["categories"] == [
            requested_name,
            "Food & Dining",
        ]
        assert data["page"]["matched_count"] == 11
        assert data["page"]["returned_count"] == 1
        category = data["page"]["items"][0]["categories"][0]
        assert category["name"] == stored_name
        assert category["hierarchy"] == ["Food", stored_name]


async def test_mcp_input_bounds():
    async with Client(main.mcp) as client:
        for args in [{"limit": 0}, {"limit": 501}, {"offset": -1}]:
            result = await client.call_tool("list_accounts", args)
            assert result.is_error


async def test_due_bills_protocol_pagination_totals_and_errors():
    args = {
        "start": "2026-09-01",
        "end": "2026-11-01",
        "timezone": "Europe/Lisbon",
        "as_of": "2026-09-01T00:00:00+01:00",
        "limit": 1,
    }
    async with Client(main.mcp) as client:
        result = await client.call_tool("list_due_bills", args)
        assert not result.is_error
        data = result.structured_content["data"]
        assert data["projection_complete"]
        assert data["totals_complete"]
        assert data["page"]["matched_count"] == 2
        assert data["page"]["next_offset"] == 1
        assert data["page"]["items"][0]["basis"] == "stored_next_execution"
        assert data["totals"]["bills_in_interval"] == [
            {"amount": "100", "currency": "EUR"}
        ]
        second = await client.call_tool("list_due_bills", {**args, "offset": 1})
        assert (
            second.structured_content["data"]["page"]["items"][0]["basis"]
            == "projected"
        )
        for invalid in (
            {"as_of": "2026-09-01"},
            {"as_of": "2026-09-01T12:00:00"},
            {"end": "2028-01-01"},
            {"timezone": "invalid"},
            {"account_ids": ["missing"]},
        ):
            failure = await client.call_tool("list_due_bills", {**args, **invalid})
            assert failure.structured_content["data"] is None
            assert failure.structured_content["error"]["code"] == "INVALID_PARAMETER"
        failure = await client.call_tool("list_due_bills", {**args, "limit": 501})
        assert failure.is_error


async def test_mcp_offset_and_hidden_accounts(synthetic):
    import sqlite3

    with sqlite3.connect(synthetic[0]) as db:
        db.execute("UPDATE ZSYNCOBJECT SET ZARCHIVED=1 WHERE Z_PK=4")
    async with Client(main.mcp) as client:
        result = (
            await client.call_tool("list_accounts", {"offset": 1, "limit": 1})
        ).structured_content["data"]
        assert result["matched_count"] == 3
        assert result["items"][0]["id"] == "2"
        assert result["next_offset"] == 2
        result = (
            await client.call_tool("list_accounts", {"include_hidden": True})
        ).structured_content["data"]
        assert result["matched_count"] == 4


async def test_configured_maximum(synthetic, monkeypatch):
    from moneywiz_mcp_server.config import Config

    monkeypatch.setattr(main, "_config", Config(str(synthetic[0]), max_results=1))
    assert (await main.list_accounts(limit=2)).error.code == "INVALID_PARAMETER"
    assert (
        await main.list_due_bills("2026-09-01", "2026-10-01", limit=2)
    ).error.code == "INVALID_PARAMETER"


async def test_unexpected_exception_sanitized(monkeypatch):
    async def fail():
        raise RuntimeError("PRIVATE SECRET DATABASE CONTENTS")

    reply = await main.guarded(fail)()
    assert reply.error.code == "INTERNAL_ERROR"
    assert "PRIVATE" not in reply.model_dump_json()


async def test_stdio_subprocess_real_client(synthetic):
    args = StdioServerParameters(
        command=sys.executable,
        args=["-m", "moneywiz_mcp_server"],
        env={**os.environ, "MONEYWIZ_DB_PATH": str(synthetic[0])},
    )
    async with Client(args, read_timeout_seconds=15) as client:
        result = await client.call_tool("list_accounts", {})
        assert result.structured_content["data"]["matched_count"] == 4


def test_validation_cli_does_not_dump_transactions(synthetic):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "moneywiz_mcp_server.validate",
            "--db",
            str(synthetic[0]),
            "--start",
            "2026-09-01T00:00:00Z",
            "--end",
            "2026-10-01T00:00:00Z",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["account_count"] == 4
    assert not report["errors"]
    assert not report["ui_reconciliation_completed"]
    assert report["interval"]["timezone"] == "UTC"
    assert "Private fabricated" not in result.stdout
    assert "Fabricated employer" not in result.stdout
    assert str(Path.home()) not in result.stdout


def test_cli_rejects_bad_path_without_leaking_it():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "moneywiz_mcp_server.validate",
            "--db",
            "/PRIVATE-SECRET/db.sqlite",
            "--start",
            "2026-09-01",
            "--end",
            "2026-10-01",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert json.loads(result.stderr)["error"]["code"] == "INVALID_DATABASE"
    assert "PRIVATE-SECRET" not in result.stderr


def test_cli_server_missing_configuration(monkeypatch):
    monkeypatch.delenv("MONEYWIZ_DB_PATH")
    result = subprocess.run(
        [sys.executable, "-m", "moneywiz_mcp_server"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert json.loads(result.stderr)["error"]["code"] == "INVALID_CONFIG"


async def test_environment_maximum_applies_without_cli_config(monkeypatch):
    monkeypatch.setenv("MAX_RESULTS", "1")
    assert (await main.list_accounts(limit=2)).error.code == "INVALID_PARAMETER"
