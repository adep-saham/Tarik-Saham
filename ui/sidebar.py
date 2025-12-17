import streamlit as st

def sidebar_inputs():
    ticker = st.sidebar.text_input("Ticker", "ANTM.JK")
    period = st.sidebar.selectbox("Period", ["3mo", "6mo", "1y"])
    interval = st.sidebar.selectbox("Interval", ["1d", "1h"])
    return ticker, period, interval
