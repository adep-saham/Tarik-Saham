import numpy as np
import pandas as pd
from core.utils import safe_float

def interpret_last(row):
    if isinstance(row, pd.DataFrame):
        row = row.iloc[-1]

    desc = {}

    close = safe_float(row.get("Close"))
    ema20 = safe_float(row.get("EMA20"))
    ema50 = safe_float(row.get("EMA50"))
    wr = safe_float(row.get("WR14"))
    cci = safe_float(row.get("CCI200"))
    ao = safe_float(row.get("AO"))
    rsi = safe_float(row.get("RSI14"))
    macd = safe_float(row.get("MACD"))
    macd_h = safe_float(row.get("MACDhist"))

    if ema20 > ema50 and close > ema20:
        desc["Trend EMA"] = "Uptrend kuat"
    elif ema20 > ema50:
        desc["Trend EMA"] = "Uptrend"
    elif ema20 < ema50:
        desc["Trend EMA"] = "Downtrend"
    else:
        desc["Trend EMA"] = "Netral"

    desc["%R(14)"] = "Oversold" if wr <= -80 else "Overbought" if wr >= -20 else "Netral"
    desc["CCI(200)"] = "Bullish" if cci > 100 else "Bearish" if cci < -100 else "Netral"
    desc["AO"] = "Bullish" if ao > 0 else "Bearish"
    desc["RSI(14)"] = "Overbought" if rsi >= 70 else "Oversold" if rsi <= 30 else "Netral"
    desc["MACD"] = "Bullish" if macd > 0 and macd_h > 0 else "Bearish"

    return desc
