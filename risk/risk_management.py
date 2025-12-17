def compute_risk(capital, risk_pct, lot_size, plan, last_close):
    if plan.get("status") == "No Trade":
        return {"status": "NoTrade"}
    entry = (plan["entry_low"] + plan["entry_high"]) / 2
    risk = entry - plan["stop"]
    max_risk = capital * risk_pct / 100
    shares = int(max_risk / risk)
    return {
        "status": "OK",
        "shares": shares,
        "position_value": shares * entry
    }
