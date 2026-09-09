"""Exports are derived only from a finalized immutable V2 revision."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
import math
import re

from .asset_identity import registry_writer
from .research_scope import _hash, _json, _immutable
from .research_facts import _plain
from .report_v2_store import VERSION, package, approval, local, read_json, manifest, save_manifest


def export_manifest(workspace, report_id, revision):
    approved, saved = approval(workspace, report_id, revision)
    root = local(workspace, package(workspace, report_id) / "Exports" / f"revision-{revision:04d}")
    document = read_json(workspace, root / "export.json")
    if (manifest(workspace, report_id).get("export_hashes", {}).get(str(revision)) != _hash(_json(document))
            or document.get("revision_hash") != saved["commit"]["revision_hash"]
            or document.get("approval_hash") != _hash(_json(approved))):
        raise ValueError("Published export does not match its frozen final revision.")
    return document


def chart_suggestions(bundle):
    """Only dated, same-definition quantities with explicit comparison labels."""
    groups = defaultdict(list)
    conflicted = {key for c in bundle["conflicts"] for key in c["fact_keys"]}
    for fact in bundle["facts"]:
        scope = fact["applicability"]
        if fact["fact_key"] in conflicted or len(fact["quantities"]) != 1 or not scope["period"] or not scope["network"]:
            continue
        quantity = fact["quantities"][0]
        value = Decimal(quantity["value"])
        if not value.is_finite() or not math.isfinite(float(value)) or abs(value) > Decimal("1e15"):
            continue
        key = (fact["subject_id"], fact["predicate"], quantity["unit"], scope["version"], scope["environment"], scope["period"])
        groups[key].append(fact)
    charts = []
    for key, facts in groups.items():
        labels = [f["applicability"]["network"] for f in facts]
        if not 2 <= len(facts) <= 8 or len(set(labels)) != len(labels):
            continue
        points = [{"label": f["applicability"]["network"], "value": f["quantities"][0]["value"],
                   "fact_revision": f["revision"], "literal": f["quantities"][0]["literal"], "source_ids": f["source_ids"]} for f in facts]
        charts.append({"chart_id": _hash(_json(points)), "title": "Documented " + key[1], "unit": key[2],
                       "as_of": key[5], "basis": "documented_claim", "points": points,
                       "limitations": "Documented parameters for the stated period; not measured current state."})
    return charts[:3]


@registry_writer
def export(workspace, report_id, *, formats=("markdown", "html", "pdf"), chart_ids=()):
    if not formats or set(formats) - {"markdown", "html", "pdf"}:
        raise ValueError("Supported report exports are Markdown, HTML and PDF.")
    approved, saved = approval(workspace, report_id)
    root = local(workspace, package(workspace, report_id) / "Exports" / f"revision-{saved['commit']['revision']:04d}")
    path = root / "export.json"
    requested = sorted(set(chart_ids))
    if path.exists():
        existing = export_manifest(workspace, report_id, saved["commit"]["revision"])
        if (existing.get("revision_hash") != saved["commit"]["revision_hash"] or existing.get("chart_ids") != requested
                or existing.get("approval_hash") != _hash(_json(approved))):
            raise ValueError("This immutable export already uses another chart selection. Its published files are preserved.")
        for name, digest in existing["files"].items():
            if _hash(local(workspace, root / name).read_bytes()) != digest:
                raise ValueError("Published export failed its integrity check.")
        return {"directory": str(root), "revision": saved["commit"]["revision"], "reused": True}
    suggestions = {c["chart_id"]: c for c in chart_suggestions(saved["evidence.json"])}
    if set(requested) - set(suggestions):
        raise ValueError("Choose a suggested chart; custom numbers and field paths cannot enter an export.")
    from .report_export import _publication_html, _write_pdf, _render_chart_svg
    charts = []
    markdown = saved["Report.md"]
    title = markdown.splitlines()[0].removeprefix("# ")
    files = {}
    for index, cid in enumerate(requested, 1):
        source = suggestions[cid]
        chart = {**source, "evidence_id": "original documentation", "filename": f"chart-{index:03d}.svg",
                 "transformation": "Direct documented quantities; no arithmetic or aggregation."}
        charts.append(chart)
        for name, text in (("Assets/" + chart["filename"], _render_chart_svg(chart)),
                           (f"Assets/chart-{index:03d}.json", _json(chart))):
            _immutable(root / name, text.encode())
            files[name] = _hash(text)
    if charts:
        section = "## Documented quantities\n\n" + "\n\n".join(
            f"### {_plain(c['title'])}\n\n![{_plain(c['title'])}](Assets/{c['filename']})\n\n"
            f"{_plain(c['limitations'])} Period: {_plain(c['as_of'])}. Unit: {_plain(c['unit'])}." for c in charts) + "\n\n"
        markdown = markdown.replace("## Sources\n", section + "## Sources\n") if "## Sources\n" in markdown else markdown + "\n" + section
    content = {"Report.md": markdown, "Analyst-Notes.md": saved["Analyst-Notes.md"],
               "Report.html": _publication_html(markdown, title=title, charts=charts),
               "evidence.json": _json(saved["evidence.json"]), "draft.json": _json(saved["draft.json"]),
               "review.json": _json(saved["review.json"]), "approval.json": _json(approved), "commit.json": _json(saved["commit"])}
    for name, text in content.items():
        _immutable(root / name, text.encode())
        files[name] = _hash(text)
    # Generate all publication formats together, so later downloads cannot pick
    # up current source changes or produce a different approved publication.
    pdf = root / "Report.pdf"
    receipt_path = root / "pdf-receipt.json"
    if receipt_path.exists():
        receipt = read_json(workspace, receipt_path)
        if (receipt.get("input_hash") != _hash(markdown) or receipt.get("pdf_hash") != _hash(pdf.read_bytes())):
            raise ValueError("Interrupted PDF export failed its integrity check.")
    elif pdf.exists():
        raise ValueError("An interrupted PDF has no integrity receipt. Its bytes are preserved for recovery.")
    else:
        temporary = root / "Report.pending.pdf"
        pdf_markdown = re.sub(r"(?<=\S) +(?=\[\^\d+\](?!:))", "\u00a0", markdown)
        _write_pdf(temporary, markdown=pdf_markdown, title=title, subject=saved["evidence.json"]["subject"]["name"], charts=charts)
        temporary.replace(pdf)
        _immutable(receipt_path, _json({"input_hash": _hash(markdown), "pdf_hash": _hash(pdf.read_bytes())}).encode())
    files["Report.pdf"] = _hash(pdf.read_bytes())
    result = {"schema_version": VERSION, "report_id": report_id, "revision": saved["commit"]["revision"],
              "revision_hash": saved["commit"]["revision_hash"], "approval_hash": _hash(_json(approved)),
              "chart_ids": requested, "files": files}
    record = manifest(workspace, report_id)
    key, digest = str(saved["commit"]["revision"]), _hash(_json(result))
    prior = record.get("export_hashes", {}).get(key)
    if prior is not None and prior != digest:
        raise ValueError("The export changed during recovery; the earlier committed publication is preserved.")
    record.setdefault("export_hashes", {})[key] = digest
    save_manifest(workspace, report_id, record)
    _immutable(path, _json(result).encode())
    return {"directory": str(root), "revision": saved["commit"]["revision"], "formats": ["markdown", "html", "pdf"], "reused": False}
