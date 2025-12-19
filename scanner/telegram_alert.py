import requests
import streamlit as st

def send_telegram_alert(message: str):
    try:
        token = st.secrets["TELEGRAM_BOT_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    except Exception:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        r = requests.post(url, data=payload, timeout=5)
        return r.status_code == 200
    except Exception:
        return False
