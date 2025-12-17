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


def scan_window(window, universe):
    results = []

    lookback = max(window * 3, 200)

    # counter alasan gagal
    c_none = 0
    c_short = 0
    c_no_close = 0
    c_nan = 0
    c_cond_fail = 0
    c_exc = 0
    first_exc = None

    for ticker in universe:
        try:
            df = load_price_data(ticker, period=f"{lookback}d", interval="1d")

            if df is None or len(df) == 0:
                c_none += 1
                continue

            if len(df) < 60:
                c_short += 1
                continue

            # normalize kolom (multiindex / nama beda)
            df = normalize_ohlcv(df)

            if "Close" not in df.columns:
                c_no_close += 1
                continue

            df = calc_indicators(df)
            last = df.iloc[-1]

            # pastikan kolom indikator ada
            if not all(col in df.columns for col in ["EMA20", "EMA50", "RSI14"]):
                c_no_close += 1
                continue

            ema20 = last["EMA20"]
            ema50 = last["EMA50"]
            rsi = last["RSI14"]

            if pd.isna(ema20) or pd.isna(ema50) or pd.isna(rsi):
                c_nan += 1
                continue

            if ema20 >= ema50 * 0.99 and rsi >= 40:
                results.append(ticker)
            else:
                c_cond_fail += 1

        except Exception as e:
            c_exc += 1
            if first_exc is None:
                first_exc = (ticker, repr(e))

    # tampilkan ringkasan debug (sekali per run)
    st.info(
        f"DEBUG window {window} | results={len(results)} | "
        f"none={c_none} short={c_short} no_close={c_no_close} "
        f"nan_ind={c_nan} cond_fail={c_cond_fail} exc={c_exc}"
    )
    if first_exc:
        st.warning(f"FIRST EXCEPTION: {first_exc[0]} -> {first_exc[1]}")

    return results


# =============================================================
# ================= PAGE =================
st.set_page_config(page_title="Tarik Saham – ADP", layout="wide")
load_theme()
st.markdown("## 📊 Tarik Saham – ADP")

# ================= LOAD UNIVERSE (IDX) =================
@st.cache_data(ttl=24 * 3600)
def get_universe():
    return load_idx_universe()

IDX_UNIVERSE = get_universe()

# ================= TABS =================
tab_single, tab_scanner = st.tabs([
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
with tab_scanner:

    st.markdown("### 🤖 Auto Sync Stocks (IDX – 30 / 60 / 120)")

    if st.button("🚀 Run Auto Scan"):

        # === PROSES SCAN ===
        sync_30 = scan_window(30, IDX_UNIVERSE)
        sync_60 = scan_window(60, IDX_UNIVERSE)
        sync_120 = scan_window(120, IDX_UNIVERSE)

        # === DEBUG JUMLAH (INI YANG KAMU TANYA) ===
        st.write("Universe:", len(IDX_UNIVERSE))
        st.write("Lolos window 30:", len(sync_30))
        st.write("Lolos window 60:", len(sync_60))
        st.write("Lolos window 120:", len(sync_120))

        # === HASIL AKHIR ===
        final_sync = list(
            (set(sync_30) & set(sync_60)) | (set(sync_30) & set(sync_120))
        )

        if not final_sync:
            st.warning("Tidak ada saham sinkron saat ini.")
        else:
            st.success(f"Ditemukan {len(final_sync)} saham sinkron")
            st.dataframe(final_sync)


    st.caption(
        "Auto Sync menampilkan saham dengan sinyal multi-window "
        "yang sudah selaras (30/60/120)."
    )














