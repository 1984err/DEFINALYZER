import copy
import json
import tempfile
import unittest
from pathlib import Path

from definalyzer.workspace import WorkspaceManager
from definalyzer.providers import ProviderResponse
from definalyzer.research_scope import prepare_scope, _hash, _json
from definalyzer.research_facts import collect_facts
from definalyzer.report_v2_store import create, manifest, load_revision, finalize, package, approval
from definalyzer.report_v2 import generate, detail, summaries, source
from definalyzer.report_v2_evidence import build_bundle, historical
from definalyzer.report_v2_writing import validate_draft
from tests.test_research_facts import FactFixture


def payload(prompt, marker):
    return json.JSONDecoder().raw_decode(prompt.split(marker + "\n", 1)[1])[0]


class NarrativeProvider:
    name = "narrative-fixture"

    def __init__(self, reject=False, invalid_number=False, interrupt=False):
        self.calls = []
        self.reject = reject
        self.invalid_number = invalid_number
        self.interrupt = interrupt

    def generate(self, prompt, **kwargs):
        self.calls.append(prompt)
        if prompt.startswith("# V2 report writing"):
            evidence = payload(prompt, "FROZEN EVIDENCE:")
            primary = evidence["subject"]["subject_id"]
            facts = [f for f in evidence["facts"] if f["subject_id"] == primary]
            f = facts[0]
            gaps = [g["gap_id"] for g in evidence["gaps"] if g["kind"] == "observations"]
            texts = [f["statement"], f["statement"] + " This describes a documented mechanism.",
                     "The documentation supports an explanation of the mechanism. Current measured activity is not established in this bundle."]
            if self.invalid_number:
                texts[0] += " The fee is 987654%."
            assertions = [{"assertion_id": "A" + str(i+1), "text": text, "kind": "interpretation" if i else "documented_claim",
                           "subject_ids": [primary], "fact_keys": [f["fact_key"]], "gap_ids": gaps if i == 2 else [],
                           "rationale": "This qualified statement follows the saved documentation.", "material_qualifiers": []} for i, text in enumerate(texts)]
            sections = [{"section_id": "S"+str(i+1), "title": title, "role": role,
                         "blocks": [{"block_id": "P"+str(i+1), "assertion_id": "A"+str(i+1), "text": texts[i]}]}
                        for i,(title,role) in enumerate((("Assessment","summary"),("Mechanism and implications","analysis"),("Conclusion","conclusion")))]
            result = {"readiness": "ready", "sections": sections, "assertions": assertions}
        elif prompt.startswith("# V2 report revision"):
            previous = payload(prompt, "PREVIOUS:")
            revision = payload(prompt, "REVISION:")
            chosen = next((b["assertion_id"] for s in previous["sections"] for b in s["blocks"] if revision["target"] in {b["block_id"], b["assertion_id"], s["section_id"]}), "A3")
            row = copy.deepcopy(next(a for a in previous["assertions"] if a["assertion_id"] == chosen))
            row["text"] += " This assessment remains limited to documentation."
            result = {"changes": [row], "readiness": "partial"}
        elif prompt.startswith("# V2 original-source assertion review"):
            if self.interrupt:
                raise KeyboardInterrupt()
            assertions = payload(prompt, "ASSERTIONS:")
            originals = payload(prompt, "ORIGINAL SOURCES:")
            lookup = {s["source_id"]: s for s in originals}
            result = {"checks": [{"assertion_id": a["assertion_id"], "support": "needs_qualification" if self.reject else "supported",
                        "subject_match": True, "context_preserved": not self.reject, "reasoning_supported": True,
                        "reason": "A material condition needs qualification." if self.reject else "Original context supports this paragraph and its qualifications.",
                        "evidence": [{"source_id": sid, "quote": lookup[sid]["context"]} for sid in a["source_ids"]]} for a in assertions]}
            if 'conclusion_check:' in prompt:
                result['conclusion_check'] = {'request_addressed':True, 'conclusion_proportionate':True,
                    'material_limits_visible':True, 'conflicts_visible':True, 'readiness':'ready', 'issues':[]}
        elif prompt.startswith("# V2 report conclusion and coverage review"):
            result = {"request_addressed": True, "conclusion_proportionate": True, "material_limits_visible": True,
                      "conflicts_visible": True, "readiness": "ready", "issues": []}
        elif prompt.startswith("# V2 edited analyst notes review"):
            evidence = payload(prompt, "ORIGINAL EVIDENCE:")
            s = evidence["sources"][0]
            result = {"supported": not self.reject, "reason": "Checked the edited notes against original documentation.",
                      "evidence": [{"source_id": s["source_id"], "quote": s["context"]}]}
        else:
            raise AssertionError("Unexpected V2 task")
        return ProviderResponse(json.dumps(result), self.name, ())


