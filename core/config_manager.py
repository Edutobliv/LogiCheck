# core/config_manager.py
# ============================================================
#  LogiCheck - Gestion de configuracion persistente
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
        if self._initialized:
            return
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._config_path = os.path.join(root, "config.json")
        self._local_config_path = os.path.join(root, "config.local.json")
        self._data = self._get_default_config()
        self.load()
        self._initialized = True

    def _get_default_config(self):
        return {
            "notifications": {
                "whatsapp": {
                    "phone": "",
                    "apikey": "",
                    "url": "https://api.callmebot.com/whatsapp.php",
                },
                "telegram": {
                    "token": "",
                    "chat_id": "",
                },
            },
            "cameras": {
                "host": "",
                "default_user": "",
                "default_pass": "",
                "default_port": 554,
                "mode": "local",
                "serial_number": "",
            },
            "ai": {
                "model_path": "",
            },
            "system": {
                "theme": "dark",
                "language": "es",
            },
        }

    def load(self):
        """Carga defaults seguros, config.json, config.local.json y variables de entorno."""
        self._data = self._get_default_config()
        for path in (self._config_path, self._local_config_path):
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                self._data = self._merge_dicts(self._data, loaded_data)
            except Exception as e:
                print(f"[CONFIG] Error cargando {path}: {e}")
        self._apply_env_overrides()

    def save(self):
        """Guarda valores locales en config.local.json para no versionar secretos."""
        try:
            with open(self._local_config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[CONFIG] Error guardando config local: {e}")

    def save_defaults(self):
        """Reescribe config.json solo con valores seguros de ejemplo."""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._get_default_config(), f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[CONFIG] Error guardando defaults: {e}")

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
        """Establece un valor usando un path y guarda automaticamente."""
        self._set_in_memory(key_path, value)
        self.save()

    def _set_in_memory(self, key_path, value):
        keys = key_path.split(".")
        current = self._data
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def _apply_env_overrides(self):
        env_map = {
            "LOGICHECK_TG_TOKEN": "notifications.telegram.token",
            "LOGICHECK_TG_CHAT_ID": "notifications.telegram.chat_id",
            "LOGICHECK_WA_PHONE": "notifications.whatsapp.phone",
            "LOGICHECK_WA_APIKEY": "notifications.whatsapp.apikey",
            "LOGICHECK_CAMERA_HOST": "cameras.host",
            "LOGICHECK_CAMERA_USER": "cameras.default_user",
            "LOGICHECK_CAMERA_PASS": "cameras.default_pass",
            "LOGICHECK_MODEL_PATH": "ai.model_path",
        }
        for env_name, key_path in env_map.items():
            value = os.environ.get(env_name)
            if value:
                self._set_in_memory(key_path, value)


config = ConfigManager()
