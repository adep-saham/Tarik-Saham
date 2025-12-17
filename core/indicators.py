import pandas as pd
import numpy as np

def calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.rename(columns=str.capitalize)

    if df.empty:
        raise ValueError("Data kosong.")

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    hh14 = df["High"].rolling(14).max()
    ll14 = df["Low"].rolling(14).min()
    df["WR14"] = -100 * (hh14 - df["Close"]) / (hh14 - ll14)

    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma_tp = tp.rolling(200).mean()
    mad = (tp - sma_tp).abs().rolling(200).mean()
    df["CCI200"] = (tp - sma_tp) / (0.015 * mad)

    mid = (df["High"] + df["Low"]) / 2
    df["AO"] = mid.rolling(5).mean() - mid.rolling(34).mean()

    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    df["ATR14"] = tr.rolling(14).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["RSI14"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACDsignal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACDhist"] = df["MACD"] - df["MACDsignal"]

    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    # ===== Volume MA20 & Ratio (SAFE VERSION) =====
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    
    vol_arr = np.asarray(df["Volume"], dtype="float64").reshape(-1)
    vol_ma_arr = np.asarray(df["VOL_MA20"], dtype="float64").reshape(-1)
    
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = vol_arr / vol_ma_arr
    
    ratio[~np.isfinite(ratio)] = np.nan
    df["VolRatio20"] = ratio


    return df

