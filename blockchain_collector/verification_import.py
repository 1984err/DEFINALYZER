"""Translate structured verification requests into neutral collection jobs.

The importer performs schema validation and mechanical translation only.  It
does not choose evidence methods, interpret claims, or decide whether a claim
is supported.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .jobs import CollectionJob


IMPORT_SCHEMA_VERSION = 1
REQUEST_FIELDS = frozenset(
    {
        "id",
        "claim",
        "why_verify",
        "chain",
        "operation",
        "parameters",
        "target",
    }
)
FENCE_PATTERN = re.compile(
    r"```definalyzer-verification[ \t]*\r?\n"
    r"(?P<body>.*?)"
    r"\r?\n```",
    re.DOTALL,
)


@dataclass(frozen=True)
class ImportResult:
    """A validated job plus an audit report for every source request."""

    job_document: Mapping[str, Any] | None
    report: Mapping[str, Any]

    @property
    def job(self) -> CollectionJob | None:
        if self.job_document is None:
            return None
        return CollectionJob.from_mapping(self.job_document)


def import_verification_requests(
    document: Mapping[str, Any],
    *,
    source: str,
    job_name: str | None = None,
) -> ImportResult:
    """Convert valid source rows and retain invalid rows for manual review."""

    if document.get("schema_version") != IMPORT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported verification schema_version "
            f"{document.get('schema_version')!r}; expected "
            f"{IMPORT_SCHEMA_VERSION}."
        )

    source_name = _required_text(document, "name")
    output_name = job_name or source_name
    rows = document.get("requests")

    if not isinstance(rows, list) or not rows:
        raise ValueError("'requests' must be a non-empty list.")

    ready_requests: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []
    request_names: set[str] = set()

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            report_rows.append(
                {
                    "index": index,
                    "status": "manual_review",
                    "reason": "Request must be an object.",
                    "source_request": row,
                }
            )
            continue

        request_id = row.get("id")
        claim = row.get("claim")
        request_document = {}

        try:
            request_id = _required_text(row, "id")
            claim = _required_text(row, "claim")
            _required_text(row, "why_verify")
            unexpected = sorted(set(row) - REQUEST_FIELDS)

            if unexpected:
                raise ValueError(
                    "Unexpected verification request field(s): "
                    + ", ".join(unexpected)
                    + "."
                )

            request_document = {
                "name": request_id,
                **{
                    key: row[key]
                    for key in (
                        "chain",
                        "operation",
                        "parameters",
                        "target",
                    )
                    if key in row
                },
            }
            request = _validate_one_request(request_document, request_names)
        except ValueError as exc:
            report_rows.append(
                {
                    "index": index,
                    "id": request_id,
                    "claim": claim,
                    "status": "manual_review",
                    "reason": str(exc),
                    "source_request": row,
                }
            )
            continue

        request_names.add(request.name)
        ready_requests.append(request_document)
        report_rows.append(
            {
                "index": index,
                "id": request_id,
                "claim": claim,
                "collection_request": request.name,
                "status": "ready",
            }
        )

    job_document: dict[str, Any] | None = None

    if ready_requests:
        job_document = {
            "schema_version": 1,
            "name": output_name,
            "metadata": {
                "created_by": "verification-request-importer",
                "verification_source": source,
                "verification_document_name": source_name,
                "verification_requests": [
                    {
                        "id": row.get("id"),
                        "claim": row.get("claim"),
                        "why_verify": row.get("why_verify"),
                        "collection_request": row.get("id"),
                    }
                    for row in rows
                    if isinstance(row, dict)
                    and row.get("id") in request_names
                ],
            },
            "requests": ready_requests,
        }
        CollectionJob.from_mapping(job_document)

    ready_count = sum(row["status"] == "ready" for row in report_rows)
    manual_count = len(report_rows) - ready_count
    report = {
        "import_schema_version": IMPORT_SCHEMA_VERSION,
        "source": source,
        "source_name": source_name,
        "job_name": output_name if job_document else None,
        "status": (
            "ready"
            if not manual_count
            else "partial"
            if ready_count
            else "manual_review"
        ),
        "ready_count": ready_count,
        "manual_review_count": manual_count,
        "requests": report_rows,
        "interpretation_performed": False,
    }
    return ImportResult(job_document=job_document, report=report)


def load_verification_requests(path: str | Path) -> Mapping[str, Any]:
    """Load raw JSON or one exact fenced JSON block from Markdown."""

    input_path = Path(path)
    text = input_path.read_text(encoding="utf-8")

    if input_path.suffix.lower() == ".json":
        payload = text
    else:
        matches = list(FENCE_PATTERN.finditer(text))

        if not matches:
            raise ValueError(
                "Markdown must contain one fenced "
                "```definalyzer-verification JSON block."
            )
        if len(matches) != 1:
            raise ValueError(
                "Markdown contains multiple definalyzer-verification blocks; "
                "split them into separate source files."
            )
        payload = matches[0].group("body")

    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Verification request JSON is invalid: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})."
        ) from exc

    if not isinstance(document, dict):
        raise ValueError("Verification request document must be a JSON object.")

    return document


def write_json_new(document: Mapping[str, Any], path: str | Path) -> Path:
    """Write indented JSON without replacing an existing artifact."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with output_path.open("x", encoding="utf-8", newline="\n") as file:
            json.dump(document, file, indent=2)
            file.write("\n")
    except FileExistsError as exc:
        raise FileExistsError(
            f"Output already exists and will not be overwritten: {output_path}"
        ) from exc

    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m blockchain_collector.verification_import",
        description=(
            "Translate structured verification requests into a validated "
            "collector job without interpreting any claims."
        ),
    )
    parser.add_argument("source", help="Markdown or JSON verification request file.")
    parser.add_argument("job", help="Path for the new collection-job JSON.")
    parser.add_argument(
        "report",
        help="Path for the new import report, including manual-review rows.",
    )
    parser.add_argument(
        "--job-name",
        help="Override the job name declared in the source document.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_path = Path(args.source).resolve()
    job_path = Path(args.job).resolve()
    report_path = Path(args.report).resolve()

    try:
        if job_path.exists() or report_path.exists():
            existing = job_path if job_path.exists() else report_path
            raise FileExistsError(
                f"Output already exists and will not be overwritten: {existing}"
            )

        document = load_verification_requests(source_path)
        result = import_verification_requests(
            document,
            source=str(source_path),
            job_name=args.job_name,
        )
        write_json_new(result.report, report_path)

        if result.job_document is not None:
            write_json_new(result.job_document, job_path)
    except (OSError, ValueError) as exc:
        print(f"Import stopped: {exc}", file=sys.stderr)
        return 1

    print(f"Ready:         {result.report['ready_count']}")
    print(f"Manual review: {result.report['manual_review_count']}")
    print(f"Report:        {report_path}")

    if result.job_document is None:
        print("No collection job was created.", file=sys.stderr)
        return 2

    print(f"Job:           {job_path}")
    return 0 if result.report["manual_review_count"] == 0 else 2


def _validate_one_request(
    request_document: Mapping[str, Any],
    request_names: set[str],
):
    from .jobs import CollectionRequest

    request = CollectionRequest.from_mapping(request_document)

    if request.name in request_names:
        raise ValueError(f"Duplicate request name {request.name!r}.")

    return request


def _required_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)

    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{key!r} must be non-empty text.")

    return item.strip()


if __name__ == "__main__":
    raise SystemExit(main())