class V2ReportTests(unittest.TestCase):
    def test_unprepared_report_explains_recovery_and_enables_generation_after_analysis(self):
        ws=self.manager.create_project(name='Unprepared',entity_type='chain')
        path=ws.sources_directory/'mechanics.md'
        path.write_text('# Unprepared\nUnprepared consensus uses validators and requires a 67% threshold in 2025.\n',encoding='utf-8')
        rid=create(ws,title='Blocked review',mode='full_review')['report_id']
        provider=NarrativeProvider()
        generate(ws,rid,provider=provider)
        self.assertEqual(provider.calls,[])
        before=load_revision(ws,rid)
        summary=summaries(ws)[0]
        self.assertEqual(summary.recovery['kind'],'prepare')
        self.assertFalse(summary.actions['refresh_evidence'].available)
        self.assertIn('Analyze the project',before['Report.md'])
        self.assertIn('checks were not run',before['Analyst-Notes.md'])
        self.prepare(ws)
        summary=summaries(ws)[0]
        self.assertEqual(summary.recovery['kind'],'ready')
        self.assertTrue(summary.actions['refresh_evidence'].available)
        self.assertEqual(load_revision(ws,rid)['Report.md'],before['Report.md'])

    def test_unsupported_measurement_request_does_not_offer_unchanged_refresh(self):
        rid=self.report(question='What is the current token price today?')
        generate(self.workspace,rid,provider=NarrativeProvider())
        summary=summaries(self.workspace)[0]
        self.assertEqual(summary.recovery['kind'],'evidence')
        self.assertTrue(summary.recovery['missing_inputs'])
        self.assertFalse(summary.actions['refresh_evidence'].available)

    def test_malformed_review_is_retried_without_rewriting_valid_prose(self):
        class OnceMalformed(NarrativeProvider):
            def generate(inner,prompt,**kwargs):
                response=super().generate(prompt,**kwargs)
                if prompt.startswith('# V2 original-source') and sum(p.startswith('# V2 original-source') for p in inner.calls)==1:
                    data=json.loads(response.text);data['checks'][0]['evidence'][0]['source_id']='S999'
                    return ProviderResponse(json.dumps(data),inner.name,())
                return response
        provider=OnceMalformed();rid=self.report(mode='full_review')
        result=generate(self.workspace,rid,provider=provider)
        self.assertEqual(result['status'],'ready_to_review')
        self.assertEqual(sum(p.startswith('# V2 report writing') for p in provider.calls),1)
        self.assertEqual(sum(p.startswith('# V2 report revision') for p in provider.calls),0)
        self.assertEqual(sum(p.startswith('# V2 original-source') for p in provider.calls),2)

    def test_counterevidence_for_an_absence_claim_reaches_the_repair_feedback(self):
        from definalyzer.report_v2_writing import review_draft
        rid,saved=self.completed()
        draft=copy.deepcopy(saved['draft.json']);bundle=saved['evidence.json']
        assertion=draft['assertions'][-1]
        assertion.update(kind='uncertainty',fact_keys=[],source_ids=[],text='The saved evidence does not describe validators.')
        for section in draft['sections']:
            for block in section['blocks']:
                if block['assertion_id']==assertion['assertion_id']:block['text']=assertion['text']
        source=bundle['sources'][0];provider=NarrativeProvider()
        def call(label,prompt):
            result=json.loads(provider.generate(prompt).text)
            if label=='assertions':
                row=next(r for r in result['checks'] if r['assertion_id']==assertion['assertion_id'])
                row.update(support='needs_qualification',context_preserved=False,reason='The original explicitly describes validators.',evidence=[{'source_id':source['source_id'],'quote':source['context']}])
            return result
        review=review_draft(manifest(self.workspace,rid),bundle,draft,call,lambda message:None)
        self.assertFalse(review['passed'])
        self.assertTrue(any(i['code']=='original_support' and 'explicitly describes' in i['message'] for i in review['issues']))
        self.assertFalse(any(i['code']=='support_review_incomplete' for i in review['issues']))

    def test_valid_but_unlinked_support_requires_writer_repair(self):
        from definalyzer.report_v2_writing import review_draft
        rid,saved=self.completed()
        draft=copy.deepcopy(saved['draft.json']);bundle=saved['evidence.json']
        assertion=draft['assertions'][-1]
        assertion['source_ids']=[]
        original=bundle['sources'][0];provider=NarrativeProvider()
        def call(label,prompt):
            result=json.loads(provider.generate(prompt).text)
            if label=='assertions':
                row=next(r for r in result['checks'] if r['assertion_id']==assertion['assertion_id'])
                row['evidence']=[{'source_id':original['source_id'],'quote':original['context']}]
            return result
        review=review_draft(manifest(self.workspace,rid),bundle,draft,call,lambda message:None)
        self.assertFalse(review['passed'])
        self.assertEqual(review['conclusion_check'],{})
        self.assertTrue(any(i['code']=='original_support' and 'not linked' in i['message'] for i in review['issues']))
        self.assertFalse(any(i['code']=='support_review_incomplete' for i in review['issues']))
        self.assertNotIn(assertion['assertion_id'],[c['assertion_id'] for c in review['checks']])

    def test_revision_receives_saved_review_errors_without_researcher_retyping_them(self):
        rid=self.report()
        generate(self.workspace,rid,provider=NarrativeProvider(reject=True))
        before=load_revision(self.workspace,rid)
        provider=NarrativeProvider()
        result=generate(self.workspace,rid,provider=provider,operation='revise',instruction='Fix review issues',expected_revision=manifest(self.workspace,rid)['revision_hash'])
        first=next(prompt for prompt in provider.calls if prompt.startswith('# V2 report revision'))
        self.assertEqual(payload(first,'REVISION:')['feedback'],[i for i in before['review.json']['issues'] if i['severity']=='error'])
        self.assertEqual(result['status'],'ready_to_review')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manager = WorkspaceManager(Path(self.temp.name)/"output")
        self.workspace = self.manager.create_project(name="Northstar", entity_type="chain")
        self.path = self.workspace.sources_directory/"mechanics.md"
        self.path.write_text("# Northstar\nNorthstar consensus uses validators and requires a 67% threshold in 2025.\n", encoding="utf-8")
        self.prepare()

    def prepare(self, workspace=None):
        workspace = workspace or self.workspace
        prepare_scope(workspace)
        return collect_facts(workspace, provider=FactFixture())[0]

    def report(self, mode="question", question="How does Northstar consensus work?", title="Consensus review", **kwargs):
        return create(self.workspace, title=title, mode=mode, question=question if mode == "question" else None, **kwargs)["report_id"]

    def completed(self, **kwargs):
        rid = self.report(**kwargs)
        generate(self.workspace, rid, provider=NarrativeProvider())
        return rid, load_revision(self.workspace, rid)

    def test_coherent_report_maps_every_paragraph_to_original_evidence(self):
        rid, saved = self.completed()
        self.assertEqual(manifest(self.workspace,rid)["status"],"ready_to_review")
        self.assertTrue(saved["review.json"]["passed"])
        self.assertEqual(len(saved["draft.json"]["assertions"]),3)
        self.assertIn("## Mechanism and implications",saved["Report.md"])
        self.assertIn("[^1]",saved["Report.md"])
        self.assertEqual(source(self.workspace,rid,0,"S1")["source"]["context"], self.path.read_bytes().decode("utf-8"))
        record = manifest(self.workspace,rid)
        with self.assertRaises(ValueError):
            finalize(self.workspace,rid,expected_revision="wrong",human_approved=True)
        finalize(self.workspace,rid,expected_revision=record["revision_hash"],human_approved=True)
        self.assertEqual(manifest(self.workspace,rid)["status"],"final")

    def test_chain_protocol_and_token_full_reviews_are_qualified_without_recommendations(self):
        for kind,name,text in (("chain","Northstar","Northstar consensus uses validators."),
                               ("protocol","Harbor Lending","Harbor Lending allocates borrower interest to suppliers and treasury."),
                               ("token","Harbor Governance","Harbor Governance holders can vote but have no contractual entitlement to fees.")):
            with self.subTest(kind=kind):
                ws = self.workspace if kind=="chain" else self.manager.create_project(name=name,entity_type=kind)
                (ws.sources_directory/"mechanics.md").write_text("# "+name+"\n"+text+"\n",encoding="utf-8")
                self.prepare(ws)
                record=create(ws,title="Full "+kind+" review",mode="full_review")
                generate(ws,record["report_id"],provider=NarrativeProvider())
                saved=load_revision(ws,record["report_id"])
                self.assertEqual(saved["draft.json"]["readiness"],"partial")
                self.assertNotIn("recommendation",[a["kind"] for a in saved["draft.json"]["assertions"]])
                finalize(ws,record["report_id"],expected_revision=saved["commit"]["revision_hash"],human_approved=True)

    def test_valuation_and_current_measurements_do_not_become_doc_only_answers(self):
        for question in ("Is Northstar undervalued?","How much revenue did Northstar earn last month?","What is current validator concentration?"):
            rid=self.report(question=question,title=question)
            provider=NarrativeProvider()
            generate(self.workspace,rid,provider=provider)
            saved=load_revision(self.workspace,rid)
            self.assertEqual(saved["draft.json"]["readiness"],"insufficient")
            self.assertFalse(provider.calls)
            self.assertLess(len(saved["Report.md"].split()),100)
            self.assertIn("documentation",saved["Analyst-Notes.md"])
            with self.assertRaises(ValueError):
                finalize(self.workspace,rid,expected_revision=saved["commit"]["revision_hash"],human_approved=True)

    def test_nonexistent_subject_evidence_and_legacy_notes_do_not_certify_report(self):
        ws=self.manager.create_project(name="Other")
        (ws.vault_entity_directory/"Architecture.md").write_text("# Architecture\nThis is secure.\n",encoding="utf-8")
        record=create(ws,title="Other review",mode="full_review")
        provider=NarrativeProvider()
        generate(ws,record["report_id"],provider=provider)
        self.assertFalse(provider.calls)
        self.assertEqual(load_revision(ws,record["report_id"])["draft.json"]["readiness"],"insufficient")

    def test_unsupported_numbers_stop_within_concise_budget_and_never_finalize(self):
        rid=self.report()
        provider=NarrativeProvider(invalid_number=True)
        result=generate(self.workspace,rid,provider=provider)
        self.assertEqual(result["status"],"needs_attention")
        self.assertEqual(len(provider.calls),1)
        self.assertIsNone(manifest(self.workspace,rid)["current_revision"])
        repeated=generate(self.workspace,rid,provider=provider)
        self.assertEqual(len(provider.calls),1)

    def test_semantic_review_failure_is_visible_after_bounded_repairs(self):
        rid=self.report()
        provider=NarrativeProvider(reject=True)
        result=generate(self.workspace,rid,provider=provider)
        self.assertEqual(result["status"],"needs_attention")
        self.assertFalse(any(p.startswith('# V2 report conclusion') for p in provider.calls))
        self.assertEqual(len([p for p in provider.calls if p.startswith(("# V2 report writing","# V2 report revision"))]),1)
        saved=load_revision(self.workspace,rid)
        self.assertFalse(saved["review.json"]["passed"])
        with self.assertRaises(ValueError):
            finalize(self.workspace,rid,expected_revision=saved["commit"]["revision_hash"],human_approved=True)

    def test_targeted_revision_preserves_unrelated_paragraphs_and_old_approval(self):
        rid,old=self.completed()
        old_hash=old["commit"]["revision_hash"]
        finalize(self.workspace,rid,expected_revision=old_hash,human_approved=True)
        result=generate(self.workspace,rid,provider=NarrativeProvider(),operation="revise",target="P2",instruction="Clarify the limitation",expected_revision=old_hash)
        new=load_revision(self.workspace,rid)
        self.assertEqual(result["revision"],1)
        self.assertEqual(old["draft.json"]["assertions"][0],new["draft.json"]["assertions"][0])
        self.assertNotEqual(old["draft.json"]["assertions"][1]["text"],new["draft.json"]["assertions"][1]["text"])
        self.assertEqual(load_revision(self.workspace,rid,0)["Report.md"],old["Report.md"])
        approval(self.workspace,rid,0)
        with self.assertRaises(ValueError):
            approval(self.workspace,rid)
        self.assertTrue(detail(self.workspace,rid)["changes"])

    def test_manual_paragraphs_receive_same_review_and_preserve_exact_words(self):
        rid,old=self.completed()
        text=old["draft.json"]["assertions"][1]["text"]+" The conclusion is limited to the saved documentation."
        generate(self.workspace,rid,provider=NarrativeProvider(),operation="manual",texts={"P2":text},expected_revision=old["commit"]["revision_hash"])
        saved=load_revision(self.workspace,rid)
        self.assertEqual(saved["draft.json"]["assertions"][1]["text"],text)
        self.assertTrue(saved["review.json"]["passed"])

    def test_edited_markdown_is_preserved_then_reconciled_and_reviewed(self):
        rid,old=self.completed()
        path=package(self.workspace,rid)/"Report.md"
        text=path.read_text(encoding="utf-8").replace("This describes a documented mechanism.","This describes a documented mechanism with explicit limits.")
        path.write_text(text,encoding="utf-8")
        edited=path.read_bytes()
        with self.assertRaises(ValueError):
            finalize(self.workspace,rid,expected_revision=old["commit"]["revision_hash"],human_approved=True)
        generate(self.workspace,rid,provider=NarrativeProvider(),operation="reconcile",expected_revision=old["commit"]["revision_hash"])
        saved=load_revision(self.workspace,rid)
        self.assertIn("with explicit limits",saved["Report.md"])
        self.assertTrue(any(p.read_bytes()==edited for p in (package(self.workspace,rid)/"Preserved").iterdir()))
        finalize(self.workspace,rid,expected_revision=saved["commit"]["revision_hash"],human_approved=True)

    def test_new_sources_flag_history_without_mutating_final_support(self):
        rid,old=self.completed()
        finalize(self.workspace,rid,expected_revision=old["commit"]["revision_hash"],human_approved=True)
        self.path.write_text("# Northstar\nNorthstar consensus requires a 75% threshold in 2025.\n",encoding="utf-8")
        self.assertTrue(historical(self.workspace,old["evidence.json"]))
        self.prepare()
        self.assertTrue(summaries(self.workspace)[0].historical)
        self.assertIn("67%",source(self.workspace,rid,0,"S1")["source"]["context"])
        approval(self.workspace,rid)
        generate(self.workspace,rid,provider=NarrativeProvider(),operation="refresh",expected_revision=old["commit"]["revision_hash"])
        self.assertIn("75%",load_revision(self.workspace,rid)["Report.md"])
        self.assertEqual(load_revision(self.workspace,rid,0)["Report.md"],old["Report.md"])

    def test_unmapped_prose_and_tampered_revision_fail_closed(self):
        rid,saved=self.completed()
        draft=copy.deepcopy(saved["draft.json"])
        draft["sections"][0]["blocks"][0]["text"]="This unreviewed sentence says something else."
        with self.assertRaises(ValueError):
            validate_draft(draft,manifest(self.workspace,rid),saved["evidence.json"])
        (saved["directory"]/"Report.md").write_text("tampered",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"integrity"):
            load_revision(self.workspace,rid)

    def test_interruption_keeps_reserved_round_and_frozen_evidence(self):
        rid=self.report(mode='full_review')
        with self.assertRaises(KeyboardInterrupt):
            generate(self.workspace,rid,provider=NarrativeProvider(interrupt=True))
        record=manifest(self.workspace,rid)
        run=package(self.workspace,rid)/"Runs"/record["pending_run"]
        self.assertEqual(json.loads((run/"state.json").read_text())["next_round"],1)
        evidence=(run/"evidence.json").read_bytes()
        provider=NarrativeProvider()
        generate(self.workspace,rid,provider=provider)
        self.assertEqual((run/"evidence.json").read_bytes(),evidence)
        self.assertEqual(manifest(self.workspace,rid)["status"],"ready_to_review")

    def test_final_exports_remain_frozen_after_source_updates_and_later_revisions(self):
        from definalyzer.report_v2_export import export
        rid, saved = self.completed()
        finalize(self.workspace,rid,expected_revision=saved["commit"]["revision_hash"],human_approved=True)
        result = export(self.workspace,rid)
        directory = Path(result['directory'])
        original = {p.name:p.read_bytes() for p in directory.iterdir() if p.is_file()}
        self.assertTrue(original['Report.pdf'].startswith(b'%PDF'))
        self.assertIn(b'67%',original['Report.md'])
        self.path.write_text('# Northstar\nChanged documentation.\n',encoding='utf-8')
        self.assertTrue(export(self.workspace,rid)['reused'])
        generate(self.workspace,rid,provider=NarrativeProvider(),operation='revise',target='S2',instruction='Qualify the explanation.',expected_revision=saved['commit']['revision_hash'])
        self.assertEqual({p.name:p.read_bytes() for p in directory.iterdir() if p.is_file()}, original)
        approval(self.workspace,rid,0)
        with self.assertRaises(ValueError): export(self.workspace,rid)

    def test_manual_notes_preserve_exact_words_and_require_original_source_review(self):
        rid, saved = self.completed()
        path = package(self.workspace,rid)/'Analyst-Notes.md'
        notes = path.read_text(encoding='utf-8')+'\nFurther question: what changes after activation?\n'
        path.write_text(notes,encoding='utf-8',newline='\n')
        generate(self.workspace,rid,provider=NarrativeProvider(),operation='reconcile',expected_revision=saved['commit']['revision_hash'])
        revised = load_revision(self.workspace,rid)
        self.assertEqual(revised['Analyst-Notes.md'],notes)
        self.assertEqual(revised['review.json']['notes_hash'],_hash(notes))
        self.assertTrue(revised['review.json']['notes_check']['supported'])
        finalize(self.workspace,rid,expected_revision=revised['commit']['revision_hash'],human_approved=True)

    def test_external_prose_outside_sections_cannot_be_silently_dropped(self):
        rid,saved=self.completed()
        path=package(self.workspace,rid)/'Report.md'
        edited=saved['Report.md'].replace('## Assessment','New unlinked claim.\n\n## Assessment')
        path.write_text(edited,encoding='utf-8',newline='\n')
        with self.assertRaisesRegex(ValueError,'every paragraph'):
            generate(self.workspace,rid,provider=NarrativeProvider(),operation='reconcile',expected_revision=saved['commit']['revision_hash'])
        self.assertEqual(path.read_text(encoding='utf-8'),edited)
        self.assertEqual(load_revision(self.workspace,rid)['commit'],saved['commit'])

    def test_tampered_approval_cannot_be_exported(self):
        from definalyzer.report_v2_export import export
        rid, saved = self.completed()
        finalize(self.workspace,rid,expected_revision=saved['commit']['revision_hash'],human_approved=True)
        path=saved['directory']/'approval.json'
        data=json.loads(path.read_text(encoding='utf-8'))
        data['finalized_at']='changed'
        path.write_text(_json(data),encoding='utf-8')
        with self.assertRaises(ValueError): export(self.workspace,rid)

    def test_modified_export_and_its_manifest_cannot_replace_the_publication(self):
        from definalyzer.report_v2_export import export,export_manifest
        rid,saved=self.completed()
        finalize(self.workspace,rid,expected_revision=saved['commit']['revision_hash'],human_approved=True)
        root=Path(export(self.workspace,rid)['directory'])
        (root/'Report.md').write_text('Altered report',encoding='utf-8')
        data=json.loads((root/'export.json').read_text(encoding='utf-8'))
        data['files']['Report.md']=_hash('Altered report')
        (root/'export.json').write_text(_json(data),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'frozen final'):
            export_manifest(self.workspace,rid,0)

    def test_resume_reuses_the_pending_revision_instruction(self):
        rid, saved = self.completed(mode='full_review')
        with self.assertRaises(KeyboardInterrupt):
            generate(self.workspace,rid,provider=NarrativeProvider(interrupt=True),operation='revise',target='P2',instruction='Explain limits.',expected_revision=saved['commit']['revision_hash'])
        generate(self.workspace,rid,provider=NarrativeProvider())
        revised=load_revision(self.workspace,rid)
        self.assertEqual(revised['commit']['operation'],'revise')
        self.assertEqual(revised['draft.json']['assertions'][0],saved['draft.json']['assertions'][0])

    def test_recommendations_require_separate_approval_only_when_present(self):
        class Recommending(NarrativeProvider):
            def generate(inner,prompt,**kwargs):
                response=super().generate(prompt,**kwargs)
                if prompt.startswith('# V2 report writing'):
                    raw=json.loads(response.text)
                    raw['assertions'][-1]['kind']='recommendation'
                    return ProviderResponse(json.dumps(raw),inner.name,())
                return response
        rid=self.report(recommendations=True)
        generate(self.workspace,rid,provider=Recommending())
        saved=load_revision(self.workspace,rid)
        with self.assertRaisesRegex(ValueError,'recommendation'):
            finalize(self.workspace,rid,expected_revision=saved['commit']['revision_hash'],human_approved=True)
        finalize(self.workspace,rid,expected_revision=saved['commit']['revision_hash'],human_approved=True,recommendation_approved=True)

    def test_chart_suggestions_require_compatible_dated_structured_quantities(self):
        from definalyzer.report_v2_export import chart_suggestions
        rid,saved=self.completed()
        bundle=copy.deepcopy(saved['evidence.json'])
        first=bundle['facts'][0]
        first['applicability'].update(network='Network A',period='2025')
        second=copy.deepcopy(first)
        second.update(fact_key='F2',revision='b'*64)
        second['applicability']['network']='Network B'
        bundle['facts']=[first,second]
        self.assertEqual(len(chart_suggestions(bundle)),1)
        second['quantities'][0]['unit']='tokens'
        self.assertEqual(chart_suggestions(bundle),[])
        second['quantities'][0]['unit']=first['quantities'][0]['unit']
        second['applicability']['period']=None
        self.assertEqual(chart_suggestions(bundle),[])

    def test_question_mechanics_are_not_confused_with_current_measurements(self):
        from definalyzer.report_v2_evidence import request_plan
        subject={'name':'Harbor','kind':'protocol'}
        self.assertEqual(request_plan({'mode':'question','question':'How much of fees goes to the treasury?'},subject)['category'],'mechanics')
        self.assertEqual(request_plan({'mode':'question','question':'How much revenue is earned today?'},subject)['category'],'historical_measurement')

    def test_dashboard_keeps_existing_v2_report_and_original_source_readable(self):
        import threading, time
        from urllib.request import Request,urlopen
        from definalyzer.dashboard import create_dashboard_server
        server=create_dashboard_server(self.manager,port=0)
        server.application._provider_factory=lambda settings:NarrativeProvider()
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base='http://127.0.0.1:'+str(server.server_port)
        def request(path,data=None):
            req=Request(base+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json','X-DEFINALYZER-Token':server.token})
            with urlopen(req) as response:return json.load(response)
        # Seed an existing experimental report through its explicit module API,
        # using the local fixture provider, then exercise read-only HTTP access.
        from definalyzer.report_v2_store import create
        from definalyzer.report_v2 import generate
        record=create(self.workspace,title='Saved dashboard report',mode='full_review')
        generate(self.workspace,record['report_id'],provider=NarrativeProvider())
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError) as denied:
            request('/api/projects/northstar/jobs',{'action':'report-draft','report_id':record['report_id']})
        self.assertEqual(denied.exception.code,400)
        report=request('/api/projects/northstar/reports/'+record['report_id'])['report']
        from urllib.parse import quote
        page=request('/api/page?path='+quote(report['report_page']))
        self.assertEqual(page['report_context']['revision'],0)
        self.assertIn('report-citation',page['html'])
        source=request('/api/projects/northstar/reports/'+record['report_id']+'/sources/0/S1')
        self.assertIn('67%',source['source']['context'])


if __name__=="__main__":
    unittest.main()
