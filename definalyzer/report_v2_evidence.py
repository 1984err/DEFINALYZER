"""Question-led selection of checked facts and portable original passages."""
from __future__ import annotations

import re
from copy import deepcopy

from .research_facts import load_facts, fact_detail
from .research_profiles import profile_questions, observation_requirements
from .research_scope import load_scope, _inputs, _hash, _json
from .report_v2_store import VERSION, now

MAX_FACTS_SCANNED = 512
MAX_CONTEXT = 12_000
MAX_SELECTED = 24
STOP = set("a an the and or is are was were be do does can how what which when of to for on in from with about this that it its their they as by have has research review full explain work works would should".split())
TOPIC_TERMS = {
    "architecture": "execution consensus finality validators receipt asynchronous architecture transaction settlement accounts staking",
    "tokenomics": "token coin supply dilution issuance emission mint burn distribution allocation utility rights tokenomics vesting unlock",
    "governance": "governance vote voting control controls admin administrator pause upgrade delay timelock permission authority",
    "security": "security audit custody trust signer exploit safety secure",
    "risk-assessment": "risk risks failure failures vulnerability losses mitigations",
    "revenue-model": "fee fees revenue earn earnings interest income treasury reserve incentives profitability accrual repurchase",
    "liquidity": "liquidity liquid redemption redeem withdrawal withdrawals exit borrow borrowing lending pool liquidation",
    "integrations-dependencies": "dependency dependencies bridge oracle integration external committee",
    "competitive-positioning": "compare comparison competitor competitive better advantage tradeoff alternatives",
    "protocol-overview": "purpose users product overview protocol boundaries relationship",
}


def tokens(text):
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2 and word not in STOP}


def request_plan(request, subject):
    question = request.get("question") or ""
    words = tokens(question) - tokens(subject["name"])
    category = "mechanics"
    if re.search(r"\b(undervalued|overvalued|valuation|price target|worth buying|buy|sell|invest|fair value)\b", question, re.I):
        category = "valuation"
    elif re.search(r"\b(compare|comparison|better|best|versus|vs\.?|outperform)\b", question, re.I):
        category = "comparison"
    elif re.search(r"\b(last (month|year|quarter)|historical|earned|realized|how much revenue)\b", question, re.I):
        category = "historical_measurement"
    elif (re.search(r"\b(today|currently|current|now|live|concentration|market cap|trading volume)\b", question, re.I)
          or (re.search(r"\b(how many|how much)\b", question, re.I)
              and not re.search(r"\b(share|percentage|portion|fees? goes|fees? go)\b", question, re.I))):
        category = "current_state"
    all_questions = profile_questions(subject["kind"])
    selected_topics = set(TOPIC_TERMS) if request["mode"] == "full_review" else {
        topic for topic, terms in TOPIC_TERMS.items() if tokens(terms) & words}
    if not selected_topics and words <= (tokens(subject["name"]) | {"purpose", "overview", "describe"}):
        selected_topics = {"protocol-overview", "architecture"}
    return {"version": 1, "category": category, "subject": subject, "topics": sorted(selected_topics),
            "questions": [{"question_id": key, **value, "supports_conclusion": value["question"]}
                          for key, value in all_questions.items() if value["topic"] in selected_topics],
            "requires_observations": category in {"valuation", "current_state", "historical_measurement"} or request["mode"] == "full_review",
            "requires_comparison": category == "comparison", "query_terms": sorted(words)}


def prompt_plan(plan):
    return {**plan, "questions": [{k: q[k] for k in ("question_id", "topic", "question")} for q in plan["questions"]]}


def prompt_bundle(bundle):
    return {"subject": bundle["subject"], "plan": prompt_plan(bundle["plan"]), "readiness_ceiling": bundle["readiness_ceiling"],
            "facts": [{k: f[k] for k in ("fact_key", "subject_id", "subject", "topic", "statement", "applicability", "quantities", "source_ids", "question_ids")} for f in bundle["facts"]],
            "sources": [{k: s[k] for k in ("source_id", "path", "start_line", "end_line", "context")} for s in bundle["sources"]],
            "gaps": bundle["gaps"], "conflicts": bundle["conflicts"]}


