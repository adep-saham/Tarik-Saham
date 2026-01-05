# ================= IMPORT =================
import streamlit as st
import pandas as pd
import altair as alt
import time

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
from risk.risk_management import compute_risk

# ================= UI =================
from ui.theme import load_theme
from ui.sidebar import sidebar_inputs

# ================= AUTO SYNC =================
from scanner.scan_engine import scan_window
from scanner.auto_scan_bundle import auto_scan_30_60_120
from scanner.auto_mode_engine import auto_switch_mode
from scanner.ranking_engine import rank_sync_stocks
from scanner.decision_engine import decide_action
from scanner.entry_confirmation import entry_confirmation
from scanner.entry_zone_engine import compute_entry_zone
from scanner.telegram_alert import send_telegram_alert

# ================= EXTRA =================
from scanner.bandarmologi_engine import compute_bandar_rekap
from services.profiler import Profiler


# ======================================================
# PAGE
# ======================================================
st.set_page_config(page_title="Tarik Saham – ADP", layout="wide")
load_theme()
st.title("📊 Tarik Saham – ADP")


# ======================================================
# CACHE (FORCED REFRESH VIA NONCE)
# ======================================================
@st.cache_data(ttl=15 * 60)
def cached_fetch_data(ticker, period="6mo", interval="1d", _nonce=None):
    return fetch_data(ticker, period, interval)


# ======================================================
# SESSION STATE
# ======================================================
if "single_params" not in st.session_state:
    st.session_state.single_params = None

if "prev_final_actions" not in st.session_state:
    st.session_state.prev_final_actions = {}

if "w30" not in st.session_state:
    st.session_state.w30 = set()
    st.session_state.w60 = set()
    st.session_state.w120 = set()


# ======================================================
# TABS (AUTO SYNC TETAP ADA)
# ======================================================
tab_single, tab_auto = st.tabs([
    "🔎 Single Stock (Pro)",
    "🤖 Auto Sync (30 / 60 / 120)"
])


# ======================================================
# TAB 1 — SINGLE STOCK (PRO, FIXED)
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

    mode = st.selectbox(
        "🧠 Mode Trading",
        ["Momentum", "Pullback", "Mean Reversion"],
        index=0
    )

    # ===== BUTTON TRIGGER =====
    if analyze_btn and raw_ticker:
        st.cache_data.clear()
        st.session_state.single_params = {
            "ticker": raw_ticker,
            "period": period,
            "interval": interval,
            "mode": mode,
            "nonce": time.time()
        }
        st.rerun()

    if not st.session_state.single_params:
        st.info("Klik **Analisa** di sidebar.")
        st.stop()

    p = st.session_state.single_params
    ticker = normalize_ticker(p["ticker"])

    df = cached_fetch_data(
        ticker, p["period"], p["interval"], _nonce=p["nonce"]
    )

    if df is None or df.empty:
        st.error("Data kosong.")
        st.stop()

    df = calc_indicators(df)
    last = df.iloc[-1]

    plan = generate_entry_plan(df)
    conf = compute_confidence(
        df, last,
        interpret_last(last),
        detect_patterns(df),
        plan
    )

    # ======================================================
    # 🔑 ROW DISAMAKAN DENGAN AUTO SYNC (FIX Sync)
    # ======================================================
    row = pd.Series({
        "Ticker": ticker,
        "Close": safe_float(last["Close"]),
        "RSI14": safe_float(last["RSI14"]),
        "Trend": plan.get("trend"),
        "Status": plan.get("status"),
        "Score": conf.get("score"),
        "Sync": 1,            # ⬅️ FIX UTAMA (WAJIB)
        "Window": "SINGLE",   # optional, info saja
    })

    # ===== DECISION ENGINE (SAMA DENGAN AUTO SYNC) =====
    decision = decide_action(row, p["mode"])
    zone = compute_entry_zone(row, p["mode"]) if decision == "BUY" else {}

    # ===== HEADER =====
    st.subheader(f"{ticker} — {decision}")

    # ===== CHART =====
    zoom = st.select_slider(
        "Window", [30, 60, 120],
        value=30,
        key=f"single_zoom_{ticker}_{p['nonce']}"
    )

    dfw = df.tail(zoom).reset_index()

    price = alt.Chart(dfw).mark_line().encode(x="Date:T", y="Close:Q")
    ema20 = alt.Chart(dfw).mark_line(strokeDash=[4,2], color="green").encode(x="Date:T", y="EMA20:Q")
    ema50 = alt.Chart(dfw).mark_line(strokeDash=[6,3], color="red").encode(x="Date:T", y="EMA50:Q")

    st.altair_chart(price + ema20 + ema50, width="stretch")

    # ===== METRICS =====
    c1, c2, c3 = st.columns(3)
    c1.metric("Close", row["Close"])
    c2.metric("RSI14", row["RSI14"])
    c3.metric("Confidence", row["Score"])

    # ======================================================
    # 2️⃣ CHECKLIST KUANTITATIF
    # ======================================================
    st.markdown("### ✅ Checklist Kuantitatif")

    checklist = pd.DataFrame([
        ["Close > EMA20", row["Close"], last["EMA20"], row["Close"] > last["EMA20"]],
        ["EMA20 > EMA50", last["EMA20"], last["EMA50"], last["EMA20"] > last["EMA50"]],
        ["RSI14", row["RSI14"], "40–70", 40 <= row["RSI14"] <= 70],
        ["Confidence", row["Score"], "≥ 75", row["Score"] >= 75],
        ["Sync", row["Sync"], "≥ 1", row["Sync"] >= 1],
    ], columns=["Item", "Value", "Rule", "Pass"])

    st.dataframe(checklist, width="stretch")

    # ======================================================
    # ENTRY & RISK
    # ======================================================
    st.markdown("### 📌 Entry & Risk")
    c4, c5, c6 = st.columns(3)
    c4.metric("Entry Low", zone.get("EntryLow", "-"))
    c5.metric("Entry High", zone.get("EntryHigh", "-"))
    c6.metric("Stop Loss", zone.get("StopLoss", "-"))

    # ======================================================
    # 3️⃣ BANDARMOLOGI (SINGLE TAB)
    # ======================================================
    st.markdown("### 🏦 Bandarmologi")

    up = st.file_uploader(
        "Upload CSV Broker Summary",
        type=["csv"],
        key="single_broker"
    )

    if up:
        bdf = pd.read_csv(up)
        bandar = compute_bandar_rekap(bdf)
        st.dataframe(bandar, width="stretch")


