import pandas as pd

# =========================
# HELPER INDICATORS
# =========================

def ensure_ema(df: pd.DataFrame, span: int, col: str) -> pd.DataFrame:
    """
    Pastikan EMA tersedia.
    """
    if col not in df.columns:
        df[col] = df["Close"].ewm(span=span, adjust=False).mean()
    return df


def ensure_rsi14(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pastikan RSI14 tersedia.
    """
    if "RSI14" not in df.columns:
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        rs = gain.rolling(14).mean() / loss.rolling(14).mean()
        df["RSI14"] = 100 - (100 / (1 + rs))
    return df


# =========================
# OPTIONAL: ENTRY & SL
# =========================

def compute_entry_sl(ema_fast, ema_slow):
    """
    Entry zone & stoploss sederhana (swing-friendly).
    """
    entry_low = ema_fast * 0.985
    entry_high = ema_fast * 1.015
    stoploss = ema_slow * 0.975
    return round(entry_low, 2), round(entry_high, 2), round(stoploss, 2)


# =========================
# OPTIONAL: BANDAR FLOW (PROXY)
# =========================

def detect_bandar(df: pd.DataFrame, ema_fast: float) -> str:
    """
    Proxy smart money berbasis volume.
    """
    if "Volume" not in df.columns or len(df) < 20:
        return "N/A"

    vol_ma = df["Volume"].rolling(20).mean().iloc[-1]
    vol_now = df["Volume"].iloc[-1]
    close = df["Close"].iloc[-1]

    if vol_now > 1.5 * vol_ma and close > ema_fast:
        return "ACCUM"
    elif vol_now < 0.7 * vol_ma:
        return "DISTRIB"
    else:
        return "NEUTRAL"


# =========================
# RANKING ENGINE
# =========================

def rank_sync_stocks(
    tickers,
    w30: set,
    w60: set,
    w120: set,
    load_price_data,
    calc_indicators=None,
    window_ref: int = 60,
    period: str = "1y",
    interval: str = "1d",
    top_n: int = 20,
):
    """
    Ranking saham sinkron (>=2 dari 3 window: 30 / 60 / 120)

    Scoring:
    - Sync window (40%)
    - Trend strength EMA (40%)
    - Momentum RSI (20%)
    """

    rows = []

    for ticker in tickers:
        # -------------------------
        # SYNC SCORE
        # -------------------------
        sync_count = (
            (ticker in w30) +
            (ticker in w60) +
            (ticker in w120)
        )

        if sync_count < 2:
            continue

        # -------------------------
        # LOAD PRICE DATA
        # -------------------------
        try:
            df = load_price_data(
                ticker,
                period=period,
                interval=interval
            )
        except Exception:
            continue

        if df is None or df.empty or "Close" not in df.columns:
            continue

        # -------------------------
        # CUSTOM INDICATORS (OPTIONAL)
        # -------------------------
        if calc_indicators is not None:
            try:
                df = calc_indicators(df)
            except Exception:
                pass

        # -------------------------
        # ENSURE CORE INDICATORS
        # -------------------------
        df = ensure_ema(df, window_ref, f"EMA{window_ref}")
        df = ensure_ema(df, window_ref * 2, f"EMA{window_ref*2}")
        df = ensure_rsi14(df)

        try:
            ema_fast = float(df[f"EMA{window_ref}"].iloc[-1])
            ema_slow = float(df[f"EMA{window_ref*2}"].iloc[-1])
            rsi = float(df["RSI14"].iloc[-1])
            close = float(df["Close"].iloc[-1])
        except Exception:
            continue

        if pd.isna(ema_fast) or pd.isna(ema_slow) or pd.isna(rsi):
            continue

        # -------------------------
        # SCORES
        # -------------------------
        trend_score = (ema_fast - ema_slow) / ema_slow
        momentum_score = rsi / 100

        total_score = (
            sync_count * 0.4 +
            trend_score * 0.4 +
            momentum_score * 0.2
        )

        # -------------------------
        # ENTRY / SL
        # -------------------------
        entry_low, entry_high, stoploss = compute_entry_sl(
            ema_fast, ema_slow
        )

        # -------------------------
        # BANDAR FLOW
        # -------------------------
        bandar = detect_bandar(df, ema_fast)

        rows.append({
            "Ticker": ticker,
            "Sync": sync_count,
            f"EMA{window_ref}": round(ema_fast, 2),
            f"EMA{window_ref*2}": round(ema_slow, 2),
            "RSI14": round(rsi, 1),
            "TrendScore": round(trend_score, 4),
            "MomentumScore": round(momentum_score, 4),
            "Score": round(total_score, 4),
            "EntryLow": entry_low,
            "EntryHigh": entry_high,
            "StopLoss": stoploss,
            "Bandar": bandar,
        })

    if not rows:
        return pd.DataFrame(columns=[
            "Ticker", "Sync",
            f"EMA{window_ref}", f"EMA{window_ref*2}",
            "RSI14", "TrendScore", "MomentumScore",
            "Score", "EntryLow", "EntryHigh", "StopLoss", "Bandar"
        ])

    df_rank = pd.DataFrame(rows)

    return (
        df_rank
        .sort_values("Score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
