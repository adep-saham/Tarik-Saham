from core.data_loader import fetch_data
from core.indicators import calc_indicators
from core.ticker_utils import normalize_ticker

def prefilter_universe(tickers, period="6mo"):
    passed = []

    for t in tickers:
        try:
            ticker = normalize_ticker(t)
            df = fetch_data(ticker, period, "1d")

            if df.empty or len(df) < 50:
                continue

            df = calc_indicators(df)

            # === AMBIL NILAI TERAKHIR SEBAGAI FLOAT ===
            close = float(df["Close"].iloc[-1])
            ema20 = float(df["EMA20"].iloc[-1])
            volume = float(df["Volume"].iloc[-1])
            vol_ma20 = float(df["VOL_MA20"].iloc[-1])
            atr = float(df["ATR14"].iloc[-1])

            # === PREFILTER RULE ===
            if (
                close > ema20 and
                volume > vol_ma20 and
                atr > 0
            ):
                passed.append(t)

        except Exception:
            # jika satu saham error, skip saja
            continue

    return passed
