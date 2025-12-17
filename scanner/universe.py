import pandas as pd

def load_idx_universe(
    path="data/idx_universe.csv",
    board_filter=("Main Board", "MAIN")
):
    df = pd.read_csv(path)

    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()

    if "board" in df.columns and board_filter:
        df = df[df["board"].isin(board_filter)]

    return df["ticker"].unique().tolist()
