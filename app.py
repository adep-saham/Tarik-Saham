import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import altair as alt

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
            Hitung & jelaskan EMA20/50, %R(14), CCI(200), AO, RSI, MACD, ATR, Volume langsung dari data Yahoo Finance.
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
    df = df.rename(columns=str.capitalize)  # Open, High, Low, Close, Volume

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

    # ATR(14)
    prev_close = df["Close"].shift(1)
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - prev_close).abs()
    tr3 = (df["Low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR14"] = tr.rolling(14).mean()

    # RSI(14)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI14"] = 100 - (100 / (1 + rs))

    # MACD (12,26,9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACDsignal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACDhist"] = df["MACD"] - df["MACDsignal"]

    # Volume MA20 & rasio (versi simpel dan aman)
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()

    # pakai numpy array 1D, apapun bentuk aslinya
    vol_arr = np.asarray(df["Volume"], dtype="float64").reshape(-1)
    vol_ma_arr = np.asarray(df["VOL_MA20"], dtype="float64").reshape(-1)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = vol_arr / vol_ma_arr

    # ganti inf / -inf jadi NaN
    ratio[~np.isfinite(ratio)] = np.nan

    # assign langsung ke kolom
    df["VolRatio20"] = ratio

    return df


def safe_float(val):
    """
    Paksa nilai apa pun (scalar / Series / ndarray) menjadi float tunggal.
    Jika tidak bisa atau NaN -> kembalikan np.nan.
    """
    if isinstance(val, (pd.Series, list, np.ndarray)):
        try:
            val = val[-1]
        except Exception:
            try:
                val = val.iloc[-1]
            except Exception:
                return np.nan
    try:
        f = float(val)
        if np.isnan(f):
            return np.nan
        return f
    except Exception:
        return np.nan

def interpret_last(row):
    """
    Terima Series (1 baris) atau DataFrame, ambil baris terakhir,
    lalu buat interpretasi indikator.
    """
    if isinstance(row, pd.DataFrame):
        row = row.iloc[-1]

    desc = {}

    close    = safe_float(row.get("Close"))
    ema20    = safe_float(row.get("EMA20"))
    ema50    = safe_float(row.get("EMA50"))
    wr       = safe_float(row.get("WR14"))
    cci      = safe_float(row.get("CCI200"))
    ao       = safe_float(row.get("AO"))
    vol      = safe_float(row.get("Volume"))
    vol_ma20 = safe_float(row.get("VOL_MA20"))
    rsi      = safe_float(row.get("RSI14"))
    macd     = safe_float(row.get("MACD"))
    macd_h   = safe_float(row.get("MACDhist"))

    # ---------- Trend EMA ----------
    if not np.isnan(ema20) and not np.isnan(ema50) and not np.isnan(close):
        if ema20 > ema50 and close > ema20:
            desc["Trend EMA"] = "Uptrend kuat (Close > EMA20 > EMA50)."
        elif ema20 > ema50 and close <= ema20:
            desc["Trend EMA"] = "Uptrend, tapi sedang koreksi ke EMA20."
        elif ema20 <= ema50 and close > ema20:
            desc["Trend EMA"] = "Potensi reversal naik (Close di atas EMA20 namun EMA20 masih di bawah EMA50)."
        else:
            desc["Trend EMA"] = "Downtrend / lemah (EMA20 di bawah EMA50 dan harga di bawah EMA20)."
    else:
        desc["Trend EMA"] = "Data belum cukup untuk membaca EMA (periode terlalu pendek?)."

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
        desc["CCI(200)"] = "Data belum cukup untuk menghitung CCI(200) (butuh ≥ 200 candle)."
    elif cci > 100:
        desc["CCI(200)"] = f"{cci:.1f} → Momentum naik kuat di timeframe besar."
    elif cci < -100:
        desc["CCI(200)"] = f"{cci:.1f} → Momentum turun kuat di timeframe besar."
    else:
        desc["CCI(200)"] = f"{cci:.1f} → Momentum masih normal."

    # ---------- AO ----------
    if np.isnan(ao):
        desc["AO"] = "Data belum cukup untuk menghitung AO (butuh ≥ 34 candle)."
    elif ao > 0:
        desc["AO"] = f"{ao:.4f} → Bias bullish (histogram di atas 0)."
    elif ao < 0:
        desc["AO"] = f"{ao:.4f} → Bias bearish (histogram di bawah 0)."
    else:
        desc["AO"] = f"{ao:.4f} → Netral."

    # ---------- Volume ----------
    if np.isnan(vol) or np.isnan(vol_ma20) or vol_ma20 == 0:
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

    # ---------- RSI(14) ----------
    if np.isnan(rsi):
        desc["RSI(14)"] = "Data belum cukup untuk menghitung RSI(14)."
    elif rsi >= 70:
        desc["RSI(14)"] = f"{rsi:.1f} → Overbought."
    elif rsi <= 30:
        desc["RSI(14)"] = f"{rsi:.1f} → Oversold (potensi rebound)."
    else:
        desc["RSI(14)"] = f"{rsi:.1f} → Zona netral."

    # ---------- MACD ----------
    if np.isnan(macd) or np.isnan(macd_h):
        desc["MACD"] = "Data belum cukup untuk MACD."
    else:
        if macd > 0 and macd_h > 0:
            desc["MACD"] = f"MACD {macd:.4f}, histogram positif → momentum bullish."
        elif macd < 0 and macd_h < 0:
            desc["MACD"] = f"MACD {macd:.4f}, histogram negatif → momentum bearish."
        else:
            desc["MACD"] = f"MACD {macd:.4f}, histogram mendekati 0 → momentum melemah / transisi."

    return desc

def detect_patterns(df: pd.DataFrame):
    """
    Deteksi pola: breakout 20 hari, support/resistance, EMA cross, divergence sederhana AO vs harga.
    Semua nilai penting dipaksa jadi float (safe_float) agar tidak ada ValueError dari Series.
    """
    patterns = []
    if len(df) < 5:
        patterns.append("Data terlalu pendek untuk deteksi pola (butuh ≥ 5 bar).")
        return patterns

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close  = safe_float(last.get("Close"))
    ema20  = safe_float(last.get("EMA20"))
    ema50  = safe_float(last.get("EMA50"))
    prev_ema20 = safe_float(prev.get("EMA20"))
    prev_ema50 = safe_float(prev.get("EMA50"))

    # ---------- Breakout 20 hari + Support / Resistance ----------
    if len(df) >= 20:
        highest_close_20_prev = safe_float(df["Close"].rolling(20).max().iloc[-2])
        if (not np.isnan(close)) and (not np.isnan(highest_close_20_prev)) and close > highest_close_20_prev:
            patterns.append(
                f"Breakout 20 hari: Close {close:.2f} di atas high 20-bar sebelumnya ({highest_close_20_prev:.2f})."
            )

        support_20 = safe_float(df["Low"].rolling(20).min().iloc[-1])
        resist_20  = safe_float(df["High"].rolling(20).max().iloc[-1])
        if not np.isnan(support_20) and not np.isnan(resist_20):
            patterns.append(
                f"Level support/resistance 20 hari: Support ~{support_20:.2f}, Resistance ~{resist_20:.2f}."
            )

    # ---------- EMA cross ----------
    if not any(np.isnan(x) for x in [ema20, ema50, prev_ema20, prev_ema50]):
        prev_rel = np.sign(prev_ema20 - prev_ema50)
        now_rel  = np.sign(ema20 - ema50)
        if prev_rel <= 0 and now_rel > 0:
            patterns.append("EMA20 baru saja golden cross ke atas EMA50 (sinyal bullish menengah).")
        elif prev_rel >= 0 and now_rel < 0:
            patterns.append("EMA20 baru saja death cross ke bawah EMA50 (sinyal bearish menengah).")

    # ---------- Divergence sederhana AO vs harga ----------
    if len(df) >= 60 and df["AO"].notna().sum() >= 10:
        win_recent = df.iloc[-30:]
        win_prev   = df.iloc[-60:-30]

        price_high_recent = safe_float(win_recent["Close"].max())
        price_high_prev   = safe_float(win_prev["Close"].max())
        ao_high_recent    = safe_float(win_recent["AO"].max())
        ao_high_prev      = safe_float(win_prev["AO"].max())

        price_low_recent = safe_float(win_recent["Close"].min())
        price_low_prev   = safe_float(win_prev["Close"].min())
        ao_low_recent    = safe_float(win_recent["AO"].min())
        ao_low_prev      = safe_float(win_prev["AO"].min())

        if (not np.isnan(price_high_recent) and not np.isnan(price_high_prev) and
            not np.isnan(ao_high_recent) and not np.isnan(ao_high_prev)):
            if price_high_recent > price_high_prev and ao_high_recent <= ao_high_prev:
                patterns.append("Indikasi bearish divergence: harga membuat high lebih tinggi, AO tidak mengkonfirmasi.")

        if (not np.isnan(price_low_recent) and not np.isnan(price_low_prev) and
            not np.isnan(ao_low_recent) and not np.isnan(ao_low_prev)):
            if price_low_recent < price_low_prev and ao_low_recent >= ao_low_prev:
                patterns.append("Indikasi bullish divergence: harga membuat low lebih rendah, AO tidak mengkonfirmasi.")

    return patterns


def generate_entry_plan(df: pd.DataFrame):
    """
    Generator entry/exit sederhana:
    - Setup Breakout: strong uptrend + breakout 20 bar + AO & volume mendukung
    - Setup Pullback: uptrend + %R oversold (pullback ke EMA20)
    """
    if len(df) < 30:
        return {"status": "Data terlalu pendek untuk membuat trading plan (butuh ≥ 30 bar)."}

    last = df.iloc[-1]
    close = safe_float(last["Close"])
    ema20 = safe_float(last["EMA20"])
    ema50 = safe_float(last["EMA50"])
    atr = safe_float(last.get("ATR14"))
    wr = safe_float(last["WR14"])
    ao = safe_float(last["AO"])
    vol = safe_float(last["Volume"])
    vol_ma20 = safe_float(last["VOL_MA20"])

    vol_ratio = np.nan
    if not np.isnan(vol_ma20) and vol_ma20 != 0:
        vol_ratio = vol / vol_ma20

    support_20 = df["Low"].rolling(20).min().iloc[-1]
    resist_20 = df["High"].rolling(20).max().iloc[-1]

    if np.isnan(atr) or atr == 0:
        atr = safe_float((df["High"] - df["Low"]).rolling(14).mean().iloc[-1])

    # Klasifikasi trend
    trend = "unknown"
    if not np.isnan(ema20) and not np.isnan(ema50) and not np.isnan(close):
        if ema20 > ema50 and close > ema20:
            trend = "strong_up"
        elif ema20 > ema50:
            trend = "up"
        elif ema20 < ema50 and close < ema20:
            trend = "down"
        else:
            trend = "sideways"

    plan = {}

    # Breakout?
    breakout = False
    if len(df) >= 20:
        prev_high_20 = df["Close"].rolling(20).max().iloc[-2]
        if close > prev_high_20:
            breakout = True

    # Setup Breakout
    if trend == "strong_up" and breakout and ao > 0 and (np.isnan(vol_ratio) or vol_ratio >= 1.5):
        entry_low = close - 0.5 * atr
        entry_high = close + 0.2 * atr
        stop = close - 1.8 * atr
        target = close + 3.0 * atr
        entry_mid = (entry_low + entry_high) / 2
        rr = (target - entry_mid) / (entry_mid - stop) if (entry_mid - stop) != 0 else np.nan
        plan.update({
            "status": "Setup Breakout",
            "entry_type": "Breakout Follow",
            "entry_low": entry_low,
            "entry_high": entry_high,
            "stop": stop,
            "target": target,
            "RR": rr,
            "note": "Breakout uptrend dengan volume & momentum mendukung."
        })

    # Setup Pullback ke EMA20
    elif trend in ["strong_up", "up"] and wr <= -80:
        entry_low = ema20 - 0.5 * atr
        entry_high = ema20 + 0.5 * atr
        stop = ema50 - 0.5 * atr
        target = resist_20
        entry_mid = (entry_low + entry_high) / 2
        rr = (target - entry_mid) / (entry_mid - stop) if (entry_mid - stop) != 0 else np.nan
        plan.update({
            "status": "Setup Pullback",
            "entry_type": "Pullback EMA20",
            "entry_low": entry_low,
            "entry_high": entry_high,
            "stop": stop,
            "target": target,
            "RR": rr,
            "note": "Uptrend, harga oversold vs %R(14) → peluang buy di sekitar EMA20."
        })

    # Tidak ada setup menarik
    else:
        plan.update({
            "status": "No Trade",
            "entry_type": "Watchlist",
            "note": "Sinyal belum ideal (trend lemah / tidak jelas / belum ada pullback menarik)."
        })

    plan["trend"] = trend
    plan["ATR14"] = atr
    plan["vol_ratio20"] = vol_ratio
    plan["support20"] = support_20
    plan["resistance20"] = resist_20

    return plan

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
            st.write(
                f"Baris data: **{len(df)}** | Rentang: **{df.index.min().date()}** s/d **{df.index.max().date()}**"
            )
            st.dataframe(df.tail().round(4))

            # Hitung indikator
            df_ind = calc_indicators(df)
            last = df_ind.iloc[-1]

            # Tabel indikator terakhir
            st.markdown("<div class='section-title'>🧮 Nilai Indikator Terakhir</div>", unsafe_allow_html=True)

            table = pd.DataFrame({
                "Indikator": [
                    "Close", "EMA20", "EMA50", "%R(14)", "CCI(200)",
                    "AO", "RSI(14)", "MACD", "MACD_hist", "ATR14",
                    "Volume", "VOL_MA20", "Vol / MA20"
                ],
                "Nilai": [
                    last["Close"],
                    last["EMA20"],
                    last["EMA50"],
                    last["WR14"],
                    last["CCI200"],
                    last["AO"],
                    last["RSI14"],
                    last["MACD"],
                    last["MACDhist"],
                    last["ATR14"],
                    last["Volume"],
                    last["VOL_MA20"],
                    last["VolRatio20"],
                ]
            })
            st.dataframe(table)

            # Interpretasi indikator
            st.markdown("<div class='section-title'>🧠 Interpretasi Otomatis</div>", unsafe_allow_html=True)
            desc = interpret_last(last)
            for k, v in desc.items():
                st.markdown(f"- **{k}**: {v}")

            # Pola teknikal
            st.markdown("<div class='section-title'>📌 Sinyal Pola Teknis</div>", unsafe_allow_html=True)
            patterns = detect_patterns(df_ind)
            if patterns:
                for p in patterns:
                    st.markdown(f"- {p}")
            else:
                st.markdown("- Tidak ada pola menonjol yang terdeteksi.")

            # Entry / Exit plan
            st.markdown("<div class='section-title'>🎯 Rencana Entry & Exit (Eksperimental)</div>", unsafe_allow_html=True)
            plan = generate_entry_plan(df_ind)
            st.write(f"Status: **{plan.get('status', 'N/A')}**")
            st.write(f"Jenis setup: **{plan.get('entry_type', 'N/A')}**")

            if plan.get("status") != "No Trade" and "entry_low" in plan:
                plan_table = pd.DataFrame({
                    "Parameter": [
                        "Entry Low", "Entry High", "Stop Loss", "Target", "RR",
                        "Trend", "ATR14", "Vol / MA20", "Support20", "Resistance20"
                    ],
                    "Nilai": [
                        plan.get("entry_low"),
                        plan.get("entry_high"),
                        plan.get("stop"),
                        plan.get("target"),
                        plan.get("RR"),
                        plan.get("trend"),
                        plan.get("ATR14"),
                        plan.get("vol_ratio20"),
                        plan.get("support20"),
                        plan.get("resistance20"),
                    ]
                })
                st.dataframe(plan_table)
            st.markdown(f"**Catatan:** {plan.get('note', '-')}")

            # ===================== CHART DENGAN ALTAIR =====================
            st.markdown("<div class='section-title'>📈 Chart Harga & Indikator</div>", unsafe_allow_html=True)

            chart_data = df_ind.copy().reset_index()
            if "Date" not in chart_data.columns:
                chart_data = chart_data.rename(columns={chart_data.columns[0]: "Date"})

            c1, c2 = st.columns(2)

            # KIRI: Harga + EMA dan AO
            with c1:
                st.markdown("**Close + EMA20/EMA50**")

                price_chart = (
                    alt.Chart(chart_data)
                    .mark_line()
                    .encode(
                        x="Date:T",
                        y=alt.Y("Close:Q", title="Harga"),
                        color=alt.value("#F5D26B")
                    )
                )
                ema20_chart = (
                    alt.Chart(chart_data)
                    .mark_line()
                    .encode(
                        x="Date:T",
                        y="EMA20:Q",
                        color=alt.value("#00E0FF")
                    )
                )
                ema50_chart = (
                    alt.Chart(chart_data)
                    .mark_line()
                    .encode(
                        x="Date:T",
                        y="EMA50:Q",
                        color=alt.value("#FF6B6B")
                    )
                )
                st.altair_chart(
                    (price_chart + ema20_chart + ema50_chart).interactive(),
                    use_container_width=True,
                )

                st.markdown("**AO (Awesome Oscillator)**")
                ao_chart = (
                    alt.Chart(chart_data)
                    .mark_bar()
                    .encode(
                        x="Date:T",
                        y=alt.Y("AO:Q", title="AO"),
                        color=alt.condition(
                            alt.datum.AO >= 0,
                            alt.value("#22c55e"),
                            alt.value("#ef4444"),
                        ),
                    )
                )
                st.altair_chart(ao_chart, use_container_width=True)

            # KANAN: Volume & CCI
            with c2:
                st.markdown("**Volume & Volume MA20**")
                vol_bar = (
                    alt.Chart(chart_data)
                    .mark_bar()
                    .encode(
                        x="Date:T",
                        y=alt.Y("Volume:Q", title="Volume"),
                        color=alt.value("#4b5563"),
                    )
                )
                vol_ma_line = (
                    alt.Chart(chart_data)
                    .mark_line()
                    .encode(
                        x="Date:T",
                        y="VOL_MA20:Q",
                        color=alt.value("#F5D26B"),
                    )
                )
                st.altair_chart((vol_bar + vol_ma_line).interactive(), use_container_width=True)

                st.markdown("**CCI(200)**")
                cci_chart = (
                    alt.Chart(chart_data)
                    .mark_line()
                    .encode(
                        x="Date:T",
                        y=alt.Y("CCI200:Q", title="CCI(200)"),
                        color=alt.value("#38bdf8"),
                    )
                )
                st.altair_chart(cci_chart.interactive(), use_container_width=True)

else:
    st.info("Masukkan kode saham di sidebar, lalu klik tombol **🚀 Analisa Saham**.")

# ===================== FOOTER =====================
st.markdown("""
<div class='footer-text'>
Technical Analyzer · EMA, %R, CCI, AO, RSI, MACD, ATR, Volume · Data dari Yahoo Finance.<br>
Gunakan sebagai alat bantu analisa, bukan rekomendasi beli/jual.
</div>
""", unsafe_allow_html=True)




