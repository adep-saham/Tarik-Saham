import pandas as pd

def build_equity_curve(
    tickers,
    load_price_data,
    decide_action_func,
    mode: str,
    holding_days: int = 5,
    base_equity: float = 100.0,
    period: str = "6mo",
    interval: str = "1d",
):
    """
    NORMALIZED equity curve:
    - No compounding explosion
    - Each trade contributes incremental return
    """

    curve = []
    cumulative_equity = base_equity

    for ticker in tickers:
        try:
            df = load_price_data(ticker, period=period, interval=interval)
        except Exception:
            continue

        if df is None or len(df) < holding_days + 10:
            continue

        df = df.reset_index(drop=True)

        for i in range(len(df) - holding_days):
            row = df.iloc[i]

            fake_row = {
                "Sync": 2,
                "RSI14": row.get("RSI14", 50),
                "TrendScore": 0.01
            }

            decision = decide_action_func(fake_row, mode)
            if decision != "BUY":
                continue

            entry = float(df.iloc[i]["Close"])
            exit_ = float(df.iloc[i + holding_days]["Close"])

            ret_pct = (exit_ - entry) / entry * 100

            # NORMALIZED increment
            cumulative_equity += ret_pct

            curve.append({
                "Ticker": ticker,
                "Trade_Index": len(curve) + 1,
                "Return_%": round(ret_pct, 2),
                "Equity": round(cumulative_equity, 2)
            })

    if not curve:
        return None

    return pd.DataFrame(curve)
