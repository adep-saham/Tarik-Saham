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
        return "background-color: #2ecc71; color: white;"
    elif val == "HOT":
        return "background-color: #e67e22; color: white;"
    elif val == "WAIT":
        return "background-color: #f1c40f; color: black;"
    elif val == "SKIP":
        return "background-color: #e74c3c; color: white;"
    return ""


# ================= PAGE =================
st.set_page_config(page_title="Tarik Saham – ADP", layout="wide")
load_theme()
st.markdown("## 📊 Tarik Saham – ADP")


# ================= SESSION INIT =================
for k in ["w30", "w60", "w120"]:
    if k not in st.session_state:
        st.session_state[k] = set()

if "bt_result" not in st.session_state:
    st.session_state.bt_result = None

if "wf_result" not in st.session_state:
    st.session_state.wf_result = None


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
    df["ticker"] = df["ticker"].apply(lambda x: x if x.endswith(".JK") else f"{x}.JK")
    return df


IDX_UNIVERSE = load_universe()

# ======================================================
# 🔎 FILTER BOARD IDX (CEPAT)
# ======================================================
st.subheader("🔎 Filter IDX Universe")

BOARD_OPTIONS = ["UTAMA", "AKSELERASI", "PENGEMBANGAN"]
selected_boards = st.multiselect(
    "Pilih papan saham IDX",
    options=BOARD_OPTIONS,
    default=["UTAMA", "AKSELERASI"]
)

if not selected_boards:
    st.warning("Pilih minimal satu papan saham.")
    st.stop()

IDX_UNIVERSE = IDX_UNIVERSE[IDX_UNIVERSE["board"].isin(selected_boards)]
TICKERS = IDX_UNIVERSE["ticker"].tolist()
st.caption(f"Universe IDX: {len(TICKERS)} saham")


# ======================================================
# 🔧 SIDEBAR — KONTROL SAJA
# ======================================================
st.sidebar.subheader("🔄 Mode Trading")

mode_option = st.sidebar.radio(
    "Pilih Mode",
    ["Auto", "Momentum", "Pullback", "Strict"],
    index=0
)


st.sidebar.divider()

st.sidebar.subheader("🧪 Backtest Mode")
run_bt = st.sidebar.button("Run Backtest (5-day hold)")

st.sidebar.divider()

st.sidebar.subheader("🔄 Walk-Forward Validation")
wf_lookback = st.sidebar.selectbox("Lookback (hari)", [3, 5, 7, 10], index=2)
run_wf = st.sidebar.button("Run Walk-Forward")

st.sidebar.subheader("📈 Equity Curve")
run_eq = st.sidebar.button("Generate Equity Curve")


# ======================================================
# 🧭 TABS
# ======================================================
tab_single, tab_auto = st.tabs([
    "🔎 Single Stock Analysis",
    "🤖 Auto Sync Stocks (30 / 60 / 120)"
])


# ======================================================
# 🔎 TAB 1 — SINGLE STOCK
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

    # Saat tombol diklik: hitung sekali, simpan hasil
    if analyze_btn and raw_ticker:
        try:
            ticker = normalize_ticker(raw_ticker)
            df = fetch_data(ticker, period, interval)

            if df is None or df.empty:
                st.error("Data kosong / ticker tidak valid.")
                st.stop()

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

            # SIMPAN agar tidak hilang saat rerun
            st.session_state.single_result = {
                "ticker": ticker,
                "df": df,
                "last": last,
                "close_price": close_price,
                "desc": desc,
                "patterns": patterns,
                "plan": plan,
                "conf": conf,
                "risk": risk,
                "badge": badge_text,
            }

        except Exception as e:
            st.error(f"Single analysis error: {e}")

    # Render hasil dari session_state (jadi tetap tampil walau rerun)
    result = st.session_state.single_result
    if result is None:
        st.info("Klik tombol **Analisa** di sidebar untuk menjalankan Single Stock Analysis.")
        st.stop()

    ticker = result["ticker"]
    df = result["df"]
    last = result["last"]
    plan = result["plan"]
    conf = result["conf"]
    risk = result["risk"]
    badge_text = result["badge"]

    st.subheader(f"{ticker} — {badge_text}")

    # ===== Ringkas (biar terasa 'jalan semua')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Close", safe_float(last.get("Close")))
    c2.metric("RSI14", round(safe_float(last.get("RSI14")), 2))
    c3.metric("Trend", str(plan.get("trend", "-")))
    c4.metric("Confidence", round(conf.get("score", 0), 2))

    # ===== Chart
    zoom = st.select_slider(
        "🔍 Window Analisa",
        options=[30, 60, 120],
        value=30,
        key="single_zoom"
    )

    df_w = df.tail(zoom)
    chart_df = df_w.reset_index().rename(columns={"index": "Date"})

    price = alt.Chart(chart_df).mark_line().encode(
        x="Date:T", y="Close:Q"
    )

    ema20 = alt.Chart(chart_df).mark_line(
        color="green", strokeDash=[4, 2]
    ).encode(x="Date:T", y="EMA20:Q")

    ema50 = alt.Chart(chart_df).mark_line(
        color="red", strokeDash=[6, 3]
    ).encode(x="Date:T", y="EMA50:Q")

    st.altair_chart((price + ema20 + ema50).interactive(), use_container_width=True)

    # ===== Detail (pakai expander biar rapi)
    with st.expander("📌 Entry Plan", expanded=True):
        st.json(plan)

    with st.expander("🧠 Interpretation & Patterns", expanded=False):
        st.write(result["desc"])
        st.json(result["patterns"])

    with st.expander("🛡️ Risk Management", expanded=False):
        # risk bisa dict atau dataframe tergantung implementasimu
        if isinstance(risk, dict):
            st.json(risk)
        else:
            st.dataframe(risk, use_container_width=True)



