# scanner/auto_scan_bundle.py
from typing import List, Dict, Set, Tuple
import streamlit as st

def auto_scan_30_60_120(
    tickers: List[str],
    scan_window_func,
    load_price_data,
    calc_indicators,
    profiler=None
) -> Dict[str, Set[str]]:
    """
    Run scan 30/60/120 sequentially with progress.
    Returns dict: {"w30": set(...), "w60": set(...), "w120": set(...)}
    """

    results = {"w30": set(), "w60": set(), "w120": set()}
    windows = [30, 60, 120]

    progress = st.progress(0)
    status = st.empty()

    for i, w in enumerate(windows, start=1):
        status.info(f"🔎 Scanning window {w} ({i}/3) — universe: {len(tickers)}")

        def _do_scan():
            wlist, _ = scan_window_func(w, tickers, load_price_data, calc_indicators)
            return set(wlist)

        try:
            if profiler:
                out = profiler.track(f"scan_window({w})", _do_scan)
            else:
                out = _do_scan()

            results[f"w{w}"] = out
            st.toast(f"✅ Scan {w} selesai: {len(out)} saham")

        except Exception as e:
            st.warning(f"⚠️ Scan {w} gagal: {e}")
            results[f"w{w}"] = set()

        progress.progress(int(i / 3 * 100))

    status.success("✅ Auto Scan selesai (30/60/120)")
    return results
