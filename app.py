# ================= IMPORT =================
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import yfinance as yf

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
from risk.risk_management import compute_risk

# ================= UI =================
from ui.theme import load_theme
from ui.sidebar import sidebar_inputs

# ================= SCANNER =================
from scanner.scan_engine import scan_window   # ← ENGINE BARU (AMAN)

# ================= RANGKING =================
from ranking_engine import rank_sync_stocks


# ================= PAGE =================
st.set_page_config(page_title="Tarik Saham – ADP", layout="wide")
load_theme()
st.markdown("## 📊 Tarik Saham – ADP")

# ======================================================
# 📥 LOAD IDX UNIVERSE
# ======================================================
@st.cache_data(ttl=24 * 3600)
def load_universe():
    df = pd.read_csv("data/idx_universe.csv")
    df.columns = [c.lower().strip() for c in df.columns]

    if "ticker" not in df.columns:
        if "kode" in df.columns:
            df = df.rename(columns={"kode": "ticker"})
        else:
            st.error("Kolom ticker/kode tidak ditemukan")
            st.stop()

    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["ticker"] = df["ticker"].apply(lambda x: x if x.endswith(".JK") else f"{x}.JK")
    return df


IDX_UNIVERSE = load_universe()

# ======================================================
# 🔎 FILTER BOARD IDX (CEPAT)
# ======================================================
st.subheader("🔎 Filter IDX Universe")

BOARD_OPTIONS = ["UTAMA", "AKSELERASI", "PENGEMBANGAN"]
selected_boards = st.multiselect(
    "Pilih papan saham IDX",
    options=BOARD_OPTIONS,
    default=["UTAMA", "AKSELERASI"]
)

if not selected_boards:
    st.warning("Pilih minimal satu papan saham.")
    st.stop()

IDX_UNIVERSE = IDX_UNIVERSE[IDX_UNIVERSE["board"].isin(selected_boards)]
TICKERS = IDX_UNIVERSE["ticker"].tolist()

st.caption(f"Universe IDX: {len(TICKERS)} saham")

# ======================================================
# 🧭 TABS
# ======================================================
tab_single, tab_auto = st.tabs([
    "🔎 Single Stock Analysis",
    "🤖 Auto Sync Stocks (30 / 60 / 120)"
])

# ======================================================
# 🔎 TAB 1 — SINGLE STOCK
# ======================================================
with tab_single:

    (
        raw_ticker,
        period,
        interval,
        capital,
        risk_pct,
        lot_size,
        analyze_btn
    ) = sidebar_inputs()

    if analyze_btn and raw_ticker:
        ticker = normalize_ticker(raw_ticker)
        df = fetch_data(ticker, period, interval)

        if df.empty:
            st.error("Data kosong / ticker tidak valid.")
            st.stop()

        df = calc_indicators(df)
        last = df.iloc[-1]

        close_price = safe_float(last.get("Close"))
        desc = interpret_last(last)
        patterns = detect_patterns(df)
        plan = generate_entry_plan(df)
        conf = compute_confidence(df, last, desc, patterns, plan)
        risk = compute_risk(capital, risk_pct, lot_size, plan, close_price)

        badge_text, _ = get_trade_badge(
            conf["score"],
            plan.get("status"),
            plan.get("trend")
        )

        st.subheader(f"{ticker} — {badge_text}")

        zoom = st.select_slider(
            "🔍 Window Analisa",
            options=[30, 60, 120],
            value=30
        )

        df_w = df.tail(zoom)

        chart_df = df_w.reset_index().rename(columns={"index": "Date"})

        price = alt.Chart(chart_df).mark_line().encode(
            x="Date:T", y="Close:Q"
        )

        ema20 = alt.Chart(chart_df).mark_line(
            color="green", strokeDash=[4, 2]
        ).encode(x="Date:T", y="EMA20:Q")

        ema50 = alt.Chart(chart_df).mark_line(
            color="red", strokeDash=[6, 3]
        ).encode(x="Date:T", y="EMA50:Q")

        st.altair_chart(
            (price + ema20 + ema50).interactive(),
            use_container_width=True
        )

# ======================================================
# 🤖 TAB 2 — AUTO SYNC
# ======================================================
with tab_auto:
    st.subheader("🤖 Auto Sync Stocks (IDX – 30 / 60 / 120)")

    col1, col2, col3 = st.columns(3)

    for k in ["w30", "w60", "w120"]:
        if k not in st.session_state:
            st.session_state[k] = set()

    with col1:
        if st.button("Scan Window 30"):
            with st.spinner("Scanning 30..."):
                w30, stats30 = scan_window(30, TICKERS, fetch_data, calc_indicators)
                st.session_state.w30 = set(w30)
                st.caption(f"30 stats: {stats30}")


    with col2:
        if st.button("Scan Window 60"):
            with st.spinner("Scanning 60..."):
                w60, stats60 = scan_window(60, TICKERS, fetch_data, calc_indicators)
                st.session_state.w60 = set(w60)
                st.caption(f"60 stats: {stats60}")


    with col3:
        if st.button("Scan Window 120"):
            with st.spinner("Scanning 120..."):
                w120, stats120 = scan_window(120, TICKERS, fetch_data, calc_indicators)
                st.session_state.w120 = set(w120)
                st.caption(f"120 stats: {stats120}")



    w30 = st.session_state.w30
    w60 = st.session_state.w60
    w120 = st.session_state.w120

    st.write("Lolos 30:", len(w30))
    st.write("Lolos 60:", len(w60))
    st.write("Lolos 120:", len(w120))

    sync_2of3 = (w30 & w60) | (w30 & w120) | (w60 & w120)

    if sync_2of3:
        st.success(f"Saham sinkron (≥2 window): {len(sync_2of3)}")
        st.dataframe(
            pd.DataFrame(sorted(sync_2of3), columns=["Ticker"]),
            use_container_width=True
        )
    else:
        st.warning("Tidak ada saham sinkron saat ini.")

    if sync_2of3:
        st.subheader("🏆 Ranking Top 20 Saham Sinkron")
    
        df_rank = rank_sync_stocks(
            tickers=sync_2of3,
            w30=w30,
            w60=w60,
            w120=w120,
            load_price_data=fetch_data,
            calc_indicators=calc_indicators
        )
    
        st.dataframe(df_rank, use_container_width=True)


