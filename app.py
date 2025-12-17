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

# ================= MAIN =================
if analyze_btn:

    if not raw_ticker:
        st.error("Kode saham belum diisi.")
        st.stop()

    ticker = normalize_ticker(raw_ticker)

    with st.spinner("Fetching data..."):
        df = fetch_data(ticker, period, interval)

    if df.empty:
        st.error("Data kosong / ticker tidak valid.")
        st.stop()

    df_ind = calc_indicators(df)
    last = df_ind.iloc[-1]

    # ================= SAFE VALUES =================
    close_price = safe_float(last.get("Close"))
    close_text = f"{close_price:.2f}" if not np.isnan(close_price) else "-"

    # ================= ANALYSIS =================
    desc = interpret_last(last)
    patterns = detect_patterns(df_ind)
    plan = generate_entry_plan(df_ind)
    conf = compute_confidence(df_ind, last, desc, patterns, plan)
    risk = compute_risk(capital, risk_pct, lot_size, plan, close_price)

    # ================= BADGE =================
    badge_text, badge_color = get_trade_badge(
        conf["score"],
        plan.get("status"),
        plan.get("trend")
    )

    # ================= HEADER =================
    st.caption(
        f"**{ticker}** | {period} | {interval} | "
        f"Close: **{close_text}** | "
        f"Decision: **{badge_text}**"
    )

    if badge_text == "BUY":
        st.success("🟢 **BUY** – Setup kuat, risk terukur.")
    elif badge_text == "WAIT":
        st.warning("🟡 **WAIT** – Tunggu konfirmasi.")
    else:
        st.error("🔴 **AVOID** – Risiko lebih besar dari peluang.")

    # ================= CORE METRICS =================
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trend", desc.get("Trend EMA", "-"))
    c2.metric("Confidence", f"{conf['score']:.0f}%")
    c4.metric("Risk / Trade", f"{risk_pct:.1f}%")

    entry_mid = "-"
    if plan.get("status") != "No Trade":
        entry_mid_val = (plan["entry_low"] + plan["entry_high"]) / 2
        entry_mid = f"{entry_mid_val:.2f}"

    c3.metric("Entry Mid", entry_mid)
    st.progress(conf["score"] / 100)

    # ================= ENTRY PLAN =================
    st.markdown("### 🎯 Entry Plan")

    if plan.get("status") == "No Trade":
        st.info("No trade setup – wait.")
    else:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Buy Zone", f"{plan['entry_low']:.0f} – {plan['entry_high']:.0f}")
        e2.metric("Stop", f"{plan['stop']:.0f}")
        e3.metric("Target", f"{plan['target']:.0f}")
        rr = plan.get("RR")
        e4.metric("RR", f"{rr:.2f}" if rr and not np.isnan(rr) else "-")

        st.caption(
            f"Setup: **{plan.get('status')}** | "
            f"Trend: **{plan.get('trend')}**"
        )

    # ================= PRICE CHART + EMA =================
    st.markdown("### 📈 Price Chart (EMA20 / EMA50 / Entry / SL / TP)")

    chart_df = df_ind.reset_index()
    chart_df = chart_df.rename(columns={chart_df.columns[0]: "Date"})

    # Close price
    price_line = (
        alt.Chart(chart_df)
        .mark_line(color="#1f77b4", strokeWidth=2)
        .encode(
            x=alt.X("Date:T", title="Date"),
            y=alt.Y("Close:Q", title="Price"),
            tooltip=["Date:T", "Close:Q"]
        )
    )

    # EMA20
    ema20_line = (
        alt.Chart(chart_df)
        .mark_line(color="#22c55e", strokeDash=[4, 2])
        .encode(
            x="Date:T",
            y="EMA20:Q"
        )
    )

    # EMA50
    ema50_line = (
        alt.Chart(chart_df)
        .mark_line(color="#ef4444", strokeDash=[6, 3])
        .encode(
            x="Date:T",
            y="EMA50:Q"
        )
    )

    layers = [price_line, ema20_line, ema50_line]

    # Entry / SL / TP
    if plan.get("status") != "No Trade":
        entry_low = plan["entry_low"]
        entry_high = plan["entry_high"]
        stop = plan["stop"]
        target = plan["target"]

        entry_band = (
            alt.Chart(pd.DataFrame({"y1": [entry_low], "y2": [entry_high]}))
            .mark_rect(opacity=0.15, color="#22c55e")
            .encode(y="y1:Q", y2="y2:Q")
        )

        stop_line = (
            alt.Chart(pd.DataFrame({"y": [stop]}))
            .mark_rule(color="#ef4444", strokeDash=[6, 4])
            .encode(y="y:Q")
        )

        target_line = (
            alt.Chart(pd.DataFrame({"y": [target]}))
            .mark_rule(color="#22c55e", strokeDash=[6, 4])
            .encode(y="y:Q")
        )

        layers.extend([entry_band, stop_line, target_line])

    st.altair_chart(
        alt.layer(*layers).interactive(),
        use_container_width=True
    )

    st.caption(
        "🟦 Close | 🟢 EMA20 | 🔴 EMA50 | "
        "🟩 Entry Zone | 🔴 Stop | 🟢 Target"
    )

    # ================= ENTRY LADDER =================
    if plan.get("status") != "No Trade":
        st.markdown("### 🧱 Entry Ladder")
        ladders = build_ladders(plan)

        for mode, rows in ladders.items():
            st.caption(mode)
            df_l = pd.DataFrame(rows, columns=["Porsi", "Harga"])
            df_l["Porsi"] = (df_l["Porsi"] * 100).astype(int).astype(str) + "%"
            st.dataframe(df_l, use_container_width=True, hide_index=True)

    # ================= RISK =================
    st.markdown("### 🛡️ Risk")

    if risk.get("status") == "OK":
        r1, r2, r3 = st.columns(3)
        r1.metric("Shares", f"{risk['shares']:,}")
        r2.metric("Position Value", f"{risk['position_value']:,.0f}")
        r3.metric("Risk Used", f"{risk_pct:.1f}%")
    else:
        st.warning(risk.get("message", "Risk tidak dapat dihitung."))

    st.caption("Bukan rekomendasi beli/jual. Gunakan risk management.")
