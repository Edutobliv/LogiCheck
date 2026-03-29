import urllib.parse
import urllib.request
import threading
from core.logger import app_logger

class CallMeBotNotifier:
    def __init__(self, phone: str = "573152587012", apikey: str = "7002133"):
        self.phone = phone
        self.apikey = apikey
        self.base_url = "https://api.callmebot.com/whatsapp.php"

    def send_message_sync(self, text: str):
        try:
            texto_codificado = urllib.parse.quote(text)
            url = f"{self.base_url}?phone={self.phone}&text={texto_codificado}&apikey={self.apikey}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    app_logger.log_action("SISTEMA", "WHATSAPP_ENVIADO", "Mensaje enviado exitosamente")
                else:
                    app_logger.log_action("SISTEMA", "WHATSAPP_ERROR", f"Error HTTP {response.status}")
        except Exception as e:
            app_logger.log_action("SISTEMA", "WHATSAPP_ERROR", str(e))

    def send_message(self, text: str):
        """Envía el mensaje en un hilo separado para no bloquear la interfaz gráfica."""
        hilo = threading.Thread(target=self.send_message_sync, args=(text,))
        hilo.daemon = True
        hilo.start()

notifier = CallMeBotNotifier()
