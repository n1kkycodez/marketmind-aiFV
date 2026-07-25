# MarketMind

AI-powered equity research platform. Not a trading platform — a fast way to
understand a publicly traded company using live data, structured analysis,
and (soon) LLM-generated reasoning.

## Stack
Python · Streamlit · Plotly · yfinance · Pandas · Feedparser · VADER Sentiment
Future: EasyOCR (portfolio screenshots), Groq / OpenAI / Anthropic (report generation)

## Project structure
```
marketmind-ai-v2/
  app.py          # routing + orchestration only
  components.py   # all UI rendering (cards, charts, sections) + CSS theme
  data.py         # yfinance / news / sentiment — cached, no UI code
  ai.py           # rule-based placeholders, shaped like future LLM calls
  utils.py        # pure formatting helpers, no Streamlit/yfinance imports
  requirements.txt
  .streamlit/config.toml
```

The layers only talk in one direction: `app.py → components.py → (data.py, ai.py) → utils.py`.
Nothing reaches back up. This is what makes it survive growing to 20k+ lines
without turning into spaghetti — you can rewrite `ai.py` entirely to call
Groq and nothing else in the app needs to change.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## What's real vs. stubbed right now

**Live / working:**
- Home search → company lookup via yfinance
- Company header, key facts, financial snapshot metrics
- Interactive price chart (1D / 1M / 6M / 1Y / 5Y)
- News feed with VADER sentiment scoring
- Competitor comparison table (edit `PEER_MAP` in `app.py` to add tickers)
- Financial health star ratings (rule-based)

**Stubbed, ready for you to wire up:**
- **Executive Summary** — currently template-assembled from yfinance's
  `longBusinessSummary`. Swap the body of `generate_executive_summary()`
  in `ai.py` for a Groq call.
- **AI Rating** — currently a weighted heuristic on P/E, revenue growth,
  margins, and analyst recommendation. Swap `generate_ai_rating()`.
- **Investment Thesis** — currently templated bull/bear/catalysts/risks.
  Swap `generate_investment_thesis()`.
- **Portfolio Analyzer** (screenshot → holdings via EasyOCR) — not yet built.
- **PDF Report Generator** — not yet built.

## Next steps (suggested order)
1. Wire a Groq API key into `ai.py` (see the docstring at the top of the
   file for the exact call shape) and swap the three functions above.
2. Build `portfolio.py`: EasyOCR extraction → ticker/share-count parsing →
   allocation + diversification scoring, following the same
   data-layer-returns-plain-dicts pattern as `data.py`.
3. Build `report.py` using `reportlab` or `weasyprint` to render a PDF from
   the same data structures already powering the on-screen sections.
4. Add `st.secrets` for API keys before deploying (never commit keys).

## Design notes
The CSS in `components.py` intentionally avoids Streamlit's default chrome
(hides the hamburger menu, footer, restyles inputs into pills) to get closer
to an Apple / Perplexity / Linear feel: generous whitespace, 16px card
radius, a single neutral palette with red/green reserved only for price and
sentiment signals. If you want to push the aesthetic further, the CSS block
at the top of `inject_custom_css()` is the only place you need to touch.
