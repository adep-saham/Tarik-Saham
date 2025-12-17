import numpy as np
import pandas as pd

def safe_float(val):
    if isinstance(val, (pd.Series, list, np.ndarray)):
        try:
            val = val.iloc[-1]
        except Exception:
            try:
                val = val[-1]
            except Exception:
                return np.nan
    try:
        f = float(val)
        return f if not np.isnan(f) else np.nan
    except Exception:
        return np.nan
