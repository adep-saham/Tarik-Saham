import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

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
def scan_window(window, universe):
    results = []

    lookback = max(window * 3, 200)

    for ticker in universe:

        # ===== QUICK TEST (SEMENTARA) =====
        st.write("TEST ticker:", ticker)
        break
        # =================================

        try:
            df = load_price_data(
                ticker,
                period=f"{lookback}d",
                interval="1d"
            )

            if df is None or len(df) < 60:
                continue

            df = calc_indicators(df)
            last = df.iloc[-1]

            ema20 = last["EMA20"]
            ema50 = last["EMA50"]
            rsi   = last["RSI14"]

            if pd.isna(ema20) or pd.isna(ema50) or pd.isna(rsi):
                continue

            if ema20 >= ema50 * 0.99 and rsi >= 40:
                results.append(ticker)

        except Exception:
            continue

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








