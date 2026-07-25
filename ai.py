"""
ai.py
Every function here returns the same shape whether it's backed by a
rule-based heuristic (today) or an LLM call (soon). That's the seam:
when you wire in Groq/OpenAI/Anthropic, you only touch the body of
these functions — components.py and app.py never change.

To add a real LLM call later, drop something like this into any function:

    from groq import Groq
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
"""

from __future__ import annotations
from utils import safe_get, format_market_cap


def generate_executive_summary(info: dict) -> str:
    """Rule-based paragraph today; swap for an LLM call using `info` as context later."""
    name = safe_get(info, "longName", "This company")
    sector = safe_get(info, "sector", "its sector")
    industry = safe_get(info, "industry", "its industry")
    summary = safe_get(info, "longBusinessSummary", "")
    market_cap = format_market_cap(info.get("marketCap"))

    first_sentence = summary.split(". ")[0] + "." if summary else f"{name} operates in the {industry} space."

    return (
        f"{first_sentence} Classified under the {sector} sector, {name} carries a market "
        f"capitalization of {market_cap}. Investors evaluating this name should weigh its "
        f"competitive position within {industry} against broader macro conditions affecting "
        f"the {sector.lower() if isinstance(sector, str) else 'sector'}."
    )


def generate_ai_rating(info: dict) -> tuple[str, float]:
    """
    Placeholder scoring model: nudges toward BUY/HOLD/SELL using a few
    widely-available fundamentals. Replace with a real model or LLM-reasoned
    score once you have historicals + peer comparisons wired up.
    """
    score = 50.0

    pe = info.get("trailingPE")
    if pe is not None:
        if pe < 15:
            score += 12
        elif pe > 40:
            score -= 12

    growth = info.get("revenueGrowth")
    if growth is not None:
        score += min(20, max(-20, growth * 100))

    margins = info.get("profitMargins")
    if margins is not None:
        score += min(15, max(-15, margins * 50))

    recommendation_key = (info.get("recommendationKey") or "").lower()
    bump = {"strong_buy": 15, "buy": 8, "hold": 0, "sell": -8, "strong_sell": -15}
    score += bump.get(recommendation_key, 0)

    score = max(5, min(95, score))

    if score >= 65:
        rating = "BUY"
    elif score >= 40:
        rating = "HOLD"
    else:
        rating = "SELL"

    return rating, round(score, 0)


def generate_financial_health(info: dict) -> dict[str, float]:
    """Rough 1-5 star heuristics per category. Swap for real scoring logic later."""
    def clamp5(x):
        return max(0.5, min(5.0, x))

    revenue_growth = info.get("revenueGrowth") or 0
    profit_margin = info.get("profitMargins") or 0
    debt_to_equity = info.get("debtToEquity")
    pe = info.get("trailingPE")

    revenue_score = clamp5(3 + revenue_growth * 10)
    profitability_score = clamp5(3 + profit_margin * 10)
    balance_sheet_score = clamp5(4 - (debt_to_equity / 100 if debt_to_equity else 1))
    valuation_score = clamp5(5 - (pe / 20 if pe else 2.5))

    return {
        "Revenue Growth": revenue_score,
        "Profitability": profitability_score,
        "Balance Sheet": balance_sheet_score,
        "Valuation": valuation_score,
    }


def generate_investment_thesis(info: dict) -> dict[str, list[str]]:
    """Template-based bull/bear/catalysts/risks. Swap the return for an LLM-generated list later."""
    name = safe_get(info, "longName", "The company")
    sector = safe_get(info, "sector", "its sector")

    bull = [
        f"{name} holds a meaningful position within {sector}.",
        "Revenue and margin trends support continued reinvestment.",
        "Balance sheet flexibility allows for opportunistic capital allocation.",
    ]
    bear = [
        "Valuation may already reflect much of the near-term growth story.",
        "Competitive intensity within the sector could pressure margins.",
        "Macro sensitivity remains a swing factor for the stock.",
    ]
    catalysts = [
        "Upcoming earnings report and forward guidance.",
        "Potential new product or segment announcements.",
        "Sector-wide demand tailwinds.",
    ]
    risks = [
        "Regulatory or geopolitical developments affecting the sector.",
        "Execution risk on strategic initiatives.",
        "Broader market volatility and rate sensitivity.",
    ]
    return {"bull": bull, "bear": bear, "catalysts": catalysts, "risks": risks}


