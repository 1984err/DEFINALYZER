import tempfile
import unittest
from pathlib import Path

from definalyzer.settings import SettingsManager


class SettingsManagerTests(unittest.TestCase):
    def test_defaults_to_hermes_without_writing_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = SettingsManager(directory)
            settings = manager.load()

        self.assertEqual(settings["llm"]["provider"], "hermes")
        self.assertIsNone(settings["llm"]["executable"])
        self.assertNotIn("token", str(settings).lower())
        self.assertNotIn("api_key", str(settings).lower())

    def test_persists_non_secret_hermes_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = SettingsManager(directory)
            manager.configure_hermes(
                executable="C:/tools/hermes.exe",
                timeout_seconds=600,
            )
            settings = manager.load()

        self.assertEqual(
            settings["llm"]["executable"],
            "C:/tools/hermes.exe",
        )
        self.assertEqual(settings["llm"]["timeout_seconds"], 600)


if __name__ == "__main__":
    unittest.main()
