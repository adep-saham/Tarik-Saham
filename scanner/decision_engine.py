"""
Decision Engine
Digunakan oleh:
- Auto Sync (30 / 60 / 120)
- Single Stock (Pro)

PRINSIP:
- TIDAK BOLEH crash hanya karena field hilang
- Semua field opsional punya default
- Mode logic terpisah & jelas
"""

def decide_action(row, mode):
    """
    row : pandas.Series atau dict-like
    mode: str -> 'Momentum' | 'Pullback' | 'Mean Reversion'

    return: 'BUY' | 'WAIT'
    """

    # ======================================================
    # SAFE EXTRACTION (DEFENSIVE)
    # ======================================================
    try:
        sync = int(row.get("Sync", 1))        # default: single dianggap sync
    except Exception:
        sync = 1

    try:
        score = float(row.get("Score", 0))
    except Exception:
        score = 0.0

    trend = row.get("Trend", "")
    status = row.get("Status", "")

    try:
        rsi = float(row.get("RSI14", 50))
    except Exception:
        rsi = 50.0

    # ======================================================
    # NORMALIZATION
    # ======================================================
    trend = str(trend).upper()
    status = str(status).upper()
    mode = str(mode).strip().title()

    # ======================================================
    # MODE: MOMENTUM
    # ======================================================
    # Filosofi:
    # - Hanya entry saat trend kuat
    # - Hindari overbought ekstrem
    if mode == "Momentum":
        if (
            sync >= 1
            and score >= 75
            and trend == "UP"
            and status in ("READY", "BREAKOUT")
            and 40 <= rsi <= 70
        ):
            return "BUY"
        return "WAIT"

    # ======================================================
    # MODE: PULLBACK
    # ======================================================
    # Filosofi:
    # - Trend utama masih UP
    # - Harga sedang retrace / konsolidasi
    if mode == "Pullback":
        if (
            sync >= 1
            and score >= 70
            and trend == "UP"
            and status in ("PULLBACK", "RETEST", "CONSOLIDATION")
            and rsi >= 40
        ):
            return "BUY"
        return "WAIT"

    # ======================================================
    # MODE: MEAN REVERSION
    # ======================================================
    # Filosofi:
    # - Tidak peduli trend
    # - Fokus oversold ekstrem
    # - Risiko tinggi → hanya kondisi ketat
    if mode == "Mean Reversion":
        if rsi <= 30:
            return "BUY"
        return "WAIT"

    # ======================================================
    # FALLBACK (AMAN)
    # ======================================================
    return "WAIT"
