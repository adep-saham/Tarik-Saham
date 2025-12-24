# services/profiler.py
import time
import pandas as pd

class Profiler:
    def __init__(self):
        self.rows = []

    def track(self, name: str, fn, *args, **kwargs):
        t0 = time.perf_counter()
        out = fn(*args, **kwargs)
        dt = (time.perf_counter() - t0) * 1000.0
        self.rows.append({"Step": name, "ms": round(dt, 2)})
        return out

    def df(self):
        if not self.rows:
            return pd.DataFrame(columns=["Step", "ms"])
        df = pd.DataFrame(self.rows)
        return df.sort_values("ms", ascending=False).reset_index(drop=True)
