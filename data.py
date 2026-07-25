"""
data.py
All external data access lives here: yfinance quotes/history, news feeds,
sentiment scoring. Every public function is cached via st.cache_data so the
UI layer never has to think about rate limits or latency.

Nothing in this file should render UI — return plain dicts / DataFrames.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import pandas as pd
import streamlit as st
import yfinance as yf
import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from utils import sentiment_label

_analyzer = SentimentIntensityAnalyzer()

WATCHLIST_PATH = Path(__file__).parent / "watchlist.json"
PORTFOLIO_PATH = Path(__file__).parent / "portfolio.json"

PERIOD_MAP = {
    "1D": ("1d", "5m"),
    "1M": ("1mo", "1d"),
    "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"),
    "5Y": ("5y", "1wk"),
}


@st.cache_data(ttl=300, show_spinner=False)
def get_ticker_info(ticker: str) -> Optional[dict]:
    """Core company profile + snapshot metrics from yfinance."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            # Some tickers only populate fast_info
            fast = t.fast_info
            if fast is None or fast.get("lastPrice") is None:
                return None
        return info
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def get_price_history(ticker: str, range_label: str = "1Y") -> pd.DataFrame:
    """Returns OHLCV history for the requested range label (see PERIOD_MAP)."""
    period, interval = PERIOD_MAP.get(range_label, ("1y", "1d"))
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval=interval)
        if hist is None or hist.empty:
            return pd.DataFrame()
        hist = hist.reset_index()
        # yfinance names the index column differently for intraday vs daily
        date_col = "Datetime" if "Datetime" in hist.columns else "Date"
        hist = hist.rename(columns={date_col: "Date"})
        return hist
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def get_news(ticker: str, company_name: str = "", limit: int = 8) -> list[dict]:
    """
    Pulls headlines from Yahoo Finance's per-ticker RSS feed and scores
    sentiment with VADER. Falls back to a Google News query if the Yahoo
    feed is empty (e.g. thinly covered tickers).
    """
    feeds_to_try = [
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    ]
    if company_name:
        query = company_name.replace(" ", "+")
        feeds_to_try.append(
            f"https://news.google.com/rss/search?q={query}+stock&hl=en-US&gl=US&ceid=US:en"
        )

    items = []
    for url in feeds_to_try:
        try:
            parsed = feedparser.parse(url)
        except Exception:
            continue
        for entry in parsed.entries[:limit]:
            title = entry.get("title", "")
            if not title:
                continue
            score = _analyzer.polarity_scores(title)
            items.append({
                "headline": title,
                "source": entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else parsed.feed.get("title", "News"),
                "date": entry.get("published", ""),
                "link": entry.get("link", ""),
                "sentiment": sentiment_label(score["compound"]),
                "sentiment_score": score["compound"],
            })
        if items:
            break

    return items[:limit]


@st.cache_data(ttl=300, show_spinner=False)
def get_competitors_info(tickers: list[str]) -> list[dict]:
    """Lightweight snapshot for a list of competitor tickers, for comparison tables."""
    results = []
    for tk in tickers:
        info = get_ticker_info(tk)
        if info:
            results.append({"ticker": tk, "info": info})
    return results


def resolve_current_price(info: dict) -> Optional[float]:
    return info.get("currentPrice") or info.get("regularMarketPrice")


def resolve_price_change_pct(info: dict) -> Optional[float]:
    price = resolve_current_price(info)
    prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
    if price is None or prev_close in (None, 0):
        return None
    return (price - prev_close) / prev_close


# ----------------------------------------------------------------------
# Market dashboard: indices, sector performance, movers
# ----------------------------------------------------------------------

# Yahoo's index tickers (^ prefix). Display name -> ticker symbol.
MARKET_INDICES = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "Russell 2000": "^RUT",
}

# SPDR sector ETFs used as a standard proxy for sector-level performance —
# this is the same approach most retail research sites use, since there's
# no free "sector index" endpoint in yfinance.
SECTOR_ETF_PROXIES = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Utilities": "XLU",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Communication Services": "XLC",
    "Materials": "XLB",
    "Real Estate": "XLRE",
}

# Curated large/mid-cap universe used to compute "movers" locally, since a
# true whole-market screener isn't available through the free yfinance API.
# This is a known, documented limitation — see README.
MOVERS_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "AMD",
    "NFLX", "JPM", "V", "MA", "UNH", "JNJ", "PG", "KO", "PEP", "XOM", "CVX",
    "WMT", "HD", "DIS", "BAC", "CRM", "ORCL", "ADBE", "INTC", "QCOM", "TXN",
    "COST", "MCD", "NKE", "PFE", "ABBV", "TMO", "LIN", "CAT", "BA", "GE",
    "PYPL", "UBER", "SHOP", "ABNB", "SNOW", "PLTR", "COIN", "SOFI", "RIVN", "F",
]


