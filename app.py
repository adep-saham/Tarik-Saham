# ======================================================
# IMPORT — STANDARD
# ======================================================
import time

import altair as alt
import pandas as pd
import streamlit as st


# ======================================================
# IMPORT — CORE
# ======================================================
from core.data_loader import fetch_data
from core.indicators import calc_indicators
from core.ticker_utils import normalize_ticker
from core.utils import safe_float


# ======================================================
# IMPORT — ANALYSIS
# ======================================================
from analysis.interpretation import interpret_last
from analysis.patterns import detect_patterns
from analysis.entry_plan import generate_entry_plan
from analysis.confidence import compute_confidence
from analysis.badge import get_trade_badge


# ======================================================
# IMPORT — RISK
# ======================================================
from risk.risk_management import compute_risk


# ======================================================
# IMPORT — UI
# ======================================================
from ui.theme import load_theme
from ui.sidebar import sidebar_inputs, sidebar_bandarmology


# ======================================================
# IMPORT — SCANNER / AUTO SYNC
# ======================================================
from scanner.scan_engine import scan_window
from scanner.auto_scan_bundle import auto_scan_30_60_120
from scanner.auto_mode_engine import auto_switch_mode
from scanner.ranking_engine import rank_sync_stocks
from scanner.decision_engine import decide_action
from scanner.entry_confirmation import entry_confirmation
from scanner.entry_zone_engine import compute_entry_zone
from scanner.telegram_alert import send_telegram_alert


