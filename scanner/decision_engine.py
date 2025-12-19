def decide_action(row):
    sync = row["Sync"]
    trend = row["TrendScore"]
    rsi = row["RSI14"]

    if sync == 3 and trend > 0 and 50 <= rsi <= 70:
        return "BUY"
    elif sync >= 2 and trend > 0 and 45 <= rsi < 50:
        return "WAIT"
    else:
        return "SKIP"
