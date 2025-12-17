import requests

TELEGRAM_TOKEN = "ISI_TOKEN_ANDA"

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg})
