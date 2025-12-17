def consensus_rule(badges):
    b30, b60, b120 = badges[30], badges[60], badges[120]

    if b30 == "BUY" and b60 == "BUY":
        return "BUY"
    if b30 == "WAIT" and b60 == "BUY":
        return "EARLY"
    return "IGNORE"
