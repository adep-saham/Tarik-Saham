import streamlit as st
import pandas as pd

# ===== CORE =====
from core.data_loader import fetch_data
from core.indicators import calc_indicators

# ===== ANALYSIS =====
from analysis.interpretation import interpret_last
from analysis.patterns import detect_patterns
from analysis.entry_plan import generate_entry_plan
from analysis.confidence import compute_confidence
from analysis.narrative import generate_narrative

# ===== RISK =====
from risk.ladders import build_ladders
from risk.risk_management import compute_risk

# ===== UI =====
from ui.theme import load_theme
from ui.sidebar import sidebar_inputs

# ===============================
# PAGE CONFIG & THEME
# ===============================
load_theme()

st.title("📊 Tarik Saham – ADP")
st.caption("EMA · %R · CCI · AO · RSI · MACD · ATR · Pola · Risk")

# ===============================
# SIDEBAR INPUT
# ===============================
(
    ticker,
    period,
    interval,
    capital,
    risk_pct,
    lot_size,
    analyze_btn
) = sidebar_inputs()

# ===============================
# MAIN FLOW
# ===============================
if analyze_btn:

    if not ticker:
        st.error("Kode saham belum diisi.")
        st.stop()

    with st.spinner(f"Mengambil data {ticker} ..."):
        df = fetch_data(ticker, period, interval)

    if df.empty:
        st.error("Data kosong dari Yahoo Finance.")
        st.stop()

    # ===== DATA =====
    st.subheader("📄 Data Harga (Tail)")
    st.dataframe(df.tail())

    # ===== INDICATORS =====
    df_ind = calc_indicators(df)
    last = df_ind.iloc[-1]

    # ===== INTERPRETATION =====
    st.subheader("🧠 Interpretasi Otomatis")
    desc = interpret_last(last)
    for k, v in desc.items():
        st.write(f"**{k}** : {v}")

    # ===== PATTERNS =====
    st.subheader("📌 Pola Teknikal")
    patterns = detect_patterns(df_ind)
    for p in patterns:
        st.write(f"- {p}")

    # ===== ENTRY PLAN =====
    st.subheader("🎯 Rencana Entry & Exit")
    plan = generate_entry_plan(df_ind)
    st.json(plan)

    # ===== CONFIDENCE =====
    st.subheader("🔥 Confidence Score")
    conf = compute_confidence(df_ind, last, desc, patterns, plan)
    st.metric("Confidence", f"{conf['score']} %")
    st.caption(conf["label"])

    # ===== NARRATIVE =====
    st.subheader("🧾 Narasi Analis")
    narrative = generate_narrative(
        ticker, last, desc, patterns, plan, conf
    )
    st.markdown(narrative)

    # ===== ENTRY LADDER =====
    st.subheader("🧱 Entry Ladder")
    ladders = build_ladders(plan)
    st.json(ladders)

    # ===== RISK MANAGEMENT =====
    st.subheader("🛡️ Risk Management")
    risk_info = compute_risk(
        capital, risk_pct, lot_size, plan, last["Close"]
    )
    st.json(risk_info)
