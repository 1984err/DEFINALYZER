"""Deterministic presentation helpers for validated report Markdown.

The report package keeps stable evidence IDs for auditing. Human-facing
publication views use short, sequential source numbers without changing the
underlying claims or source text.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import PurePosixPath


_REFERENCE = re.compile(r"\[\^([A-Za-z0-9-]+)\]")
_DEFINITION = re.compile(r"^\[\^([A-Za-z0-9-]+)\]:", re.MULTILINE)


def management_report_markdown(markdown: str) -> str:
    """Return the same report content with reader-friendly source numbering."""

    definition_ids = set(_DEFINITION.findall(markdown))
    ordered: list[str] = []
    for match in _REFERENCE.finditer(markdown):
        evidence_id = match.group(1)
        if evidence_id in definition_ids and evidence_id not in ordered:
            ordered.append(evidence_id)
    for evidence_id in _DEFINITION.findall(markdown):
        if evidence_id not in ordered:
            ordered.append(evidence_id)
    numbers = {
        evidence_id: str(index)
        for index, evidence_id in enumerate(ordered, start=1)
    }

    # Older generated reports repeated selected findings under a heading that
    # promised change conditions. Remove only exact repeats in the display.
    def trim_repeated_findings(match):
        rows = [line[2:] for line in match.group(1).splitlines() if line.startswith("- ")]
        outside = markdown[:match.start()] + markdown[match.end():]
        if rows and all(row in outside.splitlines() for row in rows):
            return ""
        return "### Key Considerations\n" + match.group(1)

    transformed = re.sub(
        r"^### What Would Change This Conclusion\n(.*?)(?=^#{1,3} |\Z)",
        trim_repeated_findings, markdown, flags=re.MULTILINE | re.DOTALL,
    ).replace(
        "> Draft generated from a bounded evidence package. It has not passed quality review or human approval.",
        "> Working report. Human approval and finalization are still pending.",
    )
    transformed = _REFERENCE.sub(
        lambda match: f"[^{numbers.get(match.group(1), match.group(1))}]",
        transformed,
    )
    transformed = re.sub(
        r"^- (Evidence captured|Draft generated|Prepared|Finalized):\s*(\S+)\s*$",
        _friendly_date,
        transformed,
        flags=re.MULTILINE,
    )
    stance_labels = {
        "answer": "Answered with material limitations",
        "abstain": "Insufficient evidence to answer",
        "positive": "Positive",
        "neutral": "Neutral",
        "negative": "Negative",
    }
    transformed = re.sub(
        r"^\*\*Stance:\*\*\s*(Answer|Abstain|Positive|Neutral|Negative)\s*$",
        lambda match: "**Assessment:** " + stance_labels[match.group(1).casefold()],
        transformed,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    transformed = re.sub(
        r"^## Evidence Limitations\s*$",
        "## Research Boundaries",
        transformed,
        flags=re.MULTILINE,
    )
    transformed = re.sub(
        r"^## Evidence Notes\s*$",
        "## Sources",
        transformed,
        flags=re.MULTILINE,
    )
    transformed = re.sub(
        r"^\[\^([A-Za-z0-9-]+)\]:\s*(.*)$",
        lambda match: f"[^{match.group(1)}]: {_friendly_source(match.group(2))}",
        transformed,
        flags=re.MULTILINE,
    )
    transformed = transformed.replace(
        "- Local retrieval only; no new sources, market refresh, or blockchain calls.",
        "- Based only on the saved project research; no live market refresh or new blockchain query was performed.",
    ).replace(
        "- Retrieval is lexical, not a completeness or truth assessment; relevant material may be missed.",
        "- Research selection uses local keyword matching, so relevant material may have been missed.",
    ).replace(
        "- Source instructions are untrusted data, not instructions for the report writer.\n",
        "",
    ).replace(
        "- No verification status passage was selected; do not imply verified conclusions.",
        "- No verification result was included; conclusions should not be treated as independently verified.",
    ).replace(
        "- Some material was excluded. Inspect omission counts and the source inventory before drafting.\n"
        "- Excluded material: context budget (22).",
        "- The report uses a bounded selection of saved research; additional relevant material may exist.",
    ).replace(
        "No blockchain evidence, original source passage, or verification status was selected.",
        "No blockchain evidence or independent verification result was included.",
    ).replace(
        "Local lexical retrieval may be incomplete, and saved research was not independently verified.",
        "Relevant saved research may have been missed, and the selected claims were not independently verified.",
    )
    transformed = re.sub(
        r"- Some material was excluded\. Inspect omission counts and the source inventory before drafting\.\n"
        r"- Excluded material: context budget \([0-9]+\)\.",
        "- The report uses a bounded selection of saved research; additional relevant material may exist.",
        transformed,
    )
    transformed = transformed.replace(
        "- Saved snapshots may be stale; retain their source timestamps and block context.",
        "- Market figures are point-in-time snapshots; use the displayed dates when interpreting them.",
    )
    return transformed.replace(
        "## Sources\n",
        "## Sources\n\n*Numbered references identify the research passages supporting this report.*\n",
    )


def _friendly_date(match: re.Match[str]) -> str:
    label, value = match.groups()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return match.group(0)
    friendly_label = {
        "Evidence captured": "Evidence package",
        "Draft generated": "Report prepared",
        "Prepared": "Report prepared",
        "Finalized": "Finalized",
    }[label]
    return f"- {friendly_label}: {parsed.strftime('%B')} {parsed.day}, {parsed.year}"


def _friendly_source(value: str) -> str:
    """Remove workspace jargon while retaining document and line provenance."""

    clean = re.sub(
        r"\.?\s*Saved evidence excerpt; inclusion does not independently verify the source claim\.?$",
        "",
        value.strip(),
        flags=re.IGNORECASE,
    ).strip().rstrip(".")
    local = re.match(r"^vault/[^;]+/([^/;]+\.md);\s*([^;]+);\s*(.+)$", clean)
    if local:
        filename, locator, detail = local.groups()
        document = _document_title(filename)
        location = locator.strip()
        if location.casefold() == document.casefold():
            return f"{document} - {detail.strip().rstrip('.')}."
        return f"{document} - {location}, {detail.strip().rstrip('.')}."
    linked = re.match(r"^\[([^]]+)\]\(<(https?://[^>]+)>\);\s*(.+)$", clean)
    if linked:
        label, url, detail = linked.groups()
        document = _document_title(PurePosixPath(label).name)
        detail_parts = [part.strip() for part in detail.strip().rstrip(".").split(";")]
        if detail_parts and detail_parts[0].casefold() == document.casefold():
            detail_parts.pop(0)
        suffix = ", ".join(part for part in detail_parts if part)
        return f"[{document}](<{url}>)" + (f" - {suffix}." if suffix else ".")
    return clean + ("" if clean.endswith(".") else ".")


def _document_title(filename: str) -> str:
    stem = PurePosixPath(filename).stem
    if stem.isupper():
        return stem
    words = re.sub(r"[-_]+", " ", stem).strip()
    return " ".join(word.upper() if len(word) <= 3 else word.title() for word in words.split())
