from core.utils import safe_float

def compute_confidence(df, last, desc, patterns, plan):
    score = 50
    if plan.get("status") != "No Trade":
        score += 25
    if "Breakout" in " ".join(patterns):
        score += 15
    return {
        "score": min(score, 100),
        "label": "High" if score >= 70 else "Medium"
    }
