"""MoneyWiz MCP Server - A Model Context Protocol server for MoneyWiz financial data.

This package provides permanently read-only MoneyWiz SQLite retrieval and
deterministic aggregation. Financial semantics require local UI reconciliation.
"""

from importlib.metadata import PackageNotFoundError, version

__author__ = "Juan Carlos Valerio Arrieta"
__email__ = "jcvalerio@gmail.com"

try:
    __version__ = version("moneywiz-mcp-server")
except PackageNotFoundError:  # pragma: no cover - only possible outside installs
    __version__ = "0.0.0"

# Re-export main components for easier imports
from .config import Config

__all__ = ["Config", "__version__"]
