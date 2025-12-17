def get_trade_badge(confidence, plan_status, trend):
    """
    Aturan sederhana & stabil:
    - BUY   : confidence >= 70, ada setup, trend up
    - WAIT  : confidence 40–69 atau setup belum ideal
    - AVOID : confidence < 40 atau No Trade
    """

    if plan_status == "No Trade":
        return "AVOID", "gray"

    if confidence >= 70 and trend in ["up", "strong_up"]:
        return "BUY", "green"

    if confidence >= 40:
        return "WAIT", "orange"

    return "AVOID", "red"
