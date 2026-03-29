import requests
import threading
from core import logger as app_logger

class LogiNotifier:
    def __init__(self):
        # Configuraciones WhatsApp (CallMeBot)
        self.wa_phone = "573152587012"
        self.wa_apikey = "7002133"
        self.wa_url = "https://api.callmebot.com/whatsapp.php"

        # Configuraciones Telegram (TOKEN y CHAT_ID)
        self.tg_token = "8684027766:AAEMGl4j3WFUlYoMoIStgVUn35D8rVheRgk"
        self.tg_chat_id = "8517822043"
        self.tg_base_url = f"https://api.telegram.org/bot{self.tg_token}"

    def _send_wa_sync(self, text: str):
        try:
            params = {
                "phone": self.wa_phone,
                "text": text,
                "apikey": self.wa_apikey
            }
            response = requests.get(self.wa_url, params=params, timeout=12)
            if response.status_code == 200:
                app_logger.log_action({"username": "SISTEMA", "role": "sistema"}, "WHATSAPP_ENVIADO", "Reporte enviado")
        except Exception as e:
            app_logger.log_action({"username": "SISTEMA", "role": "sistema"}, "WHATSAPP_ERROR", str(e))

    def _send_tg_sync(self, text: str, photo_path: str = None):
        if not self.tg_chat_id: return
        try:
            if photo_path:
                url = f"{self.tg_base_url}/sendPhoto"
                files = {'photo': open(photo_path, 'rb')}
                data = {'chat_id': self.tg_chat_id, 'caption': text, 'parse_mode': 'HTML'}
                response = requests.post(url, data=data, files=files, timeout=15)
            else:
                url = f"{self.tg_base_url}/sendMessage"
                data = {'chat_id': self.tg_chat_id, 'text': text, 'parse_mode': 'HTML'}
                response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                app_logger.log_action({"username": "SISTEMA", "role": "sistema"}, "TELEGRAM_ENVIADO", "Alerta/Foto enviada")
        except Exception as e:
            app_logger.log_action({"username": "SISTEMA", "role": "sistema"}, "TELEGRAM_ERROR", str(e))

    def send_whatsapp(self, text: str):
        threading.Thread(target=self._send_wa_sync, args=(text,), daemon=True).start()

    def send_telegram(self, text: str, photo_path: str = None):
        threading.Thread(target=self._send_tg_sync, args=(text, photo_path), daemon=True).start()

notifier = LogiNotifier()
