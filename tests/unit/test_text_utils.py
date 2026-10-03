import pytest

from moneywiz_mcp_server.utils.text_utils import normalize_category_name


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Food\u00a0&\u00a0Dining", "Food & Dining"),
        ("Food & Dining", "Food & Dining"),
        (" \tFood\u00a0\u2003 &\n\r Dining  ", "Food & Dining"),
        ("food & Dining", "food & Dining"),
        ("Food + Dining", "Food + Dining"),
        ("Food\u200b& Dining", "Food\u200b& Dining"),
        ("", ""),
    ],
)
def test_normalize_category_name(name, expected):
    assert normalize_category_name(name) == expected
    assert normalize_category_name(expected) == expected
