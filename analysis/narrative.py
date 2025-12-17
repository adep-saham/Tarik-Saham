from core.utils import safe_float

def generate_narrative(ticker, last, desc, patterns, plan, confidence):
    close = safe_float(last["Close"])
    return f"""
Ringkasan {ticker}
Harga: {close}
Trend: {desc.get('Trend EMA')}
Confidence: {confidence['score']}%
"""
