import streamlit as st

def sidebar_inputs():
    st.sidebar.header("⚙️ Pengaturan")

    ticker = st.sidebar.text_input("Kode Saham", "ANTM.JK")
    period = st.sidebar.selectbox("Periode", ["3mo", "6mo", "1y", "2y"])
    interval = st.sidebar.selectbox("Interval", ["1d", "1h", "30m"])

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
