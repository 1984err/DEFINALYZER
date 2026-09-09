"""Separate, immutable V2 report revisions; V1 packages are never rewritten."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .asset_identity import safe_path, registry_writer
from .research_scope import _hash, _json, _write, _immutable
from .workspace import slugify

VERSION = 2
REPORT_ID = re.compile(r"v2-[a-z0-9][a-z0-9-]{0,58}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
REVISION = re.compile(r"revision-[0-9]{4,}\Z")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def package(workspace, report_id):
    if not isinstance(report_id, str) or not REPORT_ID.fullmatch(report_id):
        raise ValueError("Invalid V2 report identifier.")
    relative = (workspace.reports_directory / "V2" / report_id).relative_to(workspace.root).as_posix()
    return safe_path(workspace.root, relative)


def local(workspace, path):
    return safe_path(workspace.root, Path(path).relative_to(workspace.root).as_posix())


def read_json(workspace, path):
    path = local(workspace, path)
    if path.stat().st_size > 8_000_000:
        raise ValueError("Report record exceeds its read allowance.")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Expected a report object.")
    return result


def exists(workspace, report_id):
    return isinstance(report_id, str) and bool(REPORT_ID.fullmatch(report_id)) and (package(workspace, report_id) / "report.json").is_file()


def manifest(workspace, report_id):
    result = read_json(workspace, package(workspace, report_id) / "report.json")
    if (result.get("schema_version") != VERSION or result.get("report_id") != report_id
            or result.get("project", {}).get("slug") != workspace.slug):
        raise ValueError("Report schema or owning project does not match.")
    return result


def save_manifest(workspace, report_id, data):
    _write(package(workspace, report_id) / "report.json", _json({**data, "updated_at": now()}))


@registry_writer
def create(workspace, *, title, mode, question=None, recommendations=False, audience="researcher", depth="standard"):
    if mode not in {"question", "full_review"}:
        raise ValueError("Choose a full review or an answer to a question.")
    question = str(question or "").strip()
    if mode == "question" and not question:
        raise ValueError("Enter the question this report should answer.")
    if len(question) > 2000 or audience not in {"researcher", "management"} or depth not in {"brief", "standard"}:
        raise ValueError("Invalid report request.")
    title = str(title or (question[:110] if question else workspace.name + " research review")).strip()
    if not title or len(title) > 140 or any(ord(c) < 32 for c in title):
        raise ValueError("Report title must be a single line of at most 140 characters.")
    report_id = "v2-" + slugify(title)[:55].strip("-")
    root = package(workspace, report_id)
    if root.exists() or (workspace.reports_directory / report_id).exists():
        raise FileExistsError("A report with this title already exists; choose another title.")
    root.mkdir(parents=True)
    record = {"schema_version": VERSION, "report_id": report_id,
              "project": {"slug": workspace.slug, "name": workspace.name, "kind": workspace.document["entity_type"]},
              "title": title, "mode": mode, "question": question or None, "audience": audience,
              "depth": depth, "recommendations": recommendations is True, "created_at": now(), "updated_at": now(),
              "status": "scoped", "current_revision": None, "revision_hash": None, "pending_run": None,
              "last_message": "Ready to generate from saved source-supported research."}
    save_manifest(workspace, report_id, record)
    return record


def revision_directory(workspace, report_id, revision):
    if type(revision) is not int or not 0 <= revision <= 999999:
        raise ValueError("Invalid report revision.")
    return local(workspace, package(workspace, report_id) / "Revisions" / f"revision-{revision:04d}")


def load_revision(workspace, report_id, revision=None):
    record = manifest(workspace, report_id)
    number = record["current_revision"] if revision is None else revision
    directory = revision_directory(workspace, report_id, number)
    commit = read_json(workspace, directory / "commit.json")
    if commit.get("schema_version") != VERSION or commit.get("report_id") != report_id or commit.get("revision") != number:
        raise ValueError("Report revision belongs to another package.")
    if _hash(_json({k: v for k, v in commit.items() if k != "revision_hash"})) != commit.get("revision_hash"):
        raise ValueError("Report revision commit failed its integrity check.")
    if number == record["current_revision"] and commit["revision_hash"] != record["revision_hash"]:
        raise ValueError("Active report pointer does not match its revision.")
    required = {"evidence.json", "draft.json", "review.json", "Report.md", "Analyst-Notes.md", "Quality.md"}
    if set(commit.get("files", {})) != required:
        raise ValueError("Report revision is missing required bound content.")
    result = {"commit": commit, "directory": directory}
    for name, digest in commit["files"].items():
        raw = local(workspace, directory / name).read_bytes()
        if _hash(raw) != digest:
            raise ValueError(f"Report revision integrity failed: {name}")
        result[name] = json.loads(raw) if name.endswith(".json") else raw.decode("utf-8")
    from .report_v2_evidence import validate_bundle
    validate_bundle(result["evidence.json"])
    review, draft, bundle = result["review.json"], result["draft.json"], result["evidence.json"]
    if (review.get("draft_hash") != _hash(_json(draft)) or review.get("evidence_hash") != bundle["bundle_hash"]
            or draft.get("evidence_hash") != bundle["bundle_hash"]):
        raise ValueError("The review does not bind this draft and original evidence.")
    if review.get("notes_hash") is not None and review["notes_hash"] != _hash(result["Analyst-Notes.md"]):
        raise ValueError("Edited analyst notes do not match their review.")
    return result


def edited_files(workspace, report_id, revision=None):
    record = manifest(workspace, report_id)
    if record["current_revision"] is None:
        return []
    saved = revision or load_revision(workspace, report_id)
    root = package(workspace, report_id)
    return [name for name in ("Report.md", "Analyst-Notes.md")
            if (root / name).exists() and _hash(local(workspace, root / name).read_bytes()) != saved["commit"]["files"][name]]


def commit_revision(workspace, report_id, *, bundle, draft, review, report, notes, quality, operation, run_id):
    """Write immutable files first and switch a single pointer last."""
    record = manifest(workspace, report_id)
    number = 0 if record["current_revision"] is None else record["current_revision"] + 1
    directory = revision_directory(workspace, report_id, number)
    # A previous interrupted commit can only be resumed with identical content.
    data = {"evidence.json": _json(bundle), "draft.json": _json(draft), "review.json": _json(review),
            "Report.md": report, "Analyst-Notes.md": notes, "Quality.md": quality}
    files = {}
    for name, text in data.items():
        raw = text.encode("utf-8")
        _immutable(directory / name, raw)
        files[name] = _hash(raw)
    commit = {"schema_version": VERSION, "report_id": report_id, "revision": number,
              "parent_hash": record["revision_hash"], "run_id": run_id, "operation": operation,
              "files": files}
    commit["revision_hash"] = _hash(_json(commit))
    _immutable(directory / "commit.json", _json(commit).encode())
    root = package(workspace, report_id)
    previous = load_revision(workspace, report_id) if record["current_revision"] is not None else None
    for name in ("Report.md", "Analyst-Notes.md", "Quality.md"):
        path = local(workspace, root / name)
        if path.exists() and (previous is None or _hash(path.read_bytes()) != previous["commit"]["files"][name]):
            # Preserve externally edited files before updating the active pointer.
            raw = path.read_bytes()
            _immutable(root / "Preserved" / (_hash(raw) + "-" + name), raw)
            continue
        _write(path, data[name])
    record.update(current_revision=number, revision_hash=commit["revision_hash"], pending_run=None,
                  status="ready_to_review" if review["passed"] and draft["readiness"] != "insufficient" else "needs_attention",
                  last_message=review["message"])
    save_manifest(workspace, report_id, record)
    return commit


def approval(workspace, report_id, revision=None):
    saved = load_revision(workspace, report_id, revision)
    path = saved["directory"] / "approval.json"
    if not path.exists():
        raise ValueError("This revision has not been finalized.")
    result = read_json(workspace, path)
    record = manifest(workspace, report_id)
    if (record.get("final_approvals", {}).get(str(saved["commit"]["revision"])) != _hash(_json(result))
            or result.get("schema_version") != VERSION or result.get("report_id") != report_id
            or result.get("revision_hash") != saved["commit"]["revision_hash"] or result.get("files") != saved["commit"]["files"]
            or result.get("human_approved") is not True or not saved["review.json"]["passed"]):
        raise ValueError("Final approval does not match the exact reviewed content.")
    if any(a["kind"] == "recommendation" for a in saved["draft.json"]["assertions"]) and result.get("recommendation_approved") is not True:
        raise ValueError("The recommendation requires explicit approval.")
    return result, saved


@registry_writer
def finalize(workspace, report_id, *, expected_revision, human_approved, recommendation_approved=False):
    record = manifest(workspace, report_id)
    saved = load_revision(workspace, report_id)
    if expected_revision != saved["commit"]["revision_hash"]:
        raise ValueError("The report changed after it was opened. Review the current revision before finalizing.")
    if human_approved is not True:
        raise ValueError("Finalization requires the user's explicit approval.")
    if record["pending_run"] or edited_files(workspace, report_id, saved):
        raise ValueError("Unreviewed changes remain. Reconcile or finish the revision before finalizing.")
    if not saved["review.json"]["passed"] or saved["draft.json"]["readiness"] == "insufficient":
        raise ValueError("Resolve the report's blocking review issues before finalizing.")
    recommendation = any(a["kind"] == "recommendation" for a in saved["draft.json"]["assertions"])
    if recommendation and recommendation_approved is not True:
        raise ValueError("Explicitly approve the included recommendation.")
    path = saved["directory"] / "approval.json"
    result = read_json(workspace, path) if path.exists() else {
        "schema_version": VERSION, "report_id": report_id, "revision_hash": expected_revision,
        "files": saved["commit"]["files"], "human_approved": True,
        "recommendation_approved": recommendation_approved is True, "finalized_at": now()}
    _immutable(path, _json(result).encode())
    record.setdefault("final_approvals", {})[str(saved["commit"]["revision"])] = _hash(_json(result))
    record.update(status="final", last_message="This exact report revision is final.")
    save_manifest(workspace, report_id, record)
    approval(workspace, report_id)
    return result
