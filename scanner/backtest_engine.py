import pandas as pd

def backtest_mode(
    tickers,
    load_price_data,
    decide_action_func,
    mode: str,
    holding_days: int = 5,
    period: str = "6mo",
    interval: str = "1d",
):
    results = []

    for ticker in tickers:
        try:
            df = load_price_data(
                ticker,
                period=period,
                interval=interval
            )
        except Exception:
            continue

        if df is None or len(df) < holding_days + 5:
            continue

        df = df.reset_index(drop=True)

        for i in range(len(df) - holding_days):
            row = df.iloc[i]

            fake_row = {
                "Sync": 2,  # asumsi lolos sync
                "RSI14": row.get("RSI14", 50),
                "TrendScore": 0.01  # proxy positif
            }

            decision = decide_action_func(fake_row, mode)

            if decision != "BUY":
                continue

            entry_price = df.iloc[i]["Close"]
            exit_price = df.iloc[i + holding_days]["Close"]

            ret = (exit_price - entry_price) / entry_price * 100

            results.append({
                "Ticker": ticker,
                "Mode": mode,
                "Return": ret
            })

    if not results:
        return None

    df_res = pd.DataFrame(results)

    return {
        "Mode": mode,
        "Total Trade": len(df_res),
        "Win Rate": round((df_res["Return"] > 0).mean() * 100, 2),
        "Avg Return": round(df_res["Return"].mean(), 2),
        "Max DD": round(df_res["Return"].min(), 2)
    }
