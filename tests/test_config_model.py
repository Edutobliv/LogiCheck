import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config_manager import ConfigManager
import core.model_resolver as model_resolver


class TestConfigAndModelResolver(unittest.TestCase):
    def test_config_defaults_do_not_embed_secrets(self):
        cfg = ConfigManager()
        defaults = cfg._get_default_config()
        self.assertEqual(defaults["notifications"]["telegram"]["token"], "")
        self.assertEqual(defaults["notifications"]["whatsapp"]["apikey"], "")
        self.assertEqual(defaults["cameras"]["default_pass"], "")

    def test_model_resolver_prefers_configured_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_path = os.path.join(tmp, "custom.pt")
            with open(model_path, "wb") as f:
                f.write(b"weights")

            old_get = model_resolver.config.get
            old_base = model_resolver.get_project_base_dir
            try:
                model_resolver.config.get = lambda key, default=None: model_path if key == "ai.model_path" else default
                model_resolver.get_project_base_dir = lambda: tmp
                resolved = model_resolver.resolve_model_path(required=True)
                self.assertEqual(resolved.path, model_path)
                self.assertEqual(resolved.source, "config")
            finally:
                model_resolver.config.get = old_get
                model_resolver.get_project_base_dir = old_base


if __name__ == "__main__":
    unittest.main(verbosity=2)
