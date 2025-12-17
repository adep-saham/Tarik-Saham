from core.data_loader import fetch_data
from core.indicators import calc_indicators
from core.ticker_utils import normalize_ticker

def prefilter_universe(
    tickers,
    period="6mo",
    interval="1d",
    max_candidates=50
):
    """
    Fast prefilter for large universe (300–500 stocks).
    Returns limited shortlist for deeper analysis.
    """

    passed = []

    for t in tickers:
        try:
            ticker = normalize_ticker(t)
            df = fetch_data(ticker, period, interval)

            # === HARD SKIP ===
            if df.empty or len(df) < 60:
                continue

            # === HITUNG INDIKATOR RINGAN ===
            df = calc_indicators(df)

            # === AMBIL NILAI TERAKHIR (FLOAT ONLY) ===
            close = float(df["Close"].iloc[-1])
            ema20 = float(df["EMA20"].iloc[-1])
            ema50 = float(df["EMA50"].iloc[-1])
            volume = float(df["Volume"].iloc[-1])
            vol_ma20 = float(df["VOL_MA20"].iloc[-1])
            atr = float(df["ATR14"].iloc[-1])

            # === PREFILTER RULE (FAST & STRICT) ===
            if not (close > ema20 > ema50):
                continue

            if volume < 1.2 * vol_ma20:
                continue

            if atr / close < 0.01:  # min 1% range
                continue

            if close < 100:
                continue

            passed.append(t)

            # === LIMIT OUTPUT (ANTI OVERLOAD) ===
            if len(passed) >= max_candidates:
                break

        except Exception:
            continue

    return passed
