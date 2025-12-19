import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import yfinance as yf
# ================= CORE =================
from core.data_loader import fetch_data
from core.indicators import calc_indicators
from core.ticker_utils import normalize_ticker
from core.utils import safe_float

# ================= ANALYSIS =================
from analysis.interpretation import interpret_last
from analysis.patterns import detect_patterns
from analysis.entry_plan import generate_entry_plan
from analysis.confidence import compute_confidence
from analysis.badge import get_trade_badge

# ================= RISK =================
from risk.ladders import build_ladders
from risk.risk_management import compute_risk

# ================= UI =================
from ui.theme import load_theme
from ui.sidebar import sidebar_inputs

# ================= SCANNER =================
from scanner.universe import load_idx_universe
from scanner.prefilter import prefilter_universe
from scanner.sync_engine import check_sync
from scanner.sync_rules import consensus_rule
from scanner.scan_engine import scan_window


# ================== AUTO SYNC SCAN FUNCTION ==================

def load_price_data(ticker, period="300d", interval="1d"):
    try:
        df = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            group_by="column"   # <<< INI KUNCI UTAMA
        )

        if df is None or df.empty:
            return None

        # pastikan kolom flat (bukan multiindex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df

    except Exception:
        return None

def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # kalau MultiIndex kolom (sering dari yfinance)
    if isinstance(df.columns, pd.MultiIndex):
        # ambil level terakhir (Open/High/Low/Close/Volume)
        df.columns = [c[-1] for c in df.columns]

    # normalisasi nama kolom umum
    rename_map = {}
    for col in df.columns:
        c = str(col).strip()
        rename_map[col] = c

    df = df.rename(columns=rename_map)

    # kalau hanya ada Adj Close, jadikan Close
    if "Close" not in df.columns and "Adj Close" in df.columns:
        df["Close"] = df["Adj Close"]

    # pastikan numeric
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def _ensure_ema(df, span: int, colname: str):
    if colname not in df.columns:
        df[colname] = df["Close"].ewm(span=span, adjust=False).mean()
    return df

def _ensure_rsi14(df):
    if "RSI14" not in df.columns:
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        rs = gain.rolling(14).mean() / loss.rolling(14).mean()
        df["RSI14"] = 100 - (100 / (1 + rs))
    return df

def scan_window(window, tickers):
    results = []

    for ticker in tickers:
        df = load_price_data(ticker)
        if df is None or len(df) < window * 2:
            continue

        # pakai core calc_indicators dulu (kalau ada)
        df = calc_indicators(df)

        # pastikan Close ada
        if "Close" not in df.columns:
            continue

        # pastikan EMA window tersedia
        df = _ensure_ema(df, window, f"EMA{window}")
        df = _ensure_ema(df, window * 2, f"EMA{window*2}")
        df = _ensure_rsi14(df)

        last = df.iloc[-1]
        fast = last.get(f"EMA{window}")
        slow = last.get(f"EMA{window*2}")
        rsi = last.get("RSI14")

        if pd.isna(fast) or pd.isna(slow) or pd.isna(rsi):
            continue

        # relaxed filter (biar tidak 0)
        if fast >= slow * 0.99 and rsi >= 40:
            results.append(ticker)

    return results



# =============================================================
# ================= PAGE =================
st.set_page_config(page_title="Tarik Saham – ADP", layout="wide")
load_theme()
st.markdown("## 📊 Tarik Saham – ADP")

# ================= LOAD UNIVERSE (IDX) =================
@st.cache_data(ttl=24 * 3600)
def get_universe_df():
    # path yang benar di project streamlit kamu
    path = "data/idx_universe.csv"
    df = pd.read_csv(path)

    # normalisasi nama kolom
    df.columns = [c.strip().lower() for c in df.columns]

    # beberapa file pakai 'kode' bukan 'ticker'
    if "ticker" not in df.columns:
        if "kode" in df.columns:
            df = df.rename(columns={"kode": "ticker"})
        else:
            st.error(f"Kolom ticker/kode tidak ditemukan. Kolom yang ada: {df.columns.tolist()}")
            st.stop()

    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["ticker"] = df["ticker"].apply(lambda x: x if x.endswith(".JK") else f"{x}.JK")

    return df

IDX_UNIVERSE = get_universe_df()

st.subheader("🔎 Filter IDX Universe")

BOARD_OPTIONS = ["UTAMA", "AKSELERASI", "PENGEMBANGAN"]

selected_boards = st.multiselect(
    "Pilih papan saham IDX",
    options=BOARD_OPTIONS,
    default=["UTAMA", "AKSELERASI"]  # 🚀 default cepat & likuid
)

if not selected_boards:
    st.warning("Pilih minimal satu papan saham.")
    st.stop()


IDX_UNIVERSE = IDX_UNIVERSE[
    IDX_UNIVERSE["board"].isin(selected_boards)
]

TICKERS = IDX_UNIVERSE["ticker"].tolist()


# ================= TABS =================
tab_single, tab_auto = st.tabs([
    "🔎 Single Stock Analysis",
    "🤖 Auto Sync Stocks (30 / 60 / 120)"
])

