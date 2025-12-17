import yfinance as yf
import streamlit as st

@st.cache_data(show_spinner=False)
def fetch_data(ticker: str, period: str, interval: str):
    return yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=False
    )