# ======================================================
# 🤖 TAB 2 — AUTO SYNC
# ======================================================
with tab_auto:
    st.subheader("🤖 Auto Sync Stocks (IDX – 30 / 60 / 120)")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Scan Window 30"):
            with st.spinner("Scanning 30..."):
                w30, stats30 = scan_window(30, TICKERS, fetch_data, calc_indicators)
                st.session_state.w30 = set(w30)
                st.caption(f"30 stats: {stats30}")

    with col2:
        if st.button("Scan Window 60"):
            with st.spinner("Scanning 60..."):
                w60, stats60 = scan_window(60, TICKERS, fetch_data, calc_indicators)
                st.session_state.w60 = set(w60)
                st.caption(f"60 stats: {stats60}")

    with col3:
        if st.button("Scan Window 120"):
            with st.spinner("Scanning 120..."):
                w120, stats120 = scan_window(120, TICKERS, fetch_data, calc_indicators)
                st.session_state.w120 = set(w120)
                st.caption(f"120 stats: {stats120}")

    w30 = st.session_state.w30
    w60 = st.session_state.w60
    w120 = st.session_state.w120

    st.write("Lolos 30:", len(w30))
    st.write("Lolos 60:", len(w60))
    st.write("Lolos 120:", len(w120))

    sync_2of3 = (w30 & w60) | (w30 & w120) | (w60 & w120)

    if not sync_2of3:
        st.warning("Tidak ada saham sinkron saat ini.")
        st.stop()

    st.success(f"Saham sinkron (≥2 window): {len(sync_2of3)}")
    st.dataframe(pd.DataFrame(sorted(sync_2of3), columns=["Ticker"]), use_container_width=True)

    # ======================
    # Ranking
    # ======================
    st.subheader("🏆 Ranking Top 10 Saham Sinkron")

    df_rank = rank_sync_stocks(
        tickers=sync_2of3,
        w30=w30,
        w60=w60,
        w120=w120,
        load_price_data=fetch_data,
        calc_indicators=calc_indicators,
        top_n=10
    )

    st.dataframe(df_rank, use_container_width=True)
    active_mode = mode_option
    
    if mode_option == "Auto" and df_rank is not None and not df_rank.empty:
        active_mode = auto_switch_mode(df_rank)
    
    st.sidebar.info(f"🧠 Active Mode: **{active_mode}**")

    # =========================
    # 📊 Decision Matrix + Entry Confirmation
    # =========================
    st.subheader("📊 Decision Matrix – Top 10 Saham Sinkron")
    
    # 1️⃣ Decision dasar (berdasarkan mode)
    df_rank["Decision"] = df_rank.apply(
        lambda r: decide_action(r, active_mode),
        axis=1
    )
    
    # 2️⃣ Entry confirmation (HANYA untuk BUY)
    df_rank["Confirmed"] = df_rank.apply(
        lambda r: entry_confirmation(r) if r["Decision"] == "BUY" else False,
        axis=1
    )
    
    # 3️⃣ Final Action (hasil akhir yang boleh dieksekusi)
    df_rank["FinalAction"] = df_rank.apply(
        lambda r: "BUY" if r["Decision"] == "BUY" and r["Confirmed"] else "WAIT",
        axis=1
    )
    
    # 4️⃣ Tampilkan
    styled_df = (
        df_rank[
            ["Ticker", "Sync", "RSI14", "TrendScore", "Score", "FinalAction"]
        ]
        .style
        .applymap(color_decision, subset=["FinalAction"])
    )
    
    st.dataframe(styled_df, use_container_width=True)

    # =========================
    # 🎯 Entry Zone & Stoploss
    # =========================
    df_rank[["EntryLow", "EntryHigh", "StopLoss"]] = df_rank.apply(
        lambda r: pd.Series(
            compute_entry_zone(r, active_mode)
            if r["FinalAction"] == "BUY"
            else {"EntryLow": None, "EntryHigh": None, "StopLoss": None}
        ),
        axis=1
    )
    st.subheader("🎯 Entry Plan – Final")

    st.dataframe(
        df_rank[
            [
                "Ticker",
                "FinalAction",
                "EntryLow",
                "EntryHigh",
                "StopLoss"
            ]
        ],
        use_container_width=True
    )


    # ======================================================
    # BACKTEST — Trigger sidebar, output di tab_auto (rapi)
    # ======================================================
    if run_bt:
        with st.spinner("Running backtest..."):
            rows = []
            for m in ["Momentum", "Pullback", "Strict"]:
                res = backtest_mode(
                    tickers=list(sync_2of3),
                    load_price_data=fetch_data,
                    decide_action_func=decide_action,
                    mode=m,
                    holding_days=5
                )
                if res:
                    rows.append(res)
            st.session_state.bt_result = pd.DataFrame(rows) if rows else None

    if st.session_state.bt_result is not None:
        st.subheader("📈 Backtest Result")
        st.dataframe(st.session_state.bt_result, use_container_width=True)

    # ======================================================
    # WALK-FORWARD — Trigger sidebar, output di tab_auto (rapi)
    # ======================================================
    if run_wf:
        with st.spinner("Running walk-forward..."):
            # pakai top rank saja agar cepat
            res = walk_forward_validate(
                tickers=df_rank["Ticker"].tolist(),
                load_price_data=fetch_data,
                decide_action_func=decide_action,
                mode=mode,
                lookback_days=wf_lookback
            )
            st.session_state.wf_result = res

    if st.session_state.wf_result is not None:
        res = st.session_state.wf_result
        if res:
            df_wf, summary = res
            st.subheader("🔄 Walk-Forward Validation")
            st.json(summary)
            st.dataframe(df_wf, use_container_width=True)
        else:
            st.warning("Tidak ada sinyal BUY pada periode walk-forward.")

    if run_eq and df_rank is not None and not df_rank.empty:
        with st.spinner("Building equity curve..."):
            eq_df = build_equity_curve(
                tickers=df_rank["Ticker"].tolist(),
                load_price_data=fetch_data,
                decide_action_func=decide_action,
                mode=mode,
                holding_days=5
            )
    
            st.session_state["equity_df"] = eq_df

    eq_df = st.session_state.get("equity_df")
    
    if eq_df is not None:
        st.subheader(f"📈 Equity Curve — Mode {active_mode}")
    
        chart = (
            eq_df
            .reset_index(drop=True)
            .assign(step=lambda x: range(len(x)))
        )
    
        st.line_chart(
            chart.set_index("step")["Equity"],
            use_container_width=True
        )
    
        with st.expander("📋 Detail Equity Log"):
            st.dataframe(eq_df, use_container_width=True)

st.sidebar.subheader("🔔 Telegram Alert")
enable_tg = st.sidebar.checkbox("Enable Telegram WAIT → BUY", value=True)

if enable_alerts and df_rank is not None and not df_rank.empty:
    current_map = dict(zip(df_rank["Ticker"], df_rank["FinalAction"]))

    flipped = []
    for t, cur in current_map.items():
        prev = st.session_state.prev_final_actions.get(t, None)
        if prev == "WAIT" and cur == "BUY":
            flipped.append(t)

    st.session_state.prev_final_actions = current_map

    if flipped:
        st.toast(f"🚨 WAIT → BUY: {', '.join(flipped)}", icon="🚨")

        if enable_tg:
            for t in flipped:
                row = df_rank[df_rank["Ticker"] == t].iloc[0]

                msg = (
                    "🚨 *WAIT → BUY ALERT*\n"
                    f"*Ticker*: {t}\n"
                    f"*Mode*: {active_mode}\n"
                    f"*Entry*: {row['EntryLow']} – {row['EntryHigh']}\n"
                    f"*Stoploss*: {row['StopLoss']}"
                )

                send_telegram_alert(msg)