def generate_market_pulse(indices: list[dict], sectors: list[dict], news: list[dict]) -> str:
    """
    Rule-based 'why is the market doing this today' summary. Important
    honesty note: this juxtaposes sector performance with real headlines —
    it does NOT verify that a given headline actually caused a given
    sector's move. Establishing real causal attribution needs an LLM
    reading full articles, not just RSS titles. Swap this function for
    that once you wire up Groq; keep the same (indices, sectors, news)
    signature so app.py doesn't need to change.
    """
    if not indices:
        return "Market data is unavailable right now."

    spx = next((i for i in indices if i["ticker"] == "^GSPC"), indices[0])
    direction = "higher" if (spx["pct_change"] or 0) >= 0 else "lower"

    sorted_sectors = sorted(
        [s for s in sectors if s["pct_change"] is not None],
        key=lambda s: s["pct_change"], reverse=True,
    )
    lead_line = ""
    if sorted_sectors:
        best = sorted_sectors[0]
        worst = sorted_sectors[-1]
        lead_line = (
            f" {best['sector']} led the way at {best['pct_change']*100:+.1f}%, "
            f"while {worst['sector']} lagged at {worst['pct_change']*100:+.1f}%."
        )

    news_line = ""
    if news:
        positive = sum(1 for n in news if n["sentiment"] == "Positive")
        negative = sum(1 for n in news if n["sentiment"] == "Negative")
        if positive > negative:
            tone = "Coverage today leans constructive"
        elif negative > positive:
            tone = "Coverage today leans cautious"
        else:
            tone = "Coverage today is mixed"
        top_headline = news[0]["headline"]
        news_line = f" {tone}, with reporting including: \u201c{top_headline}\u201d"

    return f"Markets are trading {direction} today.{lead_line}{news_line}"


def generate_portfolio_scores(rows: list[dict], total_value: float) -> dict:
    """
    Diversification / concentration / risk, all 0-100.

    - Diversification: derived from the Herfindahl-Hirschman Index (HHI) of
      position weights — a standard concentration measure. Low HHI (many
      similarly-sized positions) -> high diversification score.
    - Concentration: simply the largest single position's weight, as a
      percentage — the most direct, interpretable "how exposed am I to one
      name" number.
    - Risk: a weighted average of each holding's beta (yfinance-reported),
      rescaled to 0-100 around beta=1.0 as "market-average risk" (~50).
      This is a rough proxy, not a full risk model — swap for something
      more rigorous (factor exposures, volatility, drawdown) later if
      needed.
    """
    if not rows or total_value <= 0:
        return {"diversification": 0, "concentration": 0, "risk": 0}

    weights = [r["market_value"] / total_value for r in rows]
    hhi = sum(w ** 2 for w in weights)
    diversification = max(0, min(100, (1 - hhi) * 100))
    concentration = max(weights) * 100

    weighted_beta = sum(
        (r["beta"] or 1.0) * (r["market_value"] / total_value) for r in rows
    )
    risk = max(0, min(100, weighted_beta * 50))

    return {
        "diversification": round(diversification),
        "concentration": round(concentration),
        "risk": round(risk),
    }


def generate_portfolio_insights(rows: list[dict], total_value: float) -> list[str]:
    """Rule-based observations about concentration and sector exposure."""
    if not rows or total_value <= 0:
        return ["Add holdings above to see personalized insights."]

    insights = []

    top = max(rows, key=lambda r: r["market_value"])
    top_weight = top["market_value"] / total_value
    if top_weight > 0.4:
        insights.append(
            f"Over {top_weight * 100:.0f}% of your portfolio is in {top['name']} ({top['ticker']})."
        )

    sector_totals: dict[str, float] = {}
    for r in rows:
        sector_totals[r["sector"]] = sector_totals.get(r["sector"], 0) + r["market_value"]

    if sector_totals:
        top_sector, top_sector_value = max(sector_totals.items(), key=lambda kv: kv[1])
        sector_weight = top_sector_value / total_value
        if sector_weight > 0.5:
            insights.append(
                f"You are heavily concentrated in {top_sector} ({sector_weight * 100:.0f}% of your portfolio)."
            )

        major_sectors = ["Healthcare", "Financial Services", "Energy", "Consumer Defensive"]
        for sector in major_sectors:
            weight = sector_totals.get(sector, 0) / total_value
            if weight < 0.03:
                insights.append(
                    f"You own very little {sector} — adding exposure here could improve diversification."
                )
                break  # flag one under-weighted sector at a time, not a wall of text

    if len(rows) < 5:
        insights.append(
            "A small number of holdings increases concentration risk — spreading across more companies could help."
        )

    if not insights:
        insights.append("Your portfolio looks reasonably diversified across holdings and sectors.")

    return insights
