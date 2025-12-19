def decide_action(row):
    sync = int(row["Sync"])
    trend = float(row["TrendScore"])
    rsi = float(row["RSI14"])

    if sync >= 2 and trend > 0 and 55 <= rsi <= 80:
        return "BUY"
    elif sync >= 2 and trend > 0 and 45 <= rsi < 55:
        return "WAIT"
    else:
        return "SKIP"
