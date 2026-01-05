import pandas as pd
import numpy as np

def normalize_broker_type(x: str) -> str:
    x = str(x).strip().upper()
    if x in ["BY", "B", "BUY"]:
        return "BUY"
    if x in ["SL", "S", "SELL"]:
        return "SELL"
    return "OTHER"


def compute_bandar_rekap(broker_df: pd.DataFrame) -> pd.DataFrame:
    """
    ENGINE BANDARMOLOGI – FINAL (ADAPTIVE)

    Supported CSV formats:
    1) TRANSACTION-LEVEL (Stockbit / raw)
       date | broker | type | lot | avg

    2) AGGREGATED (Bandar Akum / Uptrend)
       broker | buy lot | sell lot | net lot

    Output (STANDARD):
    broker, buy_lot, sell_lot, net_lot, remaining_lot, wap_buy, wap_sell
    """

    df = broker_df.copy()
    df.columns = [c.lower().strip() for c in df.columns]

    # ======================================================
    # CASE 1 — TRANSACTION LEVEL (ENGINE LAMA)
    # ======================================================
    if {"broker", "type", "lot"}.issubset(df.columns):
        df["broker"] = df["broker"].astype(str).str.upper().str.strip()
        df["type"] = df["type"].apply(normalize_broker_type)
        df["lot"] = pd.to_numeric(df["lot"], errors="coerce").fillna(0).astype(int)

        if "avg" in df.columns:
            df["avg"] = pd.to_numeric(df["avg"], errors="coerce")
        else:
            df["avg"] = np.nan

        buy = df[df["type"] == "BUY"].groupby("broker").agg(
            buy_lot=("lot", "sum")
        )
        sell = df[df["type"] == "SELL"].groupby("broker").agg(
            sell_lot=("lot", "sum")
        )

        def wap(sub):
            if sub["avg"].isna().all():
                return np.nan
            v = (sub["avg"] * sub["lot"]).sum(skipna=True)
            q = sub["lot"].sum()
            return (v / q) if q else np.nan

        wap_buy = df[df["type"] == "BUY"].groupby("broker").apply(wap).rename("wap_buy")
        wap_sell = df[df["type"] == "SELL"].groupby("broker").apply(wap).rename("wap_sell")

        out = pd.concat([buy, sell, wap_buy, wap_sell], axis=1).fillna(0)
        out["net_lot"] = out.get("buy_lot", 0) - out.get("sell_lot", 0)
        out["remaining_lot"] = out["net_lot"]

        out = out.reset_index()
        return (
            out[["broker", "buy_lot", "sell_lot", "net_lot", "remaining_lot", "wap_buy", "wap_sell"]]
            .sort_values("net_lot", ascending=False)
            .reset_index(drop=True)
        )

    # ======================================================
    # CASE 2 — AGGREGATED (CSV KAMU)
    # ======================================================
    if {"broker", "buy lot", "sell lot"}.issubset(df.columns):
        df["broker"] = df["broker"].astype(str).str.upper().str.strip()
        df["buy_lot"] = pd.to_numeric(df["buy lot"], errors="coerce").fillna(0).astype(int)
        df["sell_lot"] = pd.to_numeric(df["sell lot"], errors="coerce").fillna(0).astype(int)

        if "net lot" in df.columns:
            df["net_lot"] = pd.to_numeric(df["net lot"], errors="coerce").fillna(
                df["buy_lot"] - df["sell_lot"]
            )
        else:
            df["net_lot"] = df["buy_lot"] - df["sell_lot"]

        df["remaining_lot"] = df["net_lot"]
        df["wap_buy"] = np.nan
        df["wap_sell"] = np.nan

        return (
            df[["broker", "buy_lot", "sell_lot", "net_lot", "remaining_lot", "wap_buy", "wap_sell"]]
            .sort_values("net_lot", ascending=False)
            .reset_index(drop=True)
        )

    # ======================================================
    # UNKNOWN FORMAT
    # ======================================================
    raise ValueError(
        f"Format CSV bandarmologi tidak dikenali. Kolom ditemukan: {list(df.columns)}"
    )
