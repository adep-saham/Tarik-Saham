# scanner/bandarmologi_engine.py
import pandas as pd
import numpy as np

def normalize_broker_type(x: str) -> str:
    x = str(x).strip().upper()
    # dukung variasi: BY/SL atau B/S
    if x in ["BY", "B", "BUY"]:
        return "BUY"
    if x in ["SL", "S", "SELL"]:
        return "SELL"
    return "OTHER"

def compute_bandar_rekap(broker_df: pd.DataFrame) -> pd.DataFrame:
    """
    Output columns:
    broker, buy_lot, sell_lot, net_lot, remaining_lot, wap_buy, wap_sell
    remaining_lot = cumulative net lot (proxy sisa bandar)
    """
    df = broker_df.copy()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"date", "broker", "type", "lot"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ada: {missing}")

    df["date"] = pd.to_datetime(df["date"])
    df["broker"] = df["broker"].astype(str).str.upper().str.strip()
    df["type"] = df["type"].apply(normalize_broker_type)
    df["lot"] = pd.to_numeric(df["lot"], errors="coerce").fillna(0).astype(int)

    if "avg" in df.columns:
        df["avg"] = pd.to_numeric(df["avg"], errors="coerce")
    else:
        df["avg"] = np.nan  # boleh kosong

    # agregasi BUY/SELL
    buy = df[df["type"] == "BUY"].groupby("broker").agg(
        buy_lot=("lot", "sum"),
        buy_val=("avg", lambda s: np.nansum(s * 0))  # placeholder
    )
    sell = df[df["type"] == "SELL"].groupby("broker").agg(
        sell_lot=("lot", "sum"),
        sell_val=("avg", lambda s: np.nansum(s * 0))  # placeholder
    )

    # Weighted avg jika avg tersedia
    def wap(sub):
        if sub["avg"].isna().all():
            return np.nan
        v = (sub["avg"] * sub["lot"]).sum(skipna=True)
        q = sub["lot"].sum()
        return (v / q) if q else np.nan

    wap_buy = df[df["type"] == "BUY"].groupby("broker").apply(wap).rename("wap_buy")
    wap_sell = df[df["type"] == "SELL"].groupby("broker").apply(wap).rename("wap_sell")

    out = pd.concat([buy, sell, wap_buy, wap_sell], axis=1).fillna(0)

    if "buy_lot" not in out.columns:
        out["buy_lot"] = 0
    if "sell_lot" not in out.columns:
        out["sell_lot"] = 0
    if "wap_buy" not in out.columns:
        out["wap_buy"] = np.nan
    if "wap_sell" not in out.columns:
        out["wap_sell"] = np.nan

    out["net_lot"] = out["buy_lot"] - out["sell_lot"]

    # remaining_lot sebagai proxy sisa lot (akumulasi net lot)
    # kalau file sudah multi hari, kita bisa hitung cumulative per broker berdasar date:
    # tapi untuk rekap ringkas: anggap "remaining = net total"
    out["remaining_lot"] = out["net_lot"]

    out = out.reset_index().rename(columns={"index": "broker"})
    out = out[["broker", "buy_lot", "sell_lot", "net_lot", "remaining_lot", "wap_buy", "wap_sell"]]
    out = out.sort_values("net_lot", ascending=False).reset_index(drop=True)
    return out
