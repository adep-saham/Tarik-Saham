def normalize_ticker(ticker: str) -> str:
    """
    Normalisasi kode saham:
    - ANTM   -> ANTM.JK
    - BBRI   -> BBRI.JK
    - ANTM.JK -> ANTM.JK
    - AAPL   -> AAPL
    """
    if not ticker:
        return ""

    t = ticker.strip().upper()

    # Kalau sudah ada suffix (AAPL, BTC-USD, ANTM.JK)
    if "." in t or "-" in t:
        return t

    # Asumsi saham Indonesia (umumnya 4–5 huruf)
    if len(t) <= 5:
        return f"{t}.JK"

    return t
