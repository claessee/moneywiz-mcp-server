"""Comparison-only normalization for stored MoneyWiz category names."""


def normalize_category_name(name: str) -> str:
    """Collapse Unicode whitespace without changing case or punctuation.

    MoneyWiz stores some category names with NBSP (U+00A0). Keep stored
    names intact for output; use this value only when comparing filters.
    """
    return " ".join(name.split())
