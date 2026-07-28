import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from blockchain_collector.envfile import load_environment_file


class EnvironmentFileTests(unittest.TestCase):
    def test_loads_comments_quotes_and_export_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "# RPC endpoints\n"
                'ETHEREUM_RPC_URL="https://ethereum.example"\n'
                "export BASE_RPC_URL=https://base.example\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                load_environment_file(path)
                ethereum = os.environ["ETHEREUM_RPC_URL"]
                base = os.environ["BASE_RPC_URL"]

        self.assertEqual(ethereum, "https://ethereum.example")
        self.assertEqual(base, "https://base.example")

    def test_does_not_replace_existing_environment_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "ETHEREUM_RPC_URL=https://file.example\n",
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {"ETHEREUM_RPC_URL": "https://existing.example"},
                clear=True,
            ):
                load_environment_file(path)
                value = os.environ["ETHEREUM_RPC_URL"]

        self.assertEqual(value, "https://existing.example")


if __name__ == "__main__":
    unittest.main()
