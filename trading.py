"""
trading.py
Buy/sell logic for the paper trading simulator. Uses live prices from
data.py (the same yfinance layer the main research app uses) so the
simulation reflects real market prices, while every dollar is virtual —
nothing here ever touches a real brokerage or moves real money.
"""

from __future__ import annotations

import database as db
from data import get_ticker_info, resolve_current_price


def get_live_price(ticker: str) -> float | None:
    info = get_ticker_info(ticker)
    if info is None:
        return None
    return resolve_current_price(info)


def buy_stock(user_id: int, ticker: str, shares: float) -> tuple[bool, str]:
    ticker = ticker.upper()
    if shares <= 0:
        return False, "Enter a positive number of shares."

    price = get_live_price(ticker)
    if price is None:
        return False, f"Couldn't find a live price for {ticker}. Check the symbol."

    cost = shares * price
    user = db.get_user_by_id(user_id)
    if user["cash_balance"] < cost:
        return False, f"Not enough cash. This trade costs {cost:,.2f}, you have {user['cash_balance']:,.2f}."

    existing = db.get_holding(user_id, ticker)
    if existing:
        total_shares = existing["shares"] + shares
        # Weighted-average cost basis, the standard approach for tracking
        # a position built from multiple purchases at different prices.
        new_avg = ((existing["shares"] * existing["avg_price"]) + (shares * price)) / total_shares
        db.upsert_holding(user_id, ticker, total_shares, new_avg)
    else:
        db.upsert_holding(user_id, ticker, shares, price)

    db.update_cash_balance(user_id, user["cash_balance"] - cost)
    db.record_trade(user_id, ticker, "BUY", shares, price)
    return True, f"Bought {shares:g} shares of {ticker} at {price:,.2f}."


def sell_stock(user_id: int, ticker: str, shares: float) -> tuple[bool, str]:
    ticker = ticker.upper()
    if shares <= 0:
        return False, "Enter a positive number of shares."

    holding = db.get_holding(user_id, ticker)
    if holding is None or holding["shares"] < shares:
        held = holding["shares"] if holding else 0
        return False, f"You only hold {held:g} shares of {ticker}."

    price = get_live_price(ticker)
    if price is None:
        return False, f"Couldn't find a live price for {ticker}. Check the symbol."

    proceeds = shares * price
    realized_pl = (price - holding["avg_price"]) * shares

    remaining = holding["shares"] - shares
    if remaining <= 0:
        db.delete_holding(user_id, ticker)
    else:
        db.upsert_holding(user_id, ticker, remaining, holding["avg_price"])

    user = db.get_user_by_id(user_id)
    db.update_cash_balance(user_id, user["cash_balance"] + proceeds)
    db.record_trade(user_id, ticker, "SELL", shares, price, realized_pl=realized_pl)

    pl_word = "gain" if realized_pl >= 0 else "loss"
    return True, f"Sold {shares:g} shares of {ticker} at {price:,.2f} — realized {pl_word} of {abs(realized_pl):,.2f}."


def get_portfolio_snapshot(user_id: int) -> dict:
    """
    Cash + holdings (with live prices, unrealized P/L) + total account
    value. Shaped to be easy to feed into the same ai.py scoring/insight
    functions the main Portfolio Analyzer already uses.
    """
    user = db.get_user_by_id(user_id)
    holdings = db.get_holdings(user_id)

    rows = []
    holdings_value = 0.0
    for h in holdings:
        info = get_ticker_info(h["ticker"])
        if info is None:
            continue
        price = resolve_current_price(info)
        if price is None:
            continue
        market_value = h["shares"] * price
        holdings_value += market_value
        rows.append({
            "ticker": h["ticker"],
            "name": info.get("shortName", h["ticker"]),
            "sector": info.get("sector") or "Other",
            "shares": h["shares"],
            "avg_price": h["avg_price"],
            "price": price,
            "market_value": market_value,
            "unrealized_pl": (price - h["avg_price"]) * h["shares"],
            "beta": info.get("beta"),
        })

    return {
        "cash_balance": user["cash_balance"],
        "holdings_value": holdings_value,
        "total_value": user["cash_balance"] + holdings_value,
        "rows": rows,
    }
