def compute_entry_zone(row, mode):
    """
    Compute entry zone & stoploss based on trading mode.
    """

    close = row.get("Close", 0)
    high = row.get("High", close)
    low = row.get("Low", close)

    ema20 = row.get("EMA20", close)
    ema50 = row.get("EMA50", close)

    # === ENTRY ZONE ===
    if mode == "Momentum":
        entry_low = high
        entry_high = high * 1.01

    elif mode == "Pullback":
        entry_low = ema20
        entry_high = ema20 * 1.01

    else:  # Strict
        entry_low = ema50
        entry_high = ema50 * 1.005

    # === STOPLOSS ===
    stoploss = min(low, entry_low * 0.97)

    return {
        "EntryLow": round(entry_low, 2),
        "EntryHigh": round(entry_high, 2),
        "StopLoss": round(stoploss, 2)
    }
