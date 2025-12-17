import streamlit as st
import pandas as pd

# ================= CORE =================
from core.data_loader import fetch_data
from core.indicators import calc_indicators
from core.ticker_utils import normalize_ticker

# ================= ANALYSIS =================
from analysis.interpretation import interpret_last
from analysis.patterns import detect_patterns
from analysis.entry_plan import generate_entry_plan
from analysis.confidence import compute_confidence
from analysis.narrative import generate_narrative

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

    ticker = normalize_ticker(raw_ticker)

    with st.spinner("Fetching data..."):
        df = fetch_data(ticker, period, interval)

    if df.empty:
        st.error("Data kosong / ticker tidak valid")
        st.stop()

    df_ind = calc_indicators(df)
    last = df_ind.iloc[-1]

    desc = interpret_last(last)
    patterns = detect_patterns(df_ind)
    plan = generate_entry_plan(df_ind)
    conf = compute_confidence(df_ind, last, desc, patterns, plan)
    risk = compute_risk(capital, risk_pct, lot_size, plan, last["Close"])

    # ================= HEADER INFO =================
    st.caption(
        f"**{ticker}** | {period} | {interval} | "
        f"Close: **{last['Close']:.2f}**"
    )

    # ================= CORE METRICS =================
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trend", desc.get("Trend EMA"))
    c2.metric("Confidence", f"{conf['score']:.0f}%")
    c3.metric("Entry Mid",
              f"{((plan.get('entry_low',0)+plan.get('entry_high',0))/2):.2f}"
              if plan.get("status") != "No Trade" else "-")
    c4.metric("Risk", f"{risk_pct:.1f}%")

    st.progress(conf["score"] / 100)

    # ================= ENTRY ZONE =================
    st.markdown("### 🎯 Entry Plan")

    if plan.get("status") == "No Trade":
        st.warning("No trade setup – wait.")
    else:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Buy", f"{plan['entry_low']:.0f} – {plan['entry_high']:.0f}")
        e2.metric("Stop", f"{plan['stop']:.0f}")
        e3.metric("Target", f"{plan['target']:.0f}")
        e4.metric("RR",
                  f"{plan.get('RR',0):.2f}"
                  if plan.get("RR") else "-")

    # ================= SIGNAL SUMMARY =================
    st.markdown("### 🧠 Signal Summary")

    s1, s2, s3 = st.columns(3)
    s1.info(f"EMA\n{desc.get('Trend EMA')}")
    s2.info(f"Momentum\n{desc.get('MACD')}")
    s3.info(f"Volume\n{desc.get('Volume','-')}")

    # ================= ENTRY LADDER =================
    if plan.get("status") != "No Trade":
        st.markdown("### 🧱 Ladder")

        ladders = build_ladders(plan)
        for mode, rows in ladders.items():
            st.caption(mode)
            df_l = pd.DataFrame(rows, columns=["Porsi", "Harga"])
            df_l["Porsi"] = (df_l["Porsi"]*100).astype(int).astype(str)+"%"
            st.dataframe(df_l, use_container_width=True, hide_index=True)

    # ================= RISK =================
    st.markdown("### 🛡️ Risk")

    if risk.get("status") == "OK":
        r1, r2, r3 = st.columns(3)
        r1.metric("Shares", f"{risk['shares']:,}")
        r2.metric("Position", f"{risk['position_value']:,.0f}")
        r3.metric("Risk Used", f"{risk_pct:.1f}%")

    # ================= FOOTNOTE =================
    st.caption("Bukan rekomendasi beli/jual. Gunakan risk management.")
