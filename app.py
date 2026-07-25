"""
app.py
Entry point. Routing + orchestration only — all rendering logic lives in
components.py, all data access in data.py, all AI/heuristic logic in ai.py.
"""

import streamlit as st
import pandas as pd

from components import (
    inject_custom_css, render_home_hero, render_company_header,
    render_company_facts, render_executive_summary, render_financial_snapshot,
    render_price_chart, render_news_section, render_ai_rating,
    render_financial_health, render_investment_thesis, render_competitor_table,
    render_index_cards, render_sector_performance, render_movers, render_market_pulse,
    render_nav_bar, render_watchlist_page, render_explore_page,
    render_portfolio_summary, render_sector_allocation_chart,
    render_largest_holdings, render_portfolio_insights, render_section_title,
    render_auth_page, render_disclaimer_gate, render_academy_header,
    render_trade_form, render_holdings_table, render_trade_history,
    render_experience_switcher, render_experience_chooser,
)
from data import (
    get_ticker_info, get_price_history, get_news, get_competitors_info,
    resolve_current_price, resolve_price_change_pct,
    get_market_indices, get_sector_performance, get_market_movers, get_market_pulse_news,
    load_watchlist, add_to_watchlist, remove_from_watchlist, get_watchlist_snapshot,
    EXPLORE_CATEGORIES, get_explore_category,
    load_portfolio, save_portfolio, get_portfolio_snapshot, extract_tickers_from_image,
)
from ai import (
    generate_executive_summary, generate_ai_rating,
    generate_financial_health, generate_investment_thesis, generate_market_pulse,
    generate_portfolio_scores, generate_portfolio_insights,
)
from utils import format_market_cap, format_ratio

import database as db
import auth
import trading

st.set_page_config(page_title="MarketMind AI — Research, Learn, Explore", page_icon="marketmind-favicon.png", layout="wide")
inject_custom_css()
db.init_db()

if "experience" not in st.session_state:
    st.session_state["experience"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "ticker" not in st.session_state:
    st.session_state["ticker"] = None
if "price_range" not in st.session_state:
    st.session_state["price_range"] = "1Y"
if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

# Optional: known peer groups for the competitor table. Extend as needed.
PEER_MAP = {
    "NVDA": ["AMD", "AVGO", "TSM"],
    "AAPL": ["MSFT", "GOOGL", "SAMSUNG"],
    "TSLA": ["GM", "F", "RIVN"],
    "MSFT": ["AAPL", "GOOGL", "AMZN"],
    "AMD": ["NVDA", "INTC", "AVGO"],
}


def go_home():
    st.session_state["page"] = "home"
    st.session_state["ticker"] = None
    st.session_state["price_range"] = "1Y"


def render_company_page(ticker: str):
    with st.spinner(f"Loading {ticker.upper()}..."):
        info = get_ticker_info(ticker)

    if info is None:
        st.error(f"Couldn't find data for **{ticker.upper()}**. Check the symbol and try again.")
        if st.button("← Back to search"):
            go_home()
            st.rerun()
        return

    ticker_upper = ticker.upper()
    on_watchlist = ticker_upper in load_watchlist()

    top_left, watch_col, back_col = st.columns([5, 2, 1])
    with watch_col:
        watch_label = "★ On Watchlist" if on_watchlist else "☆ Add to Watchlist"
        if st.button(watch_label, use_container_width=True, key="watchlist_toggle"):
            if on_watchlist:
                remove_from_watchlist(ticker_upper)
            else:
                add_to_watchlist(ticker_upper)
            st.rerun()
    with back_col:
        if st.button("← New search", use_container_width=True):
            go_home()
            st.rerun()

    price = resolve_current_price(info)
    pct_change = resolve_price_change_pct(info)

    render_company_header(info, ticker, price, pct_change)
    render_company_facts(info)

    summary = generate_executive_summary(info)
    render_executive_summary(summary)

    render_financial_snapshot(info, price, pct_change)

    hist = get_price_history(ticker, st.session_state["price_range"])
    render_price_chart(hist, st.session_state["price_range"])

    news = get_news(ticker, company_name=info.get("shortName", ticker))
    render_news_section(news)

    rating, confidence = generate_ai_rating(info)
    render_ai_rating(rating, confidence)

    health = generate_financial_health(info)
    render_financial_health(health)

    thesis = generate_investment_thesis(info)
    render_investment_thesis(thesis["bull"], thesis["bear"], thesis["catalysts"], thesis["risks"])

    peers = PEER_MAP.get(ticker_upper)
    if peers:
        peer_data = get_competitors_info(peers + [ticker_upper])
        rows = []
        for entry in peer_data:
            pi = entry["info"]
            rows.append({
                "Ticker": entry["ticker"],
                "Market Cap": format_market_cap(pi.get("marketCap")),
                "Revenue Growth": f"{(pi.get('revenueGrowth') or 0) * 100:.1f}%",
                "Profit Margin": f"{(pi.get('profitMargins') or 0) * 100:.1f}%",
                "P/E": format_ratio(pi.get("trailingPE")),
                "AI Rating": generate_ai_rating(pi)[0],
            })
        render_competitor_table(rows)


def render_home_page():
    query = render_home_hero()
    if query:
        st.session_state["ticker"] = query.upper()
        st.session_state["page"] = "company"
        st.session_state["price_range"] = "1Y"
        st.rerun()
        return

    _, toggle_col, _ = st.columns([1, 2, 1])
    with toggle_col:
        show_dashboard = st.toggle("Show today's market", value=st.session_state.get("show_dashboard", True))
        st.session_state["show_dashboard"] = show_dashboard

    if show_dashboard:
        with st.spinner("Loading market data..."):
            indices = get_market_indices()
            sectors = get_sector_performance()
            movers = get_market_movers()
            pulse_news = get_market_pulse_news()
        pulse_summary = generate_market_pulse(indices, sectors, pulse_news)
        render_market_pulse(pulse_summary)
        render_index_cards(indices)
        render_sector_performance(sectors)
        render_movers(movers)


def render_explore():
    with st.spinner("Loading categories..."):
        categories = {name: get_explore_category(name) for name in EXPLORE_CATEGORIES}
        movers = get_market_movers(limit=10)
        categories = {"Trending Today": movers["gainers"], **categories}
    render_explore_page(categories)


def render_portfolio():
    render_section_title("Portfolio Analyzer")
    st.markdown(
        "<div class='mm-card'>Upload a screenshot from Robinhood, Schwab, Fidelity, or Webull to help "
        "spot your tickers, or just add rows manually below. Either way, review every row before "
        "calculating — OCR is a starting point, not a source of truth.</div>",
        unsafe_allow_html=True,
    )

    holdings = load_portfolio()

    uploaded = st.file_uploader("Upload portfolio screenshot", type=["png", "jpg", "jpeg"])
    guessed_tickers = []
    if uploaded is not None:
        with st.spinner("Reading screenshot..."):
            guessed_tickers = extract_tickers_from_image(uploaded.read())
        if guessed_tickers:
            st.success(
                f"Possible tickers found: {', '.join(guessed_tickers)}. "
                "Added below — please confirm and enter share counts."
            )
        else:
            st.warning("Couldn't confidently detect any tickers in that image. Try a clearer screenshot, or add holdings manually below.")

    rows = [{"Ticker": t, "Shares": holdings.get(t, 0.0)} for t in holdings]
    existing = set(holdings.keys())
    for t in guessed_tickers:
        if t not in existing:
            rows.append({"Ticker": t, "Shares": 0.0})
    if not rows:
        rows = [{"Ticker": "", "Shares": 0.0}]

    df = pd.DataFrame(rows)
    st.caption("Add, edit, or remove rows below, then save to calculate.")
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="portfolio_editor")

    if st.button("Save & Calculate", type="primary"):
        new_holdings = {}
        for _, row in edited.iterrows():
            ticker = str(row["Ticker"]).strip().upper()
            shares = row["Shares"]
            try:
                shares = float(shares)
            except (TypeError, ValueError):
                shares = 0
            if ticker and shares > 0:
                new_holdings[ticker] = shares
        save_portfolio(new_holdings)
        st.rerun()

    if holdings:
        with st.spinner("Calculating portfolio..."):
            snapshot = get_portfolio_snapshot(holdings)
        if snapshot:
            total_value = sum(r["market_value"] for r in snapshot)
            scores = generate_portfolio_scores(snapshot, total_value)
            render_portfolio_summary(total_value, scores)
            render_sector_allocation_chart(snapshot)
            render_largest_holdings(snapshot, total_value)
            insights = generate_portfolio_insights(snapshot, total_value)
            render_portfolio_insights(insights)


