import pandas as pd
import requests
from io import BytesIO

# === URL RESMI IDX (BISA BERUBAH, INI CONTOH POLA UMUM) ===
IDX_URL = "https://www.idx.co.id/umbraco/surface/ListedCompany/GetListedCompany"

def download_idx_list():
    """
    Download daftar saham IDX dan simpan sebagai CSV.
    """
    # IDX endpoint biasanya butuh POST
    payload = {
        "start": 0,
        "length": 1000  # ambil semua
    }

    r = requests.post(IDX_URL, data=payload, timeout=30)
    r.raise_for_status()

    data = r.json()
    records = data.get("data", [])

    df = pd.DataFrame(records)

    # Normalisasi kolom penting
    df = df.rename(columns={
        "Code": "ticker",
        "Name": "name",
        "ListingBoard": "board"
    })

    df = df[["ticker", "name", "board"]]
    df["ticker"] = df["ticker"].str.upper().str.strip()

    df.to_csv("data/idx_universe.csv", index=False)
    print(f"Saved {len(df)} tickers to data/idx_universe.csv")

if __name__ == "__main__":
    download_idx_list()