def _assemble(facts):
    sources, lookup, rows = [], {}, []
    for fact in facts:
        ids = []
        # Include limiting passages cited by the support checker as well.
        for reference in fact["evidence"] + fact["support_check"]["evidence"]:
            key = (reference["snapshot_id"], reference["start_line"], reference["end_line"], reference["context_sha256"])
            if key not in lookup:
                sid = "S" + str(len(sources) + 1)
                lookup[key] = sid
                sources.append({**reference, "origin_id": reference["source_id"], "source_id": sid})
            else:
                # Several facts can cite different sentences in one passage.
                # The shared locator must retain the complete passage, not only
                # whichever claim happened to be selected first.
                source = sources[int(lookup[key][1:]) - 1]
                if reference["quote"] != source["quote"]:
                    source["quote"] = source["context"]
                    source["excerpt_sha256"] = _hash(source["quote"])
            ids.append(lookup[key])
        rows.append({**fact, 'question_ids':fact.get('checked_question_ids', fact['question_ids']),
                     "fact_key": "F" + str(len(rows) + 1), "source_ids": list(dict.fromkeys(ids))})
    return rows, sources


def build_bundle(workspace, request):
    document, scope = load_facts(workspace), load_scope(workspace)
    subject = scope["subject"] if scope else {"subject_id": workspace.document.get("subject_id"), "name": workspace.name, "kind": workspace.document["entity_type"]}
    plan = request_plan(request, subject)
    result = {"schema_version": VERSION, "captured_at": now(), "subject": subject, "plan": plan,
              "facts_revision": document["revision"] if document else None, "scope_revision": scope["revision"] if scope else None,
              "source_inputs": deepcopy(scope["inputs"]) if scope else {}, "facts": [], "sources": [], "coverage": [],
              "conflicts": [], "gaps": [], "omissions": [], "readiness_ceiling": "insufficient"}
    def gap(reason, kind="missing", topic=None):
        for existing in result["gaps"]:
            if existing["reason"] == reason and existing["kind"] == kind:
                existing["topics"] = sorted(set(existing.get("topics", [existing["topic"]] if existing["topic"] else [])) | ({topic} if topic else set()))
                return
        result["gaps"].append({"gap_id": "G" + str(len(result["gaps"]) + 1), "kind": kind, "topic": topic, "reason": reason})
    if not document or not scope:
        gap("Source-supported research has not been prepared for this project. Analyze the project before generating a source-backed report.")
        return seal(result)
    if document["scope_revision"] != scope["revision"] or document["inputs"] != _inputs(workspace):
        gap("Saved research predates the current sources or scope. Refresh research before using the changed evidence.", "stale_research")
        return seal(result)
    preparation = document.get('preparation', {})
    if preparation.get('selected_sources') is not None:
        gap(f"Research covers {len(preparation['source_paths'])} selected saved documents; other sources were not assessed in this preparation.", 'selection')
    if preparation.get('status') == 'partial':
        gap('Preparation is incomplete. Use the accepted claims within their documented limits; unprocessed sources remain unassessed.', 'preparation')
    primary = scope["subject"]["subject_id"]
    all_facts = document["facts"]
    scanned = all_facts[:MAX_FACTS_SCANNED]
    if len(all_facts) > len(scanned):
        gap("Some facts exceeded the bounded retrieval inventory and remain unassessed.", "omission")
    query = set(plan["query_terms"])
    ranked = []
    for fact in scanned:
        lexical = len(query & tokens(fact["statement"] + " " + fact["predicate"]))
        topical = fact["topic"] in plan["topics"]
        if request["mode"] != "full_review" and not lexical and not topical:
            continue
        ranked.append((lexical * 4 + int(topical) * 2 + int(fact["subject_id"] == primary), fact))
    ranked.sort(key=lambda row: (-row[0], row[1]["revision"]))
    relevant = {f["revision"] for _, f in ranked}
    # Related failure/dependency facts are relevant exposure context, not core mechanics.
    if relevant:
        for fact in scanned:
            if fact["revision"] not in relevant and fact["topic"] in {"risk-assessment", "security", "integrations-dependencies"}:
                ranked.append((0, fact))
                relevant.add(fact["revision"])
    by_revision = {f["revision"]: f for f in all_facts}
    conflict_groups = [group for row in document["coverage"] for group in row["conflicts"]]
    selected, considered = [], set()
    for _, candidate in ranked:
        if candidate["revision"] in considered:
            continue
        ids = {candidate["revision"]}
        # Transitive closure ensures a contrary passage cannot fall out of a group.
        changed = True
        while changed:
            before = len(ids)
            for group in conflict_groups:
                if ids.intersection(group):
                    ids.update(group)
            changed = len(ids) != before
        considered.update(ids)
        group = [fact_detail(workspace, revision) for revision in sorted(ids) if revision in by_revision]
        proposed = {f["revision"]: f for f in selected + group}
        rows, sources = _assemble(list(proposed.values()))
        size = len(_json({"facts": [{k: f[k] for k in ("fact_key", "subject", "subject_id", "topic", "statement", "applicability", "source_ids")} for f in rows],
                          "sources": [{k: s[k] for k in ("source_id", "path", "start_line", "end_line", "context")} for s in sources]}))
        if len(rows) > MAX_SELECTED or size > MAX_CONTEXT:
            result["omissions"].append({"fact_revisions": sorted(ids), "reason": "Complete source context exceeds the report allowance."})
            continue
        selected = list(proposed.values())
    result["facts"], result["sources"] = _assemble(selected)
    chosen = {f["revision"]: f["fact_key"] for f in result["facts"]}
    result["coverage"] = [deepcopy(row) for row in document["coverage"] if row["topic"] in plan["topics"]]
    for group in conflict_groups:
        if set(group) & set(chosen):
            result["conflicts"].append({"conflict_id": "K" + str(len(result["conflicts"]) + 1),
                                        "fact_keys": [chosen[r] for r in group if r in chosen], "fact_revisions": group})
    if result["omissions"]:
        gap("Some relevant facts or complete conflict groups could not fit. The report must limit its conclusion to the selected evidence.", "omission")
    for row in result["coverage"]:
        for source_gap in row["gaps"]:
            gap(source_gap["reason"], "research_gap", row["topic"])
        if not any(f["subject_id"] == primary and f["topic"] == row["topic"] for f in result["facts"]):
            gap("No selected checked documentation answers the main subject's " + row["topic"].replace("-", " ") + " questions.", "coverage", row["topic"])
    if plan["requires_observations"]:
        needs = observation_requirements(subject["kind"])
        gap("Current price, market activity and on-chain execution are not established by these saved documents.", "observations")
    if plan["requires_comparison"]:
        gap("The selected documentation does not establish a like-for-like comparison with independently scoped alternatives.", "comparison")
    if any(not f["applicability"]["period"] for f in result["facts"]):
        gap("Some source claims have no known effective period; do not describe them as measured current state.", "freshness")
    question = (request.get('question') or '').casefold()
    requested_subjects = {primary} | {f['subject_id'] for f in result['facts'] if
        f['subject'].casefold() in question and len(f['subject'].strip('$')) >= 3}
    primary_facts = [f for f in result["facts"] if f["subject_id"] in requested_subjects]
    if primary_facts and plan["category"] not in {"valuation", "current_state", "historical_measurement", "comparison"}:
        result["readiness_ceiling"] = "partial" if request["mode"] == "full_review" or result["omissions"] or result["conflicts"] else "ready"
    else:
        gap("There is insufficient evidence for the requested conclusion. Documented mechanisms cannot substitute for the missing measurements, comparison or subject evidence.", "answer")
    return seal(result)


