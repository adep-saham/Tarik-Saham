# scanner/bandarmologi_engine.py
import re
import numpy as np
import pandas as pd


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    return out


def _parse_compact_number(x):
    """
    Parse format seperti:
    - "1,255.32 B" -> 1255320000000
    - "(617.60 B)" -> -617600000000
    - "284,657,113,140.00" -> 284657113140
    - "" / NaN -> np.nan
    """
    if x is None:
        return np.nan
    s = str(x).strip()
    if s == "" or s.lower() == "nan":
        return np.nan

    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()

    # hapus koma
    s = s.replace(",", "")

    # detect suffix
    m = re.match(r"^(-?\d+(\.\d+)?)\s*([kmbtKMBT])?$", s)
    if m:
        num = float(m.group(1))
        suf = m.group(3)
        mult = 1.0
        if suf:
            suf = suf.upper()
            if suf == "K":
                mult = 1e3
            elif suf == "M":
                mult = 1e6
            elif suf == "B":
                mult = 1e9
            elif suf == "T":
                mult = 1e12
        val = num * mult
        return -val if neg else val

    # fallback: coba float langsung
    try:
        val = float(s)
        return -val if neg else val
    except Exception:
        return np.nan


def _normalize_broker_type(x: str) -> str:
    x = str(x).strip().upper()
    if x in ["BY", "B", "BUY"]:
        return "BUY"
    if x in ["SL", "S", "SELL"]:
        return "SELL"
    return "OTHER"


