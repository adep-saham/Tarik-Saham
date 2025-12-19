import pandas as pd

# =========================
# Helper indikator mandiri
# =========================

def ensure_ema(df: pd.DataFrame, span: int, col: str) -> pd.DataFrame:
    """
    Pastikan kolom EMA tersedia.
    """
    if col not in df.columns:
        df[col] = df["Close"].ewm(span=span, adjust=False).mean()
    return df


def ensure_rsi14(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pastikan kolom RSI14 tersedia.
    """
    if "RSI14" not in df.columns:
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        rs = gain.rolling(14).mean() / loss.rolling(14).mean()
        df["RSI14"] = 100 - (100 / (1 + rs))
    return df


# =========================
# Ranking Engine
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
    top_n: int = 10,
):
    """
    Ranking Top Saham Sinkron (>=2 dari 3 window: 30 / 60 / 120)

    Scoring:
    - Sinkronisasi window (40%)
    - Trend strength EMA (40%)
    - Momentum RSI (20%)
    """

    rows = []

    for ticker in tickers:
        # -------------------------
        # Hitung sinkron window
        # -------------------------
        sync_count = (
            (ticker in w30) +
            (ticker in w60) +
            (ticker in w120)
        )

        if sync_count < 2:
            continue

        # -------------------------
        # Load data harga
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
        # Indikator tambahan (jika ada)
        # -------------------------
        if calc_indicators is not None:
            try:
                df = calc_indicators(df)
            except Exception:
                pass

        # -------------------------
        # Pastikan indikator inti ada
        # -------------------------
        df = ensure_ema(df, window_ref, f"EMA{window_ref}")
        df = ensure_ema(df, window_ref * 2, f"EMA{window_ref*2}")
        df = ensure_rsi14(df)

        try:
            ema_fast = df[f"EMA{window_ref}"].iloc[-1]
            ema_slow = df[f"EMA{window_ref*2}"].iloc[-1]
            rsi = df["RSI14"].iloc[-1]
        except Exception:
            continue

        if pd.isna(ema_fast) or pd.isna(ema_slow) or pd.isna(rsi):
            continue

        # -------------------------
        # Scoring
        # -------------------------
        trend_score = (ema_fast - ema_slow) / ema_slow
        momentum_score = rsi / 100

        total_score = (
            sync_count * 0.4 +
            trend_score * 0.4 +
            momentum_score * 0.2
        )

        rows.append({
            "Ticker": ticker,
            "Sync": sync_count,
            f"EMA{window_ref}": round(float(ema_fast), 2),
            f"EMA{window_ref*2}": round(float(ema_slow), 2),
            "RSI14": round(float(rsi), 1),
            "TrendScore": round(float(trend_score), 4),
            "MomentumScore": round(float(momentum_score), 4),
            "Score": round(float(total_score), 4),
        })

    if not rows:
        return pd.DataFrame(columns=[
            "Ticker", "Sync",
            f"EMA{window_ref}", f"EMA{window_ref*2}",
            "RSI14", "TrendScore", "MomentumScore", "Score"
        ])

    df_rank = pd.DataFrame(rows)

    return (
        df_rank
        .sort_values("Score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
