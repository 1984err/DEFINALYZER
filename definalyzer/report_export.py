"""Immutable publication exports for finalized, evidence-backed reports.

This module is deliberately provider-free.  It publishes only the exact report
revision already approved by a human.  Optional charts extract numeric values
directly from saved structured evidence so a model cannot invent graph data.
"""

from __future__ import annotations

import html
import json
import math
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse

from .report_contract import (
    REPORT_SCHEMA_VERSION, content_sha256, report_package, report_timestamp,
    validate_report_manifest,
)
from .report_evidence import load_report_evidence
from .report_generation import load_report_draft
from .report_generation import escape_report_markdown
from .report_lifecycle import load_final_report
from .report_presentation import management_report_markdown
from .workspace import ProjectWorkspace


EXPORT_SCHEMA_VERSION = 1
EXPORT_FORMATS = {"markdown", "html", "pdf"}
CHART_SOURCE_TYPES = {"market_data", "blockchain_evidence"}
EVIDENCE_ID = re.compile(r"^E-[0-9]{3,}$")
FIELD_PATH = re.compile(r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$")
SAFE_ASSET = re.compile(r"^Assets/chart-[0-9]{3}\.svg$")


def download_report_pdf(*, workspace: ProjectWorkspace, report_id: str) -> bytes:
    """Render a saved report without changing it or recording human approval."""
    draft = load_report_draft(workspace=workspace, report_id=report_id)
    if draft.readiness == "insufficient":
        raise ValueError("No substantive report is available; read the analyst notes.")
    if draft.modified or draft.analyst_notes_modified:
        raise ValueError("Report files changed outside the report workflow; review those edits first.")
    package = report_package(workspace, report_id)
    manifest = _read_json(package.manifest_path)
    if manifest["status"] == "final":
        load_final_report(workspace=workspace, report_id=report_id)
        label = "Final report - approved"
    else:
        labels = {"not_run": "not run", "passed": "passed", "issues_found": "issues found"}
        quality = labels.get(manifest["quality"]["status"], "not completed")
        label = f"Working report - quality review: {quality}; not finalized"
    lines = draft.markdown.splitlines()
    lines[1:1] = ["", f"> {label}", ""]
    # Older reports kept these qualifications only in the analyst companion.
    # Include them in the download without changing the saved report or claims.
    if "### Key Qualifications" not in draft.markdown:
        limits = draft.claims["assertions"][-1].get("limitations", [])
        if limits:
            index = next((i for i, line in enumerate(lines) if line == "## Evidence Notes"), len(lines))
            lines[index:index] = ["### Key Qualifications", "", *[
                f"- {escape_report_markdown(item)}" for item in dict.fromkeys(limits)
            ], ""]
    publication = management_report_markdown("\n".join(lines))
    with TemporaryDirectory(prefix="definalyzer-pdf-") as directory:
        path = Path(directory) / "Report.pdf"
        _write_pdf(path, markdown=publication, title=manifest["title"],
                   subject=manifest["project"]["name"], charts=())
        return path.read_bytes()


@dataclass(frozen=True)
class ChartRequest:
    """A deterministic chart whose values are read from one evidence excerpt.

    ``fields`` contains ``(display label, dotted JSON field path)`` pairs.  No
    numeric values are accepted from the caller.
    """

    title: str
    evidence_id: str
    fields: tuple[tuple[str, str], ...]
    unit: str
    limitations: str = (
        "Point-in-time saved snapshot; this visual does not establish a trend "
        "or causal relationship."
    )
    kind: str = "bar"

    @classmethod
    def from_fields(
        cls, *, title: str, evidence_id: str, fields: Mapping[str, str],
        unit: str, limitations: str | None = None,
    ) -> "ChartRequest":
        return cls(
            title=title, evidence_id=evidence_id,
            fields=tuple(fields.items()), unit=unit,
            limitations=limitations or cls.__dataclass_fields__["limitations"].default,
        )


@dataclass(frozen=True)
class ReportExportResult:
    report_id: str
    revision: int
    directory: Path
    markdown_path: Path | None
    html_path: Path | None
    pdf_path: Path | None
    manifest_path: Path


def export_final_report(
    *, workspace: ProjectWorkspace, report_id: str,
    formats: Iterable[str] = ("markdown", "html", "pdf"),
    charts: Sequence[ChartRequest] = (), now: str | None = None,
) -> ReportExportResult:
    """Export one immutable publication bundle from a finalized report.

    The export refuses drafts, changed final files, stale approvals, unknown
    formats, and repeated export attempts.  This keeps a publication traceable
    to the exact approved report revision.
    """

    requested_formats = tuple(dict.fromkeys(formats))
    if not requested_formats or set(requested_formats) - EXPORT_FORMATS:
        raise ValueError("Export formats must be one or more of: markdown, html, pdf.")
    final = load_final_report(workspace=workspace, report_id=report_id)
    package = report_package(workspace, report_id)
    manifest = _read_json(package.manifest_path)
    validate_report_manifest(manifest, workspace=workspace)
    draft = load_report_draft(workspace=workspace, report_id=report_id)
    evidence = load_report_evidence(workspace=workspace, report_id=report_id)
    approval = _read_json(package.approval_path)

    exported_at = report_timestamp(now)
    if _parse_timestamp(exported_at) < _parse_timestamp(final.finalized_at):
        raise ValueError("Export timestamp cannot precede report finalization.")
    revision = final.revision
    target = package.exports_directory / f"revision-{revision:04d}"
    _safe_export_root(workspace, package.exports_directory)
    if target.exists():
        raise FileExistsError(
            f"This final report revision already has an export: {target.name}"
        )
    package.exports_directory.mkdir(parents=True, exist_ok=True)
    temporary = package.exports_directory / f".{target.name}-{uuid.uuid4().hex}.tmp"
    temporary.mkdir()
    try:
        assets = temporary / "Assets"
        assets.mkdir()
        chart_documents = [
            _build_chart(request, evidence=evidence, sequence=index)
            for index, request in enumerate(charts, start=1)
        ]
        for chart in chart_documents:
            (assets / chart["filename"]).write_text(
                _render_chart_svg(chart), encoding="utf-8", newline="\n"
            )
            _write_json(assets / chart["data_filename"], chart)

        publication = _publication_markdown(
            draft.markdown, finalized_at=final.finalized_at,
            charts=chart_documents,
        )
        file_hashes: dict[str, str] = {}
        analyst_notes_path = temporary / "Analyst-Notes.md"
        analyst_notes_path.write_text(
            draft.analyst_notes, encoding="utf-8", newline="\n"
        )
        file_hashes["Analyst-Notes.md"] = content_sha256(
            analyst_notes_path.read_bytes()
        )
        markdown_path = None
        html_path = None
        pdf_path = None
        if "markdown" in requested_formats:
            markdown_path = temporary / "Report.md"
            markdown_path.write_text(publication, encoding="utf-8", newline="\n")
            file_hashes["Report.md"] = content_sha256(markdown_path.read_bytes())
        if "html" in requested_formats:
            html_path = temporary / "Report.html"
            html_document = _publication_html(
                publication, title=manifest["title"], charts=chart_documents,
            )
            html_path.write_text(html_document, encoding="utf-8", newline="\n")
            file_hashes["Report.html"] = content_sha256(html_path.read_bytes())
        if "pdf" in requested_formats:
            pdf_path = temporary / "Report.pdf"
            _write_pdf(
                pdf_path, markdown=publication, title=manifest["title"],
                subject=manifest["project"]["name"], charts=chart_documents,
            )
            file_hashes["Report.pdf"] = content_sha256(pdf_path.read_bytes())
        for asset in sorted(assets.iterdir(), key=lambda path: path.name):
            file_hashes[f"Assets/{asset.name}"] = content_sha256(asset.read_bytes())

        export_manifest = {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "report_schema_version": REPORT_SCHEMA_VERSION,
            "report_id": report_id,
            "revision": revision,
            "exported_at": exported_at,
            "formats": list(requested_formats),
            "source": {
                "finalized_at": final.finalized_at,
                "report_sha256": approval["report_sha256"],
                "analyst_notes_sha256": content_sha256(draft.analyst_notes),
                "claims_sha256": approval["claims_sha256"],
                "quality_sha256": approval["quality_sha256"],
                "approval_sha256": manifest["human_review"]["approval_sha256"],
            },
            "files": file_hashes,
            "charts": [
                {
                    "chart_id": chart["chart_id"],
                    "title": chart["title"],
                    "evidence_id": chart["evidence_id"],
                    "as_of": chart["as_of"],
                    "unit": chart["unit"],
                    "transformation": chart["transformation"],
                    "limitations": chart["limitations"],
                    "data_file": f"Assets/{chart['data_filename']}",
                    "image_file": f"Assets/{chart['filename']}",
                }
                for chart in chart_documents
            ],
            "publication_note": (
                "A publication export preserves the approved analysis. Chart "
                "values, when present, are direct fields from saved evidence."
            ),
        }
        _validate_export_manifest(export_manifest)
        _write_json(temporary / "export.json", export_manifest)
        temporary.replace(target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)

    return ReportExportResult(
        report_id=report_id, revision=revision, directory=target,
        markdown_path=target / "Report.md" if markdown_path else None,
        html_path=target / "Report.html" if html_path else None,
        pdf_path=target / "Report.pdf" if pdf_path else None,
        manifest_path=target / "export.json",
    )


def _build_chart(
    request: ChartRequest, *, evidence: Mapping[str, Any], sequence: int,
) -> dict[str, Any]:
    title = _single_line(request.title, "Chart title", 120)
    unit = _single_line(request.unit, "Chart unit", 60)
    limitations = _single_line(request.limitations, "Chart limitations", 500)
    if request.kind != "bar":
        raise ValueError("The current publication contract supports bar charts only.")
    if not EVIDENCE_ID.fullmatch(request.evidence_id):
        raise ValueError("Chart evidence IDs must use E-001 format.")
    if not 1 <= len(request.fields) <= 12:
        raise ValueError("A chart requires between 1 and 12 numeric fields.")
    rows = {row["evidence_id"]: row for row in evidence["evidence"]}
    row = rows.get(request.evidence_id)
    if row is None:
        raise ValueError(f"Chart references unknown evidence: {request.evidence_id}")
    if row["source_type"] not in CHART_SOURCE_TYPES:
        raise ValueError(
            "Charts require structured market_data or blockchain_evidence JSON."
        )
    if row.get("as_of") is None:
        raise ValueError("A chart requires dated evidence with an as_of timestamp.")
    try:
        document = json.loads(row["excerpt"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Chart evidence must be a saved JSON object.") from exc
    if not isinstance(document, dict):
        raise ValueError("Chart evidence must be a saved JSON object.")
    labels: set[str] = set()
    paths: set[str] = set()
    points = []
    for label, field_path in request.fields:
        clean_label = _single_line(label, "Chart field label", 60)
        if clean_label in labels:
            raise ValueError("Chart field labels must be unique.")
        if not isinstance(field_path, str) or not FIELD_PATH.fullmatch(field_path):
            raise ValueError("Chart JSON fields must be simple dotted paths.")
        if field_path in paths:
            raise ValueError("Chart JSON field paths must be unique.")
        labels.add(clean_label)
        paths.add(field_path)
        value: Any = document
        for component in field_path.split("."):
            if not isinstance(value, dict) or component not in value:
                raise ValueError(f"Chart field was not found in evidence: {field_path}")
            value = value[component]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Chart field is not numeric: {field_path}")
        if not math.isfinite(float(value)):
            raise ValueError(f"Chart field is not finite: {field_path}")
        points.append({"label": clean_label, "field": field_path, "value": value})
    chart_id = f"chart-{sequence:03d}"
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "chart_id": chart_id,
        "title": title,
        "kind": "bar",
        "evidence_id": request.evidence_id,
        "source_type": row["source_type"],
        "source_path": row["source_path"],
        "source_url": row.get("source_url"),
        "source_locator": row["locator"],
        "evidence_content_sha256": row["content_sha256"],
        "as_of": row["as_of"],
        "unit": unit,
        "transformation": "Direct JSON field extraction; no arithmetic.",
        "limitations": limitations,
        "points": points,
        "filename": f"{chart_id}.svg",
        "data_filename": f"{chart_id}.json",
    }


def _publication_markdown(
    markdown: str, *, finalized_at: str, charts: Sequence[Mapping[str, Any]],
) -> str:
    lines = markdown.splitlines()
    output = []
    for line in lines:
        if line == "> Draft generated from a bounded evidence package. It has not passed quality review or human approval.":
            continue
        if line.startswith("- Draft generated:") or line.startswith("- Prepared:"):
            output.append(f"- Finalized: {finalized_at}")
            continue
        output.append(line)
    if charts:
        section = ["## Data Visuals", ""]
        for chart in charts:
            section.extend([
                f"### {chart['title']}", "",
                f"![{chart['title']}](Assets/{chart['filename']})", "",
                f"- Evidence: {chart['evidence_id']}",
                f"- As of: {chart['as_of']}",
                f"- Unit: {chart['unit']}",
                f"- Transformation: {chart['transformation']}",
                f"- Limitation: {chart['limitations']}", "",
            ])
        insertion = next(
            (index for index, line in enumerate(output) if line == "## Evidence Notes"),
            len(output),
        )
        output[insertion:insertion] = section
    while len(output) > 1 and not output[-1].strip():
        output.pop()
    return management_report_markdown("\n".join(output).rstrip() + "\n")


def _publication_html(
    markdown: str, *, title: str, charts: Sequence[Mapping[str, Any]],
) -> str:
    body = _markdown_to_html(markdown)
    css = """
:root{color-scheme:light;--ink:#172331;--muted:#66717e;--navy:#121a38;--cyan:#00a6d6;--magenta:#bd2d7d;--violet:#6846c7;--line:#dfe4e8}
*{box-sizing:border-box}body{margin:0;background:#f3f5f6;color:var(--ink);font:16px/1.62 "Segoe UI",Inter,Arial,sans-serif}
main{max-width:1040px;margin:32px auto;background:#fff;min-height:100vh;padding:78px 92px 88px;box-shadow:0 16px 52px #17233112;position:relative;overflow:hidden}
main:before{content:"";position:absolute;inset:0 0 auto;height:11px;background:linear-gradient(90deg,var(--cyan) 0 42%,var(--violet) 42% 72%,var(--magenta) 72%)}
h1,h2,h3{line-height:1.08;color:var(--navy);letter-spacing:-.025em}h1{font-size:3.7rem;font-weight:650;max-width:820px;margin:0 0 .45em}
h2{font-size:1.78rem;font-weight:650;margin:0}h3{font-size:1.25rem;color:var(--violet);margin-top:2em}
p{margin:.65em 0}a{color:#057b9e;text-decoration:none}a:hover{text-decoration:underline}
blockquote{margin:0 0 1.25em;padding:0;color:var(--magenta);font-size:.76rem;font-weight:650;letter-spacing:.08em;text-transform:uppercase}
h1+ul,h1+blockquote+ul{display:flex;flex-wrap:wrap;gap:.4em 1.6em;list-style:none;padding:0 0 2em;margin:0;border-bottom:1px solid var(--line);color:var(--muted);font-size:.8rem}
.report-section{padding-top:3.25rem}.section-heading{display:grid;grid-template-columns:2.5rem 1fr;align-items:end;gap:.75rem;margin-bottom:1.15rem}
.section-number{color:var(--cyan);font-size:.72rem;font-weight:750;letter-spacing:.08em;padding-bottom:.23rem}
.executive-summary>ul,.qualified-conclusion>ul{list-style:none;margin:0;padding:0 0 0 1.6rem;border-left:5px solid var(--cyan);font-size:1.25rem;line-height:1.5;color:var(--navy)}
.qualified-conclusion>ul{border-left-color:var(--magenta);font-size:1.13rem}.qualified-conclusion>p:first-of-type{color:var(--magenta);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700}
ul,ol{padding-left:1.25em}.finding-note{font-size:.88rem;color:var(--muted);margin:.42em 0 .7em 1.4em;padding:0}
.material-unknowns,.risks-and-counterarguments{border-top:1px solid var(--line)}
.research-boundaries{margin-top:1rem;border-top:1px solid var(--line)}.research-boundaries ul{columns:2;column-gap:2.4rem;font-size:.9rem;color:var(--muted)}.research-boundaries li{break-inside:avoid;margin-bottom:.65em}
.sources{border-top:1px solid var(--line)}.sources>p{color:var(--muted);font-size:.86rem;margin-bottom:1.35rem}.sources-list{columns:2;column-gap:2.8rem}
sup{font-size:.65em;line-height:0;margin-left:.08em}sup a{font-weight:750}.source-note{display:grid;grid-template-columns:1.25rem 1fr;gap:.65rem;break-inside:avoid;font-size:.82rem;color:var(--muted);padding:0 0 1rem;margin:0}
.source-number{color:var(--magenta);font-weight:750;font-size:.76rem;padding-top:.12rem}
img{display:block;max-width:100%;height:auto;margin:1.8em auto}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid var(--line);padding:.7em .55em;text-align:left}th{color:var(--navy);font-size:.78rem;text-transform:uppercase;letter-spacing:.05em}
code{background:#edf1f3;padding:.1em .25em}pre{overflow:auto;background:#121a38;color:#f4f7fa;padding:1em}
@media(max-width:720px){main{margin:0;padding:52px 25px}h1{font-size:2.45rem}.report-section{padding-top:2.4rem}.research-boundaries ul,.sources-list{columns:1}}
@media print{body{background:white}main{box-shadow:none;max-width:none;margin:0;padding:0;overflow:visible}main:before{display:none}a{color:inherit}}
""".strip()
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        f"<title>{html.escape(title)}</title>\n<style>{css}</style>\n</head>\n"
        f"<body><main>{body}</main></body>\n</html>\n"
    )


def _markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None
    in_code = False
    code: list[str] = []
    section_open = False
    sources_list_open = False
    section_number = 0
    current_section = ""

    def flush() -> None:
        if paragraph:
            output.append("<p>" + " ".join(_html_inline(line.strip()) for line in paragraph) + "</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    def close_section() -> None:
        nonlocal section_open, sources_list_open
        if sources_list_open:
            output.append("</div>")
            sources_list_open = False
        if section_open:
            output.append("</section>")
            section_open = False

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            flush(); close_list()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code.clear(); in_code = False
            else:
                in_code = True
            index += 1; continue
        if in_code:
            code.append(line); index += 1; continue
        image = re.fullmatch(r"!\[(.+?)\]\((Assets/chart-[0-9]{3}\.svg)\)", line)
        if image and SAFE_ASSET.fullmatch(image.group(2)):
            flush(); close_list()
            output.append(f'<img src="{image.group(2)}" alt="{html.escape(_unescape_markdown(image.group(1)))}">')
            index += 1; continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush(); close_list()
            level = len(heading.group(1)); value = heading.group(2)
            anchor = re.sub(r"[^a-z0-9]+", "-", _unescape_markdown(value).casefold()).strip("-")
            if level == 2:
                close_section()
                section_number += 1
                current_section = anchor
                section_open = True
                output.append(
                    f'<section class="report-section {html.escape(anchor)}">'
                    f'<div class="section-heading"><span class="section-number">{section_number:02d}</span>'
                    f'<h2 id="{html.escape(anchor)}">{_html_inline(value)}</h2></div>'
                )
            else:
                output.append(f'<h{level} id="{html.escape(anchor)}">{_html_inline(value)}</h{level}>')
            index += 1; continue
        if line.startswith("|") and index + 1 < len(lines) and re.fullmatch(r"\|?[\s:|-]+\|?", lines[index + 1]):
            flush(); close_list()
            headers = _table_cells(line)
            output.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{_html_inline(cell)}</th>" for cell in headers) + "</tr></thead><tbody>")
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                output.append("<tr>" + "".join(f"<td>{_html_inline(cell)}</td>" for cell in _table_cells(lines[index])) + "</tr>")
                index += 1
            output.append("</tbody></table></div>"); continue
        footnote = re.match(r"^\[\^([A-Za-z0-9-]+)\]:\s*(.*)$", line)
        if footnote:
            flush(); close_list()
            if current_section == "sources" and not sources_list_open:
                output.append('<div class="sources-list">')
                sources_list_open = True
            output.append(
                f'<div class="source-note" id="note-{html.escape(footnote.group(1))}">'
                f'<span class="source-number">{html.escape(footnote.group(1))}</span>'
                f'<span>{_html_inline(footnote.group(2))}</span></div>'
            )
            index += 1; continue
        nested_item = re.match(r"^\s{2,}[-*+]\s+(.*)$", line)
        if nested_item:
            flush(); close_list()
            output.append(
                '<p class="finding-note">'
                + _html_inline(nested_item.group(1)) + "</p>"
            )
            index += 1; continue
        item = re.match(r"^\s*([-*+] |\d+\. )(.*)$", line)
        if item:
            flush(); desired = "ol" if item.group(1)[0].isdigit() else "ul"
            if list_type != desired:
                close_list(); output.append(f"<{desired}>"); list_type = desired
            output.append("<li>" + _html_inline(item.group(2)) + "</li>")
            index += 1; continue
        if line.startswith(">"):
            flush(); close_list(); output.append("<blockquote>" + _html_inline(line.lstrip("> ")) + "</blockquote>")
            index += 1; continue
        if not line.strip():
            flush(); close_list(); index += 1; continue
        paragraph.append(line); index += 1
    flush(); close_list()
    if in_code:
        output.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
    close_section()
    return "\n".join(output)


def _html_inline(value: str) -> str:
    text = _unescape_markdown(value)
    tokens: list[str] = []

    def store(fragment: str) -> str:
        tokens.append(fragment)
        return f"\x00{len(tokens) - 1}\x00"

    link_pattern = re.compile(r"\[([^\]]+)\]\(<(https?://[^>]+)>\)")
    text = link_pattern.sub(
        lambda match: store(
            f'<a href="{html.escape(_safe_url(match.group(2)), quote=True)}">{html.escape(match.group(1))}</a>'
        ), text,
    )
    text = re.sub(
        r"\[\^([A-Za-z0-9-]+)\]",
        lambda match: store(f'<sup><a href="#note-{html.escape(match.group(1))}">{html.escape(match.group(1))}</a></sup>'),
        text,
    )
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    for index, token in enumerate(tokens):
        escaped = escaped.replace(f"\x00{index}\x00", token)
    return escaped


def _render_chart_svg(chart: Mapping[str, Any]) -> str:
    width, height = 820, 470
    left, right, top, bottom = 95, 30, 85, 115
    plot_width, plot_height = width - left - right, height - top - bottom
    values = [float(point["value"]) for point in chart["points"]]
    low, high = min(0.0, min(values)), max(0.0, max(values))
    if high == low:
        high = low + 1.0
    span = high - low
    baseline = top + high / span * plot_height
    group = plot_width / len(values)
    bar_width = min(72.0, group * .58)
    colors = ("#007c91", "#5b21b6", "#b5179e", "#ea580c")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(chart["title"])}</title>',
        f'<desc id="desc">Bar chart in {html.escape(chart["unit"])} using {html.escape(chart["evidence_id"])} as of {html.escape(chart["as_of"])}.</desc>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="34" font-family="Arial,sans-serif" font-size="24" font-weight="700" fill="#111827">{html.escape(chart["title"])}</text>',
        f'<text x="{left}" y="58" font-family="Arial,sans-serif" font-size="13" fill="#52606d">As of {html.escape(chart["as_of"])} | Unit: {html.escape(chart["unit"])}</text>',
        f'<line x1="{left}" y1="{baseline:.2f}" x2="{width-right}" y2="{baseline:.2f}" stroke="#8193a1" stroke-width="1"/>',
    ]
    for tick in range(5):
        value = low + span * tick / 4
        y = top + (high - value) / span * plot_height
        parts.extend([
            f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" stroke="#e5edf1" stroke-width="1"/>',
            f'<text x="{left-10}" y="{y+4:.2f}" text-anchor="end" font-family="Arial,sans-serif" font-size="11" fill="#52606d">{html.escape(_number_text(value))}</text>',
        ])
    for index, point in enumerate(chart["points"]):
        value = float(point["value"])
        y_value = top + (high - value) / span * plot_height
        y = min(y_value, baseline)
        bar_height = max(1.0, abs(y_value - baseline))
        x = left + group * index + (group - bar_width) / 2
        parts.extend([
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="3" fill="{colors[index % len(colors)]}"/>',
            f'<text x="{x + bar_width/2:.2f}" y="{max(78, y-8):.2f}" text-anchor="middle" font-family="Arial,sans-serif" font-size="12" font-weight="700" fill="#111827">{html.escape(_number_text(value))}</text>',
            f'<text x="{x + bar_width/2:.2f}" y="{height-bottom+27}" text-anchor="middle" font-family="Arial,sans-serif" font-size="12" fill="#253746">{html.escape(point["label"])}</text>',
        ])
    parts.extend([
        f'<text x="{left}" y="{height-34}" font-family="Arial,sans-serif" font-size="11" fill="#52606d">Source: saved evidence {html.escape(chart["evidence_id"])} | Direct field extraction; no arithmetic.</text>',
        f'<text x="{left}" y="{height-16}" font-family="Arial,sans-serif" font-size="10" fill="#6b7280">{html.escape(chart["limitations"])}</text>',
        "</svg>",
    ])
    return "\n".join(parts) + "\n"


