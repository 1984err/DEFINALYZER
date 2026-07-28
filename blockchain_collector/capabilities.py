"""Machine-readable description of collector capabilities."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Mapping, Sequence

from .evidence import EVIDENCE_SCHEMA_VERSION
from .jobs import JOB_SCHEMA_VERSION, SUPPORTED_OPERATIONS, TARGET_OPERATIONS
from .request_validation import PARAMETER_RULES
from .rpc import SUPPORTED_CHAINS
from .standard_calls import STANDARD_FUNCTIONS


def capability_manifest() -> dict[str, Any]:
    return {
        "job_schema_version": JOB_SCHEMA_VERSION,
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "result_statuses": ["collected", "partial", "failed"],
        "chains": {
            key: asdict(configuration)
            for key, configuration in sorted(SUPPORTED_CHAINS.items())
        },
        "operations": {
            operation: _operation_manifest(operation)
            for operation in sorted(SUPPORTED_OPERATIONS)
        },
        "standard_functions": {
            name: {
                "signature": function.signature,
                "selector": function.selector,
                "argument_types": list(function.argument_types),
                "output_types": list(function.output_types),
            }
            for name, function in sorted(STANDARD_FUNCTIONS.items())
        },
        "interfaces": {
            "json_cli": (
                "python -m blockchain_collector <job.json> <evidence.json>"
            ),
            "guided_menu": "python -m blockchain_collector.menu",
            "capabilities": "python -m blockchain_collector.capabilities",
            "verification_import": (
                "python -m blockchain_collector.verification_import "
                "<source.md|json> <job.json> <report.json>"
            ),
        },
        "interpretation": False,
    }


def render_capability_manifest() -> str:
    return json.dumps(capability_manifest(), indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        raise SystemExit("The capabilities command does not accept arguments.")

    print(render_capability_manifest(), end="")
    return 0


def _operation_manifest(operation: str) -> Mapping[str, Any]:
    rule = PARAMETER_RULES[operation]
    return {
        "requires_registry_target": operation in TARGET_OPERATIONS,
        "required_parameters": sorted(rule.required),
        "optional_parameters": sorted(rule.optional),
    }


if __name__ == "__main__":
    raise SystemExit(main())