@st.cache_data(ttl=300, show_spinner=False)
def get_market_indices() -> list[dict]:
    """Current level + daily % change for the four major US indices."""
    results = []
    for name, ticker in MARKET_INDICES.items():
        info = get_ticker_info(ticker)
        if info is None:
            continue
        price = resolve_current_price(info)
        pct = resolve_price_change_pct(info)
        results.append({"name": name, "ticker": ticker, "price": price, "pct_change": pct})
    return results


@st.cache_data(ttl=300, show_spinner=False)
def get_sector_performance() -> list[dict]:
    """Today's % change for each sector, via SPDR sector ETF proxies."""
    results = []
    for sector, etf in SECTOR_ETF_PROXIES.items():
        info = get_ticker_info(etf)
        if info is None:
            continue
        pct = resolve_price_change_pct(info)
        results.append({"sector": sector, "etf": etf, "pct_change": pct})
    results.sort(key=lambda r: r["pct_change"] if r["pct_change"] is not None else 0, reverse=True)
    return results


@st.cache_data(ttl=300, show_spinner=False)
def get_market_movers(limit: int = 5) -> dict:
    """
    Gainers / losers / most-active computed from a curated large-cap
    universe (see MOVERS_UNIVERSE). This is NOT a full-market screener —
    free yfinance has no such endpoint — but it surfaces meaningful moves
    among widely-held names, which is what most users actually care about.
    """
    rows = []
    for ticker in MOVERS_UNIVERSE:
        info = get_ticker_info(ticker)
        if info is None:
            continue
        price = resolve_current_price(info)
        pct = resolve_price_change_pct(info)
        volume = info.get("regularMarketVolume") or info.get("volume")
        if price is None or pct is None:
            continue
        rows.append({
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "price": price,
            "pct_change": pct,
            "volume": volume or 0,
        })

    gainers = sorted(rows, key=lambda r: r["pct_change"], reverse=True)[:limit]
    losers = sorted(rows, key=lambda r: r["pct_change"])[:limit]
    most_active = sorted(rows, key=lambda r: r["volume"], reverse=True)[:limit]

    return {"gainers": gainers, "losers": losers, "most_active": most_active}


@st.cache_data(ttl=600, show_spinner=False)
def get_market_pulse_news(limit: int = 6) -> list[dict]:
    """
    General market-wide headlines (not ticker-specific) used to give the
    homepage 'why' summary some real context. Uses Yahoo Finance's broad
    market RSS feed.
    """
    url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EDJI,%5EIXIC&region=US&lang=en-US"
    try:
        parsed = feedparser.parse(url)
    except Exception:
        return []

    items = []
    for entry in parsed.entries[:limit]:
        title = entry.get("title", "")
        if not title:
            continue
        score = _analyzer.polarity_scores(title)
        items.append({
            "headline": title,
            "link": entry.get("link", ""),
            "sentiment": sentiment_label(score["compound"]),
        })
    return items


# ----------------------------------------------------------------------
# Watchlist (local persistence)
# ----------------------------------------------------------------------
# Since MarketMind runs locally, "remembering" a watchlist is just plain
# file I/O — no special persistence system needed. watchlist.json sits
# next to app.py and survives restarts. Swap this for a real DB (SQLite,
# Postgres) later if you add multi-user support; the function signatures
# below wouldn't need to change.

def load_watchlist() -> list[str]:
    """Reads saved tickers from watchlist.json."""
    try:
        if WATCHLIST_PATH.exists():
            with open(WATCHLIST_PATH, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [t.upper() for t in data]
    except Exception:
        pass
    return []


def save_watchlist(tickers: list[str]) -> None:
    try:
        with open(WATCHLIST_PATH, "w") as f:
            json.dump(sorted(set(t.upper() for t in tickers)), f, indent=2)
    except Exception:
        pass


def add_to_watchlist(ticker: str) -> list[str]:
    tickers = load_watchlist()
    ticker = ticker.upper()
    if ticker not in tickers:
        tickers.append(ticker)
        save_watchlist(tickers)
    return tickers


def remove_from_watchlist(ticker: str) -> list[str]:
    tickers = load_watchlist()
    ticker = ticker.upper()
    if ticker in tickers:
        tickers.remove(ticker)
        save_watchlist(tickers)
    return tickers


def get_watchlist_snapshot() -> list[dict]:
    """
    Current price + % change for every saved ticker. Deliberately NOT
    cached at this level — it always reflects the latest add/remove —
    while the underlying get_ticker_info() calls are still individually
    cached for 5 minutes, so this stays cheap.
    """
    rows = []
    for ticker in load_watchlist():
        info = get_ticker_info(ticker)
        if info is None:
            rows.append({"ticker": ticker, "name": ticker, "price": None, "pct_change": None})
            continue
        rows.append({
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "price": resolve_current_price(info),
            "pct_change": resolve_price_change_pct(info),
        })
    return rows


# ----------------------------------------------------------------------
# Explore
# ----------------------------------------------------------------------

EXPLORE_CATEGORIES = {
    "Top AI Companies": ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "PLTR", "AVGO", "CRM", "ORCL", "IBM"],
    "Semiconductors": ["NVDA", "AMD", "AVGO", "TSM", "INTC", "QCOM", "TXN", "MU", "ASML", "LRCX"],
    "Largest Companies": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "LLY", "TSLA", "V"],
    "Dividend Stocks": ["JNJ", "PG", "KO", "PEP", "VZ", "T", "XOM", "CVX", "MMM", "ABBV"],
    "Growth Stocks": ["NVDA", "TSLA", "SHOP", "PLTR", "CRWD", "NET", "DDOG", "SNOW", "UBER", "ABNB"],
    "Value Stocks": ["BRK-B", "JPM", "BAC", "WFC", "F", "GM", "T", "VZ", "INTC", "PFE"],
    "Popular ETFs": ["SPY", "QQQ", "VOO", "VTI", "ARKK", "XLK", "SCHD", "DIA", "IWM", "GLD"],
}