def render_academy():
    """Gate order: logged out -> auth page. Logged in but hasn't accepted
    the disclaimer -> disclaimer gate. Both cleared -> trading dashboard."""
    user = auth.current_user()

    if user is None:
        render_auth_page()
        return

    if not user["disclaimer_accepted"]:
        render_disclaimer_gate()
        return

    logout_col = st.columns([6, 1])[1]
    with logout_col:
        if st.button("Log Out", use_container_width=True):
            auth.log_out()
            st.rerun()

    with st.spinner("Loading your account..."):
        snapshot = trading.get_portfolio_snapshot(user["id"])

    render_academy_header(user["username"], snapshot["cash_balance"], snapshot["total_value"])

    action, ticker, shares, submitted = render_trade_form()
    if submitted:
        if not ticker or shares <= 0:
            st.warning("Enter a ticker and a positive number of shares.")
        else:
            with st.spinner(f"Processing {action.lower()} order..."):
                if action == "BUY":
                    success, message = trading.buy_stock(user["id"], ticker, shares)
                else:
                    success, message = trading.sell_stock(user["id"], ticker, shares)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    render_holdings_table(snapshot["rows"])

    if snapshot["rows"]:
        scores = generate_portfolio_scores(snapshot["rows"], snapshot["total_value"])
        render_portfolio_summary(snapshot["total_value"], scores)
        render_sector_allocation_chart(snapshot["rows"])
        insights = generate_portfolio_insights(snapshot["rows"], snapshot["total_value"])
        render_portfolio_insights(insights)

    trades = db.get_trade_history(user["id"])
    render_trade_history(trades)


# ----------------------------------------------------------------------
# Routing
# ----------------------------------------------------------------------

experience = st.session_state["experience"]

if experience is None:
    render_experience_chooser()

elif experience == "research":
    render_experience_switcher("research")
    render_nav_bar(st.session_state["page"], len(load_watchlist()), len(load_portfolio()))

    if st.session_state["page"] == "watchlist":
        rows = get_watchlist_snapshot()
        render_watchlist_page(rows)
    elif st.session_state["page"] == "portfolio":
        render_portfolio()
    elif st.session_state["page"] == "company" and st.session_state.get("ticker"):
        render_company_page(st.session_state["ticker"])
    else:
        render_home_page()

elif experience == "learn":
    render_experience_switcher("learn")
    render_academy()

elif experience == "explore":
    render_experience_switcher("explore")
    render_explore()
