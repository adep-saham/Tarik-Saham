def auto_switch_mode(df_rank):
    """
    Decide best trading mode based on market regime.
    """

    if df_rank is None or df_rank.empty:
        return "Strict"

    avg_trend = df_rank["TrendScore"].mean()
    avg_rsi = df_rank["RSI14"].mean()
    sync_ratio = (df_rank["Sync"] >= 2).mean()

    # STRONG TREND
    if avg_trend > 0.35 and 50 <= avg_rsi <= 75 and sync_ratio > 0.6:
        return "Momentum"

    # TREND BUT OVEREXTENDED
    if avg_trend > 0.2 and avg_rsi > 65 and sync_ratio > 0.4:
        return "Pullback"

    # BAD / SIDEWAYS MARKET
    return "Strict"
