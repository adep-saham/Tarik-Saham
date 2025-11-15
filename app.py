import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import altair as alt

# ==========================
# TELEGRAM CONFIG (TOKEN ONLY)
# ==========================

TELEGRAM_TOKEN = "8214976664:AAHNNAzjAema7k-3hh87nITTl9OvsHhY6UE"  # TIDAK muncul di UI

# ========================
# FUNGSI TELEGRAM
# ========================

st.sidebar.header("📢 Telegram Alerts")
telegram_chat = st.sidebar.text_input("Chat ID Telegram")
send_alerts = st.sidebar.checkbox("Aktifkan Alert Telegram", value=False)

def send_telegram(msg, chat_id):
    import requests
    if not chat_id:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram Error:", e)

# ===================== PAGE CONFIG =====================
st.set_page_config(
    page_title="Tarik Saham - ADP",
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
        <div class="title-text">Tarik Saham - ADP</div>
        <div class="subtitle-text">
            EMA20/50, %R(14), CCI(200), AO, RSI, MACD, ATR, Volume + Pola + Entry Plan + Risk.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ===================== SIDEBAR INPUT =====================
st.sidebar.header("⚙️ Pengaturan Data")

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

st.sidebar.header("💰 Risk Management")
capital = st.sidebar.number_input(
    "Modal trading (nominal)",
    min_value=0.0,
    value=10_000_000.0,
    step=1_000_000.0,
    help="Dalam mata uang yang sama dengan harga saham."
)
risk_pct = st.sidebar.number_input(
    "Risk per trade (%)",
    min_value=0.1,
    max_value=10.0,
    value=1.0,
    step=0.1,
    help="Berapa % modal yang siap dirisikokan per 1 posisi."
)
lot_size = st.sidebar.number_input(
    "Ukuran 1 lot",
    min_value=1,
    value=100,
    step=1,
    help="Saham Indonesia biasanya 1 lot = 100 saham."
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

    # Volume MA20 & rasio (versi aman)
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()

    vol_arr = np.asarray(df["Volume"], dtype="float64").reshape(-1)
    vol_ma_arr = np.asarray(df["VOL_MA20"], dtype="float64").reshape(-1)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = vol_arr / vol_ma_arr
    ratio[~np.isfinite(ratio)] = np.nan

    df["VolRatio20"] = ratio

    return df

def safe_float(val):
    """
    Paksa nilai apa pun (scalar / Series / ndarray) menjadi float tunggal.
    Jika tidak bisa atau NaN -> kembalikan np.nan.
    """
    if isinstance(val, (pd.Series, list, np.ndarray)):
        try:
            val = val.iloc[-1]
        except Exception:
            try:
                val = val[-1]
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
    Semua nilai penting dipaksa jadi float.
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

    # Breakout 20 hari + Support / Resistance
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

    # EMA cross
    if not any(np.isnan(x) for x in [ema20, ema50, prev_ema20, prev_ema50]):
        prev_rel = np.sign(prev_ema20 - prev_ema50)
        now_rel  = np.sign(ema20 - ema50)
        if prev_rel <= 0 and now_rel > 0:
            patterns.append("EMA20 baru saja golden cross ke atas EMA50 (sinyal bullish menengah).")
        elif prev_rel >= 0 and now_rel < 0:
            patterns.append("EMA20 baru saja death cross ke bawah EMA50 (sinyal bearish menengah).")

    # Divergence sederhana AO vs harga
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
    Semua nilai penting dipaksa jadi float.
    """
    if len(df) < 30:
        return {"status": "Data terlalu pendek untuk membuat trading plan (butuh ≥ 30 bar)."}

    last = df.iloc[-1]

    close = safe_float(last.get("Close"))
    ema20 = safe_float(last.get("EMA20"))
    ema50 = safe_float(last.get("EMA50"))
    atr   = safe_float(last.get("ATR14"))
    wr    = safe_float(last.get("WR14"))
    ao    = safe_float(last.get("AO"))
    vol   = safe_float(last.get("Volume"))
    vol_ma20 = safe_float(last.get("VOL_MA20"))

    support_20 = safe_float(df["Low"].rolling(20).min().iloc[-1])
    resist_20  = safe_float(df["High"].rolling(20).max().iloc[-1])

    if np.isnan(atr) or atr == 0:
        atr = safe_float((df["High"] - df["Low"]).rolling(14).mean().iloc[-1])

    vol_ratio = np.nan
    if not np.isnan(vol) and not np.isnan(vol_ma20) and vol_ma20 != 0:
        vol_ratio = vol / vol_ma20

    # Trend
    trend = "unknown"
    if not any(np.isnan(x) for x in [close, ema20, ema50]):
        if ema20 > ema50 and close > ema20:
            trend = "strong_up"
        elif ema20 > ema50:
            trend = "up"
        elif ema20 < ema50 and close < ema20:
            trend = "down"
        else:
            trend = "sideways"

    plan = {}

    # Breakout 20-bar?
    breakout = False
    if len(df) >= 20 and not np.isnan(close):
        prev_high_20 = safe_float(df["Close"].rolling(20).max().iloc[-2])
        if not np.isnan(prev_high_20) and close > prev_high_20:
            breakout = True

    # Setup Breakout
    if (trend == "strong_up"
        and breakout
        and ao > 0
        and (np.isnan(vol_ratio) or vol_ratio >= 1.5)
        and not np.isnan(atr)
        and atr > 0):

        entry_low  = close - 0.5 * atr
        entry_high = close + 0.2 * atr
        stop       = close - 1.8 * atr
        target     = close + 3.0 * atr
        entry_mid  = (entry_low + entry_high) / 2

        rr = np.nan
        if entry_mid > stop:
            rr = (target - entry_mid) / (entry_mid - stop)

        plan.update({
            "status"    : "Setup Breakout",
            "entry_type": "Breakout Follow",
            "entry_low" : entry_low,
            "entry_high": entry_high,
            "stop"      : stop,
            "target"    : target,
            "RR"        : rr,
            "note"      : "Breakout uptrend dengan volume & momentum mendukung."
        })

    # Setup Pullback ke EMA20
    elif trend in ["strong_up", "up"] and wr <= -80 and not np.isnan(ema20) and not np.isnan(atr):
        entry_low  = ema20 - 0.5 * atr
        entry_high = ema20 + 0.5 * atr
        stop       = ema50 - 0.5 * atr if not np.isnan(ema50) else ema20 - 2 * atr
        target     = resist_20 if not np.isnan(resist_20) else ema20 + 3 * atr
        entry_mid  = (entry_low + entry_high) / 2

        rr = np.nan
        if entry_mid > stop:
            rr = (target - entry_mid) / (entry_mid - stop)

        plan.update({
            "status"    : "Setup Pullback",
            "entry_type": "Pullback EMA20",
            "entry_low" : entry_low,
            "entry_high": entry_high,
            "stop"      : stop,
            "target"    : target,
            "RR"        : rr,
            "note"      : "Uptrend, harga oversold vs %R(14) → peluang buy di sekitar EMA20."
        })

    else:
        plan.update({
            "status"    : "No Trade",
            "entry_type": "Watchlist",
            "note"      : "Sinyal belum ideal (trend lemah / tidak jelas / belum ada pullback menarik)."
        })

    plan["trend"]       = trend
    plan["ATR14"]       = atr
    plan["vol_ratio20"] = vol_ratio
    plan["support20"]   = support_20
    plan["resistance20"]= resist_20

    return plan

# ---------- Fitur 1: Confidence Score ----------
def compute_confidence(df, last, desc, patterns, plan):
    close = safe_float(last.get("Close"))
    ema20 = safe_float(last.get("EMA20"))
    ema50 = safe_float(last.get("EMA50"))
    ao    = safe_float(last.get("AO"))
    atr   = safe_float(last.get("ATR14"))
    vol_ratio = plan.get("vol_ratio20")
    if vol_ratio is None or np.isnan(vol_ratio):
        vol_ratio = safe_float(last.get("VolRatio20"))

    trend = plan.get("trend", "unknown")
    if trend == "strong_up":
        trend_score = 1.0
    elif trend == "up":
        trend_score = 0.7
    elif trend == "sideways":
        trend_score = 0.4
    elif trend == "down":
        trend_score = 0.1
    else:
        trend_score = 0.5

    if np.isnan(ao):
        ao_score = 0.5
    elif ao > 0:
        ao_score = 0.8
    elif ao < 0:
        ao_score = 0.2
    else:
        ao_score = 0.5

    if np.isnan(vol_ratio):
        vol_score = 0.5
    elif vol_ratio >= 2:
        vol_score = 1.0
    elif vol_ratio >= 1.5:
        vol_score = 0.8
    elif vol_ratio >= 1.2:
        vol_score = 0.6
    elif vol_ratio >= 1.0:
        vol_score = 0.4
    else:
        vol_score = 0.2

    breakout_score = 0.3
    if any("Breakout 20 hari" in p for p in patterns):
        breakout_score = 1.0
    elif trend in ["strong_up", "up"]:
        breakout_score = 0.6

    if not np.isnan(atr) and not np.isnan(close) and close > 0:
        atr_pct = atr / close
        if 0.01 <= atr_pct <= 0.05:
            volat_score = 0.9
        elif 0.005 <= atr_pct <= 0.08:
            volat_score = 0.7
        else:
            volat_score = 0.4
    else:
        volat_score = 0.5

    score = (
        trend_score * 0.3 +
        ao_score * 0.2 +
        vol_score * 0.2 +
        breakout_score * 0.2 +
        volat_score * 0.1
    ) * 100.0

    score = max(0.0, min(100.0, score))

    if score >= 80:
        label = "Very High (A+) – Sinyal sangat kuat, tapi tetap perlu money management."
    elif score >= 65:
        label = "High (A) – Sinyal menarik untuk dipertimbangkan."
    elif score >= 40:
        label = "Medium (B) – Boleh watchlist, tunggu konfirmasi."
    else:
        label = "Low (C) – Lebih baik hanya dipantau."

    return {"score": score, "label": label}

# ---------- Fitur 2: Narasi Analis Otomatis ----------
def generate_narrative(ticker, last, desc, patterns, plan, confidence):
    close = safe_float(last.get("Close"))
    trend_text = desc.get("Trend EMA", "-")
    rsi_text   = desc.get("RSI(14)", "-")
    macd_text  = desc.get("MACD", "-")
    vol_text   = desc.get("Volume", "-")

    patt_text = "\n".join(f"- {p}" for p in patterns) if patterns else "- Tidak ada pola menonjol."

    status = plan.get("status", "No Trade")
    entry_type = plan.get("entry_type", "Watchlist")
    note = plan.get("note", "")

    narrative = f"""
**Ringkasan {ticker}**

- Harga terakhir sekitar **{close:.2f}**.
- {trend_text}
- {rsi_text}
- {macd_text}
- {vol_text}

**Pola teknikal yang terdeteksi:**
{patt_text}

**Rencana trading (eksperimental):**

- Status setup: **{status}**
- Tipe setup: **{entry_type}**
- Catatan: {note}

**Confidence Score:** ~**{confidence['score']:.0f}%** → {confidence['label']}

Narasi ini bukan rekomendasi beli/jual, hanya rangkuman kondisi teknikal terakhir untuk membantu pengambilan keputusan.
"""
    return narrative

# ---------- Fitur 3: Entry Ladder ----------
def build_ladders(plan):
    ladders = {"status": plan.get("status", "No Trade")}

    if plan.get("status") == "No Trade" or "entry_low" not in plan or "entry_high" not in plan:
        ladders["message"] = "Belum ada setup entry yang valid (status No Trade atau level entry belum lengkap)."
        return ladders

    low = plan["entry_low"]
    high = plan["entry_high"]
    mid = (low + high) / 2
    mid_low = (low + mid) / 2
    mid_high = (mid + high) / 2

    ladders["Konservatif"] = [
        (0.40, low),
        (0.30, mid_low),
        (0.30, mid),
    ]

    ladders["Agresif"] = [
        (0.30, mid_high),
        (0.30, high),
        (0.20, mid),
        (0.20, low),
    ]

    ladders["Breakout"] = [
        (0.50, high),
        (0.30, mid_high),
        (0.20, mid),
    ]

    return ladders

# ---------- Fitur 4: Risk Management ----------
def compute_risk(capital, risk_pct, lot_size, plan, last_close):
    info = {}

    if plan.get("status") == "No Trade" or \
       "entry_low" not in plan or "entry_high" not in plan or "stop" not in plan:
        info["status"] = "NoTrade"
        info["message"] = "Belum ada setup dengan level entry & stop yang lengkap."
        return info

    entry_mid = (plan["entry_low"] + plan["entry_high"]) / 2
    stop = plan["stop"]

    risk_per_share = entry_mid - stop
    if risk_per_share <= 0:
        info["status"] = "Invalid"
        info["message"] = "Stop loss berada di atas/sama dengan entry (tidak valid untuk posisi long)."
        return info

    max_risk_money = capital * risk_pct / 100.0
    if max_risk_money <= 0:
        info["status"] = "NoCapital"
        info["message"] = "Modal atau risk % tidak valid."
        return info

    max_shares = max_risk_money / risk_per_share
    max_lot = int(max_shares // lot_size)

    if max_lot <= 0:
        info["status"] = "TooSmall"
        info["message"] = "Modal/risk terlalu kecil untuk setup ini (hasil perhitungan < 1 lot)."
        return info

    shares = max_lot * lot_size
    used_risk_money = shares * risk_per_share
    position_value = shares * entry_mid

    info.update({
        "status": "OK",
        "entry_mid": entry_mid,
        "stop": stop,
        "risk_per_share": risk_per_share,
        "max_lot": max_lot,
        "shares": shares,
        "max_risk_money": max_risk_money,
        "used_risk_money": used_risk_money,
        "position_value": position_value,
        "risk_pct": risk_pct,
        "capital": capital,
    })
    return info

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

            # ===== Indikator tabel =====
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

            # ===== Interpretasi =====
            st.markdown("<div class='section-title'>🧠 Interpretasi Otomatis</div>", unsafe_allow_html=True)
            desc = interpret_last(last)
            for k, v in desc.items():
                st.markdown(f"- **{k}**: {v}")

            # ===== Pola teknikal =====
            st.markdown("<div class='section-title'>📌 Sinyal Pola Teknis</div>", unsafe_allow_html=True)
            patterns = detect_patterns(df_ind)
            if patterns:
                for p in patterns:
                    st.markdown(f"- {p}")
            else:
                st.markdown("- Tidak ada pola menonjol yang terdeteksi.")

            # ===== Entry / Exit plan =====
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

            # ===== Confidence Score =====
            st.markdown("<div class='section-title'>🔥 Confidence Sinyal</div>", unsafe_allow_html=True)
            conf = compute_confidence(df_ind, last, desc, patterns, plan)
            st.metric("Confidence Score", f"{conf['score']:.0f} %")
            st.caption(f"Tingkat keyakinan: {conf['label']}")
            st.progress(conf["score"] / 100.0)

            # ===== Narasi Analis =====
            st.markdown("<div class='section-title'>🧾 Narasi Analis Otomatis</div>", unsafe_allow_html=True)
            narrative = generate_narrative(ticker, last, desc, patterns, plan, conf)
            st.markdown(narrative)

            # ===== Entry Ladder =====
            st.markdown("<div class='section-title'>🧱 Entry Ladder Rekomendasi</div>", unsafe_allow_html=True)
            ladders = build_ladders(plan)
            if ladders.get("status") == "No Trade" or "Konservatif" not in ladders:
                st.write(ladders.get("message", "Belum ada setup yang layak dieksekusi."))
            else:
                for mode in ["Konservatif", "Agresif", "Breakout"]:
                    if mode in ladders:
                        st.markdown(f"**{mode}**")
                        rows = [{"Porsi": f"{int(p*100)}%", "Harga": h} for (p, h) in ladders[mode]]
                        st.table(pd.DataFrame(rows))

            # ===== Risk Management =====
            st.markdown("<div class='section-title'>🛡️ Risk Management</div>", unsafe_allow_html=True)
            risk_info = compute_risk(capital, risk_pct, lot_size, plan, last["Close"])
            if risk_info.get("status") != "OK":
                st.write(risk_info.get("message", "Risk tidak dapat dihitung."))
            else:
                r = risk_info
                risk_df = pd.DataFrame({
                    "Parameter": [
                        "Modal",
                        "Risk per trade (%)",
                        "Risk maksimal (nominal)",
                        "Entry rata-rata",
                        "Stop loss",
                        "Risk per saham",
                        "Lot maksimum",
                        "Jumlah saham",
                        "Nilai posisi (approx)",
                        "Risk nominal yang dipakai"
                    ],
                    "Nilai": [
                        r["capital"],
                        r["risk_pct"],
                        r["max_risk_money"],
                        r["entry_mid"],
                        r["stop"],
                        r["risk_per_share"],
                        r["max_lot"],
                        r["shares"],
                        r["position_value"],
                        r["used_risk_money"],
                    ]
                })
                st.table(risk_df)

            # ===== CHART DENGAN ALTAIR =====
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

# ===================== MULTI TICKER ANALYZER =====================
st.sidebar.header("📦 Multi Ticker Scanner")
multi_input = st.sidebar.text_area(
    "Masukkan banyak ticker (pisahkan dengan koma):",
    value="BBRI.JK, BBCA.JK, ANTM.JK",
    help="Contoh: BBRI.JK, BBCA.JK, ANTM.JK, BUMI.JK"
)
scan_btn = st.sidebar.button("📡 Scan Semua Ticker", use_container_width=True)

if scan_btn:
    tickers = [t.strip().upper() for t in multi_input.split(",") if t.strip()]
    results = []

    st.markdown("<div class='section-title'>📡 Hasil Scan Multi Ticker</div>", unsafe_allow_html=True)

    with st.spinner("Scanning semua ticker..."):
        for tk in tickers:
            try:
                df = fetch_data(tk, period, interval)
                if df.empty:
                    results.append({
                        "Ticker": tk,
                        "Status": "Data Kosong"
                    })
                    continue

                df_ind = calc_indicators(df)
                last = df_ind.iloc[-1]

                desc = interpret_last(last)
                patterns = detect_patterns(df_ind)
                plan = generate_entry_plan(df_ind)
                conf = compute_confidence(df_ind, last, desc, patterns, plan)

                results.append({
                    "Ticker": tk,
                    "Harga": safe_float(last["Close"]),
                    "Trend": plan.get("trend", "-"),
                    "Confidence": conf["score"],
                    "Entry Type": plan.get("entry_type", "-"),
                    "RR": plan.get("RR", np.nan),
                    "VolSpike": plan.get("vol_ratio20"),
                    "Status": plan.get("status"),
                })

            except Exception as e:
                results.append({
                    "Ticker": tk,
                    "Status": f"Error: {str(e)}"
                })

    df_rank = pd.DataFrame(results)

    # urutkan berdasarkan confidence terbesar
    if "Confidence" in df_rank.columns:
        df_rank = df_rank.sort_values("Confidence", ascending=False)

    st.dataframe(df_rank)
    st.sidebar.header("🎯 Screener Kustom")
    filter_trend = st.sidebar.multiselect("Trend wajib", ["strong_up", "up"], default=["strong_up", "up"])
    min_conf = st.sidebar.slider("Minimal Confidence", 0, 100, 60)
    min_vol_ratio = st.sidebar.slider("Minimal Volume Spike (x)", 0.0, 3.0, 1.2, 0.1)
    ao_filter = st.sidebar.selectbox("AO harus", ["Tidak wajib", "Harus > 0"], index=1)

# ===================== AUTO TOP PICKS + TELEGRAM =====================
if scan_btn and len(df_rank) > 0 and "Confidence" in df_rank.columns:
    st.markdown("<div class='section-title'>🏆 Top Picks Hari Ini</div>", unsafe_allow_html=True)

    # Hanya saham yang bukan No Trade
    df_valid = df_rank[df_rank["Status"] != "No Trade"].copy()
    top_picks = df_valid.sort_values("Confidence", ascending=False).head(3)

    if len(top_picks) == 0:
        st.info("Belum ada saham dengan sinyal kuat hari ini.")
    else:
        st.dataframe(top_picks)

        # Tampilkan ringkas di layar
        for _, row in top_picks.iterrows():
            st.success(
                f"**{row['Ticker']}** – Confidence **{row['Confidence']:.0f}%** "
                f"| Trend: **{row['Trend']}** | Entry: **{row['Entry Type']}**"
            )

        # Kirim ke Telegram (jika user aktifkan & isi Chat ID)
        if send_alerts and telegram_chat:
            for _, row in top_picks.iterrows():
                msg = (
                    f"🔥 *ALERT: {row['Ticker']}*\n"
                    f"Trend: {row['Trend']}\n"
                    f"Confidence: {row['Confidence']:.0f}%\n"
                    f"Entry: {row['Entry Type']}\n"
                    f"RR: {row['RR']}\n"
                    f"Volume Spike: {row['VolSpike']}"
                )
                send_telegram(msg, telegram_chat)

            st.success("Alert Telegram dikirim!")

# ===================== SCREENER KUSTOM =====================
if scan_btn:
    st.markdown("<div class='section-title'>🎛️ Screener Kustom</div>", unsafe_allow_html=True)

    sc = df_rank.copy()

    sc = sc[
        (sc["Trend"].isin(filter_trend)) &
        (sc["Confidence"] >= min_conf) &
        (sc["VolSpike"] >= min_vol_ratio)
    ]

    if ao_filter == "Harus > 0":
        sc = sc[sc["Status"] != "No Trade"]

    if len(sc) == 0:
        st.warning("Tidak ada saham yang memenuhi filter kustom.")
    else:
        st.dataframe(sc)
        st.success(f"{len(sc)} saham cocok dengan filter kamu.")

# ===================== EXPORTER =====================
import io

if scan_btn:
    st.markdown("<div class='section-title'>📤 Export Data</div>", unsafe_allow_html=True)

    # Export Excel
    try:
        excel_buffer = io.BytesIO()
        df_rank.to_excel(excel_buffer, index=False)
        st.download_button(
            label="📊 Download Excel",
            data=excel_buffer.getvalue(),
            file_name="multi_ticker_scan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except ModuleNotFoundError:
        st.warning("Export Excel membutuhkan library **openpyxl**. Tambahkan `openpyxl` di requirements.txt.")

    # Export PDF (kalau sudah pasang pdfkit + wkhtmltopdf)
    import pdfkit
    html_table = df_rank.to_html()
    pdf_buffer = pdfkit.from_string(html_table, False)
    st.download_button(
        label="📄 Download PDF",
        data=pdf_buffer,
        file_name="multi_ticker_scan.pdf",
        mime="application/pdf"
    )


# ===================== FOOTER =====================
st.markdown("""
<div class='footer-text'>
Technical Analyzer · EMA, %R, CCI, AO, RSI, MACD, ATR, Volume, Pola & Risk · Data dari Yahoo Finance.<br>
Gunakan sebagai alat bantu analisa, bukan rekomendasi beli/jual.
</div>
""", unsafe_allow_html=True)











