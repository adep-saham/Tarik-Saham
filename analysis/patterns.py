import numpy as np
from core.utils import safe_float

def detect_patterns(df):
    patterns = []
    if len(df) < 20:
        return ["Data terlalu pendek"]

    last = df.iloc[-1]
    close = safe_float(last["Close"])
    high20 = safe_float(df["Close"].rolling(20).max().iloc[-2])

    if close > high20:
        patterns.append("Breakout 20 hari")

    return patterns