def seal(bundle):
    result = deepcopy(bundle)
    result.pop("bundle_hash", None)
    result["bundle_hash"] = _hash(_json(result))
    return result


def validate_bundle(bundle):
    if bundle.get("schema_version") != VERSION or seal(bundle)["bundle_hash"] != bundle.get("bundle_hash"):
        raise ValueError("Frozen report evidence failed its integrity check.")
    ids = {s["source_id"] for s in bundle["sources"]}
    if len(ids) != len(bundle["sources"]):
        raise ValueError("Duplicate frozen source IDs.")
    for source in bundle["sources"]:
        if (_hash(source["context"]) != source["context_sha256"] or source["quote"] not in source["context"]
                or _hash(source["quote"]) != source["excerpt_sha256"]):
            raise ValueError("Frozen original source context or quote does not resolve.")
    for fact in bundle["facts"]:
        if fact["kind"] != "documented_claim" or fact["support_check"]["status"] != "supported" or not set(fact["source_ids"]) <= ids:
            raise ValueError("Report fact lacks checked original-source lineage.")


def historical(workspace, bundle):
    document, scope = load_facts(workspace), load_scope(workspace)
    return (not document or not scope or document["revision"] != bundle["facts_revision"]
            or scope["revision"] != bundle["scope_revision"] or _inputs(workspace) != bundle["source_inputs"])
