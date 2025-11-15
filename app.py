import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# ===================== PAGE CONFIG =====================
st.set_page_config(
    page_title="Technical Analyzer - Yahoo Finance",
    layout="wide"
)

# ===================== GOLD-BLACK THEME =====================
st.markdown("""
    <style>
    .main {background-color: #050608; color: #F8F3E7;}
    body {background-color: #050608;}
    .title-text {
        font-size: 32px;
        font-weight: 900;
        color: #F5D26B;
    }
    .subtitle-text {
        font-size: 15px;
        color: #D8D2C2;
        margin-top: -4px;
    }
    .section-title {
        font-size: 20px;
        font-weight: 700;
        color: #F5D26B;
        padding-top: 14px;
        padding-bottom: 4px;
    }
    .info-box {
        padding: 10px 16px;
        background-color: #111317;
        border-radius: 8px;
        border-left: 3px solid #F5D26B;
        color: #E7E0CF;
        font-size: 13px;
        margin-top: 10px;
        margin-bottom: 6px;
    }
    .footer-text {
        text-align: center;
        padding-top: 25px;
        padding-bottom: 10px;
        color: #A99C7A;
        font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# ===================== HEADER =====================
st.markdown("""
<div style='display:flex; align-items:center; gap:12px; margin-bottom:8px;'>
    <img src="https://img.icons8.com/fluency/96/combo-chart--v1.png" width="60">
    <div>
        <div class="title-text">Technical Analyzer (Yahoo Finance)</div>
        <div class="subtitle-text">
            Hitung & jelaskan EMA20/50, %R(14), CCI(200), AO, dan Volume langsung dari data Yahoo Finance.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ===================== SIDEBAR INPUT =====================
st.sidebar.header("⚙️ Pengaturan")

default_ticker = "BUMI.JK"
ticker = st.sidebar.text_input(
    "Kode saham (Yahoo Finance)",
    value=default_ticker,
    help="Contoh: BUMI.JK, TLKM.JK, BBCA.JK, AAPL, TSLA, dsb."
)

period = st.sidebar.selectbox(
    "Periode data",
    options=["3mo", "6mo", "1y", "2y", "5y"],
    index=2,
    help="Rentang waktu historis yang akan diambil."
)

interval = st.sidebar.selectbox(
    "Interval candle",
    options=["1d", "1h", "30m"],
    index=0,
    help="Interval bar untuk perhitungan indikator."
)

analyze_btn = st.sidebar.button("🚀 Analisa Saham", use_container_width=True)

st.markdown("<div class='section-title'>📌 Info</div>", unsafe_allow_html=True)
st.markdown("""
<div class="info-box">
Masukkan kode saham sesuai format Yahoo Finance. Untuk saham Indonesia gunakan akhiran <b>.JK</b>, misalnya:
<ul>
<li><b>BUMI.JK</b> – Bumi Resources</li>
<li><b>ANTM.JK</b> – Aneka Tambang</li>
<li><b>BBRI.JK</b> – Bank Rakyat Indonesia</li>
</ul>
Aplikasi ini mengambil data OHLCV dari Yahoo Finance secara langsung, tanpa perlu TradingView berbayar.
</div>
""", unsafe_allow_html=True)

# ===================== HELPER FUNGSI =====================

@st.cache_data(show_spinner=False)
def fetch_data(ticker: str, period: str, interval: str):
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False)
    return df

def calc_indicators(df: pd.DataFrame):
    df = df.copy()
    df = df.rename(columns=str.capitalize)  # Open, High, Low, Close, Volume dsb.

    if len(df) == 0:
        raise ValueError("Data kosong dari Yahoo Finance.")

    # EMA 20 & EMA 50
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # Williams %R (14)
    period_wr = 14
    hh14 = df["High"].rolling(period_wr).max()
    ll14 = df["Low"].rolling(period_wr).min()
    df["WR14"] = -100 * (hh14 - df["Close"]) / (hh14 - ll14)

    # CCI (200)
    period_cci = 200
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    sma_tp = tp.rolling(period_cci).mean()
    mad = (tp - sma_tp).abs().rolling(period_cci).mean()
    df["CCI200"] = (tp - sma_tp) / (0.015 * mad)

    # Awesome Oscillator (AO)
    mid = (df["High"] + df["Low"]) / 2.0
    sma5 = mid.rolling(5).mean()
    sma34 = mid.rolling(34).mean()
    df["AO"] = sma5 - sma34

    # Volume MA20
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()

    return df

import pandas as pd
import numpy as np

