import streamlit as st
import pandas as pd

# ===============================
# CORE
# ===============================
from core.data_loader import fetch_data
from core.indicators import calc_indicators
from core.ticker_utils import normalize_ticker

# ===============================
# ANALYSIS
# ===============================
from analysis.interpretation import interpret_last
from analysis.patterns import detect_patterns
from analysis.entry_plan import generate_entry_plan
from analysis.confidence import compute_confidence
from analysis.narrative import generate_narrative

# ===============================
# RISK
# ===============================
from risk.ladders import build_ladders
from risk.risk_management import compute_risk

# ===============================
# UI
# ===============================
from ui.theme import load_theme
from ui.sidebar import sidebar_inputs


# ===============================
# PAGE CONFIG
# ===============================
load_theme()

st.markdown("## 📊 Tarik Saham – ADP")

# ===============================
# SIDEBAR
# ===============================
(
    raw_ticker,
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

    if not raw_ticker:
        st.error("Kode saham belum diisi.")
        st.stop()

    ticker = normalize_ticker(raw_ticker)

    st.markdown(
        f"**Ticker:** `{ticker}` &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**Periode:** `{period}` &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**Interval:** `{interval}`"
    )

    with st.spinner(f"Mengambil data {ticker} ..."):
        df = fetch_data(ticker, period, interval)

    if df.empty:
        st.error(f"Data kosong / ticker tidak valid: {ticker}")
        st.stop()

    # ===============================
    # DATA HARGA
    # ===============================
    st.markdown("### 📄 Data Harga (5 Terakhir)")
    st.dataframe(df.tail().round(2), use_container_width=True)

    # ===============================
    # INDICATORS
    # ===============================
    df_ind = calc_indicators(df)
    last = df_ind.iloc[-1]

    # ===============================
    # INTERPRETASI
    # ===============================
    st.markdown("### 🧠 Interpretasi Otomatis")
    desc = interpret_last(last)

    c1, c2, c3 = st.columns(3)
    cols = [c1, c2, c3]

    for i, (k, v) in enumerate(desc.items()):
        cols[i % 3].info(f"**{k}**\n\n{v}")

    # ===============================
    # POLA
    # ===============================
    st.markdown("### 📌 Pola Teknikal")
    patterns = detect_patterns(df_ind)

    if patterns:
        for p in patterns:
            st.markdown(f"- {p}")
    else:
        st.markdown("- Tidak ada pola menonjol")

    # ===============================
    # ENTRY PLAN
    # ===============================
    st.markdown("### 🎯 Rencana Entry & Exit")
    plan = generate_entry_plan(df_ind)

    if plan.get("status") == "No Trade":
        st.warning("Belum ada setup trading yang valid.")
    else:
        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Entry Low", f"{plan['entry_low']:.2f}")
        m2.metric("Entry High", f"{plan['entry_high']:.2f}")
        m3.metric("Stop Loss", f"{plan['stop']:.2f}")
        m4.metric("Target", f"{plan['target']:.2f}")

        st.caption(
            f"📌 **Setup:** {plan.get('status')} | "
            f"**Trend:** {plan.get('trend')}"
        )

    # ===============================
    # CONFIDENCE
    # ===============================
    st.markdown("### 🔥 Confidence Score")
    conf = compute_confidence(df_ind, last, desc, patterns, plan)

    st.metric(
        label="Keyakinan Sinyal",
        value=f"{conf['score']:.0f}%",
        delta=conf["label"]
    )
    st.progress(conf["score"] / 100)

    # ===============================
    # NARASI
    # ===============================
    st.markdown("### 🧾 Narasi Analis Otomatis")
    narrative = generate_narrative(
        ticker,
        last,
        desc,
        patterns,
        plan,
        conf
    )
    st.success(narrative)

    # ===============================
    # ENTRY LADDER
    # ===============================
    st.markdown("### 🧱 Entry Ladder")
    ladders = build_ladders(plan)

    if ladders.get("status") == "No Trade":
        st.info("Tidak ada entry ladder (No Trade).")
    else:
        for mode, rows in ladders.items():
            st.markdown(f"**{mode}**")
            df_ladder = pd.DataFrame(rows, columns=["Porsi", "Harga"])
            df_ladder["Porsi"] = (
                (df_ladder["Porsi"] * 100)
                .astype(int)
                .astype(str) + "%"
            )
            st.table(df_ladder)

    # ===============================
    # RISK MANAGEMENT
    # ===============================
    st.markdown("### 🛡️ Risk Management")
    risk_info = compute_risk(
        capital,
        risk_pct,
        lot_size,
        plan,
        last["Close"]
    )

    if risk_info.get("status") != "OK":
        st.warning(risk_info.get("message", "Risk tidak valid."))
    else:
        r1, r2, r3 = st.columns(3)
        r1.metric("Jumlah Saham", f"{risk_info['shares']:,}")
        r2.metric("Nilai Posisi", f"{risk_info['position_value']:,.0f}")
        r3.metric("Risk per Trade", f"{risk_pct}%")
