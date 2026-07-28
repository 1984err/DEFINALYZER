import json
import tempfile
import unittest
from pathlib import Path

from blockchain_collector.registry import RegistryTarget, load_registry_targets


ADDRESS = "0x1234567890abcdef1234567890ABCDEF12345678"


class RegistryTargetTests(unittest.TestCase):
    def test_preserves_documented_address_casing(self) -> None:
        target = RegistryTarget.from_mapping(
            {
                "address": ADDRESS,
                "chain": "Ethereum",
                "source": "https://docs.example/deployments",
            }
        )

        self.assertEqual(target.address, ADDRESS)

    def test_rejects_registry_placeholder(self) -> None:
        with self.assertRaisesRegex(ValueError, "documented text value"):
            RegistryTarget.from_mapping(
                {
                    "address": "Not documented",
                    "chain": "Ethereum",
                    "source": "registry.md",
                }
            )

    def test_rejects_negative_deployment_block(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            RegistryTarget.from_mapping(
                {
                    "address": ADDRESS,
                    "chain": "Ethereum",
                    "source": "registry.md",
                    "deployment_block": -1,
                }
            )


class RegistryLoaderTests(unittest.TestCase):
    def test_loads_wrapped_targets_and_retains_duplicates(self) -> None:
        row = {
            "address": ADDRESS,
            "chain": "Ethereum",
            "source": "registry.md",
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps({"targets": [row, row]}), encoding="utf-8")
            targets = load_registry_targets(path)

        self.assertEqual(len(targets), 2)
        self.assertEqual(targets[0], targets[1])

    def test_reports_invalid_row_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps({"targets": ["bad-row"]}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "index 0"):
                load_registry_targets(path)


if __name__ == "__main__":
    unittest.main()
