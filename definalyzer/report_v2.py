"""Automatic V2 report preparation, writing, review, repair and revisions."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from difflib import unified_diff
from uuid import uuid4

from .asset_identity import registry_writer
from .research_scope import _hash, _json, _write, _immutable
from .operation_budget import BudgetProvider, BudgetExceeded
from .cancellation import check_cancelled
from .report_v2_store import (VERSION, package, manifest, save_manifest, read_json, local,
                             load_revision, commit_revision, edited_files, exists, now, approval)
from .report_v2_evidence import build_bundle, validate_bundle, historical
from .report_v2_writing import (MAX_PROMPT, writing_prompt, validate_draft, apply_changes, targeted_changes,
                              review_draft, render_report, render_notes, render_quality, insufficient)

MAX_REPAIRS = 2


def _provider_call(workspace, provider, run, label, prompt, usage):
    check_cancelled()
    if len(prompt) > MAX_PROMPT:
        raise ValueError("This report step exceeds the bounded context allowance; a more concise revision is needed.")
    fingerprint = _hash(prompt)
    directory = run / "Calls" / (label + "-" + fingerprint)
    response_path = directory / "response.txt"
    if response_path.exists():
        text = local(workspace, response_path).read_text(encoding="utf-8")
        usage["reused_calls"] += 1
    else:
        if (directory / "started.json").exists():
            raise ValueError("An earlier call was interrupted; this reserved attempt cannot be silently repeated.")
        if isinstance(provider, BudgetProvider):
            provider.check_available(prompt)
        _immutable(directory / "prompt.txt", prompt.encode())
        _immutable(directory / "started.json", _json({"started_at": now(), "provider": getattr(provider, "name", "configured_provider")}).encode())
        usage["provider_calls"] += 1
        usage["provider_input_characters"] += len(prompt)
        response = provider.generate(prompt, working_directory=workspace.project_root)
        text = response.text
        _immutable(response_path, text.encode())
    if len(text) > 100_000:
        raise ValueError("Report response exceeds its allowance.")
    text = text.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Expected structured report output.")
    return data


def _manual_draft(previous, texts, request, bundle):
    known = {b["block_id"]: b["assertion_id"] for s in previous["sections"] for b in s["blocks"]}
    if not isinstance(texts, dict) or not texts or set(texts) - set(known):
        raise ValueError("Manual edits must identify existing paragraphs.")
    changes = [{"assertion_id": known[bid], "text": text, "rationale": "User-supplied wording checked against the linked original evidence."} for bid, text in texts.items()]
    return apply_changes(previous, {"changes": changes}, request, bundle)


def _external_draft(workspace, report_id, previous, request, bundle):
    """Reconcile edited prose exactly; users retain the generated citation numbers."""
    path = local(workspace, package(workspace, report_id) / "Report.md")
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    if len(text) > 30_000:
        raise ValueError("Edited report exceeds its reconciliation allowance.")
    original_text = load_revision(workspace, report_id)["Report.md"]
    if text.splitlines()[0] != original_text.splitlines()[0]:
        raise ValueError("Keep the saved report title when editing its Markdown; create a new report to change the title.")
    original_parts = re.split(r"(?m)^## Sources\s*$", original_text, maxsplit=1)
    edited_parts = re.split(r"(?m)^## Sources\s*$", text, maxsplit=1)
    if [s.splitlines() for s in original_parts[1:]] != [s.splitlines() for s in edited_parts[1:]]:
        raise ValueError("Keep the frozen Sources section unchanged. Use latest research for new evidence.")
    before_sources = re.split(r"(?m)^## Sources\s*$", text, maxsplit=1)[0]
    groups, active, lines = [], None, []
    def flush():
        nonlocal lines
        if lines and active is not None:
            paragraph = " ".join(line.strip() for line in lines).strip()
            if paragraph:
                active["paragraphs"].append(paragraph)
        lines = []
    for line in before_sources.splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            flush()
            active = {"title": line[3:].strip(), "paragraphs": []}
            groups.append(active)
        elif not line.strip():
            flush()
        else:
            if active is None and line.strip():
                raise ValueError("Place edited prose under a report section so every paragraph receives review.")
            lines.append(line)
    flush()
    groups = [g for g in groups if g["paragraphs"]]
    if len(groups) < 2:
        raise ValueError("Keep the report's assessment and conclusion headings when editing its Markdown.")
    sources = {s["source_id"] for s in bundle["sources"]}
    assertions, sections = [], []
    for index, group in enumerate(groups):
        blocks = []
        for paragraph in group["paragraphs"]:
            refs = {"S" + n for n in re.findall(r"\[\^(\d+)\]", paragraph)}
            if refs - sources:
                raise ValueError("An edited paragraph cites a source outside this frozen evidence bundle.")
            wording = re.sub(r"\s*\[\^\d+\]", "", paragraph).strip()
            wording = re.sub(r"\\([\\`*_{}\[\]<>#|])", r"\1", wording)
            facts = [f for f in bundle["facts"] if refs.intersection(f["source_ids"])]
            original = next((a for a in previous["assertions"] if a["text"] == wording), None)
            if not facts and original is None:
                raise ValueError("Keep source citations with edited factual paragraphs; unlinked new prose cannot be finalized.")
            aid = "A" + str(len(assertions) + 1)
            assertion = {"assertion_id": aid, "text": wording, "kind": original["kind"] if original else "interpretation",
                         "subject_ids": sorted({f["subject_id"] for f in facts}) or [bundle["subject"]["subject_id"]],
                         "fact_keys": [f["fact_key"] for f in facts], "gap_ids": original["gap_ids"] if original else [],
                         "rationale": "User-edited Markdown reconciled without changing the supplied wording.", "material_qualifiers": []}
            assertions.append(assertion)
            blocks.append({"block_id": "P" + str(len(assertions)), "assertion_id": aid, "text": wording})
        sections.append({"section_id": "S" + str(index + 1), "title": group["title"],
                         "role": "summary" if index == 0 else "conclusion" if index == len(groups) - 1 else "analysis", "blocks": blocks})
    draft = validate_draft({"readiness": previous["readiness"], "sections": sections, "assertions": assertions}, request, bundle)
    return draft, _hash(raw)


@registry_writer
def generate(workspace, report_id, *, provider, operation="generate", instruction=None, target="report", texts=None,
             expected_revision=None, progress=None):
    progress = progress or (lambda message: None)
    if operation not in {"generate", "revise", "refresh", "manual", "reconcile"}:
        raise ValueError("Unknown report operation.")
    record = manifest(workspace, report_id)
    root = package(workspace, report_id)
    previous = load_revision(workspace, report_id) if record["current_revision"] is not None else None
    if operation in {"revise", "manual", "reconcile", "refresh"} and previous and expected_revision != record["revision_hash"]:
        raise ValueError("The report changed. Open its current revision before submitting changes.")
    if operation in {"revise", "manual", "reconcile"} and previous is None:
        raise ValueError("Generate a report before revising it.")
    if operation == "revise" and (not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 2000):
        raise ValueError("Describe the requested revision in at most 2000 characters.")
    if (previous and edited_files(workspace, report_id, previous) and operation != "reconcile"
            and not (operation == "generate" and record["pending_run"])):
        raise ValueError("Edited report files are preserved. Review those edits before requesting another generated revision.")
    if operation == "generate" and previous and not record["pending_run"]:
        return {"report_id": report_id, "status": record["status"], "revision": record["current_revision"], "reused": True}
    usage = {"provider_calls": 0, "provider_input_characters": 0, "reused_calls": 0}
    input_key = _hash(_json({"operation": operation, "instruction": instruction, "target": target, "texts": texts}))
    pending = record["pending_run"]
    if pending and operation != "refresh":
        if not re.fullmatch(r"[a-f0-9]{32}", pending):
            raise ValueError("Invalid pending report run.")
        run = local(workspace, root / "Runs" / pending)
        state = read_json(workspace, run / "state.json")
        if operation == "generate":
            operation = state["operation"]
            instruction, target, texts = (state.get("instruction"), state.get("target", "report"), state.get("texts"))
            input_key = state["input_key"]
        if state["input_key"] != input_key:
            raise ValueError("Resume the pending operation first, or explicitly refresh the evidence to start a new run.")
        bundle = read_json(workspace, run / "evidence.json")
        validate_bundle(bundle)
    else:
        pending = uuid4().hex
        run = local(workspace, root / "Runs" / pending)
        progress("Preparing a frozen report bundle from source-supported research")
        bundle = build_bundle(workspace, record) if operation in {"generate", "refresh"} else previous["evidence.json"]
        state = {"schema_version": VERSION, "input_key": input_key, "operation": operation, "next_round": 0,
                 "instruction": instruction, "target": target, "texts": texts,
                 "feedback": None, "draft": None, "review": None, "manual_hash": None}
        if operation == "revise" and previous:
            state["feedback"] = [i for i in previous["review.json"]["issues"] if i["severity"] == "error"] or None
        _immutable(run / "evidence.json", _json(bundle).encode())
        _write(run / "state.json", _json(state))
        record.update(pending_run=pending, status="generating", last_message="Preparing and reviewing the report.")
        save_manifest(workspace, report_id, record)
    if not isinstance(provider, BudgetProvider):
        concise = record.get('depth') == 'brief' or record['mode'] == 'question'
        provider = BudgetProvider(provider, run / 'budget.json', calls=2 if concise else 9,
                                  characters=48_000 if concise else 216_000, seconds=120 if concise else 360)
    try:
        if bundle["readiness_ceiling"] == "insufficient":
            draft, review = insufficient(bundle)
        else:
            base = previous["draft.json"] if previous and operation in {"revise", "manual", "reconcile"} else None
            if operation == "manual" and state["draft"] is None:
                state["draft"] = _manual_draft(base, texts, record, bundle)
            if operation == "reconcile" and state["draft"] is None:
                state["draft"], state["manual_hash"] = _external_draft(workspace, report_id, base, record, bundle)
                notes_path = local(workspace, root / "Analyst-Notes.md")
                if notes_path.exists() and _hash(notes_path.read_bytes()) != previous["commit"]["files"]["Analyst-Notes.md"]:
                    state["manual_notes"] = notes_path.read_bytes().decode("utf-8")
            _write(run / "state.json", _json(state))
            round_limit = 1 if record.get('depth') == 'brief' or record['mode'] == 'question' else MAX_REPAIRS + 1
            for round_number in range(state["next_round"], round_limit):
                state["next_round"] = round_number + 1
                _write(run / "state.json", _json(state))
                progress(f"Report round {round_number + 1}/{MAX_REPAIRS + 1}: writing and checking; original evidence remains frozen")
                review_failures = {i["code"] for i in state["feedback"] or []}
                review_only = bool(state["draft"] and review_failures and review_failures <= {"support_review_incomplete", "conclusion_review_incomplete"})
                def call(label, prompt):
                    retry_check = review_only and ((label == "assertions" and "support_review_incomplete" in review_failures)
                                                    or (label == "conclusion" and "conclusion_review_incomplete" in review_failures))
                    cache_label = f"round-{round_number}-{label}" if label == "write" or retry_check else label
                    return _provider_call(workspace, provider, run, cache_label, prompt, usage)
                try:
                    if operation not in {"manual", "reconcile"} and not review_only:
                        current = state["draft"] or base
                        response = call("write", writing_prompt(record, bundle, previous=current, instruction=instruction,
                                                                target=target, feedback=state["feedback"]))
                        proposed = apply_changes(current, response, record, bundle, target=target if base and round_number == 0 else "report") if current else validate_draft(response, record, bundle)
                        if base:
                            targeted_changes(base, proposed, target)
                        state["draft"] = proposed
                        _write(run / "state.json", _json(state))
                    state["review"] = review_draft(record, bundle, state["draft"], call, progress)
                    if state.get("manual_notes") is not None:
                        from .report_v2_writing import review_notes
                        review_notes(bundle, state["manual_notes"], state["review"], call)
                    state["feedback"] = [i for i in state["review"]["issues"] if i["severity"] == "error"]
                except Exception as error:
                    state["feedback"] = [{"severity": "error", "code": "invalid_draft", "assertion_ids": [], "message": str(error)[:1200]}]
                    state["review"] = None
                _write(run / "state.json", _json(state))
                if not state["feedback"] or operation in {"manual", "reconcile"}:
                    break
            draft, review = state["draft"], state["review"]
            if draft is None or review is None:
                state['budget_exhausted'] = state['next_round'] >= round_limit
                _write(run / 'state.json', _json(state))
                record.update(status="needs_attention", last_message=(state["feedback"] or [{"message": "Report generation did not finish."}])[0]["message"])
                save_manifest(workspace, report_id, record)
                return {"report_id": report_id, "status": "needs_attention", "message": record["last_message"], **usage}
        # Review may narrow a nominally ready answer without turning an advisory
        # gap into a hard failure. Bind the amended draft to that same decision.
        if review.get("conclusion_check", {}).get("readiness") == "partial" and draft["readiness"] == "ready":
            draft = {**draft, "readiness": "partial"}
            review = {**review, "draft_hash": _hash(_json(draft))}
        report, notes, quality = render_report(record, bundle, draft), render_notes(record, bundle, draft, review), render_quality(review)
        if state.get("manual_notes") is not None:
            notes = state["manual_notes"]
        commit = commit_revision(workspace, report_id, bundle=bundle, draft=draft, review=review, report=report,
                                 notes=notes, quality=quality, operation=operation, run_id=pending)
        if operation == "reconcile" and review["passed"]:
            path = local(workspace, root / "Report.md")
            if _hash(path.read_bytes()) == state["manual_hash"]:
                _write(path, report)
        state.update(complete=True, committed_revision=commit["revision"], review=review, draft=draft)
        _write(run / "state.json", _json(state))
        progress(review["message"])
        return {"report_id": report_id, "status": manifest(workspace, report_id)["status"], "revision": commit["revision"],
                "revision_hash": commit["revision_hash"], "readiness": draft["readiness"], **usage}
    except BudgetExceeded as error:
        state['budget_exhausted'] = True
        _write(run / 'state.json', _json(state))
        record = manifest(workspace, report_id)
        message = 'Report stopped at its call or time limit. Saved steps are retained; no automatic retry will run.'
        record.update(status='needs_attention', last_message=message)
        save_manifest(workspace, report_id, record)
        return {'report_id':report_id, 'status':'needs_attention', 'message':message, **usage}
    except BaseException as error:
        record = manifest(workspace, report_id)
        record.update(status="needs_attention", last_message="Report work was interrupted; saved steps can be resumed." if not isinstance(error, Exception) else str(error)[:1200])
        save_manifest(workspace, report_id, record)
        raise


def summaries(workspace):
    from .application import ReportSummary, ActionAvailability
    root = workspace.reports_directory / "V2"
    if not root.exists():
        return []
    rows = []
    for directory in sorted(local(workspace, root).iterdir()):
        if not exists(workspace, directory.name):
            continue
        record = manifest(workspace, directory.name)
        saved = load_revision(workspace, directory.name) if record["current_revision"] is not None else None
        approval_path = saved["directory"] / "approval.json" if saved else None
        approved = approval(workspace, record["report_id"])[0] if approval_path and approval_path.exists() else None
        edited = edited_files(workspace, directory.name, saved) if saved else []
        readable = (saved["directory"] if saved else directory).relative_to(workspace.vault_root)
        publishable = saved and saved["draft.json"]["readiness"] != "insufficient"
        passed = saved and saved["review.json"]["passed"]
        exports = []
        for path in (directory / "Exports").glob("revision-*/export.json"):
            match = re.fullmatch(r"revision-(\d+)", path.parent.name)
            if match:
                exports.append(int(match[1]))
        exhausted = False
        is_historical = bool(saved and historical(workspace, saved["evidence.json"]))
        recovery = None
        if saved and not publishable:
            current = build_bundle(workspace, record)
            missing = list(dict.fromkeys(g["reason"] for g in current["gaps"]))
            if current["readiness_ceiling"] != "insufficient":
                recovery = {"kind": "ready", "label": "Ready to generate", "message": "Prepared research is now available for this request. Generate the report using it; the earlier attempt stays saved.", "missing_inputs": []}
            elif not current["facts_revision"] or not current["scope_revision"] or any(g["kind"] == "stale_research" for g in current["gaps"]):
                recovery = {"kind": "prepare", "label": "Research needs preparation", "message": "This report needs prepared, source-checked research. Existing notes alone cannot be used by the new report writer. Prepare research first, then return here to generate the report. This does not mean the project has no useful information.", "missing_inputs": missing}
            else:
                recovery = {"kind": "evidence", "label": "More evidence needed", "message": "Research is prepared, but it cannot support this request yet. Add sources addressing the missing inputs below and prepare research again, or ask a narrower question. Repeating this report with unchanged research will not help.", "missing_inputs": missing}
        if record["pending_run"]:
            pending_state = read_json(workspace, directory / "Runs" / record["pending_run"] / "state.json")
            exhausted = pending_state["next_round"] > MAX_REPAIRS or pending_state.get('budget_exhausted', False)
        actions = {"generate_draft": bool((not saved or record["pending_run"]) and not exhausted), "prepare_evidence": False,
                   "review_quality": False, "revise": bool(publishable and not record["pending_run"] and not edited),
                   "refresh_evidence": bool((recovery and recovery["kind"] == "ready") or (not recovery and (is_historical or exhausted) and (not record["pending_run"] or record["status"] == "needs_attention"))),
                   "edit": bool(publishable and not record["pending_run"] and not edited),
                   "reconcile": bool(saved and edited and not record["pending_run"]),
                   "finalize": bool(publishable and passed and not edited and not record["pending_run"] and not approved),
                   "export": bool(approved)}
        rows.append(ReportSummary(report_id=record["report_id"], title=record["title"], mode=record["mode"], question=record["question"],
            status="needs_attention" if edited else record["status"], revision=record["current_revision"] if saved else 0,
            quality_status="not_run" if saved and not publishable else "passed" if passed else "issues_found" if saved else "not_run", created_at=record["created_at"], updated_at=record["updated_at"],
            finalized_at=approved["finalized_at"] if approved else None, recommendation_approved=bool(approved and approved["recommendation_approved"]),
            readiness=saved["draft.json"]["readiness"] if saved else None,
            report_page=(readable / "Report.md").as_posix() if saved else None,
            analyst_notes_page=(readable / "Analyst-Notes.md").as_posix() if saved else None,
            quality_page=(readable / "Quality.md").as_posix() if saved else None, export_revisions=tuple(sorted(exports)),
            actions={k: ActionAvailability(v, None if v else "This action is not available for the current report state.") for k, v in actions.items()},
            schema_version=VERSION, historical=is_historical, revision_hash=record["revision_hash"], recovery=recovery,
            needs_recommendation_approval=bool(saved and any(a["kind"] == "recommendation" for a in saved["draft.json"]["assertions"])),
            message="Edited files are preserved and need review." if edited else record["last_message"], edited_files=tuple(edited)))
    return rows


def detail(workspace, report_id):
    record = manifest(workspace, report_id)
    summary = next(r for r in summaries(workspace) if r.report_id == report_id)
    if record["current_revision"] is None:
        return {"report": summary.to_dict(), "assertions": [], "sections": [], "revisions": []}
    saved = load_revision(workspace, report_id)
    previous = load_revision(workspace, report_id, record["current_revision"] - 1) if record["current_revision"] else None
    comparison = list(unified_diff((previous["Report.md"] if previous else "").splitlines(keepends=True), saved["Report.md"].splitlines(keepends=True),
                                  fromfile="Previous revision", tofile="Current revision"))
    prior_assertions = {a["assertion_id"]: a for a in previous["draft.json"]["assertions"]} if previous else {}
    changes = [{"assertion_id": a["assertion_id"], "before": prior_assertions.get(a["assertion_id"], {}).get("text"), "after": a["text"],
                "support_changed": a["fact_keys"] != prior_assertions.get(a["assertion_id"], {}).get("fact_keys", [])}
               for a in saved["draft.json"]["assertions"] if a != prior_assertions.get(a["assertion_id"])]
    current_ids = {a["assertion_id"] for a in saved["draft.json"]["assertions"]}
    changes.extend({"assertion_id": aid, "before": row["text"], "after": None, "support_changed": True}
                   for aid, row in prior_assertions.items() if aid not in current_ids)
    revisions = []
    for number in range(record["current_revision"] + 1):
        revision = load_revision(workspace, report_id, number)
        revisions.append({"revision": number, "revision_hash": revision["commit"]["revision_hash"],
                          "operation": revision["commit"]["operation"],
                          "report_page": (revision["directory"] / "Report.md").relative_to(workspace.vault_root).as_posix()})
    from .report_v2_export import chart_suggestions
    return {"report": summary.to_dict(), "assertions": saved["draft.json"]["assertions"], "sections": saved["draft.json"]["sections"],
            "review": saved["review.json"], "gaps": saved["evidence.json"]["gaps"], "comparison": "".join(comparison),
            "changes": changes, "revisions": revisions, "suggested_charts": chart_suggestions(saved["evidence.json"])}


def source(workspace, report_id, revision, source_id):
    saved = load_revision(workspace, report_id, revision)
    found = next((s for s in saved["evidence.json"]["sources"] if s["source_id"] == source_id), None)
    if found is None:
        raise FileNotFoundError("Report source was not found.")
    return {"report_id": report_id, "revision": revision, "source": found}


def interrupted_project(workspace):
    """Reflect an interrupted dashboard job without discarding its report steps."""
    for row in summaries(workspace):
        record = manifest(workspace, row.report_id)
        if record["pending_run"] and record["status"] == "generating":
            record.update(status="needs_attention", last_message="Generation was interrupted. Resume to reuse saved steps and the remaining repair allowance.")
            save_manifest(workspace, row.report_id, record)
