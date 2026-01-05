# ================= IMPORT =================
import streamlit as st
import pandas as pd
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
from risk.risk_management import compute_risk

# ================= UI =================
from ui.theme import load_theme
from ui.sidebar import sidebar_inputs

# ================= SCANNER =================
from scanner.scan_engine import scan_window
from scanner.equity_engine import build_equity_curve
from scanner.auto_mode_engine import auto_switch_mode
from scanner.entry_confirmation import entry_confirmation
from scanner.entry_zone_engine import compute_entry_zone
from scanner.telegram_alert import send_telegram_alert

# ================= RANKING =================
from scanner.ranking_engine import rank_sync_stocks
from scanner.decision_engine import decide_action
from scanner.auto_scan_bundle import auto_scan_30_60_120
from scanner.bandarmologi_engine import compute_bandar_rekap

from services.profiler import Profiler

# ======================================================
# 🚀 PERFORMANCE — CACHE DATA
# ======================================================
@st.cache_data(ttl=15 * 60, show_spinner=False)
def cached_fetch_data(ticker, period="6mo", interval="1d"):
    return fetch_data(ticker, period, interval)


def safe_scan(window, tickers):
    try:
        return scan_window(window, tickers, cached_fetch_data, calc_indicators)
    except Exception as e:
        st.warning(f"⚠️ Scan {window} error: {e}")
        return [], None


# ================= STYLE =================
def color_decision(val):
    if val == "BUY":
        return "background-color:#2ecc71;color:white"
    if val == "WAIT":
        return "background-color:#f1c40f;color:black"
    return ""


# ================= PAGE =================
st.set_page_config(page_title="Tarik Saham – ADP", layout="wide")
load_theme()
st.markdown("## 📊 Tarik Saham – ADP (Upgraded)")


# ================= SESSION INIT =================
for k in ["w30", "w60", "w120"]:
    if k not in st.session_state:
        st.session_state[k] = set()

if "single_result" not in st.session_state:
    st.session_state.single_result = None

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
        df = df.rename(columns={"kode": "ticker"})

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
# SIDEBAR — MODE
# ======================================================
st.sidebar.subheader("🔄 Mode Trading")
mode_option = st.sidebar.radio(
    "Pilih Mode",
    ["Auto", "Momentum", "Pullback", "Strict"],
    index=0
)

st.sidebar.divider()
run_eq = st.sidebar.button("📈 Generate Equity Curve")
enable_alerts = st.sidebar.checkbox("Enable WAIT → BUY Alert", True)
enable_tg = st.sidebar.checkbox("Enable Telegram Alert", True)


# ======================================================
# TABS
# ======================================================
tab_single, tab_auto = st.tabs([
    "🔎 Single Stock",
    "🤖 Auto Sync (30 / 60 / 120)"
])