def _write_pdf(
    path: Path, *, markdown: str, title: str, subject: str,
    charts: Sequence[Mapping[str, Any]],
) -> None:
    try:
        import reportlab
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
            TableStyle,
        )
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics.shapes import Drawing
    except ImportError as exc:
        raise RuntimeError(
            "PDF export requires ReportLab. Install project requirements first."
        ) from exc

    fonts = Path(reportlab.__file__).resolve().parent / "fonts"
    regular, bold = "Helvetica", "Helvetica-Bold"
    system_regular = Path("C:/Windows/Fonts/segoeui.ttf")
    system_bold = Path("C:/Windows/Fonts/seguisb.ttf")
    system_italic = Path("C:/Windows/Fonts/segoeuii.ttf")
    vera, vera_bold = fonts / "Vera.ttf", fonts / "VeraBd.ttf"
    if system_regular.exists() and system_bold.exists():
        try:
            pdfmetrics.registerFont(TTFont("DefinalyzerSans", str(system_regular)))
            pdfmetrics.registerFont(TTFont("DefinalyzerSans-Bold", str(system_bold)))
            if system_italic.exists():
                pdfmetrics.registerFont(TTFont("DefinalyzerSans-Italic", str(system_italic)))
            regular, bold = "DefinalyzerSans", "DefinalyzerSans-Bold"
        except Exception:
            pass
    elif vera.exists() and vera_bold.exists():
        try:
            pdfmetrics.registerFont(TTFont("DefinalyzerSans", str(vera)))
            pdfmetrics.registerFont(TTFont("DefinalyzerSans-Bold", str(vera_bold)))
            regular, bold = "DefinalyzerSans", "DefinalyzerSans-Bold"
        except Exception:
            pass

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="EyebrowX", parent=styles["BodyText"], fontName=bold, fontSize=7.4, leading=9, textColor=colors.HexColor("#00a6d6"), spaceAfter=9, uppercase=True))
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName=bold, fontSize=31, leading=35, alignment=0, textColor=colors.HexColor("#121a38"), spaceAfter=10))
    styles.add(ParagraphStyle(name="SectionNumberX", parent=styles["BodyText"], fontName=bold, fontSize=7.2, leading=9, textColor=colors.HexColor("#00a6d6")))
    styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName=bold, fontSize=17, leading=20, textColor=colors.HexColor("#121a38"), spaceAfter=0))
    styles.add(ParagraphStyle(name="H3x", parent=styles["Heading3"], fontName=bold, fontSize=12.2, leading=15, textColor=colors.HexColor("#6846c7"), spaceBefore=13, spaceAfter=7, keepWithNext=1))
    styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontName=regular, fontSize=9.35, leading=13.8, textColor=colors.HexColor("#25313d"), spaceAfter=6))
    styles.add(ParagraphStyle(name="BulletX", parent=styles["BodyX"], leftIndent=13, firstLineIndent=-8, bulletIndent=2, spaceAfter=4))
    styles.add(ParagraphStyle(name="NoteX", parent=styles["BodyX"], leftIndent=18, fontSize=7.9, leading=11.1, textColor=colors.HexColor("#66717e"), spaceAfter=3))
    styles.add(ParagraphStyle(name="MetaX", parent=styles["BodyX"], fontSize=7.5, leading=10.2, textColor=colors.HexColor("#66717e"), spaceAfter=2))
    styles.add(ParagraphStyle(name="SourceX", parent=styles["MetaX"], fontSize=7.2, leading=10.2, spaceAfter=0))
    styles.add(ParagraphStyle(name="PreviewX", parent=styles["MetaX"], fontName=bold, textColor=colors.HexColor("#bd2d7d"), spaceAfter=8, uppercase=True))
    styles.add(ParagraphStyle(name="ExecutiveX", parent=styles["BodyX"], fontSize=12.7, leading=18.2, textColor=colors.HexColor("#121a38"), spaceAfter=0))
    styles.add(ParagraphStyle(name="ConclusionX", parent=styles["BodyX"], fontSize=11.3, leading=16.6, textColor=colors.HexColor("#121a38"), spaceAfter=0))
    charts_by_asset = {f"Assets/{chart['filename']}": chart for chart in charts}

    story = []
    source_flowables = []
    lines = markdown.splitlines()
    index = 0
    current_section = ""
    section_number = 0

    def section_heading(text: str):
        nonlocal section_number
        section_number += 1
        table = Table([[Paragraph(f"{section_number:02d}", styles["SectionNumberX"]), Paragraph(_pdf_inline(text, regular, bold), styles["H2x"])]], colWidths=[.34*inch, 6.35*inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return table

    def accent_statement(text: str, color: str, style_name: str):
        table = Table([["", Paragraph(_pdf_inline(text, regular, bold), styles[style_name])]], colWidths=[.055*inch, 6.57*inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(color)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 0),
            ("LEFTPADDING", (1, 0), (1, 0), 14),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return table

    def bullet_flowable(text: str):
        if current_section == "Executive Summary":
            return accent_statement(text, "#00a6d6", "ExecutiveX")
        if current_section == "Qualified Conclusion":
            return accent_statement(text, "#bd2d7d", "ConclusionX")
        return Paragraph(
            _pdf_inline(text, regular, bold), styles["BulletX"], bulletText="-"
        )

    while index < len(lines):
        line = lines[index]
        image = re.fullmatch(r"!\[(.+?)\]\((Assets/chart-[0-9]{3}\.svg)\)", line)
        if image and image.group(2) in charts_by_asset:
            chart = charts_by_asset[image.group(2)]
            story.append(KeepTogether([
                _pdf_chart(
                    chart, Drawing, VerticalBarChart, colors,
                    regular=regular, bold=bold,
                ),
            ]))
            index += 1; continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level = min(3, len(heading.group(1)))
            if level == 2:
                current_section = heading.group(2)
            if level == 1:
                story.extend([
                    Paragraph("DEFINALYZER / RESEARCH BRIEF", styles["EyebrowX"]),
                    Paragraph(_pdf_inline(heading.group(2), regular, bold), styles["ReportTitle"]),
                    HRFlowable(width="100%", thickness=.8, color=colors.HexColor("#dfe4e8"), spaceBefore=2, spaceAfter=8),
                ])
                index += 1
                continue
            heading_flowable = (
                section_heading(heading.group(2))
                if level == 2 else
                Paragraph(_pdf_inline(heading.group(2), regular, bold), styles["H3x"])
            )
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            # Keep a visual section's heading, chart title, and chart together.
            # Otherwise ReportLab can strand both headings at a page bottom and
            # move only the drawing onto the next page.
            if level == 2 and next_index < len(lines):
                chart_heading = re.match(r"^###\s+(.+)$", lines[next_index])
                chart_index = next_index + 1
                while chart_index < len(lines) and not lines[chart_index].strip():
                    chart_index += 1
                chart_image = (
                    re.fullmatch(
                        r"!\[(.+?)\]\((Assets/chart-[0-9]{3}\.svg)\)",
                        lines[chart_index],
                    )
                    if chart_heading and chart_index < len(lines) else None
                )
                if chart_image and chart_image.group(2) in charts_by_asset:
                    chart = charts_by_asset[chart_image.group(2)]
                    story.append(KeepTogether([
                        Spacer(1, 18), heading_flowable, Spacer(1, 8),
                        Paragraph(
                            _pdf_inline(chart_heading.group(1), regular, bold),
                            styles["H3x"],
                        ),
                        _pdf_chart(
                            chart, Drawing, VerticalBarChart, colors,
                            regular=regular, bold=bold,
                        ),
                    ]))
                    index = chart_index + 1
                    continue
            first_item = (
                re.match(r"^\s*[-*+]\s+(.*)$", lines[next_index])
                if level >= 2 and next_index < len(lines) else None
            )
            if first_item:
                story.append(KeepTogether([
                    Spacer(1, 18 if level == 2 else 8), heading_flowable,
                    Spacer(1, 8 if level == 2 else 3),
                    bullet_flowable(first_item.group(1)),
                ]))
                index = next_index + 1
                continue
            story.extend([
                Spacer(1, 18 if level == 2 else 8), heading_flowable,
            ])
            index += 1; continue
        if line.startswith("|") and index + 1 < len(lines) and re.fullmatch(r"\|?[\s:|-]+\|?", lines[index + 1]):
            table_rows = [_table_cells(line)]
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                table_rows.append(_table_cells(lines[index])); index += 1
            widths = [6.6 * inch / max(1, len(table_rows[0]))] * len(table_rows[0])
            data = [[Paragraph(_pdf_inline(cell, regular, bold), styles["MetaX"]) for cell in row] for row in table_rows]
            table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf3f5")),
                ("FONTNAME", (0, 0), (-1, 0), bold),
                ("LINEBELOW", (0, 0), (-1, -1), .35, colors.HexColor("#dfe4e8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([table, Spacer(1, 9)]); continue
        footnote = re.match(r"^\[\^([A-Za-z0-9-]+)\]:\s*(.*)$", line)
        if footnote:
            source_flowables.append(Paragraph(
                f'<font color="#bd2d7d"><b>{html.escape(footnote.group(1))}</b></font> '
                + _pdf_inline(footnote.group(2), regular, bold),
                styles["SourceX"],
            ))
            index += 1; continue
        nested_item = re.match(r"^\s{2,}[-*+]\s+(.*)$", line)
        if nested_item:
            story.append(Paragraph(
                _pdf_inline(nested_item.group(1), regular, bold), styles["NoteX"]
            ))
            index += 1; continue
        item = re.match(r"^\s*[-*+]\s+(.*)$", line)
        if item:
            if not current_section and item.group(1).startswith((
                "Subject:", "Evidence captured:", "Evidence package:",
                "Draft generated:", "Report prepared:", "Finalized:",
            )):
                story.append(Paragraph(
                    _pdf_inline(item.group(1), regular, bold), styles["MetaX"]
                ))
            else:
                story.append(KeepTogether([bullet_flowable(item.group(1))]))
            index += 1; continue
        if line.startswith(">"):
            story.append(Paragraph(
                _pdf_inline(line.lstrip("> "), regular, bold), styles["PreviewX"]
            ))
            index += 1; continue
        if not line.strip():
            story.append(Spacer(1, 3)); index += 1; continue
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not re.match(r"^(#{1,6}\s|[-*+]\s|\[\^|>|\||!\[)", lines[index]):
            paragraph.append(lines[index]); index += 1
        story.append(Paragraph(_pdf_inline(" ".join(paragraph), regular, bold), styles["BodyX"]))

    if source_flowables:
        split = (len(source_flowables) + 1) // 2
        left, right = source_flowables[:split], source_flowables[split:]
        source_rows = []
        for row_index in range(split):
            source_rows.append([
                left[row_index], "",
                right[row_index] if row_index < len(right) else "",
            ])
        source_table = Table(
            source_rows, colWidths=[3.18*inch, .28*inch, 3.18*inch],
            hAlign="LEFT",
        )
        source_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([Spacer(1, 8), source_table])

    document = SimpleDocTemplate(
        str(path), pagesize=A4, rightMargin=.72*inch, leftMargin=.72*inch,
        topMargin=.78*inch, bottomMargin=.68*inch,
        title=_pdf_text(title), author="DEFINALYZER",
        subject=_pdf_text(subject), creator="DEFINALYZER",
    )

    def decorate(canvas, doc):
        canvas.saveState()
        page_width, page_height = A4
        usable = page_width - 1.44*inch
        canvas.setFillColor(colors.HexColor("#00a6d6"))
        canvas.rect(.72*inch, page_height-.26*inch, usable*.42, .075*inch, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#6846c7"))
        canvas.rect(.72*inch+usable*.42, page_height-.26*inch, usable*.30, .075*inch, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#bd2d7d"))
        canvas.rect(.72*inch+usable*.72, page_height-.26*inch, usable*.28, .075*inch, fill=1, stroke=0)
        canvas.setFont(bold, 6.6); canvas.setFillColor(colors.HexColor("#7b8490"))
        canvas.drawString(.72*inch, .32*inch, "DEFINALYZER / RESEARCH BRIEF")
        canvas.setFont(regular, 7.2)
        canvas.drawRightString(page_width-.72*inch, .32*inch, f"{doc.page:02d}")
        canvas.restoreState()

    document.build(story, onFirstPage=decorate, onLaterPages=decorate)


def _pdf_chart(chart, Drawing, VerticalBarChart, colors, *, regular, bold):
    # Title and complete provenance are already rendered from the publication
    # Markdown around this visual. Keep the chart itself focused on the data.
    drawing = Drawing(480, 220)
    values = [float(point["value"]) for point in chart["points"]]
    bar = VerticalBarChart()
    bar.x, bar.y, bar.width, bar.height = 52, 38, 408, 160
    bar.data = [values]
    bar.categoryAxis.categoryNames = [_pdf_text(point["label"]) for point in chart["points"]]
    bar.categoryAxis.labels.fontName = regular
    bar.categoryAxis.labels.fontSize = 7.5
    bar.valueAxis.labels.fontName = regular
    bar.valueAxis.labels.fontSize = 7.5
    bar.valueAxis.labelTextFormat = lambda value: _number_text(float(value))
    bar.valueAxis.valueMin = min(0.0, min(values))
    high = max(0.0, max(values))
    bar.valueAxis.valueMax = high if high > bar.valueAxis.valueMin else high + 1
    bar.bars[0].fillColor = colors.HexColor("#007c91")
    bar.bars[0].strokeColor = colors.HexColor("#005f73")
    bar.barSpacing = 4
    bar.barLabelFormat = lambda value: _number_text(float(value))
    bar.barLabels.fontName = bold
    bar.barLabels.fontSize = 7.5
    bar.barLabels.nudge = 6
    drawing.add(bar)
    return drawing


def _pdf_inline(value: str, regular: str, bold: str) -> str:
    text = _pdf_text(_unescape_markdown(value))
    text = re.sub(r"\[([^\]]+)\]\(<https?://[^>]+>\)", r"\1", text)
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", rf'<font name="{bold}">\1</font>', escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*", r"\1", escaped)
    escaped = re.sub(
        r"\[\^([A-Za-z0-9-]+)\]",
        r'<super><font size="6">\1</font></super>',
        escaped,
    )
    return escaped


def _pdf_text(value: Any) -> str:
    return str(value).replace("\u2014", " - ").replace("\u2013", "-").replace("\u2212", "-").replace("\u00a0", " ")


def _validate_export_manifest(document: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "report_schema_version", "report_id", "revision",
        "exported_at", "formats", "source", "files", "charts",
        "publication_note",
    }
    if set(document) != required or document.get("schema_version") != EXPORT_SCHEMA_VERSION:
        raise ValueError("Export manifest has an invalid structure.")
    if document.get("report_schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("Export manifest has an invalid report schema.")
    if not isinstance(document.get("revision"), int) or document["revision"] < 0:
        raise ValueError("Export revision is invalid.")
    report_timestamp(document.get("exported_at"))
    if not isinstance(document.get("formats"), list) or not document["formats"] or set(document["formats"]) - EXPORT_FORMATS:
        raise ValueError("Export formats are invalid.")
    files = document.get("files")
    if not isinstance(files, dict) or any(
        not isinstance(path, str) or not re.fullmatch(r"(?:Report\.(?:md|html|pdf)|Analyst-Notes\.md|Assets/chart-[0-9]{3}\.(?:svg|json))", path)
        or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)
        for path, digest in files.items()
    ):
        raise ValueError("Export file hashes are invalid.")
    source = document.get("source")
    if not isinstance(source, dict) or set(source) != {
        "finalized_at", "report_sha256", "claims_sha256", "quality_sha256",
        "approval_sha256", "analyst_notes_sha256",
    } or any(
        not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value)
        for key, value in source.items() if key != "finalized_at"
    ):
        raise ValueError("Export source provenance is invalid.")
    report_timestamp(source["finalized_at"])


def _safe_export_root(workspace: ProjectWorkspace, root: Path) -> None:
    package_root = workspace.reports_directory.resolve()
    try:
        root.resolve().relative_to(package_root)
    except (ValueError, OSError) as exc:
        raise ValueError("Report exports must remain inside the report workspace.") from exc
    current = root.absolute()
    while current != package_root.absolute():
        if current.exists() and (current.is_symlink() or getattr(current, "is_junction", lambda: False)()):
            raise ValueError("Report export directories cannot be links or junctions.")
        current = current.parent


def _safe_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Publication links must be HTTP(S) URLs without credentials.")
    return value


def _single_line(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")
    clean = value.strip()
    if len(clean) > maximum or any(ord(character) < 32 for character in clean):
        raise ValueError(f"{label} is invalid or exceeds {maximum} characters.")
    return clean


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _number_text(value: float) -> str:
    if value == 0:
        return "0"
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"{value / 1_000_000_000:.3g}B"
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.3g}M"
    if absolute >= 1_000:
        return f"{value / 1_000:.3g}K"
    return f"{value:.4g}"


def _unescape_markdown(value: str) -> str:
    return re.sub(r"\\([\\`*_{}\[\]<>#!|])", r"\1", value)


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return document


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
