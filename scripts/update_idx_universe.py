import requests
import pandas as pd
from pathlib import Path

# ===============================
# IDX ENDPOINT (RESMI - DIPAKAI FRONTEND IDX)
# ===============================
IDX_URL = "https://www.idx.co.id/umbraco/surface/ListedCompany/GetListedCompany"

def download_idx_universe(output_path="data/idx_universe.csv"):
    print("🔽 Downloading IDX listed companies...")

    payload = {
        "start": 0,
        "length": 1000,   # cukup untuk seluruh saham
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    r = requests.post(IDX_URL, data=payload, headers=headers, timeout=30)
    r.raise_for_status()

    json_data = r.json()
    records = json_data.get("data", [])

    if not records:
        raise RuntimeError("IDX response kosong, endpoint mungkin berubah")

    df = pd.DataFrame(records)

    # === NORMALISASI KOLOM PENTING ===
    df = df.rename(columns={
        "Code": "ticker",
        "Name": "name",
        "ListingBoard": "board",
        "Status": "status",
    })

    df = df[["ticker", "name", "board", "status"]]

    df["ticker"] = df["ticker"].str.upper().str.strip()
    df["board"] = df["board"].str.upper().str.strip()
    df["status"] = df["status"].str.upper().str.strip()

    # === FILTER: HANYA SAHAM AKTIF ===
    df = df[df["status"] == "AKTIF"]

    # === PASTIKAN FOLDER ADA ===
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)
    print(f"✅ Saved {len(df)} saham ke {output_path}")

if __name__ == "__main__":
    download_idx_universe()