# ======================================================
# TAB 1 — SINGLE STOCK
# ======================================================
# ======================================================
# TAB 1 — SINGLE STOCK (UPGRADED)
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
            df = cached_fetch_data(ticker, period, interval)

            if df is None or df.empty:
                st.error("Data kosong / ticker tidak valid.")
            else:
                df = calc_indicators(df)
                last = df.iloc[-1]

                # --- CORE ANALYSIS ---
                desc = interpret_last(last)
                patterns = detect_patterns(df)
                plan = generate_entry_plan(df)
                conf = compute_confidence(df, last, desc, patterns, plan)

                close_px = safe_float(last.get("Close"))
                rsi = safe_float(last.get("RSI14"))
                trend = plan_get(plan, "trend", default="-")
                score = conf.get("score", 0)

                # --- RISK ---
                risk = compute_risk(
                    capital,
                    risk_pct,
                    lot_size,
                    plan,
                    close_px
                )

                # --- BADGE ---
                badge_text, _ = get_trade_badge(
                    score,
                    plan_get(plan, "status", default=None),
                    trend
                )

                # ======================================================
                # ✅ DECISION GATE (yang bikin hasil benar-benar berubah)
                # - BUY: score tinggi + trend UP + RSI tidak ekstrem
                # - WAIT_OVERSOLD: RSI <= 30 walau score bagus (hindari catch falling knife)
                # - WAIT: lainnya
                # ======================================================
                status = plan_get(plan, "status", default=None)

                if score >= 80 and trend == "UP" and (rsi is None or rsi > 35) and status == "READY":
                    decision = "BUY"
                elif score >= 70 and (rsi is not None and rsi <= 30):
                    decision = "WAIT_OVERSOLD"
                else:
                    decision = "WAIT"

                # --- ENTRY ZONE (tampilkan hanya saat BUY) ---
                entry_low = plan_get(plan, "entry_low", "EntryLow", default=None)
                entry_high = plan_get(plan, "entry_high", "EntryHigh", default=None)
                stop_loss = plan_get(plan, "stop_loss", "StopLoss", default=None)

                if decision != "BUY":
                    entry_low, entry_high, stop_loss = None, None, None

                st.session_state.single_result = {
                    "ticker": ticker,
                    "df": df,
                    "last": last,
                    "desc": desc,
                    "patterns": patterns,
                    "plan": plan,
                    "conf": conf,
                    "risk": risk,
                    "badge": badge_text,
                    "decision": decision,
                    "entry": {
                        "EntryLow": entry_low,
                        "EntryHigh": entry_high,
                        "StopLoss": stop_loss
                    },
                    "meta": {
                        "score": score,
                        "rsi": rsi,
                        "trend": trend,
                        "status": status,
                        "close": close_px
                    }
                }

        except Exception as e:
            st.error(f"Single analysis error: {e}")

    result = st.session_state.single_result
    if not result:
        st.info("Klik **Analisa** di sidebar.")
    else:
        df = result["df"]
        last = result["last"]
        decision = result["decision"]
        meta = result["meta"]
        score = meta["score"]
        rsi = meta["rsi"]
        trend = meta["trend"]
        status = meta["status"]

        # ================= HEADER (JELAS TERLIHAT) =================
        if decision == "BUY":
            st.subheader(f"{result['ticker']} — 🟢 BUY")
        elif decision == "WAIT_OVERSOLD":
            st.subheader(f"{result['ticker']} — 🟡 WAIT (Oversold)")
        else:
            st.subheader(f"{result['ticker']} — ⚪ WAIT")

        st.caption(f"Badge: {result['badge']} | Trend: {trend} | Status: {status} | Score: {score} | RSI: {rsi}")

        # ================= CHART =================
        zoom = st.select_slider(
            "🔍 Window Analisa",
            options=[30, 60, 120],
            value=30,
            key="single_zoom"
        )

        dfw = df.tail(zoom).reset_index()

        price = alt.Chart(dfw).mark_line().encode(
            x="Date:T", y="Close:Q"
        )
        ema20 = alt.Chart(dfw).mark_line(
            color="green", strokeDash=[4, 2]
        ).encode(x="Date:T", y="EMA20:Q")
        ema50 = alt.Chart(dfw).mark_line(
            color="red", strokeDash=[6, 3]
        ).encode(x="Date:T", y="EMA50:Q")

        st.altair_chart((price + ema20 + ema50).interactive(), use_container_width=True)

        # ================= QUICK METRICS =================
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Close", round(safe_float(last.get("Close")), 2))
        c2.metric("RSI14", round(safe_float(last.get("RSI14")), 2))
        c3.metric("Trend", trend)
        c4.metric("Confidence", round(score, 2))

        # ================= DECISION REASON (BIAR TERASA UPGRADE) =================
        st.markdown("### 🧠 Decision Reason")
        if decision == "BUY":
            st.success(f"BUY karena: Score {score} ≥ 80, Trend UP, RSI {rsi} > 35, Status READY.")
        elif decision == "WAIT_OVERSOLD":
            st.warning(f"WAIT karena: RSI {rsi} ≤ 30 (oversold ekstrem). Tunggu rebound/base dulu.")
        else:
            st.info(f"WAIT karena: belum memenuhi syarat BUY (Score/Trend/Status/RSI).")

        # ================= ENTRY & RISK SUMMARY =================
        st.markdown("### 📌 Entry & Risk Summary")
        e = result["entry"]
        r = result["risk"]

        c5, c6, c7 = st.columns(3)
        c5.metric("Entry Range", f"{e['EntryLow']} – {e['EntryHigh']}" if e["EntryLow"] is not None else "-")
        c6.metric("Stop Loss", e["StopLoss"] if e["StopLoss"] is not None else "-")
        # risk_management output bisa dict / df tergantung implementasi kamu
        risk_amount = r.get("risk_amount") if isinstance(r, dict) else None
        c7.metric("Risk (Rp)", risk_amount if risk_amount is not None else "-")

        # ================= DETAIL =================
        with st.expander("📋 Entry Plan Detail"):
            st.json(result["plan"])

        with st.expander("🧠 Confidence Detail"):
            st.json(result["conf"])

        with st.expander("🧩 Pattern & Interpretation"):
            st.write(result["desc"])
            st.json(result["patterns"])