def interpret_last(row):
    """
    Terima Series (satu baris) atau DataFrame (beberapa baris),
    lalu ambil baris terakhir dan kembalikan interpretasi indikator.
    """
    # Kalau yang dikirim DataFrame, ambil baris terakhir dulu
    if isinstance(row, pd.DataFrame):
        row = row.iloc[-1]

    desc = {}

    # Ambil nilai sebagai float Python biasa (bukan Series)
    close = float(row["Close"])
    ema20 = float(row["EMA20"])
    ema50 = float(row["EMA50"])
    wr    = float(row["WR14"])   if not pd.isna(row["WR14"])   else np.nan
    cci   = float(row["CCI200"]) if not pd.isna(row["CCI200"]) else np.nan
    ao    = float(row["AO"])     if not pd.isna(row["AO"])     else np.nan
    vol   = float(row["Volume"])
    vol_ma20 = float(row["VOL_MA20"]) if not pd.isna(row["VOL_MA20"]) else np.nan

    # ---------- Trend EMA ----------
    if ema20 > ema50 and close > ema20:
        desc["Trend EMA"] = "Uptrend kuat (Close > EMA20 > EMA50)."
    elif ema20 > ema50 and close <= ema20:
        desc["Trend EMA"] = "Uptrend, tapi sedang koreksi ke EMA20."
    elif ema20 <= ema50 and close > ema20:
        desc["Trend EMA"] = "Potensi reversal naik (Close di atas EMA20 namun EMA20 masih di bawah EMA50)."
    else:
        desc["Trend EMA"] = "Downtrend / lemah (EMA20 di bawah EMA50 dan harga di bawah EMA20)."

    # ---------- %R(14) ----------
    if np.isnan(wr):
        desc["%R(14)"] = "Data belum cukup untuk menghitung %R(14)."
    elif wr <= -80:
        desc["%R(14)"] = f"{wr:.1f} → Oversold (potensi rebound jangka pendek)."
    elif wr >= -20:
        desc["%R(14)"] = f"{wr:.1f} → Overbought (rawan koreksi jangka pendek)."
    else:
        desc["%R(14)"] = f"{wr:.1f} → Zona netral."

    # ---------- CCI(200) ----------
    if np.isnan(cci):
        desc["CCI(200)"] = "Data belum cukup untuk menghitung CCI(200)."
    elif cci > 100:
        desc["CCI(200)"] = f"{cci:.1f} → Momentum naik kuat di timeframe besar."
    elif cci < -100:
        desc["CCI(200)"] = f"{cci:.1f} → Momentum turun kuat di timeframe besar."
    else:
        desc["CCI(200)"] = f"{cci:.1f} → Momentum masih normal."

    # ---------- AO ----------
    if np.isnan(ao):
        desc["AO"] = "Data belum cukup untuk menghitung AO."
    elif ao > 0:
        desc["AO"] = f"{ao:.4f} → Bias bullish (histogram di atas 0)."
    elif ao < 0:
        desc["AO"] = f"{ao:.4f} → Bias bearish (histogram di bawah 0)."
    else:
        desc["AO"] = f"{ao:.4f} → Netral."

    # ---------- Volume ----------
    if np.isnan(vol_ma20) or vol_ma20 == 0:
        vol_text = "Data belum cukup untuk menghitung Volume MA20."
    else:
        ratio = vol / vol_ma20
        if ratio >= 2:
            vol_text = f"Volume {ratio:.1f}× di atas rata-rata 20 hari → spike besar (potensi pergerakan signifikan)."
        elif ratio >= 1.2:
            vol_text = f"Volume {ratio:.1f}× di atas rata-rata → tekanan beli/jual mulai meningkat."
        else:
            vol_text = f"Volume {ratio:.1f}× dari rata-rata → aktivitas normal/rendah."
    desc["Volume"] = vol_text

    return desc


# ===================== MAIN FLOW =====================
if analyze_btn:
    if not ticker:
        st.error("Mohon isi kode saham terlebih dahulu.")
    else:
        with st.spinner(f"Mengambil data {ticker} dari Yahoo Finance..."):
            df = fetch_data(ticker, period, interval)

        if df.empty:
            st.error("Data kosong. Cek kembali kode saham / periode / interval.")
        else:
            st.markdown("<div class='section-title'>📊 Data Harga (ringkasan)</div>", unsafe_allow_html=True)
            st.write(f"Baris data: **{len(df)}** | Rentang: **{df.index.min().date()}** s/d **{df.index.max().date()}**")
            st.dataframe(df.tail().round(4))

            # Hitung indikator
            df_ind = calc_indicators(df)
            last = df_ind.iloc[-1]
            desc = interpret_last(last)
            # Tabel indikator terakhir
            st.markdown("<div class='section-title'>🧮 Nilai Indikator Terakhir</div>", unsafe_allow_html=True)

            table = pd.DataFrame({
                "Indikator": ["Close", "EMA20", "EMA50", "%R(14)", "CCI(200)", "AO", "Volume", "VOL_MA20"],
                "Nilai": [
                    last["Close"],
                    last["EMA20"],
                    last["EMA50"],
                    last["WR14"],
                    last["CCI200"],
                    last["AO"],
                    last["Volume"],
                    last["VOL_MA20"],
                ]
            })
            st.dataframe(table)

            # Interpretasi
            st.markdown("<div class='section-title'>🧠 Interpretasi Otomatis</div>", unsafe_allow_html=True)
            desc = interpret_last(last)
            for k, v in desc.items():
                st.markdown(f"- **{k}**: {v}")

            # Chart
            st.markdown("<div class='section-title'>📈 Chart Harga & Indikator</div>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)

            with c1:
                st.markdown("**Close + EMA20/EMA50**")
                chart_df = df_ind[["Close", "EMA20", "EMA50"]].copy()
                chart_df.index = pd.to_datetime(df_ind.index)
                st.line_chart(chart_df)

                st.markdown("**AO (Awesome Oscillator)**")
                st.bar_chart(df_ind["AO"])

            with c2:
                st.markdown("**Volume & Volume MA20**")
                vol_df = df_ind[["Volume", "VOL_MA20"]].copy()
                vol_df.index = pd.to_datetime(df_ind.index)
                st.line_chart(vol_df)

                st.markdown("**CCI(200)**")
                st.line_chart(df_ind["CCI200"])

else:
    st.info("Masukkan kode saham di sidebar, lalu klik tombol **🚀 Analisa Saham**.")

# ===================== FOOTER =====================
st.markdown("""
<div class='footer-text'>
Technical Analyzer · EMA, %R, CCI, AO, Volume · Data dari Yahoo Finance.<br>
Gunakan sebagai alat bantu analisa, bukan rekomendasi beli/jual.
</div>
""", unsafe_allow_html=True)


