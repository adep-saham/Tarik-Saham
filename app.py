# ================= IMPORT =================
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
from risk.risk_management import compute_risk

# ================= UI =================
from ui.theme import load_theme
from ui.sidebar import sidebar_inputs

# ================= SCANNER =================
from scanner.scan_engine import scan_window
from scanner.backtest_engine import backtest_mode
from scanner.walkforward_engine import walk_forward_validate
from scanner.equity_engine import build_equity_curve
from scanner.auto_mode_engine import auto_switch_mode
from scanner.entry_confirmation import entry_confirmation
from scanner.entry_zone_engine import compute_entry_zone
from scanner.telegram_alert import send_telegram_alert

# ================= RANKING =================
from scanner.ranking_engine import rank_sync_stocks
from scanner.decision_engine import decide_action


# ================= STYLE =================
def color_decision(val):
    if val == "BUY":
        return "background-color:#2ecc71;color:white"
    if val == "WAIT":
        return "background-color:#f1c40f;color:black"
    if val == "SKIP":
        return "background-color:#e74c3c;color:white"
    return ""


# ================= PAGE =================
st.set_page_config(page_title="Tarik Saham – ADP", layout="wide")
load_theme()
st.markdown("## 📊 Tarik Saham – ADP")


# ================= SESSION INIT =================
for k in ["w30", "w60", "w120"]:
    if k not in st.session_state:
        st.session_state[k] = set()

if "single_result" not in st.session_state:
    st.session_state.single_result = None

if "bt_result" not in st.session_state:
    st.session_state.bt_result = None

if "wf_result" not in st.session_state:
    st.session_state.wf_result = None

if "equity_df" not in st.session_state:
    st.session_state.equity_df = None

if "prev_final_actions" not in st.session_state:
    st.session_state.prev_final_actions = {}


# ======================================================
# 📥 LOAD IDX UNIVERSE
# ======================================================
@st.cache_data(ttl=24 * 3600)
def load_universe():
    df = pd.read_csv("data/idx_universe.csv")
    df.columns = [c.lower().strip() for c in df.columns]

    if "ticker" not in df.columns:
        if "kode" in df.columns:
            df = df.rename(columns={"kode": "ticker"})
        else:
            st.error("Kolom ticker/kode tidak ditemukan")
            st.stop()

    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["ticker"] = df["ticker"].apply(
        lambda x: x if x.endswith(".JK") else f"{x}.JK"
    )
    return df


IDX_UNIVERSE = load_universe()


# ======================================================
# 🔎 FILTER IDX
# ======================================================
st.subheader("🔎 Filter IDX Universe")

boards = st.multiselect(
    "Pilih papan saham IDX",
    ["UTAMA", "AKSELERASI", "PENGEMBANGAN"],
    default=["UTAMA", "AKSELERASI"]
)

IDX_UNIVERSE = IDX_UNIVERSE[IDX_UNIVERSE["board"].isin(boards)]
TICKERS = IDX_UNIVERSE["ticker"].tolist()

st.caption(f"Universe IDX: {len(TICKERS)} saham")


# ======================================================
# SIDEBAR — KONTROL
# ======================================================
st.sidebar.subheader("🔄 Mode Trading")
mode_option = st.sidebar.radio(
    "Pilih Mode",
    ["Auto", "Momentum", "Pullback", "Strict"],
    index=0
)

st.sidebar.divider()

st.sidebar.subheader("🧪 Backtest")
run_bt = st.sidebar.button("Run Backtest (5-day hold)")

st.sidebar.subheader("🔄 Walk-Forward")
wf_lookback = st.sidebar.selectbox("Lookback (hari)", [3, 5, 7, 10], index=2)
run_wf = st.sidebar.button("Run Walk-Forward")

st.sidebar.subheader("📈 Equity Curve")
run_eq = st.sidebar.button("Generate Equity Curve")

st.sidebar.subheader("🔔 Alerts")
enable_alerts = st.sidebar.checkbox("Enable WAIT → BUY Alert", value=True)
enable_tg = st.sidebar.checkbox("Enable Telegram Alert", value=True)


# ======================================================
# TABS
# ======================================================
tab_single, tab_auto = st.tabs([
    "🔎 Single Stock Analysis",
    "🤖 Auto Sync Stocks (30 / 60 / 120)"
])


