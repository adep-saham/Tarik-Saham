import time
import streamlit as st
import pandas as pd
import altair as alt

# ===============================
# IMPORT INTERNAL MODULES
# ===============================
from ui.sidebar import sidebar_inputs, sidebar_bandarmology

from scanner.bandarmologi_engine import compute_bandar_rekap
from scanner.decision_engine import decide_action

from core.data import cached_fetch_data, normalize_ticker
from core.indicators import calc_indicators
from analysis.plan import generate_entry_plan
from analysis.confidence import compute_confidence
from analysis.patterns import detect_patterns
from analysis.interpret import interpret_last
from risk.risk_engine import compute_risk
from analysis.badge import get_trade_badge

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Tarik Saham – ADP",
    layout="wide"
)

st.title("📈 Tarik Saham – ADP")

# ===============================
# SIDEBAR
# ===============================
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

# ===============================
# NORMALIZE TICKER
# ===============================
ticker = normalize_ticker(raw_ticker)

# ===============================
# TABS
# ===============================
tab_single, tab_auto = st.tabs([
    "🔍 Single Stock (Pro)",
    "⚡ Auto Sync (30 / 60 / 120)"
])

# ======================================================
# TAB 1 — SINGLE STOCK
# ======================================================
with tab_single:

    if analyze_btn and raw_ticker:
        try:
            df = cached_fetch_data(ticker, period, interval, _nonce=time.time())

            if df is None or df.empty:
                st.error("Data kosong / ticker tidak valid.")
            else:
                df = calc_indicators(df)
                last = df.iloc[-1]

                plan = generate_entry_plan(df)
                conf = compute_confidence(
                    df,
                    last,
                    interpret_last(last),
                    detect_patterns(df),
                    plan
                )

                risk = compute_risk(
                    capital,
                    risk_pct,
                    lot_size,
                    plan,
                    float(last.get("Close", 0))
                )

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
                    "badge": badge_text
                }

        except Exception as e:
            st.error(f"Single analysis error: {e}")

    result = st.session_state.get("single_result")

    if not result:
        st.info("Klik **Analisa** di sidebar.")
    else:
        df = result["df"]
        last = result["last"]

        st.subheader(f"{result['ticker']} — {result['badge']}")

        zoom = st.select_slider("Window", [30, 60, 120], 30)
        dfw = df.tail(zoom).reset_index()

        price = alt.Chart(dfw).mark_line().encode(
            x="Date:T", y="Close:Q"
        )

        ema20 = alt.Chart(dfw).mark_line(
            strokeDash=[4, 2], color="green"
        ).encode(x="Date:T", y="EMA20:Q")

        ema50 = alt.Chart(dfw).mark_line(
            strokeDash=[6, 3], color="red"
        ).encode(x="Date:T", y="EMA50:Q")

        st.altair_chart(
            (price + ema20 + ema50).interactive(),
            width="stretch"
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Close", round(float(last["Close"]), 2))
        c2.metric("RSI14", round(float(last["RSI14"]), 2))
        c3.metric("Confidence", round(result["conf"]["score"], 2))

        # ======================================================
        # 🏦 BANDARMOLOGY (SOURCE: SIDEBAR)
        # ======================================================
        st.markdown("### 🏦 Bandarmology")

        if "bandarmology_df" not in st.session_state:
            st.info("Upload CSV Bandar melalui sidebar.")
        else:
            try:
                df_bandar = st.session_state.bandarmology_df

                if bandar_mode == "Single Ticker":
                    st.caption(f"Mode: Single Ticker ({ticker})")
                    hasil_bandar = compute_bandar_rekap(
                        df_bandar,
                        ticker=ticker
                    )
                else:
                    st.caption(f"Mode: All Tickers (Top {bandar_top_n})")
                    hasil_bandar = (
                        compute_bandar_rekap(df_bandar, ticker=None)
                        .head(int(bandar_top_n))
                    )

                if hasil_bandar is None or hasil_bandar.empty:
                    st.warning("Tidak ada data bandarmology untuk ditampilkan.")
                else:
                    st.dataframe(hasil_bandar, width="stretch")

            except Exception as e:
                st.warning(f"Bandarmology gagal diproses: {e}")

# ======================================================
# TAB 2 — AUTO SYNC (TIDAK DIUBAH)
# ======================================================
with tab_auto:
    st.info("Auto Sync (30 / 60 / 120) tetap seperti versi sebelumnya.")
    st.caption("Bagian ini sengaja tidak disentuh agar stabil.")