# ======================================================
# IMPORT — EXTRA
# ======================================================
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
# TAB 1 — SINGLE STOCK (PRO)
# ======================================================
with tab_single:
    # --------------------------------------------------
    # SIDEBAR INPUT
    # --------------------------------------------------
    (
        raw_ticker,
        period,
        interval,
        capital,
        risk_pct,
        lot_size,
        analyze_btn
    ) = sidebar_inputs()

    bandar_mode, bandar_top_n = sidebar_bandarmology()

    mode = st.selectbox(
        "🧠 Mode Trading",
        ["Momentum", "Pullback", "Mean Reversion"],
        index=0
    )

    # --------------------------------------------------
    # BUTTON TRIGGER
    # --------------------------------------------------
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

    # --------------------------------------------------
    # GUARD
    # --------------------------------------------------
    if not st.session_state.single_params:
        st.info("Klik **Analisa** di sidebar.")
        st.stop()

    # --------------------------------------------------
    # FETCH + INDICATOR
    # --------------------------------------------------
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

    # --------------------------------------------------
    # ANALYSIS CORE
    # --------------------------------------------------
    plan = generate_entry_plan(df)
    conf = compute_confidence(
        df, last,
        interpret_last(last),
        detect_patterns(df),
        plan
    )

    # --------------------------------------------------
    # 🔑 ROW DISAMAKAN DENGAN AUTO SYNC (FIX Sync)
    # --------------------------------------------------
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

    # --------------------------------------------------
    # DECISION ENGINE (SAMA DENGAN AUTO SYNC)
    # --------------------------------------------------
    decision = decide_action(row, p["mode"])
    zone = compute_entry_zone(row, p["mode"]) if decision == "BUY" else {}

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------
    st.subheader(f"{ticker} — {decision}")

    # --------------------------------------------------
    # CHART
    # --------------------------------------------------
    zoom = st.select_slider(
        "Window", [30, 60, 120],
        value=30,
        key=f"single_zoom_{ticker}_{p['nonce']}"
    )

    dfw = df.tail(zoom).reset_index()

    price = alt.Chart(dfw).mark_line().encode(x="Date:T", y="Close:Q")
    ema20 = alt.Chart(dfw).mark_line(strokeDash=[4, 2], color="green").encode(x="Date:T", y="EMA20:Q")
    ema50 = alt.Chart(dfw).mark_line(strokeDash=[6, 3], color="red").encode(x="Date:T", y="EMA50:Q")

    st.altair_chart(price + ema20 + ema50, width="stretch")

    # --------------------------------------------------
    # METRICS
    # --------------------------------------------------
    c1, c2, c3 = st.columns(3)
    c1.metric("Close", row["Close"])
    c2.metric("RSI14", row["RSI14"])
    c3.metric("Confidence", row["Score"])

    # --------------------------------------------------
    # 2️⃣ CHECKLIST KUANTITATIF
    # --------------------------------------------------
    st.markdown("### ✅ Checklist Kuantitatif")

    checklist = pd.DataFrame([
        ["Close > EMA20", row["Close"], last["EMA20"], row["Close"] > last["EMA20"]],
        ["EMA20 > EMA50", last["EMA20"], last["EMA50"], last["EMA20"] > last["EMA50"]],
        ["RSI14", row["RSI14"], "40–70", 40 <= row["RSI14"] <= 70],
        ["Confidence", row["Score"], "≥ 75", row["Score"] >= 75],
        ["Sync", row["Sync"], "≥ 1", row["Sync"] >= 1],
    ], columns=["Item", "Value", "Rule", "Pass"])

    st.dataframe(checklist, width="stretch")

    # --------------------------------------------------
    # ENTRY & RISK
    # --------------------------------------------------
    st.markdown("### 📌 Entry & Risk")
    c4, c5, c6 = st.columns(3)
    c4.metric("Entry Low", zone.get("EntryLow", "-"))
    c5.metric("Entry High", zone.get("EntryHigh", "-"))
    c6.metric("Stop Loss", zone.get("StopLoss", "-"))

    # --------------------------------------------------
    # 3️⃣ BANDARMOLOGI (SINGLE TAB)
    # --------------------------------------------------
    st.markdown("### 🏦 Bandarmologi")

    up = st.file_uploader(
        "Upload CSV Bandar / Broker Summary",
        type=["csv"],
        key="single_broker"
    )

    if up:
        bdf = pd.read_csv(up)

        st.caption("Mode: deteksi otomatis format CSV (Broker Summary / Aggregated / Bandar Value Table).")

        # ====== MODE 1: tampilkan untuk ticker saat ini (single) ======
        st.markdown("#### A) Rekap untuk ticker saat ini")
        try:
            bandar_single = compute_bandar_rekap(bdf, ticker=ticker)
            st.dataframe(bandar_single, width="stretch")
        except Exception as e:
            st.warning(f"Tidak bisa rekap single ticker: {e}")

        # ====== MODE 2: analisa semua simbol dalam CSV ======
        st.markdown("#### B) Analisa semua saham dalam CSV")
        colA, colB, colC = st.columns([1, 1, 2])
        top_n = colA.number_input("Top N", min_value=10, max_value=300, value=50, step=10)
        do_fetch_tech = colB.checkbox("Tambah teknikal (fetch harga)", value=True)
        run_all = colC.button("🚀 Analisa Semua Simbol", use_container_width=True)

        if run_all:
            # 1) Ambil tabel bandar untuk semua symbol (format CSV kamu)
            bandar_all = compute_bandar_rekap(bdf, ticker=None)

            # Kalau outputnya bukan format symbol-table, stop
            cols = set([c.lower() for c in bandar_all.columns])
            if "symbol" not in cols:
                st.error("CSV ini bukan format Symbol/Bandar Value. Untuk analisa semua saham, CSV harus punya kolom 'Symbol' & 'Bandar Value'.")
                st.stop()

            # 2) Ranking awal berdasarkan kekuatan bandar
            # (kalau ada MA20 -> kita pakai BV - MA20; kalau tidak ada, pakai BV saja)
            df_all = bandar_all.copy()
            df_all.columns = [c.lower() for c in df_all.columns]

            # pastikan numeric
            if "bandar_value" in df_all.columns and "bandar_value_ma20" in df_all.columns:
                df_all["strength"] = df_all["bandar_value"] - df_all["bandar_value_ma20"]
            elif "bandar_value" in df_all.columns:
                df_all["strength"] = df_all["bandar_value"]
            else:
                df_all["strength"] = 0

            df_all = df_all.sort_values("strength", ascending=False).head(int(top_n)).reset_index(drop=True)

            # 3) Kalau tidak fetch teknikal, tampilkan saja
            if not do_fetch_tech:
                st.dataframe(df_all, width="stretch")
                st.stop()

            # 4) Fetch teknikal untuk Top N (ini yang berat)
            rows = []
            prog = st.progress(0, text="Fetching teknikal...")

            for i, sym in enumerate(df_all["symbol"].astype(str).tolist()):
                t = sym.strip().upper()
                t_jk = t if t.endswith(".JK") else f"{t}.JK"

                try:
                    dfx = cached_fetch_data(t_jk, period, interval, _nonce=time.time())
                    if dfx is None or dfx.empty:
                        continue

                    dfx = calc_indicators(dfx)
                    lastx = dfx.iloc[-1]

                    # plan/conf seperti single
                    planx = generate_entry_plan(dfx)
                    confx = compute_confidence(
                        dfx, lastx,
                        interpret_last(lastx),
                        detect_patterns(dfx),
                        planx
                    )

                    # row untuk decide_action (HARUS ada Sync)
                    r = pd.Series({
                        "Ticker": t_jk,
                        "Close": safe_float(lastx.get("Close")),
                        "RSI14": safe_float(lastx.get("RSI14")),
                        "EMA20": safe_float(lastx.get("EMA20")),
                        "EMA50": safe_float(lastx.get("EMA50")),
                        "Trend": planx.get("trend"),
                        "Status": planx.get("status"),
                        "Score": float(confx.get("score", 0)),
                        "Sync": 1,  # single dianggap sync
                    })

                    decisionx = decide_action(r, mode)
                    rows.append({
                        "Ticker": t_jk,
                        "BandarSignal": df_all.loc[i, "signal"] if "signal" in df_all.columns else None,
                        "BandarStrength": float(df_all.loc[i, "strength"]),
                        "Close": r["Close"],
                        "RSI14": r["RSI14"],
                        "EMA20": r["EMA20"],
                        "EMA50": r["EMA50"],
                        "Trend": r.get("Trend", ""),
                        "Status": r.get("Status", ""),
                        "Score": r["Score"],
                        "Decision": decisionx,
                    })

                except Exception:
                    # skip simbol bermasalah agar tidak menghentikan semua
                    pass

                prog.progress((i + 1) / len(df_all), text=f"Fetching teknikal... {i + 1}/{len(df_all)}")

            prog.empty()

            if not rows:
                st.warning("Tidak ada data teknikal yang berhasil diambil. Cek koneksi data source / ticker.")
                st.stop()

            out = pd.DataFrame(rows)

            # ranking final: BUY dulu, lalu Score, lalu BandarStrength
            out["BUY_rank"] = (out["Decision"] == "BUY").astype(int)
            out = out.sort_values(["BUY_rank", "Score", "BandarStrength"], ascending=[False, False, False]).drop(columns=["BUY_rank"])

            st.success(f"Selesai. Total dianalisa: {len(out)} ticker.")
            st.dataframe(out, width="stretch")


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

    def safe_entry_zone(row, mode_):
        if row["Decision"] == "BUY":
            z = compute_entry_zone(row, mode_)
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
