import json
import unittest

from blockchain_collector.capabilities import (
    capability_manifest,
    render_capability_manifest,
)
from blockchain_collector.jobs import SUPPORTED_OPERATIONS
from blockchain_collector.request_validation import PARAMETER_RULES


class CapabilityManifestTests(unittest.TestCase):
    def test_manifest_covers_every_operation_and_parameter_rule(self):
        manifest = capability_manifest()

        self.assertEqual(
            set(manifest["operations"]),
            SUPPORTED_OPERATIONS,
        )
        self.assertEqual(
            set(manifest["operations"]),
            set(PARAMETER_RULES),
        )

    def test_exposes_supported_chains_and_standard_functions(self):
        manifest = capability_manifest()

        self.assertEqual(
            set(manifest["chains"]),
            {"ethereum", "arbitrum", "base"},
        )
        self.assertIn("balanceOf", manifest["standard_functions"])
        self.assertEqual(
            manifest["standard_functions"]["balanceOf"]["argument_types"],
            ["address"],
        )
        self.assertFalse(manifest["interpretation"])

    def test_rendered_manifest_is_valid_json(self):
        document = json.loads(render_capability_manifest())

        self.assertEqual(document["job_schema_version"], 1)
        self.assertEqual(
            document["result_statuses"],
            ["collected", "partial", "failed"],
        )


if __name__ == "__main__":
    unittest.main()
