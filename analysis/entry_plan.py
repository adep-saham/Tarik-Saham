import numpy as np
from core.utils import safe_float

def generate_entry_plan(df):
    last = df.iloc[-1]
    close = safe_float(last["Close"])
    atr = safe_float(last["ATR14"])

    if np.isnan(atr):
        return {"status": "No Trade"}

    return {
        "status": "Setup Breakout",
        "entry_low": close - atr,
        "entry_high": close + 0.3 * atr,
        "stop": close - 2 * atr,
        "target": close + 3 * atr,
        "trend": "up"
    }