# ======================================================
# 🔎 TAB 1 — SINGLE STOCK ANALYSIS
# ======================================================
with tab_single:

    (
        raw_ticker,
        period,
        interval,
        capital,
        risk_pct,
        lot_size,
        analyze_btn
    ) = sidebar_inputs()

    if "run_single" not in st.session_state:
        st.session_state.run_single = False

    if analyze_btn:
        st.session_state.run_single = True

    if st.session_state.run_single and raw_ticker:

        ticker = normalize_ticker(raw_ticker)
        df = fetch_data(ticker, period, interval)

        if df.empty:
            st.error("Data kosong / ticker tidak valid.")
            st.stop()

        df_ind = calc_indicators(df)
        last = df_ind.iloc[-1]

        close_price = safe_float(last.get("Close"))
        close_text = f"{close_price:.2f}" if not np.isnan(close_price) else "-"

        desc = interpret_last(last)
        patterns = detect_patterns(df_ind)
        plan = generate_entry_plan(df_ind)
        conf = compute_confidence(df_ind, last, desc, patterns, plan)
        risk = compute_risk(capital, risk_pct, lot_size, plan, close_price)

        badge_text, _ = get_trade_badge(
            conf["score"],
            plan.get("status"),
            plan.get("trend")
        )

        st.caption(
            f"**{ticker}** | {period} | {interval} | "
            f"Close: **{close_text}** | "
            f"Decision: **{badge_text}**"
        )

        if badge_text == "BUY":
            st.success("🟢 BUY – Setup kuat")
        elif badge_text == "WAIT":
            st.warning("🟡 WAIT – Tunggu konfirmasi")
        else:
            st.error("🔴 AVOID – Risiko dominan")

        # ===== ZOOM =====
        zoom = st.select_slider(
            "🔍 Window Analisa",
            options=[30, 60, 120],
            value=30
        )

        df_w = df_ind.tail(min(zoom, len(df_ind)))
        last_w = df_w.iloc[-1]
        desc_w = interpret_last(last_w)

        c1, c2, c3 = st.columns(3)
        c1.metric("Trend", desc_w.get("Trend EMA", "-"))
        c2.metric("Confidence", f"{conf['score']:.0f}%")
        c3.metric("Risk / Trade", f"{risk_pct:.1f}%")

        # ===== CHART =====
        chart_df = df_w.reset_index()
        chart_df = chart_df.rename(columns={chart_df.columns[0]: "Date"})

        price = alt.Chart(chart_df).mark_line(color="#1f77b4").encode(
            x="Date:T", y="Close:Q"
        )

        ema20 = alt.Chart(chart_df).mark_line(
            color="#22c55e", strokeDash=[4, 2]
        ).encode(x="Date:T", y="EMA20:Q")

        ema50 = alt.Chart(chart_df).mark_line(
            color="#ef4444", strokeDash=[6, 3]
        ).encode(x="Date:T", y="EMA50:Q")

        layers = [price, ema20, ema50]

        if plan.get("status") != "No Trade":
            entry_band = alt.Chart(pd.DataFrame({
                "y1": [plan["entry_low"]],
                "y2": [plan["entry_high"]]
            })).mark_rect(opacity=0.15, color="#22c55e").encode(
                y="y1:Q", y2="y2:Q"
            )
            layers.append(entry_band)

        st.altair_chart(
            alt.layer(*layers).interactive(),
            use_container_width=True
        )

# ======================================================
# 🤖 TAB 2 — AUTO SYNC SCANNER
# ======================================================
with tab_auto:
    st.subheader("🤖 Auto Sync Stocks (IDX – 30 / 60 / 120)")
    st.caption(f"Universe IDX: {len(TICKERS)} saham")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Scan Window 30"):
            with st.spinner("Scanning window 30..."):
                st.session_state["w30"] = set(scan_window(30, TICKERS))

    with col2:
        if st.button("Scan Window 60"):
            with st.spinner("Scanning window 60..."):
                st.session_state["w60"] = set(scan_window(60, TICKERS))

    with col3:
        if st.button("Scan Window 120"):
            with st.spinner("Scanning window 120..."):
                st.session_state["w120"] = set(scan_window(120, TICKERS))

    w30 = st.session_state.get("w30", set())
    w60 = st.session_state.get("w60", set())
    w120 = st.session_state.get("w120", set())

    if w30:
        st.write("Lolos window 30:", len(w30))
    if w60:
        st.write("Lolos window 60:", len(w60))
    if w120:
        st.write("Lolos window 120:", len(w120))

    if w30 or w60 or w120:
        sync_2of3 = (w30 & w60) | (w30 & w120) | (w60 & w120)
        st.success(f"Saham sinkron (≥2 window): {len(sync_2of3)}")

        if sync_2of3:
            st.dataframe(
                pd.DataFrame(sorted(sync_2of3), columns=["Ticker"]),
                use_container_width=True
            )



    
    st.caption(
        "Auto Sync menampilkan saham dengan sinyal multi-window "
        "yang sudah selaras (30/60/120)."
    )
    

























