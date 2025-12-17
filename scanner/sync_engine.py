from analysis.interpretation import interpret_last
from analysis.badge import get_trade_badge

def check_sync(df_ind, plan, conf):
    results = {}

    for w in [30, 60, 120]:
        df_w = df_ind.tail(w)
        last = df_w.iloc[-1]
        desc = interpret_last(last)

        badge, _ = get_trade_badge(
            conf["score"],
            plan.get("status"),
            desc.get("Trend EMA")
        )
        results[w] = badge

    return results
