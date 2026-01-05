import streamlit as st
import pandas as pd


def sidebar_inputs():
    # ===============================
    # PENGATURAN UTAMA
    # ===============================
    st.sidebar.header("⚙️ Pengaturan")

    ticker = st.sidebar.text_input("Kode Saham", "ANTM")
    period = st.sidebar.selectbox("Periode", ["3mo", "6mo", "1y", "2y"])
    interval = st.sidebar.selectbox("Interval", ["1d", "1h", "30m"])

    # ===============================
    # RISK MANAGEMENT
    # ===============================
    st.sidebar.header("💰 Risk Management")
    capital = st.sidebar.number_input("Modal", value=10_000_000.0)
    risk_pct = st.sidebar.number_input("Risk per trade (%)", value=1.0)
    lot_size = st.sidebar.number_input("Ukuran 1 lot", value=100)

    analyze_btn = st.sidebar.button("🚀 Analisa")

    return (
        ticker,
        period,
        interval,
        capital,
        risk_pct,
        lot_size,
        analyze_btn
    )


# ======================================================
# BANDARMOLOGY (DIPISAH, AMAN)
# ======================================================
def sidebar_bandarmology():
    st.sidebar.markdown("---")
    st.sidebar.header("📊 Bandarmology")

    # Upload CSV sekali saja
    up = st.sidebar.file_uploader(
        "Upload CSV Bandar",
        type=["csv"],
        key="bandar_csv"
    )

    if up is not None:
        try:
            df = pd.read_csv(up)
            st.session_state["bandarmology_df"] = df
            st.sidebar.success("CSV Bandar dimuat")
        except Exception as e:
            st.sidebar.error(f"Gagal baca CSV: {e}")

    # Mode analisa
    mode = st.sidebar.radio(
        "Mode Bandarmology",
        ["Single Ticker", "All Tickers"],
        horizontal=False
    )

    # Top N hanya relevan untuk All Tickers
    top_n = st.sidebar.number_input(
        "Top N (All Tickers)",
        min_value=10,
        max_value=300,
        value=50,
        step=10
    )

    return mode, top_n