# ======================================================
# TAB 2 — AUTO SYNC
# ======================================================
with tab_auto:
    st.subheader("🤖 Auto Sync Stocks")

    # --- Profiler ---
    prof = Profiler()

    colA, colB, colC = st.columns([1,1,2])

    with colA:
        run_auto = st.button("⚡ SCAN AUTO (30+60+120)")

    with colB:
        show_profile = st.checkbox("🧪 Tampilkan Profiling", value=True)

    with colC:
        st.caption("Auto scan akan menjalankan 30→60→120 + progress + cache")

    if run_auto:
        results = auto_scan_30_60_120(
            tickers=TICKERS,
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

    # === PROFILING RESULT ===
    if show_profile:
        with st.expander("🧪 Profiling (Step Paling Berat)", expanded=False):
            st.dataframe(prof.df(), use_container_width=True)

    if not sync:
        st.warning("Tidak ada saham sinkron.")
        st.stop()

    # === RANKING (juga diprofiling) ===
    df_rank = prof.track(
        "rank_sync_stocks",
        rank_sync_stocks,
        tickers=sync,
        w30=w30, w60=w60, w120=w120,
        load_price_data=cached_fetch_data,
        calc_indicators=calc_indicators,
        top_n=20
    )

    active_mode = auto_switch_mode(df_rank) if mode_option == "Auto" else mode_option
    st.info(f"🧠 Active Mode: **{active_mode}**")

    df_rank["Decision"] = df_rank.apply(lambda r: decide_action(r, active_mode), axis=1)
    df_rank["Confirmed"] = df_rank.apply(
        lambda r: entry_confirmation(r) if r["Decision"] == "BUY" else False,
        axis=1
    )

    def safe_entry_zone(row, mode):
        if row["Decision"] == "BUY":
            zone = compute_entry_zone(row, mode)
            return pd.Series({
                "EntryLow": zone.get("EntryLow"),
                "EntryHigh": zone.get("EntryHigh"),
                "StopLoss": zone.get("StopLoss"),
            })
        else:
            return pd.Series({
                "EntryLow": None,
                "EntryHigh": None,
                "StopLoss": None,
            })
    
    df_rank[["EntryLow", "EntryHigh", "StopLoss"]] = df_rank.apply(
        lambda r: safe_entry_zone(r, active_mode),
        axis=1
    )


    df_rank["FinalAction"] = df_rank.apply(
        lambda r: "BUY"
        if r["Decision"] == "BUY"
        and r["Confirmed"]
        and pd.notna(r.get("EntryLow"))
        else "WAIT",
        axis=1
    )

    st.subheader("📊 Decision Matrix")
    st.dataframe(
        df_rank[["Ticker", "FinalAction", "EntryLow", "EntryHigh", "StopLoss"]]
        .style.applymap(color_decision, subset=["FinalAction"]),
        use_container_width=True
    )

    # ======================================================
    # 📊 BANDARMOLOGI — Upload Broker Summary CSV
    # ======================================================
    st.subheader("🏦 Rekap Bandarmologi (Upload Broker Summary)")
    st.caption("Upload CSV broker summary dari Stockbit/RTI/TradingView/broker. Minimal: date, broker, type(BY/SL), lot, avg(optional).")

    up = st.file_uploader("Upload CSV Broker Summary", type=["csv"], key="broker_csv")

    if up is not None:
        try:
            broker_df = pd.read_csv(up)
            bandar = compute_bandar_rekap(broker_df)

            st.markdown("### ✅ Rekap Tabel Bandar (Remaining Lots + WAP)")
            st.dataframe(bandar, use_container_width=True)

            # ringkas top bandar akumulasi
            top_acc = bandar.sort_values("net_lot", ascending=False).head(10)
            st.markdown("### 🔥 Top 10 Bandar (Net Lot)")
            st.dataframe(top_acc, use_container_width=True)

        except Exception as e:
            st.error(f"Gagal proses broker CSV: {e}")
    else:
        st.info("Belum ada broker CSV. Rekap bandarmologi akan muncul setelah upload.")

    # ===== ALERT & EQUITY (biarkan seperti versi kamu) =====
    # (tetap gunakan blok alert dan equity curve yang sudah ada)


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
                    send_telegram_alert(
                        f"🚨 *WAIT → BUY*\n"
                        f"*Ticker*: {t}\n"
                        f"*Mode*: {active_mode}\n"
                        f"*Entry*: {r['EntryLow']} – {r['EntryHigh']}\n"
                        f"*SL*: {r['StopLoss']}"
                    )

    if run_eq:
        st.session_state.equity_df = build_equity_curve(
            tickers=df_rank["Ticker"].tolist(),
            load_price_data=cached_fetch_data,
            decide_action_func=decide_action,
            mode=active_mode,
            holding_days=5
        )

    if st.session_state.equity_df is not None:
        st.subheader("📈 Equity Curve")
        st.line_chart(st.session_state.equity_df["Equity"])




