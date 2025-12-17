import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ================= CORE =================
from core.data_loader import fetch_data
from core.indicators import calc_indicators
from core.ticker_utils import normalize_ticker
from core.utils import safe_float

# ================= ANALYSIS =================
from analysis.interpretation import interpret_last
from analysis.patterns import detect_patterns
from analysis.entry_plan import generate_entry_plan
from analysis.confidence import compute_confidence
from analysis.badge import get_trade_badge

# ================= RISK =================
from risk.ladders import build_ladders
from risk.risk_management import compute_risk

# ================= UI =================
from ui.theme import load_theme
from ui.sidebar import sidebar_inputs


# ================= PAGE =================
load_theme()
st.markdown("## 📊 Tarik Saham – ADP")

(
    raw_ticker,
    period,
    interval,
    capital,
    risk_pct,
    lot_size,
    analyze_btn
) = sidebar_inputs()

# ================= STATE =================
if "run_analysis" not in st.session_state:
    st.session_state.run_analysis = False

if analyze_btn:
    st.session_state.run_analysis = True

# ================= ANALYZE ONCE =================
if st.session_state.run_analysis:

    ticker = normalize_ticker(raw_ticker)
    df = fetch_data(ticker, period, interval)

    if df.empty:
        st.error("Data kosong / ticker tidak valid.")
        st.stop()

    df_ind = calc_indicators(df)
    last_full = df_ind.iloc[-1]

    close_price = safe_float(last_full.get("Close"))
    close_text = f"{close_price:.2f}" if not np.isnan(close_price) else "-"

    # ===== FULL ANALYSIS (ONCE) =====
    desc_full = interpret_last(last_full)
    patterns_full = detect_patterns(df_ind)
    plan_full = generate_entry_plan(df_ind)
    conf_full = compute_confidence(df_ind, last_full, desc_full, patterns_full, plan_full)
    risk_full = compute_risk(capital, risk_pct, lot_size, plan_full, close_price)

    # ===== MULTI WINDOW ANALYSIS =====
    windows = [30, 60, 120]
    window_results = {}

    for w in windows:
        df_w = df_ind.tail(min(w, len(df_ind))).copy()
        last_w = df_w.iloc[-1]

        desc_w = interpret_last(last_w)
        patterns_w = detect_patterns(df_w)

        badge_w, _ = get_trade_badge(
            conf_full["score"],
            plan_full.get("status"),
            desc_w.get("Trend EMA")
        )

        window_results[w] = {
            "desc": desc_w,
            "patterns": patterns_w,
            "badge": badge_w,
            "df": df_w
        }

    # ===== CONSENSUS BADGE =====
    badge_values = [window_results[w]["badge"] for w in windows]

    if badge_values.count("BUY") >= 2:
        consensus = "BUY"
    elif badge_values.count("AVOID") >= 2:
        consensus = "AVOID"
    else:
        consensus = "WAIT"

    # ================= HEADER =================
    st.caption(
        f"**{ticker}** | {period} | {interval} | "
        f"Close: **{close_text}**"
    )

    if consensus == "BUY":
        st.success("🟢 **CONSENSUS BUY** – Mayoritas window mendukung.")
    elif consensus == "WAIT":
        st.warning("🟡 **CONSENSUS WAIT** – Belum sinkron.")
    else:
        st.error("🔴 **CONSENSUS AVOID** – Risiko dominan.")

    # ================= WINDOW BADGES =================
    st.markdown("### 🚦 Signal per Window")

    b1, b2, b3 = st.columns(3)
    b1.metric("30 Candle", window_results[30]["badge"])
    b2.metric("60 Candle", window_results[60]["badge"])
    b3.metric("120 Candle", window_results[120]["badge"])

    # ================= ZOOM SLIDER =================
    st.markdown("### 🔍 Chart Window")
    zoom_window = st.select_slider(
        "Pilih window chart",
        options=[30, 60, 120],
        value=30
    )

    df_chart = window_results[zoom_window]["df"]

    # ================= PRICE CHART =================
    chart_df = df_chart.reset_index()
    chart_df = chart_df.rename(columns={chart_df.columns[0]: "Date"})

    price_line = (
        alt.Chart(chart_df)
        .mark_line(color="#1f77b4", strokeWidth=2)
        .encode(x="Date:T", y="Close:Q")
    )

    ema20 = (
        alt.Chart(chart_df)
        .mark_line(color="#22c55e", strokeDash=[4, 2])
        .encode(x="Date:T", y="EMA20:Q")
    )

    ema50 = (
        alt.Chart(chart_df)
        .mark_line(color="#ef4444", strokeDash=[6, 3])
        .encode(x="Date:T", y="EMA50:Q")
    )

    layers = [price_line, ema20, ema50]

    if plan_full.get("status") != "No Trade":
        entry_band = (
            alt.Chart(pd.DataFrame({
                "y1": [plan_full["entry_low"]],
                "y2": [plan_full["entry_high"]]
            }))
            .mark_rect(opacity=0.15, color="#22c55e")
            .encode(y="y1:Q", y2="y2:Q")
        )

        stop = (
            alt.Chart(pd.DataFrame({"y": [plan_full["stop"]]}))
            .mark_rule(color="#ef4444", strokeDash=[6, 4])
            .encode(y="y:Q")
        )

        target = (
            alt.Chart(pd.DataFrame({"y": [plan_full["target"]]}))
            .mark_rule(color="#22c55e", strokeDash=[6, 4])
            .encode(y="y:Q")
        )

        layers.extend([entry_band, stop, target])

    st.altair_chart(
        alt.layer(*layers).interactive(),
        use_container_width=True
    )

    # ================= ENTRY PLAN =================
    st.markdown("### 🎯 Entry Plan (Full Data)")
    if plan_full.get("status") == "No Trade":
        st.info("No trade setup.")
    else:
        e1, e2, e3 = st.columns(3)
        e1.metric("Buy Zone", f"{plan_full['entry_low']:.0f} – {plan_full['entry_high']:.0f}")
        e2.metric("Stop", f"{plan_full['stop']:.0f}")
        e3.metric("Target", f"{plan_full['target']:.0f}")

    # ================= RISK =================
    st.markdown("### 🛡️ Risk Management")
    if risk_full.get("status") == "OK":
        r1, r2, r3 = st.columns(3)
        r1.metric("Shares", f"{risk_full['shares']:,}")
        r2.metric("Position Value", f"{risk_full['position_value']:,.0f}")
        r3.metric("Risk / Trade", f"{risk_pct:.1f}%")

    st.caption("Bukan rekomendasi beli/jual. Gunakan risk management.")
