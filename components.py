"""
components.py
All Streamlit-facing UI building blocks. Keep these small and composable —
app.py should mostly just call functions from this file in sequence.
"""

from __future__ import annotations
import re
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go

from utils import (
    format_currency, format_market_cap, format_percent, format_ratio,
    render_stars, sentiment_color, pct_change_color, safe_get,
)


def _html(markup: str) -> str:
    """
    Collapse an HTML string to a single line before handing it to st.markdown.

    Streamlit's markdown renderer (CommonMark) treats a blank or
    whitespace-only line as the END of an HTML block. Multi-line f-strings
    with optional/empty interpolations (e.g. a delta line that's "" when
    there's no delta) create exactly that kind of blank line, which
    silently truncates rendering and dumps the remaining tags as literal
    text. Collapsing all whitespace runs to a single space makes that
    class of bug impossible.
    """
    return re.sub(r"\s+", " ", markup).strip()


def _md(markup: str) -> None:
    """st.markdown with unsafe_allow_html, always flattened via _html()."""
    st.markdown(_html(markup), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Theme / CSS
# ----------------------------------------------------------------------

def inject_custom_css() -> None:
    st.markdown(_html("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        #MainMenu, header, footer {visibility: hidden;}
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1360px;
        }

        :root {
            --mm-border: #eaeaea;
            --mm-bg-card: #ffffff;
            --mm-text-primary: #111111;
            --mm-text-secondary: #6b7280;
            --mm-accent: #2563eb;
            --mm-radius: 16px;
        }

        /* Kill Streamlit's default input chrome, replace with pill search */
        div[data-baseweb="input"] > div {
            border-radius: 999px !important;
            border: 1px solid var(--mm-border) !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
        }
        input {
            font-size: 16px !important;
        }

        .mm-card {
            background: var(--mm-bg-card);
            border: 1px solid var(--mm-border);
            border-radius: var(--mm-radius);
            padding: 22px 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            margin-bottom: 16px;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .mm-card:hover {
            border-color: #d8d4fb;
            box-shadow: 0 4px 14px rgba(167, 139, 250, 0.1);
        }

        .mm-logo {
            text-align: center;
            font-size: 2.6rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.2rem;
            color: var(--mm-text-primary);
        }
        .mm-subtitle {
            text-align: center;
            color: var(--mm-text-secondary);
            font-size: 1.05rem;
            margin-bottom: 2.2rem;
            font-weight: 500;
        }

        .mm-section-title {
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--mm-text-primary);
            margin: 2.2rem 0 0.8rem 0;
        }

        .mm-metric-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }
        @media (max-width: 700px) {
            .mm-metric-grid { grid-template-columns: repeat(2, 1fr); }
        }
        .mm-metric-card {
            background: #fafafa;
            border: 1px solid var(--mm-border);
            border-radius: 14px;
            padding: 16px 18px;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }
        .mm-metric-card:hover {
            transform: translateY(-3px);
            border-color: transparent;
            box-shadow: 0 0 0 1.5px #a78bfa, 0 8px 20px rgba(167, 139, 250, 0.18);
        }
        .mm-metric-label {
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--mm-text-secondary);
            margin-bottom: 6px;
        }
        .mm-metric-value {
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--mm-text-primary);
            letter-spacing: -0.01em;
        }
        .mm-metric-delta {
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 2px;
        }

        .mm-header-row {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            flex-wrap: wrap;
        }
        .mm-company-name {
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }
        .mm-ticker-tag {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.85rem;
            color: var(--mm-text-secondary);
            background: #f2f2f2;
            padding: 2px 8px;
            border-radius: 6px;
            margin-left: 8px;
        }
        .mm-price {
            font-size: 1.6rem;
            font-weight: 700;
        }
        .mm-price-change {
            font-size: 0.95rem;
            font-weight: 600;
            margin-left: 8px;
        }
        .mm-meta-row {
            color: var(--mm-text-secondary);
            font-size: 0.9rem;
            margin-top: 4px;
        }

        .mm-news-item {
            padding: 12px 0;
            border-bottom: 1px solid var(--mm-border);
        }
        .mm-news-item:last-child { border-bottom: none; }
        .mm-news-headline {
            font-weight: 600;
            font-size: 0.95rem;
            color: var(--mm-text-primary);
            text-decoration: none;
        }
        .mm-news-meta {
            font-size: 0.78rem;
            color: var(--mm-text-secondary);
            margin-top: 3px;
        }
        .mm-sentiment-badge {
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 2px 9px;
            border-radius: 999px;
            margin-left: 8px;
        }

        .mm-rating-badge {
            display: inline-block;
            font-size: 1.6rem;
            font-weight: 800;
            letter-spacing: 0.02em;
            padding: 10px 22px;
            border-radius: 12px;
        }
        .mm-confidence {
            color: var(--mm-text-secondary);
            font-size: 0.95rem;
            margin-top: 8px;
        }

        .mm-stars-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            font-size: 0.92rem;
        }
        .mm-stars {
            color: #111;
            letter-spacing: 2px;
        }

        .mm-thesis-col {
            padding: 4px 0;
        }
        .mm-thesis-title {
            font-weight: 700;
            font-size: 0.95rem;
            margin-bottom: 8px;
        }
        .mm-thesis-list li {
            margin-bottom: 6px;
            font-size: 0.9rem;
            line-height: 1.5;
        }

        div.stButton > button {
            border-radius: 999px;
            border: 1px solid var(--mm-border);
            font-weight: 600;
            padding: 6px 18px;
            transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.25s ease, color 0.25s ease, border-color 0.25s ease;
        }
        div.stButton > button:hover {
            transform: scale(1.06);
            background: linear-gradient(90deg, #ff2fb8, #a78bfa, #4dd0e1) !important;
            background-size: 200% 200% !important;
            animation: mm-gradient-flow 3s ease infinite;
            color: #ffffff !important;
            border-color: transparent !important;
            box-shadow: 0 8px 22px rgba(167, 139, 250, 0.35);
        }
        div.stButton > button:active {
            transform: scale(0.97);
        }
        /* Text inside a hovered button should stay white regardless of
           Streamlit's internal markup (p tags, spans, etc. inside button) */
        div.stButton > button:hover * {
            color: #ffffff !important;
        }

        /* ---------------------------------------------------------- */
        /* MarketMind Learn: playful accent, reserved for this space  */
        /* only — Research and Explore stay clean and neutral.        */
        /* ---------------------------------------------------------- */
        :root {
            --mm-fuschia: #d6009c;
        }

        @keyframes mm-rainbow-spin {
            0%   { background-position: 0% 50%; }
            100% { background-position: 200% 50%; }
        }

        .mm-rainbow-border {
            border-radius: 20px;
            padding: 3px;
            background: linear-gradient(90deg, #ff2fb8, #ff7a59, #ffd93d, #4dd0e1, #a78bfa, #ff2fb8);
            background-size: 300% 300%;
            animation: mm-rainbow-spin 8s linear infinite;
            margin-bottom: 16px;
        }
        .mm-rainbow-border-inner {
            background: #ffffff;
            border-radius: 17px;
            padding: 22px 24px;
        }

        /* Hover-only rainbow border wrapper — same visual as the permanent
           Learn card, but the gradient stays invisible until hovered. Used
           on Research/Explore so the whole trio shares one signature
           interaction: hover = scale up + rainbow glow appears. */
        .mm-rainbow-border-hover {
            border-radius: 20px;
            padding: 3px;
            background: linear-gradient(90deg, #ff2fb8, #ff7a59, #ffd93d, #4dd0e1, #a78bfa, #ff2fb8);
            background-size: 300% 300%;
            margin-bottom: 16px;
            opacity: 0;
            transition: opacity 0.25s ease, transform 0.25s ease;
        }
        .mm-rainbow-border-hover:hover {
            opacity: 1;
            animation: mm-rainbow-spin 8s linear infinite;
            transform: scale(1.02);
        }
        .mm-rainbow-border-hover .mm-experience-card {
            border: none;
            box-shadow: none;
        }

        .mm-experience-card {
            border-radius: 20px;
            padding: 28px 26px;
            border: 1px solid var(--mm-border);
            background: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            height: 100%;
            min-height: 230px;
            box-sizing: border-box;
            transition: transform 0.2s ease;
        }
        .mm-experience-icon {
            font-size: 2rem;
            margin-bottom: 10px;
        }
        .mm-experience-title {
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            margin-bottom: 6px;
        }
        .mm-experience-desc {
            color: var(--mm-text-secondary);
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .mm-pill-nav button {
            border-radius: 999px !important;
        }

        /* ================================================================
           MarketMind AI landing page design system
           ================================================================ */

        /* Smooth, cheap-to-render transitions used everywhere */
        .mm-card, .mm-feature-card {
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }

        /* Rainbow accent — used sparingly: focus rings, the Learn card,
           and the primary CTA. Everything else stays clean white/gray. */
        @keyframes mm-gradient-flow {
            0%   { background-position: 0% 50%; }
            50%  { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .mm-rainbow-text {
            background: linear-gradient(90deg, #ff2fb8, #ff7a59, #ffd93d, #4dd0e1, #a78bfa, #ff2fb8);
            background-size: 300% 300%;
            animation: mm-gradient-flow 6s ease infinite;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        div[data-baseweb="input"]:focus-within > div {
            border: 1px solid transparent !important;
            background-image: linear-gradient(#fff, #fff), linear-gradient(90deg, #ff2fb8, #4dd0e1, #a78bfa);
            background-origin: border-box;
            background-clip: padding-box, border-box;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.12) !important;
        }

        /* Animated background: soft floating blurred gradient blobs, CSS-only.
           Kept behind content (z-index -1) and cheap to render — only
           transform/opacity are animated, both GPU-friendly. */
        .mm-hero-bg {
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 640px;
            overflow: hidden;
            z-index: -1;
            pointer-events: none;
        }
        .mm-blob {
            position: absolute;
            border-radius: 50%;
            filter: blur(70px);
            opacity: 0.35;
        }
        @keyframes mm-float-1 {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(40px, 30px); }
        }
        @keyframes mm-float-2 {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(-30px, 40px); }
        }
        @keyframes mm-float-3 {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(20px, -30px); }
        }
        .mm-blob-1 {
            width: 380px; height: 380px; top: -80px; left: 5%;
            background: linear-gradient(135deg, #a78bfa, #4dd0e1);
            animation: mm-float-1 14s ease-in-out infinite;
        }
        .mm-blob-2 {
            width: 320px; height: 320px; top: 60px; right: 8%;
            background: linear-gradient(135deg, #ff7a59, #ffd93d);
            animation: mm-float-2 16s ease-in-out infinite;
        }
        .mm-blob-3 {
            width: 260px; height: 260px; top: 260px; left: 38%;
            background: linear-gradient(135deg, #ff2fb8, #a78bfa);
            animation: mm-float-3 12s ease-in-out infinite;
        }

        /* Staggered fade-in-on-load. Streamlit re-renders the whole page on
           every interaction, so a true scroll-triggered reveal (which needs
           IntersectionObserver JS — not reliably executable inside
           st.markdown) isn't practical here without extra plumbing. This is
           the honest, working substitute: everything gracefully fades up
           the moment its section renders. */
        @keyframes mm-fade-up {
            from { opacity: 0; transform: translateY(14px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        .mm-fade { animation: mm-fade-up 0.6s ease both; }
        .mm-fade-1 { animation-delay: 0.05s; }
        .mm-fade-2 { animation-delay: 0.15s; }
        .mm-fade-3 { animation-delay: 0.25s; }
        .mm-fade-4 { animation-delay: 0.35s; }

        /* Hero */
        .mm-hero-wrap {
            position: relative;
            min-height: 78vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 2rem 1rem;
        }
        .mm-hero-logo {
            font-size: 4rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.4rem;
        }
        .mm-hero-tagline {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--mm-text-primary);
            margin-bottom: 1rem;
            letter-spacing: -0.01em;
        }
        .mm-hero-desc {
            max-width: 620px;
            color: var(--mm-text-secondary);
            font-size: 1.05rem;
            line-height: 1.6;
            margin: 0 auto 2rem auto;
        }
        .mm-cta-row {
            display: flex;
            gap: 14px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .mm-cta-primary {
            display: inline-block;
            padding: 14px 32px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 1rem;
            text-decoration: none;
            color: #ffffff;
            background: linear-gradient(90deg, #ff2fb8, #a78bfa, #4dd0e1);
            background-size: 200% 200%;
            animation: mm-gradient-flow 6s ease infinite;
            box-shadow: 0 4px 16px rgba(167, 139, 250, 0.35);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }
        .mm-cta-secondary {
            display: inline-block;
            padding: 14px 32px;
            border-radius: 999px;
            font-weight: 600;
            font-size: 1rem;
            text-decoration: none;
            color: var(--mm-text-primary);
            border: 1px solid var(--mm-border);
            background: #ffffff;
            transition: transform 0.18s ease, border-color 0.18s ease;
        }
        .mm-cta-secondary:hover {
            transform: scale(1.03);
            border-color: #a78bfa;
        }
        .mm-cta-note {
            display: block;
            margin-top: 6px;
            font-size: 0.75rem;
            color: var(--mm-text-secondary);
        }

        /* Section scaffolding */
        .mm-section {
            max-width: 1360px;
            margin: 0 auto;
            padding: 4rem 1rem;
        }
        .mm-section-narrow {
            max-width: 720px;
            margin: 0 auto;
            padding: 3rem 1rem;
            text-align: center;
        }
        .mm-eyebrow {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--mm-text-secondary);
            text-align: center;
            margin-bottom: 0.6rem;
        }
        .mm-h2 {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            text-align: center;
            margin-bottom: 0.8rem;
        }
        .mm-h2-desc {
            text-align: center;
            color: var(--mm-text-secondary);
            font-size: 1.02rem;
            line-height: 1.6;
            max-width: 640px;
            margin: 0 auto 2.4rem auto;
        }

        /* Feature cards */
        .mm-feature-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }
        @media (max-width: 900px) {
            .mm-feature-grid { grid-template-columns: repeat(2, 1fr); }
        }
        .mm-feature-card {
            background: #ffffff;
            border: 1px solid var(--mm-border);
            border-radius: 16px;
            padding: 22px 20px;
        }
        .mm-feature-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 28px rgba(0,0,0,0.07);
            border-color: #d8d4fb;
        }
        .mm-feature-icon {
            font-size: 1.5rem;
            margin-bottom: 10px;
        }
        .mm-feature-title {
            font-weight: 700;
            font-size: 0.95rem;
            margin-bottom: 4px;
        }
        .mm-feature-desc {
            font-size: 0.82rem;
            color: var(--mm-text-secondary);
            line-height: 1.5;
        }

        /* Timeline */
        .mm-timeline {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 2rem;
        }
        .mm-timeline-step {
            background: #ffffff;
            border: 1px solid var(--mm-border);
            border-radius: 14px;
            padding: 18px 26px;
            text-align: center;
            min-width: 150px;
        }
        .mm-timeline-step:hover {
            transform: translateY(-3px);
            border-color: #d8d4fb;
        }
        .mm-timeline-num {
            font-size: 0.72rem;
            font-weight: 700;
            color: #a78bfa;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }
        .mm-timeline-label {
            font-weight: 700;
            font-size: 0.95rem;
        }
        .mm-timeline-arrow {
            font-size: 1.3rem;
            color: var(--mm-border);
        }

        /* Trusted sources */
        .mm-source-row {
            display: flex;
            justify-content: center;
            gap: 14px;
            flex-wrap: wrap;
        }
        .mm-source-badge {
            padding: 10px 20px;
            border-radius: 999px;
            border: 1px solid var(--mm-border);
            font-weight: 600;
            font-size: 0.85rem;
            color: var(--mm-text-secondary);
            background: #fafafa;
        }

        /* Creator section */
        .mm-creator-card {
            max-width: 640px;
            margin: 0 auto;
            background: #fafafa;
            border: 1px solid var(--mm-border);
            border-radius: 20px;
            padding: 32px;
            text-align: center;
        }
        .mm-creator-avatar {
            width: 64px; height: 64px;
            border-radius: 50%;
            background: linear-gradient(135deg, #ff2fb8, #a78bfa, #4dd0e1);
            margin: 0 auto 14px auto;
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; color: #fff; font-size: 1.4rem;
        }
        .mm-creator-name {
            font-weight: 800;
            font-size: 1.15rem;
        }
        .mm-creator-role {
            color: var(--mm-text-secondary);
            font-size: 0.88rem;
            margin-bottom: 12px;
        }
        .mm-creator-bio {
            font-size: 0.92rem;
            line-height: 1.6;
            color: var(--mm-text-primary);
        }

        /* Footer */
        .mm-footer {
            border-top: 1px solid var(--mm-border);
            margin-top: 3rem;
            padding: 2.5rem 1rem 1.5rem 1rem;
            text-align: center;
        }
        .mm-footer-links {
            display: flex;
            justify-content: center;
            gap: 24px;
            flex-wrap: wrap;
            margin-bottom: 14px;
            font-size: 0.88rem;
        }
        .mm-footer-links a {
            color: var(--mm-text-secondary);
            text-decoration: none;
        }
        .mm-footer-links a:hover {
            color: var(--mm-text-primary);
        }
        .mm-footer-version {
            font-size: 0.75rem;
            color: var(--mm-text-secondary);
        }

        /* Staged loader: clean solid-color progress bar + narrated caption,
           inspired by "AI pipeline stage" loading UX. Several selectors
           are targeted since Streamlit's internal progress-bar DOM
           structure has shifted across versions — if your installed
           version doesn't match, the bar still works, it just keeps
           Streamlit's default fill. */
        div[data-testid="stProgress"] > div > div {
            background: #f2f2f2 !important;
            border-radius: 999px !important;
            height: 6px !important;
        }
        div[data-testid="stProgress"] > div > div > div {
            background: var(--mm-text-primary) !important;
            border-radius: 999px !important;
        }
        .mm-loader-caption {
            font-size: 0.85rem;
            color: var(--mm-text-secondary);
            margin-top: 6px;
            font-weight: 500;
        }

        /* Sticky glassmorphism nav — real position:sticky, always present
           from the top rather than JS-triggered "appear after N px
           scrolled" (that exact behavior needs scroll-listener JS, which
           Streamlit's HTML renderer strips). The blur means it reads as
           part of the hero at the very top and becomes a clean glass bar
           once whiter content scrolls underneath it. */
        .mm-topnav {
            position: sticky;
            top: 0;
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 22px;
            margin: 0 auto 1rem auto;
            max-width: 1360px;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.65);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(234, 234, 234, 0.8);
        }
        .mm-topnav-logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 800;
            font-size: 1.05rem;
            text-decoration: none;
            color: var(--mm-text-primary);
        }
        .mm-logo-mark {
            width: 28px; height: 28px;
            border-radius: 8px;
            background: linear-gradient(135deg, #ff2fb8, #a78bfa, #4dd0e1);
            display: flex; align-items: center; justify-content: center;
            color: #fff; font-weight: 800; font-size: 0.85rem;
            flex-shrink: 0;
        }
        .mm-topnav-links {
            display: flex;
            align-items: center;
            gap: 22px;
        }
        .mm-topnav-links a {
            font-size: 0.88rem;
            font-weight: 600;
            color: var(--mm-text-secondary);
            text-decoration: none;
        }
        .mm-topnav-links a:hover {
            color: var(--mm-text-primary);
        }
        .mm-topnav-cta {
            padding: 8px 18px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.85rem;
            color: #fff;
            text-decoration: none;
            background: linear-gradient(90deg, #ff2fb8, #a78bfa, #4dd0e1);
            background-size: 200% 200%;
            animation: mm-gradient-flow 6s ease infinite;
        }

        /* Stronger glow on the primary CTA — the "expensive" detail */
        .mm-cta-primary:hover {
            transform: scale(1.04);
            box-shadow: 0 0 0 1px rgba(255,255,255,0.4) inset,
                        0 8px 20px rgba(255, 47, 184, 0.25),
                        0 8px 28px rgba(167, 139, 250, 0.35),
                        0 8px 28px rgba(77, 208, 225, 0.25);
        }

        .mm-social-proof {
            margin-top: 0.6rem;
            font-size: 0.85rem;
            color: var(--mm-text-secondary);
            font-weight: 500;
        }

        /* Product showcase (screenshots) */
        .mm-showcase-placeholder {
            aspect-ratio: 16 / 10;
            border-radius: 14px;
            background: linear-gradient(135deg, #fafafa, #f2f2f2);
            border: 1px dashed var(--mm-border);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--mm-text-secondary);
            font-size: 0.85rem;
            text-align: center;
            padding: 1rem;
        }

        /* Final CTA band */
        .mm-final-cta {
            text-align: center;
            background: linear-gradient(135deg, #fdf2ff, #f2f9ff);
            border-radius: 24px;
            padding: 3.5rem 1.5rem;
            margin: 1rem auto 2rem auto;
            max-width: 1360px;
        }
        .mm-final-cta .mm-h2 { margin-bottom: 0.4rem; }
        </style>
        """), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Experience switcher (Research / Learn / Explore)
# ----------------------------------------------------------------------

def render_main_nav(experience: str | None, page: str, watchlist_count: int = 0, portfolio_count: int = 0) -> None:
    """
    One single nav row for the whole app, replacing what used to be two
    stacked rows (top-level experience switcher + a second Research-only
    sub-nav). Logo on the left, the three experiences always visible in
    the middle, and — only while inside Research — a couple of smaller,
    visually lighter secondary links on the right so they don't compete
    for attention with the three main experiences.
    """
    if experience == "research":
        logo_col, r_col, l_col, e_col, watch_col, portfolio_col = st.columns([2.4, 1.6, 1.6, 1.6, 1.5, 1.5])
    else:
        logo_col, r_col, l_col, e_col = st.columns([3, 2, 2, 2])

    with logo_col:
        if st.button("MarketMind", key="nav_logo"):
            st.session_state["experience"] = None
            st.session_state["page"] = "home"
            st.rerun()
    with r_col:
        if st.button("📈 Research", key="nav_research", use_container_width=True,
                     type="primary" if experience == "research" else "secondary"):
            st.session_state["experience"] = "research"
            st.session_state["page"] = "home"
            st.rerun()
    with l_col:
        if st.button("🎓 Learn", key="nav_learn", use_container_width=True,
                     type="primary" if experience == "learn" else "secondary"):
            st.session_state["experience"] = "learn"
            st.rerun()
    with e_col:
        if st.button("🔍 Explore", key="nav_explore", use_container_width=True,
                     type="primary" if experience == "explore" else "secondary"):
            st.session_state["experience"] = "explore"
            st.rerun()

    if experience == "research":
        with watch_col:
            label = f"★ ({watchlist_count})" if watchlist_count else "☆ Watchlist"
            if st.button(label, key="nav_watchlist", use_container_width=True,
                         type="primary" if page == "watchlist" else "secondary"):
                st.session_state["page"] = "watchlist"
                st.rerun()
        with portfolio_col:
            label = f"Portfolio ({portfolio_count})" if portfolio_count else "Portfolio"
            if st.button(label, key="nav_portfolio", use_container_width=True,
                         type="primary" if page == "portfolio" else "secondary"):
                st.session_state["page"] = "portfolio"
                st.rerun()

    st.markdown(_html("<div style='height:8px'></div>"), unsafe_allow_html=True)


def _render_product_showcase(image_filename: str, title: str, description: str, button_label: str, experience_key: str) -> None:
    """
    One product's screenshot row: title, screenshot (or an honest
    placeholder if the file hasn't been added yet), description, and a
    real 'Learn More' button that switches straight into that experience.

    Drop actual screenshots into a `screenshots/` folder next to app.py,
    named research.png / learn.png / explore.png, and they'll show up
    here automatically — no code changes needed.
    """
    st.markdown(_html(f"<div class='mm-h2' style='font-size:1.3rem; text-align:left; margin-top:2.5rem;'>{title}</div>"), unsafe_allow_html=True)

    image_path = Path(__file__).parent / "screenshots" / image_filename
    if image_path.exists():
        with st.container(border=True):
            st.image(str(image_path), use_container_width=True)
    else:
        st.markdown(_html(f"""
            <div class="mm-showcase-placeholder">
                <div style="font-size:1.6rem; margin-bottom:6px;">🖼️</div>
                <div>Add <code>screenshots/{image_filename}</code> next to app.py to show a real screenshot here.</div>
            </div>
            """), unsafe_allow_html=True)

    st.markdown(_html(f"<div style='color:var(--mm-text-secondary); font-size:0.95rem; margin:10px 0 12px 0;'>{description}</div>"), unsafe_allow_html=True)
    if st.button(button_label, key=f"showcase_{experience_key}"):
        st.session_state["experience"] = experience_key
        if experience_key == "research":
            st.session_state["page"] = "home"
        st.rerun()


def render_landing_page() -> None:
    """
    The full marketing landing page — sticky nav, hero, animated background,
    product cards, explainer sections, screenshots, feature grid, final CTA,
    and footer. This replaces the old bare three-card chooser as the very
    first screen someone sees.
    """
    # --- Sticky glassmorphism nav ---------------------------------------
    st.markdown(_html("""
        <div class="mm-topnav">
            <a href="#" class="mm-topnav-logo">
                <div class="mm-logo-mark">M</div>
                MarketMind AI
            </a>
            <div class="mm-topnav-links">
                <a href="#mm-products">Research</a>
                <a href="#mm-products">Learn</a>
                <a href="#mm-products">Explore</a>
                <a href="#mm-about">About</a>
                <a href="https://github.com" target="_blank">GitHub</a>
            </div>
            <a href="#mm-products" class="mm-topnav-cta">Get Started</a>
        </div>
        """), unsafe_allow_html=True)

    # --- Hero ---------------------------------------------------------
    st.markdown(_html("""
        <div class="mm-hero-wrap mm-fade">
            <div class="mm-hero-bg">
                <div class="mm-blob mm-blob-1"></div>
                <div class="mm-blob mm-blob-2"></div>
                <div class="mm-blob mm-blob-3"></div>
            </div>
            <div class="mm-hero-logo">MarketMind <span class="mm-rainbow-text">AI</span></div>
            <div class="mm-hero-tagline">Research Smarter. Learn Faster. Invest Better.</div>
            <div class="mm-hero-desc">
                AI-powered equity research, market discovery, portfolio analysis, and investing
                education — all in one modern platform.
            </div>
            <div class="mm-cta-row">
                <a href="#mm-products" class="mm-cta-primary">Get Started</a>
                <a href="#mm-demo-note" class="mm-cta-secondary">Watch Demo</a>
            </div>
            <div class="mm-social-proof">Powered by live market data and AI-powered research</div>
        </div>
        """), unsafe_allow_html=True)

    # "Watch Demo" is an honest placeholder for now — no video exists yet.
    st.markdown(_html("""
        <div id="mm-demo-note" style="text-align:center; margin-top:-1.5rem;">
            <span class="mm-cta-note">Demo video coming soon — for now, jump straight into a product below.</span>
        </div>
        """), unsafe_allow_html=True)

    # --- Why MarketMind AI (right after the hero) ------------------------
    st.markdown(_html("""
        <div id="mm-about" class="mm-section-narrow mm-fade mm-fade-1">
            <div class="mm-eyebrow">Why another investing platform?</div>
            <div class="mm-h2" style="font-size:1.6rem;">Most platforms overwhelm beginners.</div>
            <div class="mm-h2-desc">
                Most AI tools hallucinate financial information.<br/><br/>
                MarketMind combines real market data with AI-powered research to make investing
                easier to understand.
            </div>
        </div>
        """), unsafe_allow_html=True)

    # --- Product cards --------------------------------------------------
    st.markdown(_html("<div id='mm-products'></div>"), unsafe_allow_html=True)
    st.markdown(_html("""
        <div class="mm-section mm-fade mm-fade-1">
            <div class="mm-eyebrow">Three products, one platform</div>
            <div class="mm-h2">Choose your experience</div>
        </div>
        """), unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(_html("""
            <div class="mm-experience-card">
                <div class="mm-experience-icon">📈</div>
                <div class="mm-experience-title">MarketMind Research</div>
                <div class="mm-experience-desc">Professional equity research with AI summaries, financial
                analysis, competitor insights, news sentiment, portfolio analysis, and institutional-style
                reports.</div>
            </div>
            """), unsafe_allow_html=True)
        if st.button("Enter Research", key="choose_research", use_container_width=True, type="primary"):
            st.session_state["experience"] = "research"
            st.session_state["page"] = "home"
            st.rerun()

    with col2:
        st.markdown(_html("""
            <div class="mm-rainbow-border">
                <div class="mm-rainbow-border-inner mm-experience-card" style="border:none; box-shadow:none;">
                    <div class="mm-experience-icon">🎓</div>
                    <div class="mm-experience-title">MarketMind Learn</div>
                    <div class="mm-experience-desc">Interactive investing education with lessons, quizzes,
                    AI explanations, achievements, and a live $5,000 virtual portfolio.</div>
                </div>
            </div>
            """), unsafe_allow_html=True)
        if st.button("Enter Learn", key="choose_learn", use_container_width=True, type="primary"):
            st.session_state["experience"] = "learn"
            st.rerun()

    with col3:
        st.markdown(_html("""
            <div class="mm-experience-card">
                <div class="mm-experience-icon">🔍</div>
                <div class="mm-experience-title">MarketMind Explore</div>
                <div class="mm-experience-desc">Discover sectors, trending stocks, ETFs, market movers,
                earnings, and investment opportunities.</div>
            </div>
            """), unsafe_allow_html=True)
        if st.button("Enter Explore", key="choose_explore", use_container_width=True, type="primary"):
            st.session_state["experience"] = "explore"
            st.rerun()

    # --- How it works timeline -------------------------------------------
    st.markdown(_html("""
        <div class="mm-section mm-fade mm-fade-2" style="padding-top:1rem;">
            <div class="mm-eyebrow">How it works</div>
            <div class="mm-h2">From a ticker to a decision</div>
            <div class="mm-timeline">
                <div class="mm-timeline-step">
                    <div class="mm-timeline-num">STEP 1</div>
                    <div class="mm-timeline-label">Search</div>
                </div>
                <div class="mm-timeline-arrow">→</div>
                <div class="mm-timeline-step">
                    <div class="mm-timeline-num">STEP 2</div>
                    <div class="mm-timeline-label">Analyze</div>
                </div>
                <div class="mm-timeline-arrow">→</div>
                <div class="mm-timeline-step">
                    <div class="mm-timeline-num">STEP 3</div>
                    <div class="mm-timeline-label">Understand</div>
                </div>
                <div class="mm-timeline-arrow">→</div>
                <div class="mm-timeline-step">
                    <div class="mm-timeline-num">STEP 4</div>
                    <div class="mm-timeline-label">Invest Smarter</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    # --- Features grid ----------------------------------------------------
    features = [
        ("🧠", "AI Equity Research", "Executive summaries and investment theses generated from live company data."),
        ("📡", "Live Market Data", "Real-time prices, charts, and fundamentals pulled straight from the market."),
        ("📊", "Portfolio Analysis", "Sector allocation, concentration, and diversification scoring at a glance."),
        ("💚", "Financial Health Scores", "Revenue growth, profitability, balance sheet, and valuation — rated simply."),
        ("⚖️", "Investment Thesis", "Bull case, bear case, catalysts, and risks laid out side by side."),
        ("📰", "News Sentiment", "Headlines scored positive, neutral, or negative, from real financial feeds."),
        ("🥊", "Competitor Analysis", "See how a company stacks up against its closest peers."),
        ("📈", "Interactive Charts", "Zoomable price history across 1D to 5Y, styled to stay out of your way."),
        ("💵", "Virtual Portfolio", "Practice investing with $5,000 in virtual cash and real market prices."),
        ("🎓", "Investing Lessons", "Bite-sized lessons on the concepts that actually matter."),
        ("🏆", "Achievements", "Milestones and badges that make learning to invest feel like progress."),
        ("🔍", "Market Discovery", "Browse sectors, ETFs, and trending names without needing a ticker in mind."),
    ]
    cards_html = "".join(f"""
        <div class="mm-feature-card">
            <div class="mm-feature-icon">{icon}</div>
            <div class="mm-feature-title">{title}</div>
            <div class="mm-feature-desc">{desc}</div>
        </div>
        """ for icon, title, desc in features)
    st.markdown(_html(f"""
        <div class="mm-section mm-fade mm-fade-2">
            <div class="mm-eyebrow">Everything in one place</div>
            <div class="mm-h2">Built for how people actually research stocks</div>
            <div style="height:1.5rem;"></div>
            <div class="mm-feature-grid">{cards_html}</div>
        </div>
        """), unsafe_allow_html=True)

    # --- Trusted data sources ----------------------------------------------
    st.markdown(_html("""
        <div class="mm-section-narrow mm-fade mm-fade-3">
            <div class="mm-eyebrow">Powered by real data</div>
            <div class="mm-source-row">
                <span class="mm-source-badge">Yahoo Finance</span>
                <span class="mm-source-badge">SEC Filings</span>
                <span class="mm-source-badge">Financial News APIs</span>
                <span class="mm-source-badge">OpenAI</span>
                <span class="mm-source-badge">+ more soon</span>
            </div>
        </div>
        """), unsafe_allow_html=True)

    # --- Meet the creator ----------------------------------------------------
    st.markdown(_html("""
        <div class="mm-section-narrow mm-fade mm-fade-3">
            <div class="mm-eyebrow">Meet the Creator</div>
            <div class="mm-creator-card">
                <div class="mm-creator-avatar">NC</div>
                <div class="mm-creator-name">Nikhil Channamraju</div>
                <div class="mm-creator-role">Computer Science + Pre-Business · UNC Chapel Hill</div>
                <div class="mm-creator-bio">
                    Passionate about AI, finance, and building modern software. Built MarketMind AI to
                    combine artificial intelligence with professional-quality equity research, while
                    making investing more accessible to everyone.
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    # --- Final CTA --------------------------------------------------------
    st.markdown(_html("""
        <div class="mm-final-cta mm-fade mm-fade-4">
            <div class="mm-h2">Ready to research smarter?</div>
            <div class="mm-h2-desc">Start using MarketMind AI today.</div>
        </div>
        """), unsafe_allow_html=True)
    _, cta_col, _ = st.columns([2, 1, 2])
    with cta_col:
        if st.button("Launch Research", key="final_cta_launch", use_container_width=True, type="primary"):
            st.session_state["experience"] = "research"
            st.session_state["page"] = "home"
            st.rerun()

    # --- Footer ----------------------------------------------------------
    st.markdown(_html("""
        <div class="mm-footer mm-fade mm-fade-4">
            <div class="mm-footer-links">
                <a href="#mm-products">Research</a>
                <a href="#mm-products">Learn</a>
                <a href="#mm-products">Explore</a>
                <a href="https://github.com" target="_blank">GitHub</a>
                <a href="https://linkedin.com" target="_blank">LinkedIn</a>
                <a href="mailto:hello@marketmind.ai">Contact</a>
            </div>
            <div class="mm-footer-version">MarketMind AI · v3.0</div>
        </div>
        """), unsafe_allow_html=True)


# Backwards-compatible alias — older code / notes may still reference the
# original name.
render_experience_chooser = render_landing_page



# ----------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------

def render_nav_bar(current_page: str, watchlist_count: int, portfolio_count: int = 0) -> None:
    """Research experience's internal nav — Explore and Learn have moved
    out to the top-level experience switcher, so this only needs Home/
    Watchlist/Portfolio now."""
    logo_col, watch_col, portfolio_col = st.columns([5, 2, 2])
    with logo_col:
        if st.button("MarketMind Research", key="nav_home", type="secondary"):
            st.session_state["page"] = "home"
            st.session_state["ticker"] = None
            st.rerun()
    with watch_col:
        label = f"★ Watchlist ({watchlist_count})" if watchlist_count else "☆ Watchlist"
        if st.button(label, key="nav_watchlist", use_container_width=True,
                     type="primary" if current_page == "watchlist" else "secondary"):
            st.session_state["page"] = "watchlist"
            st.rerun()
    with portfolio_col:
        label = f"Portfolio ({portfolio_count})" if portfolio_count else "Portfolio"
        if st.button(label, key="nav_portfolio", use_container_width=True,
                     type="primary" if current_page == "portfolio" else "secondary"):
            st.session_state["page"] = "portfolio"
            st.rerun()
    st.markdown(_html("<div style='height:8px'></div>"), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Watchlist page
# ----------------------------------------------------------------------

def render_watchlist_page(rows: list[dict]) -> None:
    render_section_title("Your Watchlist")

    if not rows:
        st.markdown(_html(
            "<div class='mm-card'>Your watchlist is empty. Search a company and tap "
            "\u201cAdd to Watchlist\u201d on its page to save it here.</div>"
        ), unsafe_allow_html=True)
        return

    for row in rows:
        c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
        with c1:
            st.markdown(_html(f"""
                <div style="padding-top:10px;">
                    <span style="font-weight:700; font-family:'IBM Plex Mono', monospace;">{row['ticker']}</span>
                    <span style="color:var(--mm-text-secondary); margin-left:8px;">{row['name']}</span>
                </div>
                """), unsafe_allow_html=True)
        with c2:
            color = pct_change_color(row["pct_change"])
            arrow = "▲" if (row["pct_change"] or 0) >= 0 else "▼"
            price_str = format_currency(row["price"]) if row["price"] else "—"
            pct_str = format_percent(row["pct_change"]) if row["pct_change"] is not None else "—"
            st.markdown(_html(f"""
                <div style="padding-top:10px; text-align:right;">
                    <span style="font-weight:600;">{price_str}</span>
                    <span style="color:{color}; font-weight:700; margin-left:6px;">{arrow} {pct_str}</span>
                </div>
                """), unsafe_allow_html=True)
        with c3:
            if st.button("View", key=f"view_{row['ticker']}", use_container_width=True):
                st.session_state["ticker"] = row["ticker"]
                st.session_state["page"] = "company"
                st.session_state["price_range"] = "1Y"
                st.rerun()
        with c4:
            if st.button("Remove", key=f"remove_{row['ticker']}", use_container_width=True):
                from data import remove_from_watchlist
                remove_from_watchlist(row["ticker"])
                st.rerun()


# ----------------------------------------------------------------------
# Home page
# ----------------------------------------------------------------------

def render_home_hero() -> str | None:
    st.markdown(_html("<div style='height: 4vh'></div>"), unsafe_allow_html=True)
    st.markdown(_html("<div class='mm-logo'>MarketMind</div>"), unsafe_allow_html=True)
    st.markdown(_html("<div class='mm-subtitle'>AI-Powered Equity Research</div>"), unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        query = st.text_input(
            "search", placeholder="Search Apple, NVIDIA, Tesla...",
            label_visibility="collapsed", key="home_search",
        )
    return query.strip() if query else None


def render_market_pulse(summary_text: str) -> None:
    render_section_title("Today's Market")
    st.markdown(_html(f"<div class='mm-card'>{summary_text}</div>"), unsafe_allow_html=True)


def render_index_cards(indices: list[dict]) -> None:
    render_section_title("Markets")
    if not indices:
        st.markdown(_html("<div class='mm-card'>Market data unavailable right now.</div>"), unsafe_allow_html=True)
        return

    cols = st.columns(len(indices))
    for col, idx in zip(cols, indices):
        color = pct_change_color(idx["pct_change"])
        arrow = "▲" if (idx["pct_change"] or 0) >= 0 else "▼"
        with col:
            st.markdown(_html(f"""
                <div class="mm-metric-card">
                    <div class="mm-metric-label">{idx['name']}</div>
                    <div class="mm-metric-value">{format_currency(idx['price'], decimals=0) if idx['price'] and idx['price'] > 1000 else format_ratio(idx['price'])}</div>
                    <div class="mm-metric-delta" style="color:{color}">{arrow} {format_percent(idx['pct_change'])}</div>
                </div>
                """), unsafe_allow_html=True)


def render_sector_performance(sectors: list[dict]) -> None:
    render_section_title("Sector Performance")
    if not sectors:
        st.markdown(_html("<div class='mm-card'>Sector data unavailable right now.</div>"), unsafe_allow_html=True)
        return

    max_abs = max((abs(s["pct_change"] or 0) for s in sectors), default=0.01) or 0.01
    rows = ""
    for s in sectors:
        pct = s["pct_change"] or 0
        color = pct_change_color(pct)
        width_pct = min(100, (abs(pct) / max_abs) * 100)
        # bar grows from center-left, red bars implicitly shown via color, not direction
        rows += f"""
        <div style="display:flex; align-items:center; justify-content:space-between; padding:9px 0; border-bottom:1px solid var(--mm-border);">
            <span style="font-size:0.9rem; font-weight:600; width:200px;">{s['sector']}</span>
            <div style="flex:1; background:#f2f2f2; border-radius:6px; height:8px; margin:0 14px; overflow:hidden;">
                <div style="width:{width_pct:.0f}%; background:{color}; height:100%; border-radius:6px;"></div>
            </div>
            <span style="font-size:0.9rem; font-weight:700; color:{color}; width:70px; text-align:right;">{format_percent(pct)}</span>
        </div>
        """
    st.markdown(_html(f"<div class='mm-card'>{rows}</div>"), unsafe_allow_html=True)


def _mover_row(ticker: str, name: str, price: float, pct: float) -> str:
    color = pct_change_color(pct)
    arrow = "▲" if pct >= 0 else "▼"
    return f"""
    <div style="display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-bottom:1px solid var(--mm-border);">
        <div>
            <span style="font-weight:700; font-family:'IBM Plex Mono', monospace; font-size:0.85rem;">{ticker}</span>
            <span style="color:var(--mm-text-secondary); font-size:0.82rem; margin-left:8px;">{name}</span>
        </div>
        <div style="text-align:right;">
            <span style="font-weight:600; font-size:0.9rem;">{format_currency(price)}</span>
            <span style="color:{color}; font-weight:700; font-size:0.85rem; margin-left:8px;">{arrow} {format_percent(pct)}</span>
        </div>
    </div>
    """


def render_movers(movers: dict) -> None:
    render_section_title("Market Movers")
    tab1, tab2, tab3 = st.tabs(["Biggest Gainers", "Biggest Losers", "Most Active"])

    with tab1:
        rows = "".join(_mover_row(r["ticker"], r["name"], r["price"], r["pct_change"]) for r in movers["gainers"])
        st.markdown(_html(f"<div class='mm-card'>{rows or 'No data available.'}</div>"), unsafe_allow_html=True)
    with tab2:
        rows = "".join(_mover_row(r["ticker"], r["name"], r["price"], r["pct_change"]) for r in movers["losers"])
        st.markdown(_html(f"<div class='mm-card'>{rows or 'No data available.'}</div>"), unsafe_allow_html=True)
    with tab3:
        rows = "".join(_mover_row(r["ticker"], r["name"], r["price"], r["pct_change"]) for r in movers["most_active"])
        st.markdown(_html(f"<div class='mm-card'>{rows or 'No data available.'}</div>"), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Company header
# ----------------------------------------------------------------------

def render_company_header(info: dict, ticker: str, price: float | None, pct_change: float | None) -> None:
    name = safe_get(info, "longName", ticker)
    exchange = safe_get(info, "exchange", "—")
    sector = safe_get(info, "sector", "—")
    industry = safe_get(info, "industry", "—")
    color = pct_change_color(pct_change)
    arrow = "▲" if (pct_change or 0) >= 0 else "▼"

    st.markdown(_html(f"""
        <div class="mm-card">
            <div class="mm-header-row">
                <div>
                    <span class="mm-company-name">{name}</span>
                    <span class="mm-ticker-tag">{ticker.upper()}</span>
                </div>
                <div>
                    <span class="mm-price">{format_currency(price)}</span>
                    <span class="mm-price-change" style="color:{color}">
                        {arrow} {format_percent(abs(pct_change) if pct_change is not None else None, already_pct=False)}
                    </span>
                </div>
            </div>
            <div class="mm-meta-row">{exchange} &nbsp;·&nbsp; {sector} &nbsp;·&nbsp; {industry}</div>
        </div>
        """), unsafe_allow_html=True)


def render_company_facts(info: dict) -> None:
    facts = {
        "CEO": safe_get(info, "companyOfficers", [{}])[0].get("name", "—") if info.get("companyOfficers") else "—",
        "Employees": f"{info.get('fullTimeEmployees'):,}" if info.get("fullTimeEmployees") else "—",
        "Country": safe_get(info, "country", "—"),
        "Website": safe_get(info, "website", "—"),
    }
    cols = st.columns(4)
    for col, (label, value) in zip(cols, facts.items()):
        with col:
            st.markdown(_html(f"""<div class="mm-metric-card">
                    <div class="mm-metric-label">{label}</div>
                    <div class="mm-metric-value" style="font-size:0.95rem; word-break:break-word;">{value}</div>
                </div>"""), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Staged progress loader
# ----------------------------------------------------------------------
# Inspired by a "narrated" loading pattern: instead of a bare spinner, show
# a thin progress bar plus a caption that advances through named pipeline
# stages ("Initialization", "Data Retrieval", "Compilation"...). The key
# difference from a purely cosmetic version: each stage's percentage only
# advances once its real work function actually finishes, so this never
# adds artificial delay — it's genuine progress, just narrated.

class StagedLoader:
    def __init__(self):
        self._bar = st.progress(0)
        self._caption = st.empty()

    def run_stage(self, label: str, fn):
        """Renders `label` as the current stage, runs fn(), then returns
        its result. Call this once per stage, in order."""
        self._caption.markdown(
            _html(f"<div class='mm-loader-caption'>{label}</div>"),
            unsafe_allow_html=True,
        )
        result = fn()
        return result

    def advance(self, pct: int):
        self._bar.progress(min(100, max(0, pct)))

    def done(self):
        self._bar.progress(100)
        self._bar.empty()
        self._caption.empty()


def run_staged(stages: list[tuple[str, "callable"]]):
    """
    Convenience wrapper: stages is a list of (label, work_fn) pairs, run in
    order with the progress bar advancing evenly between them. Returns the
    list of results in the same order.

    Example:
        info, hist, news = run_staged([
            ("Initialization — Pulling real-time quote and identifiers...", lambda: get_ticker_info(ticker)),
            ("Data Retrieval — Fetching price history and financials...", lambda: get_price_history(ticker)),
            ("Intelligence — Scanning news and analyst sentiment...", lambda: get_news(ticker)),
        ])
    """
    loader = StagedLoader()
    results = []
    n = len(stages)
    for i, (label, fn) in enumerate(stages):
        loader.advance(int((i / n) * 100))
        results.append(loader.run_stage(label, fn))
    loader.done()
    return results


# ----------------------------------------------------------------------
# Executive summary
# ----------------------------------------------------------------------

def render_section_title(title: str) -> None:
    st.markdown(_html(f"<div class='mm-section-title'>{title}</div>"), unsafe_allow_html=True)


def render_executive_summary(summary_text: str) -> None:
    render_section_title("Executive Summary")
    st.markdown(_html(f"<div class='mm-card'>{summary_text}</div>"), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Financial snapshot
# ----------------------------------------------------------------------

def metric_card(label: str, value: str, delta: str | None = None, delta_color: str = "#6b7280") -> str:
    delta_html = f"<div class='mm-metric-delta' style='color:{delta_color}'>{delta}</div>" if delta else ""
    return f"""<div class="mm-metric-card">
        <div class="mm-metric-label">{label}</div>
        <div class="mm-metric-value">{value}</div>
        {delta_html}
    </div>"""


def render_financial_snapshot(info: dict, price: float | None, pct_change: float | None) -> None:
    render_section_title("Financial Snapshot")

    cards = [
        ("Current Price", format_currency(price)),
        ("Market Cap", format_market_cap(info.get("marketCap"))),
        ("P/E Ratio", format_ratio(info.get("trailingPE"))),
        ("EPS", format_currency(info.get("trailingEps"))),
        ("Revenue (TTM)", format_market_cap(info.get("totalRevenue"))),
        ("Dividend Yield", format_percent(info.get("dividendYield"), already_pct=True) if info.get("dividendYield") else "—"),
        ("52 Week High", format_currency(info.get("fiftyTwoWeekHigh"))),
        ("52 Week Low", format_currency(info.get("fiftyTwoWeekLow"))),
    ]

    html = "<div class='mm-metric-grid'>" + "".join(metric_card(l, v) for l, v in cards) + "</div>"
    st.markdown(_html(html), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Price chart
# ----------------------------------------------------------------------

def render_price_chart(hist_df, range_label: str) -> None:
    render_section_title("Price Chart")

    ranges = ["1D", "1M", "6M", "1Y", "5Y"]
    cols = st.columns(len(ranges))
    for c, r in zip(cols, ranges):
        with c:
            if st.button(r, key=f"range_{r}", use_container_width=True,
                         type="primary" if r == range_label else "secondary"):
                st.session_state["price_range"] = r
                st.rerun()

    if hist_df is None or hist_df.empty:
        st.markdown(_html("<div class='mm-card'>No price data available.</div>"), unsafe_allow_html=True)
        return

    line_color = "#111111"
    up = hist_df["Close"].iloc[-1] >= hist_df["Close"].iloc[0]
    line_color = "#1a8a4a" if up else "#c0392b"

    y_min = float(hist_df["Close"].min())
    y_max = float(hist_df["Close"].max())
    span = y_max - y_min
    # Guard against a near-flat series (e.g. a very quiet 1D session) so the
    # padding never collapses to zero and the chart still shows a visible band.
    if span < y_max * 0.002:
        span = y_max * 0.01
    padding = span * 0.18
    y_range = [y_min - padding, y_max + padding]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_df["Date"], y=hist_df["Close"],
        mode="lines", line=dict(color=line_color, width=2),
        fill="tozeroy", fillcolor=_hex_to_rgba(line_color, 0.08),
        hovertemplate="%{x|%b %d, %Y}<br>$%{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=340,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter", size=12, color="#6b7280"),
        xaxis=dict(showgrid=False, showline=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#f2f2f2", showline=False, zeroline=False,
                    tickprefix="$", range=y_range, autorange=False),
        hovermode="x unified",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


# ----------------------------------------------------------------------
# News intelligence
# ----------------------------------------------------------------------

def render_news_section(news_items: list[dict]) -> None:
    render_section_title("News Intelligence")

    if not news_items:
        st.markdown(_html("<div class='mm-card'>No recent news found.</div>"), unsafe_allow_html=True)
        return

    rows = ""
    for item in news_items:
        color = sentiment_color(item["sentiment"])
        rows += f"""
        <div class="mm-news-item">
            <a class="mm-news-headline" href="{item['link']}" target="_blank">{item['headline']}</a>
            <span class="mm-sentiment-badge" style="background:{color}1a; color:{color};">{item['sentiment']}</span>
            <div class="mm-news-meta">{item['source']} · {item['date']}</div>
        </div>
        """
    st.markdown(_html(f"<div class='mm-card'>{rows}</div>"), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# AI rating
# ----------------------------------------------------------------------

def render_ai_rating(rating: str, confidence: float) -> None:
    render_section_title("AI Rating")
    colors = {
        "BUY": ("#1a8a4a", "#eafaf0"),
        "HOLD": ("#b8860b", "#fdf6e3"),
        "SELL": ("#c0392b", "#fdecea"),
    }
    fg, bg = colors.get(rating, ("#6b7280", "#f2f2f2"))
    st.markdown(_html(f"""
        <div class="mm-card" style="text-align:center;">
            <span class="mm-rating-badge" style="color:{fg}; background:{bg};">{rating}</span>
            <div class="mm-confidence">Confidence: <strong>{confidence:.0f}%</strong></div>
        </div>
        """), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Financial health
# ----------------------------------------------------------------------

def render_financial_health(ratings: dict[str, float]) -> None:
    render_section_title("Financial Health")
    rows = ""
    for label, score in ratings.items():
        rows += f"""
        <div class="mm-stars-row">
            <span>{label}</span>
            <span class="mm-stars">{render_stars(score)}</span>
        </div>
        """
    st.markdown(_html(f"<div class='mm-card'>{rows}</div>"), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Investment thesis
# ----------------------------------------------------------------------

def render_investment_thesis(bull: list[str], bear: list[str], catalysts: list[str], risks: list[str]) -> None:
    render_section_title("Investment Thesis")

    def col_html(title: str, items: list[str]) -> str:
        lis = "".join(f"<li>{i}</li>" for i in items)
        return f"""<div class="mm-thesis-col">
            <div class="mm-thesis-title">{title}</div>
            <ul class="mm-thesis-list">{lis}</ul>
        </div>"""

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(_html(f"<div class='mm-card'>{col_html('Bull Case', bull)}</div>"), unsafe_allow_html=True)
        st.markdown(_html(f"<div class='mm-card'>{col_html('Catalysts', catalysts)}</div>"), unsafe_allow_html=True)
    with c2:
        st.markdown(_html(f"<div class='mm-card'>{col_html('Bear Case', bear)}</div>"), unsafe_allow_html=True)
        st.markdown(_html(f"<div class='mm-card'>{col_html('Risks', risks)}</div>"), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Competitor analysis
# ----------------------------------------------------------------------

def render_competitor_table(rows: list[dict]) -> None:
    render_section_title("Competitor Analysis")
    if not rows:
        st.markdown(_html("<div class='mm-card'>No competitor data available.</div>"), unsafe_allow_html=True)
        return

    import pandas as pd
    df = pd.DataFrame(rows)
    with st.container(border=True):
        st.dataframe(df, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------
# Explore page
# ----------------------------------------------------------------------

def render_explore_page(categories: dict[str, list[dict]]) -> None:
    render_section_title("Explore")
    tab_names = list(categories.keys())
    tabs = st.tabs(tab_names)
    for tab, name in zip(tabs, tab_names):
        with tab:
            rows = categories.get(name, [])
            if not rows:
                st.markdown(_html("<div class='mm-card'>No data available for this category right now.</div>"), unsafe_allow_html=True)
                continue
            for i in range(0, len(rows), 2):
                cols = st.columns(2)
                for col, row in zip(cols, rows[i:i + 2]):
                    with col:
                        color = pct_change_color(row["pct_change"])
                        arrow = "▲" if (row["pct_change"] or 0) >= 0 else "▼"
                        st.markdown(_html(f"""
                            <div class="mm-metric-card" style="margin-bottom:10px;">
                                <span style="font-weight:700; font-family:'IBM Plex Mono', monospace;">{row['ticker']}</span>
                                <span style="color:var(--mm-text-secondary); margin-left:6px; font-size:0.82rem;">{row['name']}</span>
                                <div style="margin-top:6px;">
                                    <span style="font-weight:600;">{format_currency(row['price'])}</span>
                                    <span style="color:{color}; font-weight:700; margin-left:8px;">{arrow} {format_percent(row['pct_change'])}</span>
                                </div>
                            </div>
                            """), unsafe_allow_html=True)
                        if st.button("View", key=f"explore_view_{name}_{row['ticker']}", use_container_width=True):
                            st.session_state["ticker"] = row["ticker"]
                            st.session_state["page"] = "company"
                            st.session_state["price_range"] = "1Y"
                            st.rerun()


# ----------------------------------------------------------------------
# Portfolio analyzer
# ----------------------------------------------------------------------

def render_portfolio_summary(total_value: float, scores: dict) -> None:
    render_section_title("Portfolio Summary")
    cards = [
        ("Total Value", format_currency(total_value)),
        ("Diversification Score", f"{scores['diversification']}/100"),
        ("Concentration Score", f"{scores['concentration']}/100"),
        ("Risk Score", f"{scores['risk']}/100"),
    ]
    html = "<div class='mm-metric-grid'>" + "".join(metric_card(l, v) for l, v in cards) + "</div>"
    st.markdown(_html(html), unsafe_allow_html=True)


def render_sector_allocation_chart(rows: list[dict]) -> None:
    render_section_title("Sector Allocation")
    sector_totals: dict[str, float] = {}
    for r in rows:
        sector_totals[r["sector"]] = sector_totals.get(r["sector"], 0) + r["market_value"]

    if not sector_totals:
        st.markdown(_html("<div class='mm-card'>No allocation data yet.</div>"), unsafe_allow_html=True)
        return

    palette = ["#111111", "#2563eb", "#6b7280", "#1a8a4a", "#c0392b",
               "#b8860b", "#8b5cf6", "#0ea5e9", "#f97316", "#14b8a6", "#94a3b8"]
    fig = go.Figure(data=[go.Pie(
        labels=list(sector_totals.keys()),
        values=list(sector_totals.values()),
        hole=0.55,
        marker=dict(colors=palette),
        textinfo="label+percent",
    )])
    fig.update_layout(
        height=360, margin=dict(l=0, r=0, t=10, b=0),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        font=dict(family="Inter", size=12),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_largest_holdings(rows: list[dict], total_value: float) -> None:
    render_section_title("Largest Holdings")
    sorted_rows = sorted(rows, key=lambda r: r["market_value"], reverse=True)
    body = ""
    for r in sorted_rows:
        weight = (r["market_value"] / total_value) if total_value else 0
        body += f"""
        <div style="display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-bottom:1px solid var(--mm-border);">
            <div>
                <span style="font-weight:700; font-family:'IBM Plex Mono', monospace;">{r['ticker']}</span>
                <span style="color:var(--mm-text-secondary); margin-left:8px; font-size:0.85rem;">{r['name']}</span>
            </div>
            <div style="text-align:right;">
                <span style="font-weight:600;">{format_currency(r['market_value'])}</span>
                <span style="color:var(--mm-text-secondary); margin-left:8px; font-size:0.85rem;">{weight*100:.1f}%</span>
            </div>
        </div>
        """
    st.markdown(_html(f"<div class='mm-card'>{body}</div>"), unsafe_allow_html=True)


def render_portfolio_insights(insights: list[str]) -> None:
    render_section_title("Portfolio Insights")
    lis = "".join(f"<li>{i}</li>" for i in insights)
    st.markdown(_html(f"<div class='mm-card'><ul class='mm-thesis-list'>{lis}</ul></div>"), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Learn: authentication
# ----------------------------------------------------------------------

def render_auth_page() -> None:
    import auth

    st.markdown(_html("""
        <div class="mm-rainbow-border" style="max-width:520px; margin:0 auto;">
            <div class="mm-rainbow-border-inner" style="text-align:center;">
                <div class="mm-logo" style="font-size:2rem;">MarketMind Learn</div>
                <div class="mm-subtitle" style="margin-bottom:0;">Learn to invest with $5,000 in virtual cash</div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        tab_login, tab_signup, tab_forgot = st.tabs(["Log In", "Sign Up", "Forgot Password"])

        with tab_login:
            with st.form("login_form"):
                identifier = st.text_input("Username or email")
                password = st.text_input("Password", type="password")
                remember = st.checkbox("Remember me (this session)")
                submitted = st.form_submit_button("Log In", use_container_width=True, type="primary")
            if submitted:
                success, message = auth.log_in(identifier, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        with tab_signup:
            with st.form("signup_form"):
                new_username = st.text_input("Username")
                new_email = st.text_input("Email")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords don't match.")
                else:
                    success, message = auth.sign_up(new_username, new_email, new_password)
                    if success:
                        st.success(message + " Head to the Log In tab.")
                    else:
                        st.error(message)

        with tab_forgot:
            st.caption(
                "This is a simplified local reset (no email is sent) — confirm your "
                "username and email, then set a new password."
            )
            with st.form("forgot_form"):
                r_username = st.text_input("Username")
                r_email = st.text_input("Email")
                r_new_password = st.text_input("New password", type="password")
                submitted = st.form_submit_button("Reset Password", use_container_width=True)
            if submitted:
                success, message = auth.reset_password(r_username, r_email, r_new_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)


def render_disclaimer_gate() -> None:
    st.markdown(_html("<div class='mm-section-title'>Before you start</div>"), unsafe_allow_html=True)
    st.markdown(_html("""
        <div class="mm-card">
            This simulator is for educational purposes only. It does not provide financial or
            investment advice. Simulated performance does not guarantee future real-world returns.
            MarketMind AI is not responsible for any financial decisions made based on information
            from this platform.
        </div>
        """), unsafe_allow_html=True)

    accepted = st.checkbox("I understand this is a simulation and not financial advice.")
    if st.button("Continue to Paper Trading", type="primary", disabled=not accepted):
        import auth
        import database as db
        user = auth.current_user()
        db.accept_disclaimer(user["id"])
        st.session_state["auth_user"]["disclaimer_accepted"] = True
        st.rerun()


# ----------------------------------------------------------------------
# Learn: virtual portfolio dashboard
# ----------------------------------------------------------------------

def render_academy_header(username: str, cash_balance: float, total_value: float) -> None:
    render_section_title(f"{username}'s Virtual Portfolio")
    cards = [
        ("Total Account Value", format_currency(total_value)),
        ("Cash Balance", format_currency(cash_balance)),
        ("Invested Value", format_currency(total_value - cash_balance)),
    ]
    html = "<div class='mm-metric-grid'>" + "".join(metric_card(l, v) for l, v in cards) + "</div>"
    st.markdown(_html(html), unsafe_allow_html=True)


def render_trade_form() -> tuple[str, str, float, bool]:
    """Renders the buy/sell form. Returns (action, ticker, shares, submitted) —
    app.py owns actually executing the trade, since that's a consequential
    side effect (moving virtual cash) that belongs outside the UI layer."""
    render_section_title("Place a Trade")
    with st.form("trade_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            ticker = st.text_input("Ticker", placeholder="e.g. AAPL")
        with c2:
            shares = st.number_input("Shares", min_value=0.0, step=1.0, format="%.2f")
        with c3:
            action = st.selectbox("Action", ["Buy", "Sell"])
        submitted = st.form_submit_button("Submit Trade", use_container_width=True, type="primary")
    return action.upper(), ticker.strip().upper(), shares, submitted


def render_holdings_table(rows: list[dict]) -> None:
    render_section_title("Your Holdings")
    if not rows:
        st.markdown(_html("<div class='mm-card'>You don't own any positions yet — place your first trade above.</div>"), unsafe_allow_html=True)
        return

    body = ""
    for r in rows:
        pl = r["unrealized_pl"]
        color = pct_change_color(pl)
        arrow = "▲" if pl >= 0 else "▼"
        body += f"""
        <div style="display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-bottom:1px solid var(--mm-border);">
            <div>
                <span style="font-weight:700; font-family:'IBM Plex Mono', monospace;">{r['ticker']}</span>
                <span style="color:var(--mm-text-secondary); margin-left:8px; font-size:0.85rem;">{r['shares']:g} sh @ avg {format_currency(r['avg_price'])}</span>
            </div>
            <div style="text-align:right;">
                <span style="font-weight:600;">{format_currency(r['market_value'])}</span>
                <span style="color:{color}; font-weight:700; margin-left:8px;">{arrow} {format_currency(abs(pl))}</span>
            </div>
        </div>
        """
    st.markdown(_html(f"<div class='mm-card'>{body}</div>"), unsafe_allow_html=True)


def render_trade_history(trades: list[dict]) -> None:
    render_section_title("Trade History")
    if not trades:
        st.markdown(_html("<div class='mm-card'>No trades yet.</div>"), unsafe_allow_html=True)
        return

    import pandas as pd
    df = pd.DataFrame([{
        "Date": t["timestamp"][:19].replace("T", " "),
        "Ticker": t["ticker"],
        "Action": t["action"],
        "Shares": t["shares"],
        "Price": t["price"],
        "Realized P/L": t["realized_pl"] if t["realized_pl"] is not None else "—",
    } for t in trades])
    with st.container(border=True):
        st.dataframe(df, use_container_width=True, hide_index=True)
