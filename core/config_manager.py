# core/config_manager.py
# ============================================================
#  LogiCheck — Gestión de Configuración Persistente
# ============================================================

import json
import os
import threading

class ConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized: return
        self._config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config.json"
        )
        self._data = self._get_default_config()
        self.load()
        self._initialized = True

    def _get_default_config(self):
        return {
            "notifications": {
                "whatsapp": {
                    "phone": "573152587012",
                    "apikey": "7002133",
                    "url": "https://api.callmebot.com/whatsapp.php"
                },
                "telegram": {
                    "token": "8684027766:AAEMGl4j3WFUlYoMoIStgVUn35D8rVheRgk",
                    "chat_id": "8517822043"
                }
            },
            "cameras": {
                "default_user": "Samuel",
                "default_pass": "Samuel123.",
                "default_port": 554
            },
            "system": {
                "theme": "dark",
                "language": "es"
            }
        }

    def load(self):
        """Carga la configuración desde el archivo JSON."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    # Merge con default para asegurar que nuevas keys existan
                    self._data = self._merge_dicts(self._get_default_config(), loaded_data)
            except Exception as e:
                print(f"[CONFIG] Error cargando config: {e}")

    def save(self):
        """Guarda la configuración actual en el archivo JSON."""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[CONFIG] Error guardando config: {e}")

    def _merge_dicts(self, default, loaded):
        """Actualiza recursivamente el dict default con los valores del dict loaded."""
        for k, v in loaded.items():
            if isinstance(v, dict) and k in default and isinstance(default[k], dict):
                self._merge_dicts(default[k], v)
            else:
                default[k] = v
        return default

    def get(self, key_path, default=None):
        """Retorna un valor usando un path tipo 'notifications.telegram.token'."""
        keys = key_path.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def set(self, key_path, value):
        """Establece un valor usando un path y guarda automáticamente."""
        keys = key_path.split(".")
        current = self._data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        self.save()

# Singleton instance
config = ConfigManager()
