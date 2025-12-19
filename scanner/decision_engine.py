def decide_action(row, mode="Momentum"):
    sync = int(row["Sync"])
    trend = float(row["TrendScore"])
    rsi = float(row["RSI14"])

    if mode == "Momentum":
        if sync >= 2 and trend > 0 and 55 <= rsi <= 80:
            return "BUY"
        elif sync >= 2 and trend > 0 and rsi > 80:
            return "HOT"
        elif sync >= 2 and trend > 0 and 45 <= rsi < 55:
            return "WAIT"
        else:
            return "SKIP"

    elif mode == "Pullback":
        if sync >= 2 and trend > 0 and 50 <= rsi <= 65:
            return "BUY"
        elif sync >= 2 and trend > 0 and 40 <= rsi < 50:
            return "WAIT"
        else:
            return "SKIP"

    else:  # Strict
        if sync == 3 and trend > 0 and 50 <= rsi <= 65:
            return "BUY"
        elif sync >= 2 and trend > 0 and 45 <= rsi < 50:
            return "WAIT"
        else:
            return "SKIP"
