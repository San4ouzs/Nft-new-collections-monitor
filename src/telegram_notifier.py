import requests

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, text: str):
        if not self.bot_token or not self.chat_id:
            print("[WARN] Telegram creds not set; message would be:\n", text)
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True
        }
        r = requests.post(url, json=payload, timeout=15)
        if not r.ok:
            print("[ERROR] Telegram send failed:", r.text)