def compute_bandar_rekap(df: pd.DataFrame, ticker: str | None = None) -> pd.DataFrame:
    """
    AUTO-DETECT input formats.

    OUTPUT 1 (Broker Rekap):
      broker, buy_lot, sell_lot, net_lot, remaining_lot, wap_buy, wap_sell

    OUTPUT 2 (Bandar Value Table):
      symbol, bandar_value, bandar_value_ma10, bandar_value_ma20,
      previous_bandar_value, value_ma20, signal
    """
    if df is None or df.empty:
        raise ValueError("CSV kosong.")

    df0 = _norm_cols(df)

    # ======================================================
    # FORMAT A: Transaction-level broker (Stockbit/raw)
    # columns: date | broker | type | lot | avg(optional)
    # ======================================================
    if {"broker", "type", "lot"}.issubset(df0.columns):
        if "date" not in df0.columns:
            # date optional, tapi broker/type/lot cukup
            df0["date"] = pd.NaT
        else:
            df0["date"] = pd.to_datetime(df0["date"], errors="coerce")

        df0["broker"] = df0["broker"].astype(str).str.upper().str.strip()
        df0["type"] = df0["type"].apply(_normalize_broker_type)
        df0["lot"] = pd.to_numeric(df0["lot"], errors="coerce").fillna(0).astype(int)
        df0["avg"] = pd.to_numeric(df0["avg"], errors="coerce") if "avg" in df0.columns else np.nan

        buy_lot = df0[df0["type"] == "BUY"].groupby("broker")["lot"].sum().rename("buy_lot")
        sell_lot = df0[df0["type"] == "SELL"].groupby("broker")["lot"].sum().rename("sell_lot")

        def _wap(sub):
            if "avg" not in sub.columns or sub["avg"].isna().all():
                return np.nan
            q = sub["lot"].sum()
            return (sub["avg"] * sub["lot"]).sum() / q if q else np.nan

        wap_buy = df0[df0["type"] == "BUY"].groupby("broker").apply(_wap).rename("wap_buy")
        wap_sell = df0[df0["type"] == "SELL"].groupby("broker").apply(_wap).rename("wap_sell")

        out = pd.concat([buy_lot, sell_lot, wap_buy, wap_sell], axis=1).fillna(0)
        out["net_lot"] = out.get("buy_lot", 0) - out.get("sell_lot", 0)
        out["remaining_lot"] = out["net_lot"]
        out = out.reset_index().sort_values("net_lot", ascending=False).reset_index(drop=True)

        return out[["broker", "buy_lot", "sell_lot", "net_lot", "remaining_lot", "wap_buy", "wap_sell"]]

    # ======================================================
    # FORMAT B: Aggregated broker
    # columns: broker | buy lot | sell lot | net lot(optional)
    # ======================================================
    if {"broker", "buy lot", "sell lot"}.issubset(df0.columns):
        out = df0.copy()
        out["broker"] = out["broker"].astype(str).str.upper().str.strip()
        out["buy_lot"] = pd.to_numeric(out["buy lot"], errors="coerce").fillna(0).astype(int)
        out["sell_lot"] = pd.to_numeric(out["sell lot"], errors="coerce").fillna(0).astype(int)
        out["net_lot"] = pd.to_numeric(out.get("net lot", out["buy_lot"] - out["sell_lot"]), errors="coerce").fillna(
            out["buy_lot"] - out["sell_lot"]
        )
        out["remaining_lot"] = out["net_lot"]
        out["wap_buy"] = np.nan
        out["wap_sell"] = np.nan

        out = out[["broker", "buy_lot", "sell_lot", "net_lot", "remaining_lot", "wap_buy", "wap_sell"]]
        return out.sort_values("net_lot", ascending=False).reset_index(drop=True)

    # ======================================================
    # FORMAT C: Bandar Value table (CSV kamu)
    # columns: symbol | bandar value | bandar value ma 10/20 | previous bandar value | value ma 20
    # ======================================================
    # NOTE: kolom 'unnamed: x' akan diabaikan
    if "symbol" in df0.columns and "bandar value" in df0.columns:
        out = df0.copy()

        # optional filter by ticker (single stock)
        if ticker:
            t = str(ticker).replace(".JK", "").upper().strip()
            out["symbol"] = out["symbol"].astype(str).str.upper().str.strip()
            out = out[out["symbol"] == t].copy()

        # parse numeric
        out["bandar_value"] = out["bandar value"].apply(_parse_compact_number)
        out["bandar_value_ma20"] = out.get("bandar value ma 20", pd.Series([np.nan] * len(out))).apply(_parse_compact_number)
        out["bandar_value_ma10"] = out.get("bandar value ma 10", pd.Series([np.nan] * len(out))).apply(_parse_compact_number)
        out["previous_bandar_value"] = out.get("previous bandar value", pd.Series([np.nan] * len(out))).apply(_parse_compact_number)
        out["value_ma20"] = out.get("value ma 20", pd.Series([np.nan] * len(out))).apply(_parse_compact_number)

        # signal sederhana (bisa kamu ubah nanti)
        # UP kalau BV > MA20 dan BV > MA10
        def _sig(r):
            bv = r["bandar_value"]
            ma20 = r["bandar_value_ma20"]
            ma10 = r["bandar_value_ma10"]
            if pd.isna(bv):
                return "NA"
            if (not pd.isna(ma20)) and (not pd.isna(ma10)) and bv > ma20 and bv > ma10:
                return "UPTREND"
            if (not pd.isna(ma20)) and bv < ma20:
                return "DOWN"
            return "SIDE"

        out["signal"] = out.apply(_sig, axis=1)

        # return compact output
        keep = [
            "symbol",
            "bandar_value",
            "bandar_value_ma10",
            "bandar_value_ma20",
            "previous_bandar_value",
            "value_ma20",
            "signal",
        ]
        keep = [c for c in keep if c in out.columns]
        out = out[keep].copy()

        # kalau tidak difilter ticker: sort by strength (BV - MA20)
        if "bandar_value_ma20" in out.columns:
            out["bv_minus_ma20"] = out["bandar_value"] - out["bandar_value_ma20"]
            out = out.sort_values("bv_minus_ma20", ascending=False).drop(columns=["bv_minus_ma20"], errors="ignore")

        return out.reset_index(drop=True)

    # ======================================================
    # UNKNOWN FORMAT
    # ======================================================
    raise ValueError(f"Format CSV tidak dikenali. Kolom ditemukan: {list(df0.columns)}")
