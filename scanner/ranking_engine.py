import pandas as pd

def rank_sync_stocks(
    tickers,
    w30, w60, w120,
    load_price_data,
    calc_indicators,
    window_ref=60
):
    rows = []

    for t in tickers:
        sync_count = (
            (t in w30) +
            (t in w60) +
            (t in w120)
        )

        if sync_count < 2:
            continue

        df = load_price_data(t, period="1y", interval="1d")
        df = calc_indicators(df)

        ema_fast = df[f"EMA{window_ref}"].iloc[-1]
        ema_slow = df[f"EMA{window_ref*2}"].iloc[-1]
        rsi = df["RSI14"].iloc[-1]

        trend_score = (ema_fast - ema_slow) / ema_slow
        momentum_score = rsi / 100

        total_score = (
            sync_count * 0.4 +
            trend_score * 0.4 +
            momentum_score * 0.2
        )

        rows.append({
            "Ticker": t,
            "Sync": sync_count,
            "EMA_fast": round(ema_fast, 2),
            "EMA_slow": round(ema_slow, 2),
            "RSI": round(rsi, 1),
            "Score": round(total_score, 4)
        })

    df_rank = pd.DataFrame(rows)
    return df_rank.sort_values("Score", ascending=False).head(20)
