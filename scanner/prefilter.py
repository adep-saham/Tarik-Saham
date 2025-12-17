from core.data_loader import fetch_data
from core.indicators import calc_indicators
from core.ticker_utils import normalize_ticker

def prefilter_universe(tickers, period="6mo"):
    passed = []

    for t in tickers:
        ticker = normalize_ticker(t)
        df = fetch_data(ticker, period, "1d")
        if df.empty or len(df) < 50:
            continue

        df = calc_indicators(df)
        last = df.iloc[-1]

        if (
            last["Close"] > last["EMA20"]
            and last["Volume"] > last["VOL_MA20"]
            and last["ATR14"] > 0
        ):
            passed.append(t)

    return passed
