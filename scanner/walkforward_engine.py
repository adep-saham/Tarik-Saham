import pandas as pd

def walk_forward_validate(
    tickers,
    load_price_data,
    decide_action_func,
    mode: str,
    lookback_days: int = 7,
    period: str = "1mo",
    interval: str = "1d",
):
    """
    Walk-forward validation:
    - cek sinyal BUY di H-n
    - bandingkan dengan harga hari ini
    """

    today_results = []

    for ticker in tickers:
        try:
            df = load_price_data(
                ticker,
                period=period,
                interval=interval
            )
        except Exception:
            continue

        if df is None or len(df) < lookback_days + 2:
            continue

        df = df.reset_index(drop=True)

        close_today = float(df.iloc[-1]["Close"])

        for i in range(1, lookback_days + 1):
            row = df.iloc[-1 - i]

            # Proxy row untuk decision
            fake_row = {
                "Sync": 2,                 # diasumsikan lolos sync
                "RSI14": row.get("RSI14", 50),
                "TrendScore": 0.01         # diasumsikan tren positif
            }

            decision = decide_action_func(fake_row, mode)

            if decision != "BUY":
                continue

            entry_price = float(row["Close"])
            ret = (close_today - entry_price) / entry_price * 100

            today_results.append({
                "Ticker": ticker,
                "Signal_Day": f"H-{i}",
                "Entry_Price": round(entry_price, 2),
                "Today_Price": round(close_today, 2),
                "Return_%": round(ret, 2)
            })

    if not today_results:
        return None

    df_res = pd.DataFrame(today_results)

    summary = {
        "Mode": mode,
        "Signals": len(df_res),
        "Win Rate (%)": round((df_res["Return_%"] > 0).mean() * 100, 2),
        "Avg Return (%)": round(df_res["Return_%"].mean(), 2),
        "Best": round(df_res["Return_%"].max(), 2),
        "Worst": round(df_res["Return_%"].min(), 2),
    }

    return df_res, summary
