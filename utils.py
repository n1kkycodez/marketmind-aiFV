"""
utils.py
Small, reusable, dependency-free helper functions.
No Streamlit imports here — keep this layer pure so it's testable.
"""

from __future__ import annotations
from typing import Any, Optional


def safe_get(d: dict, key: str, default: Any = None) -> Any:
    """Get a value from a dict, treating None the same as missing."""
    val = d.get(key, default)
    return val if val is not None else default


def format_currency(value: Optional[float], decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"${value:,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def format_market_cap(value: Optional[float]) -> str:
    """1.23e12 -> '$1.23T', 4.5e9 -> '$4.50B', etc."""
    if value is None:
        return "—"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"

    abs_val = abs(value)
    if abs_val >= 1e12:
        return f"${value / 1e12:.2f}T"
    if abs_val >= 1e9:
        return f"${value / 1e9:.2f}B"
    if abs_val >= 1e6:
        return f"${value / 1e6:.2f}M"
    return f"${value:,.0f}"


def format_percent(value: Optional[float], decimals: int = 2, already_pct: bool = False) -> str:
    """value as a fraction (0.045) unless already_pct=True (4.5)."""
    if value is None:
        return "—"
    try:
        pct = value if already_pct else value * 100
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct:.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def format_large_number(value: Optional[float]) -> str:
    return format_market_cap(value)


def format_ratio(value: Optional[float], decimals: int = 2, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        return f"{value:.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def render_stars(rating: float, max_stars: int = 5) -> str:
    """rating: 0-5 float -> '★★★★☆' style string."""
    rating = max(0, min(max_stars, round(rating)))
    return "★" * rating + "☆" * (max_stars - rating)


def sentiment_label(compound_score: float) -> str:
    """VADER compound score -> Positive/Neutral/Negative."""
    if compound_score >= 0.05:
        return "Positive"
    if compound_score <= -0.05:
        return "Negative"
    return "Neutral"


def sentiment_color(label: str) -> str:
    return {
        "Positive": "#1a8a4a",
        "Negative": "#c0392b",
        "Neutral": "#6b7280",
    }.get(label, "#6b7280")


def pct_change_color(value: Optional[float]) -> str:
    if value is None:
        return "#6b7280"
    return "#1a8a4a" if value >= 0 else "#c0392b"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
