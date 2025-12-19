def confirm_by_volume(row):
    """
    Confirm entry using volume expansion
    """
    vol = row.get("Volume", 0)
    vol_ma = row.get("VolMA20", 0)

    if vol_ma == 0:
        return False

    return vol > vol_ma * 1.2
