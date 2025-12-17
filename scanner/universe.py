import pandas as pd
import os

def load_idx_universe(path="data/idx_universe.csv"):
    if not os.path.exists(path):
        return []

    df = pd.read_csv(path)

    df["ticker"] = (
    df["ticker"]
    .astype(str)
    .str.upper()
    .str.strip()
    .apply(lambda x: f"{x}.JK" if not x.endswith(".JK") else x)
    )


    # ❌ JANGAN FILTER BOARD DULU
    # BIAR SEMUA SAHAM IDX MASUK

    return df["ticker"].dropna().unique().tolist()