# ======================================================
# TAB 2 — AUTO SYNC (TIDAK DIUBAH)
# ======================================================
with tab_auto:
    st.subheader("🤖 Auto Sync Stocks (30 / 60 / 120)")

    run_auto = st.button("⚡ SCAN AUTO (30+60+120)")
    prof = Profiler()

    if run_auto:
        results = auto_scan_30_60_120(
            tickers=[],  # tetap pakai universe kamu
            scan_window_func=scan_window,
            load_price_data=cached_fetch_data,
            calc_indicators=calc_indicators,
            profiler=prof
        )
        st.session_state.w30 = results["w30"]
        st.session_state.w60 = results["w60"]
        st.session_state.w120 = results["w120"]

    w30, w60, w120 = st.session_state.w30, st.session_state.w60, st.session_state.w120
    sync = (w30 & w60) | (w30 & w120) | (w60 & w120)

    st.caption(
        f"30∩60: {len(w30 & w60)} | "
        f"30∩120: {len(w30 & w120)} | "
        f"60∩120: {len(w60 & w120)} | "
        f"Total Sync: {len(sync)}"
    )

    if not sync:
        st.warning("Tidak ada saham sinkron.")
        st.stop()

    df_rank = rank_sync_stocks(
        tickers=sync,
        w30=w30, w60=w60, w120=w120,
        load_price_data=cached_fetch_data,
        calc_indicators=calc_indicators,
        top_n=20
    )

    active_mode = auto_switch_mode(df_rank)
    st.info(f"🧠 Active Mode: **{active_mode}**")

    df_rank["Decision"] = df_rank.apply(
        lambda r: decide_action(r, active_mode), axis=1
    )

    df_rank["Confirmed"] = df_rank.apply(
        lambda r: entry_confirmation(r) if r["Decision"] == "BUY" else False,
        axis=1
    )

    def safe_entry_zone(row, mode):
        if row["Decision"] == "BUY":
            z = compute_entry_zone(row, mode)
            return pd.Series({
                "EntryLow": z.get("EntryLow"),
                "EntryHigh": z.get("EntryHigh"),
                "StopLoss": z.get("StopLoss"),
            })
        return pd.Series({"EntryLow": None, "EntryHigh": None, "StopLoss": None})

    df_rank[["EntryLow", "EntryHigh", "StopLoss"]] = df_rank.apply(
        lambda r: safe_entry_zone(r, active_mode), axis=1
    )

    st.subheader("📊 Decision Matrix")
    st.dataframe(
        df_rank[["Ticker", "Decision", "EntryLow", "EntryHigh", "StopLoss"]],
        width="stretch"
    )