# ======================================================
# TAB 1 — SINGLE STOCK
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

    if analyze_btn and raw_ticker:
        try:
            ticker = normalize_ticker(raw_ticker)
            df = fetch_data(ticker, period, interval)

            if df is None or df.empty:
                st.error("Data kosong / ticker tidak valid.")
            else:
                df = calc_indicators(df)
                last = df.iloc[-1]

                close_price = safe_float(last.get("Close"))
                desc = interpret_last(last)
                patterns = detect_patterns(df)
                plan = generate_entry_plan(df)
                conf = compute_confidence(df, last, desc, patterns, plan)
                risk = compute_risk(capital, risk_pct, lot_size, plan, close_price)

                badge_text, _ = get_trade_badge(
                    conf["score"],
                    plan.get("status"),
                    plan.get("trend")
                )

                st.session_state.single_result = {
                    "ticker": ticker,
                    "df": df,
                    "last": last,
                    "plan": plan,
                    "conf": conf,
                    "risk": risk,
                    "badge": badge_text,
                }

        except Exception as e:
            st.error(f"Single analysis error: {e}")

    result = st.session_state.single_result
    if result:
        st.subheader(f"{result['ticker']} — {result['badge']}")

        zoom = st.select_slider(
            "🔍 Window Analisa",
            options=[30, 60, 120],
            value=30
        )

        df_w = result["df"].tail(zoom).reset_index()

        price = alt.Chart(df_w).mark_line().encode(
            x="Date:T", y="Close:Q"
        )
        ema20 = alt.Chart(df_w).mark_line(
            color="green", strokeDash=[4, 2]
        ).encode(x="Date:T", y="EMA20:Q")
        ema50 = alt.Chart(df_w).mark_line(
            color="red", strokeDash=[6, 3]
        ).encode(x="Date:T", y="EMA50:Q")

        st.altair_chart(
            (price + ema20 + ema50).interactive(),
            use_container_width=True
        )
        # ===============================
        # 🔍 RINGKASAN CEPAT
        # ===============================
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Close", round(safe_float(last.get("Close")), 2))
        c2.metric("RSI14", round(safe_float(last.get("RSI14")), 2))
        c3.metric("Trend", plan.get("trend", "-"))
        c4.metric("Confidence", round(conf.get("score", 0), 2))
        
        
        # ===============================
        # 📌 ENTRY PLAN
        # ===============================
        with st.expander("📌 Entry Plan", expanded=True):
            st.json(plan)
        
        
        # ===============================
        # 🧠 INTERPRETATION & PATTERN
        # ===============================
        with st.expander("🧠 Interpretation & Patterns", expanded=False):
            st.write(desc)
            st.json(patterns)
        
        
        # ===============================
        # 🛡️ RISK MANAGEMENT
        # ===============================
        with st.expander("🛡️ Risk Management", expanded=False):
            if isinstance(risk, dict):
                st.json(risk)
            else:
                st.dataframe(risk, use_container_width=True)
        
        
        # ===============================
        # 📊 CONFIDENCE DETAIL
        # ===============================
        with st.expander("📊 Confidence Detail", expanded=False):
            st.json(conf)



# ======================================================
# TAB 2 — AUTO SYNC
# ======================================================
with tab_auto:
    st.subheader("🤖 Auto Sync Stocks")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Scan 30"):
            w30, _ = scan_window(30, TICKERS, fetch_data, calc_indicators)
            st.session_state.w30 = set(w30)

    with col2:
        if st.button("Scan 60"):
            w60, _ = scan_window(60, TICKERS, fetch_data, calc_indicators)
            st.session_state.w60 = set(w60)

    with col3:
        if st.button("Scan 120"):
            w120, _ = scan_window(120, TICKERS, fetch_data, calc_indicators)
            st.session_state.w120 = set(w120)

    w30, w60, w120 = (
        st.session_state.w30,
        st.session_state.w60,
        st.session_state.w120
    )

    sync = (w30 & w60) | (w30 & w120) | (w60 & w120)

    if not sync:
        st.warning("Tidak ada saham sinkron.")
    else:
        df_rank = rank_sync_stocks(
            tickers=sync,
            w30=w30,
            w60=w60,
            w120=w120,
            load_price_data=fetch_data,
            calc_indicators=calc_indicators,
            top_n=10
        )

        active_mode = (
            auto_switch_mode(df_rank)
            if mode_option == "Auto"
            else mode_option
        )

        st.info(f"🧠 Active Mode: **{active_mode}**")

        df_rank["Decision"] = df_rank.apply(
            lambda r: decide_action(r, active_mode),
            axis=1
        )

        df_rank["Confirmed"] = df_rank.apply(
            lambda r: entry_confirmation(r)
            if r["Decision"] == "BUY" else False,
            axis=1
        )

        df_rank["FinalAction"] = df_rank.apply(
            lambda r: "BUY"
            if r["Decision"] == "BUY" and r["Confirmed"]
            else "WAIT",
            axis=1
        )

        df_rank[["EntryLow", "EntryHigh", "StopLoss"]] = df_rank.apply(
            lambda r: pd.Series(
                compute_entry_zone(r, active_mode)
                if r["FinalAction"] == "BUY"
                else {"EntryLow": None, "EntryHigh": None, "StopLoss": None}
            ),
            axis=1
        )

        st.subheader("📊 Decision Matrix")
        st.dataframe(
            df_rank[
                ["Ticker", "FinalAction", "EntryLow", "EntryHigh", "StopLoss"]
            ].style.applymap(color_decision, subset=["FinalAction"]),
            use_container_width=True
        )

        # ===== ALERT =====
        if enable_alerts:
            current = dict(zip(df_rank["Ticker"], df_rank["FinalAction"]))
            flipped = [
                t for t, v in current.items()
                if st.session_state.prev_final_actions.get(t) == "WAIT"
                and v == "BUY"
            ]
            st.session_state.prev_final_actions = current

            if flipped:
                st.toast(f"🚨 WAIT → BUY: {', '.join(flipped)}")
                if enable_tg:
                    for t in flipped:
                        r = df_rank[df_rank["Ticker"] == t].iloc[0]
                        msg = (
                            "🚨 *WAIT → BUY*\n"
                            f"*Ticker*: {t}\n"
                            f"*Mode*: {active_mode}\n"
                            f"*Entry*: {r['EntryLow']} – {r['EntryHigh']}\n"
                            f"*StopLoss*: {r['StopLoss']}"
                        )
                        send_telegram_alert(msg)

        # ===== EQUITY =====
        if run_eq:
            st.session_state.equity_df = build_equity_curve(
                tickers=df_rank["Ticker"].tolist(),
                load_price_data=fetch_data,
                decide_action_func=decide_action,
                mode=active_mode,
                holding_days=5
            )

        if st.session_state.equity_df is not None:
            eq = st.session_state.equity_df.reset_index(drop=True)
            eq["step"] = range(len(eq))
            st.subheader("📈 Equity Curve")
            st.line_chart(eq.set_index("step")["Equity"])

