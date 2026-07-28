"""Command-line interface for raw blockchain evidence collection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .envfile import load_environment_file
from .evidence import write_evidence_bundle
from .executor import execute_collection_job
from .jobs import load_collection_job


EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_PARTIAL_FAILURE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m blockchain_collector",
        description=(
            "Collect raw EVM evidence from a versioned JSON job. "
            "This command does not interpret or verify claims."
        ),
    )
    parser.add_argument("job", help="Path to the collection job JSON file.")
    parser.add_argument(
        "output",
        help="Path for the new evidence JSON file. Existing files are preserved.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Environment file containing RPC URLs. Default: .env",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    job_path = Path(args.job).resolve()
    output_path = Path(args.output).resolve()
    env_path = Path(args.env_file).resolve()

    try:
        if env_path.exists():
            load_environment_file(env_path)

        job = load_collection_job(job_path)
        bundle = execute_collection_job(job, job_source=str(job_path))
        write_evidence_bundle(bundle, output_path)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Collection stopped: {exc}", file=sys.stderr)
        return EXIT_ERROR

    collected = sum(record.status == "collected" for record in bundle.records)
    partial = sum(record.status == "partial" for record in bundle.records)
    failed = sum(record.status == "failed" for record in bundle.records)

    print(f"Job:       {bundle.job_name}")
    print(f"Collected: {collected}")
    print(f"Partial:   {partial}")
    print(f"Failed:    {failed}")
    print(f"Evidence:  {output_path}")

    if partial or failed:
        print(
            "Evidence was written, but one or more requests are incomplete.",
            file=sys.stderr,
        )
        return EXIT_PARTIAL_FAILURE

    return EXIT_SUCCESS
