# scanner/scan_engine.py
import pandas as pd

def _ensure_ema(df: pd.DataFrame, span: int, colname: str) -> pd.DataFrame:
    if colname not in df.columns:
        df[colname] = df["Close"].ewm(span=span, adjust=False).mean()
    return df

def _ensure_rsi14(df: pd.DataFrame) -> pd.DataFrame:
    if "RSI14" not in df.columns:
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        rs = gain.rolling(14).mean() / loss.rolling(14).mean()
        df["RSI14"] = 100 - (100 / (1 + rs))
    return df
tickers = tickers[:1]

def scan_window(
    window: int,
    tickers: list[str],
    load_price_data,
    calc_indicators=None,
    relaxed: bool = True,
) -> tuple[list[str], dict]:

    results = []
    stats = {
        "total": 0,
        "none": 0,
        "short": 0,
        "no_close": 0,
        "nan_ind": 0,
        "cond_fail": 0,
        "exc": 0,
        "passed": 0,
    }

    min_len = window * 2

    for ticker in tickers:
        stats["total"] += 1
        try:
            # ⬇️ PAKSA LOAD DATA PANJANG
            df = load_price_data(ticker)


            if df is None or len(df) == 0:
                stats["none"] += 1
                continue

            if "Close" not in df.columns:
                stats["no_close"] += 1
                continue

            if len(df) < window * 2:
                stats["short"] += 1
                continue


            if calc_indicators is not None:
                df = calc_indicators(df)

            df = _ensure_ema(df, window, f"EMA{window}")
            df = _ensure_ema(df, window * 2, f"EMA{window*2}")
            df = _ensure_rsi14(df)

            last = df.iloc[-1]
            fast = last.get(f"EMA{window}")
            slow = last.get(f"EMA{window*2}")
            rsi = last.get("RSI14")

            if pd.isna(fast) or pd.isna(slow) or pd.isna(rsi):
                stats["nan_ind"] += 1
                continue

            ema_ok = (fast >= slow * 0.99) if relaxed else (fast > slow)
            rsi_ok = rsi >= 40

            if ema_ok and rsi_ok:
                results.append(ticker)
                stats["passed"] += 1
            else:
                stats["cond_fail"] += 1

        except Exception as e:
            stats["exc"] += 1
            stats["last_error"] = f"{ticker}: {e}"
            break


    return results, stats