@st.cache_data(ttl=300, show_spinner=False)
def get_explore_category(name: str) -> list[dict]:
    tickers = EXPLORE_CATEGORIES.get(name, [])
    rows = []
    for ticker in tickers:
        info = get_ticker_info(ticker)
        if info is None:
            continue
        rows.append({
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "price": resolve_current_price(info),
            "pct_change": resolve_price_change_pct(info),
            "market_cap": info.get("marketCap"),
        })
    return rows


# ----------------------------------------------------------------------
# Portfolio (manual entry + best-effort OCR)
# ----------------------------------------------------------------------
# Same "just a local JSON file" persistence pattern as the watchlist.

def load_portfolio() -> dict[str, float]:
    """{ticker: shares}"""
    try:
        if PORTFOLIO_PATH.exists():
            with open(PORTFOLIO_PATH, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {k.upper(): float(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_portfolio(holdings: dict[str, float]) -> None:
    try:
        clean = {k.upper(): float(v) for k, v in holdings.items() if v and float(v) > 0}
        with open(PORTFOLIO_PATH, "w") as f:
            json.dump(clean, f, indent=2)
    except Exception:
        pass


def get_portfolio_snapshot(holdings: dict[str, float]) -> list[dict]:
    """Live price, sector, and market value for every saved holding."""
    rows = []
    for ticker, shares in holdings.items():
        info = get_ticker_info(ticker)
        if info is None:
            continue
        price = resolve_current_price(info)
        if price is None:
            continue
        rows.append({
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "sector": info.get("sector") or "Other",
            "shares": shares,
            "price": price,
            "market_value": shares * price,
            "beta": info.get("beta"),
            "pct_change": resolve_price_change_pct(info),
        })
    return rows


_OCR_READER = None

# Common non-ticker words that would otherwise false-positive as tickers
# (all-caps 1-5 letter tokens are extremely common in broker app UI chrome).
_OCR_NOISE_WORDS = {
    "THE", "AND", "FOR", "YOU", "YOUR", "TOTAL", "VALUE", "SHARES", "SHARE",
    "TODAY", "BUY", "SELL", "STOCK", "STOCKS", "PORTFOLIO", "CASH", "ACCOUNT",
    "GAIN", "LOSS", "AVG", "COST", "PRICE", "MARKET", "NYSE", "NASDAQ", "INC",
    "CORP", "ETF", "USD", "ALL", "NEW", "DAY", "WEEK", "YEAR", "OPEN", "HIGH",
    "LOW", "CLOSE", "AMT", "QTY", "INV", "APP", "USA", "P", "L",
}


def _get_ocr_reader():
    global _OCR_READER
    if _OCR_READER is None:
        import easyocr
        _OCR_READER = easyocr.Reader(["en"], gpu=False)
    return _OCR_READER


def extract_tickers_from_image(image_bytes: bytes) -> list[str]:
    """
    Best-effort ticker detection from a portfolio screenshot.

    Deliberately conservative: this only flags plausible ticker-like tokens
    for the person to confirm — it does NOT try to auto-extract share
    counts. Broker app layouts vary too much to reliably pair a number with
    the right ticker without real risk of a false pairing, and a wrong
    share count would silently corrupt every downstream calculation
    (portfolio value, allocation, risk score). Share counts are always
    entered/confirmed by hand in the editable table.
    """
    try:
        from PIL import Image
        import numpy as np
        import io
        import re

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        reader = _get_ocr_reader()
        results = reader.readtext(np.array(image), detail=0)
    except Exception:
        return []

    candidates = []
    for text in results:
        for token in re.findall(r"\b[A-Z]{1,5}\b", text.upper()):
            if token in _OCR_NOISE_WORDS:
                continue
            if token not in candidates:
                candidates.append(token)
    return candidates[:20]
