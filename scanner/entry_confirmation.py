def confirm_by_volume(row):
    """
    Confirm entry using volume expansion
    """
    vol = row.get("Volume", 0)
    vol_ma = row.get("VolMA20", 0)

    if vol_ma == 0:
        return False

    return vol > vol_ma * 1.2

def confirm_by_bandar(row):
    open_ = row.get("Open", 0)
    close = row.get("Close", 0)
    high = row.get("High", 0)
    low = row.get("Low", 0)

    body = abs(close - open_)
    upper_shadow = high - max(open_, close)

    if body == 0:
        return False

    return (
        close > open_
        and upper_shadow < body * 1.5
    )

def entry_confirmation(row):
    """
    Final entry confirmation:
    Volume OR Bandar confirmation
    """
    vol_ok = confirm_by_volume(row)
    bandar_ok = confirm_by_bandar(row)

    return vol_ok or bandar_ok
