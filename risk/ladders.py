def build_ladders(plan):
    if plan.get("status") == "No Trade":
        return {"status": "No Trade"}
    low = plan["entry_low"]
    high = plan["entry_high"]
    mid = (low + high) / 2
    return {
        "Konservatif": [(0.5, low), (0.5, mid)],
        "Agresif": [(0.5, mid), (0.5, high)]
    }
