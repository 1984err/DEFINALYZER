"""Offline Phase B cases: original sources, controlled responses, real pipeline.

These tests enforce code contracts. They do not certify a live model's accuracy.
"""
import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from definalyzer.workspace import WorkspaceManager
from definalyzer.providers import ProviderResponse
from definalyzer import research_facts as rf
from definalyzer.research_scope import _inputs, _write, _json, _hash, prepare_scope
from definalyzer.research_quality import source_gap, repair_quote
from definalyzer.research_preparation import prepare_research, preparation_sources
from definalyzer.operation_budget import BudgetProvider, BudgetExceeded
from definalyzer.cancellation import cancellation_scope, OperationCancelled
from definalyzer.report_v2 import generate
from definalyzer.report_v2_store import create, load_revision, manifest, package
from definalyzer.report_v2_evidence import build_bundle
from definalyzer.report_v2_writing import validate_draft, writing_prompt
from tests.test_research_facts import FactFixture
from tests.test_report_v2 import NarrativeProvider, payload

FIXTURE = Path(__file__).parent/'fixtures/extraction_demo'


class ExtractionDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manager = WorkspaceManager(Path(self.temp.name)/'output')
        self.ws = self.manager.create_project(name='Pump.fun', entity_type='protocol')
        self.fixture = json.loads((FIXTURE/'cases.json').read_text(encoding='utf-8'))
        self.blocks = {}
        for name, row in self.fixture['blocks'].items():
            raw = (FIXTURE/'snapshots'/f"{row['snapshot_sha256']}.md").read_bytes()
            source = self.ws.sources_directory/row['path']
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(raw)
            snapshot = self.ws.project_root/'scope/snapshots'/f"{row['snapshot_sha256']}.md"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(raw)
            self.blocks[name] = {**row, 'snapshot':row['snapshot_sha256'], 'relationship':'unresolved',
                'applicability':{}, 'subjects':['Pump.fun','$PUMP','PumpSwap','pump_rust_client'], 'route':'qualified'}
        self.subjects = {'pump-fun':{'name':'Pump.fun'}, 'token':{'name':'$PUMP'},
                         'swap':{'name':'PumpSwap'}, 'sdk':{'name':'pump_rust_client'}, 'program':{'name':'pump'}}

    def proposal(self, block, statement, *, subject='pump-fun', topic='revenue-model', quote=None, quantities=None):
        return {'kind':'documented_claim', 'subject_id':subject, 'topic':topic, 'predicate':'test mechanism',
                'statement':statement, 'applicability':{}, 'question_ids':[topic+'.1', topic+'.2'],
                'quantities':quantities or [], 'evidence':[{'block_id':self.blocks[block]['block_id'], 'quote':quote or statement}]}

    def validate(self, candidate, names=None, subjects=None):
        blocks = [self.blocks[n] for n in names] if names else list(self.blocks.values())
        return rf.validate_proposal(self.ws, candidate, blocks={b['block_id']:b for b in blocks}, subjects=subjects or self.subjects)

    def run_batch(self, candidates, names, *, check_change=None, extract_change=None):
        class Controlled:
            name = 'offline-demo-fixture'
            def __init__(inner): inner.calls=[]
            def generate(inner, prompt, **kwargs):
                inner.calls.append(prompt)
                if prompt.startswith('# Original-source'):
                    data={'facts':copy.deepcopy(candidates), 'gaps':[]}
                    if extract_change: extract_change(data, prompt)
                else:
                    facts=payload(prompt,'PROPOSALS:')
                    data={'checks':[{'proposal_id':f['proposal_id'], 'status':'supported', 'subject_match':True,
                        'context_preserved':True, 'reason':'Controlled support decision.', 'evidence':f['evidence']} for f in facts]}
                    if check_change: check_change(data)
                return ProviderResponse(json.dumps(data),inner.name,())
        provider=Controlled()
        usage={'provider_calls':0,'provider_input_characters':0,'reused_calls':0}
        result=rf._run_batch(self.ws,provider,[self.blocks[n] for n in names],self.subjects,
                            self.ws.project_root/'test-batch',usage,lambda _:None)
        return result,provider

    def test_B01_fee_conditions_and_B03_six_quantity_row(self):
        row='| 0 – 420 SOL  | 0.300%  | 0.930%  | 0.020%  | 1.250%  |'
        quantities=[{'value':v,'unit':u,'literal':lit} for v,u,lit in
            [('0','SOL','0 – 420 SOL'),('420','SOL','0 – 420 SOL'),('0.300','%','0.300%'),
             ('0.930','%','0.930%'),('0.020','%','0.020%'),('1.250','%','1.250%')]]
        statement='For canonical SOL pools, the 0–420 SOL tier has creator 0.300%, protocol 0.930%, LP 0.020%, total 1.250%.'
        fact=self.validate(self.proposal('fees',statement,subject='swap',quote=row,quantities=quantities))
        self.assertEqual(len(fact['quantities']),6)
        with self.assertRaises(ValueError):
            self.validate(self.proposal('fees',statement.replace('1.250%','8%'),subject='swap',quote=row))
        self.assertIn('at most 16',rf.PROMPT_RULES)

    def test_B02_leading_decimal_accepts_equivalence_and_rejects_tenfold_error(self):
        quote='Some users may experience fee increases of up to .1% on certain transactions.'
        p=self.proposal('mobile',quote,quantities=[{'value':'0.1','unit':'%','literal':'.1%'}])
        self.assertEqual(self.validate(p)['quantities'][0]['value'],'0.1')
        with self.assertRaises(ValueError): self.validate({**p,'statement':quote.replace('.1%','1%')})
        self.assertEqual(rf._number_set('.1%'),rf._number_set('0.1%'))
        self.assertNotEqual(rf._number_set('.1%'),rf._number_set('1%'))

    def test_B04_token_rights_keep_token_subject_and_original_date_boundaries(self):
        quote='The $PUMP token does not represent a right to revenues or any other distribution.'
        fact=self.validate(self.proposal('token',quote,subject='token',topic='tokenomics'))
        self.assertEqual(fact['subject'],'$PUMP')
        text=rf.resolve_reference(self.ws,fact['evidence'][0])['context']
        self.assertIn('prior to April 29, 2026',text)
        self.assertIn('prior to April 28, 2026',self.blocks['announcement']['text'])

    def test_B05_B13_filters_do_not_discard_mixed_material_token_block(self):
        self.assertIn('Illustrative',source_gap(self.blocks['hypothetical']))
        self.assertIn('not price',source_gap(self.blocks['clickwrap']))
        self.assertIsNone(source_gap(self.blocks['token']))
        batches,_=rf._batch_blocks({'blocks':[self.blocks[n] for n in ('hypothetical','clickwrap','token')]})
        self.assertEqual({b['block_id'] for batch in batches for b in batch},{self.blocks['token']['block_id']})

    def test_B06_supported_label_correction_uses_only_two_calls(self):
        statement='The purchases of the $PUMP token contemplated herein may be effectuated by third parties.'
        p=self.proposal('announcement',statement)
        def labels(data): data['checks'][0]['question_ids']=['revenue-model.2']
        result,provider=self.run_batch([p],['announcement'],check_change=labels)
        self.assertEqual(len(provider.calls),2)
        self.assertEqual(result['accepted'][0]['statement'],statement)
        self.assertEqual(result['accepted'][0]['checked_question_ids'],['revenue-model.2'])
        self.assertIsNone(result['feedback'])

    def test_B07_same_document_sdk_alias_and_B08_intro_reference(self):
        scope={'subject':{'name':'Pump.fun','kind':'protocol','subject_id':'pump-fun'},'blocks':list(self.blocks.values())}
        subjects=rf._subjects(scope)
        sdk=next(k for k,v in subjects.items() if v['name']=='pump_rust_client')
        self.assertIn('pump-rust-client',subjects[sdk]['documented_aliases'])
        quote='`pump-rust-client` exposes an `idl-build` feature'
        self.validate(self.proposal('idl',quote,subject=sdk,topic='architecture'),subjects=subjects)
        subjects={'curve':{'name':'pump bonding curve program'}}
        quote='## These are 8 new fee recipients ( common for both programs )'
        fact=self.validate(self.proposal('recipients','The pump bonding curve program shares 8 new fee recipients with the other named program.',subject='curve',quote=quote),names=['intro','recipients'],subjects=subjects)
        self.assertEqual(len(fact['evidence']),2)
        self.assertIn(self.blocks['intro']['block_id'],{r['block_id'] for r in fact['evidence']})

    def test_B09_real_semantic_error_cannot_pass_on_a_valid_quote(self):
        p=self.proposal('decoding','The raw IDL type and wrapped state types both fail on legacy accounts.',subject='sdk',topic='architecture',quote='The raw IDL type does not, and will fail\non legacy accounts.')
        def reject(data): data['checks'][0].update(status='needs_qualification',context_preserved=False,reason='The original distinguishes raw IDL from zero-padding wrappers.')
        # The second response deliberately omits repair_of, so it cannot create
        # an unrelated branch or bypass the original semantic rejection.
        result,provider=self.run_batch([p],['decoding'],check_change=reject)
        self.assertFalse(result['accepted'])
        self.assertTrue(result['feedback'])
        self.assertLessEqual(len(provider.calls),4)

    def test_B10_reordered_duplicate_and_unrelated_repair_are_not_new_research(self):
        q="Your wrapper's `Accounts` struct must mirror pump's `BuyV2` account order\nexactly:"
        p=self.proposal('wrapper','The wrapper Accounts struct must mirror Pump BuyV2 account order exactly.',subject='program',topic='architecture',quote=q)
        other={**p,'statement':'The wrapper Accounts struct must exactly mirror Pump BuyV2 account order.'}
        result,provider=self.run_batch([p,other],['wrapper'])
        self.assertEqual(len(result['accepted']),1)
        self.assertEqual(len(payload(provider.calls[1],'PROPOSALS:')),1)

    def test_B11_noncontiguous_quote_restores_actual_intervening_lines(self):
        text=self.blocks['accounts']['text']
        proposed='## Bonding Curve\n- Buy instructions should have 18 accounts in total\n- Sell instruction should have 16 accounts for non cashback coins'
        repaired=repair_quote(text,proposed)
        self.assertIn('- Account needs to be mutable',repaired)
        self.assertIn(repaired,text)
        with self.assertRaises(ValueError): repair_quote(text,proposed.replace('18','19'))

    def test_B12_ambiguity_rejection_is_local_and_B14_image_gap_is_explicit(self):
        good=self.proposal('token','The $PUMP token does not represent a right to revenues or any other distribution.',subject='token')
        bad=self.proposal('token','Affiliated entities have no obligation to purchase tokens.',subject='token',quote='but are not under no obligation to do so.')
        def decide(data):
            data['checks'][1].update(status='unclear',context_preserved=False,reason='The double negative is ambiguous.')
        result,_=self.run_batch([good,bad],['token'],check_change=decide)
        self.assertEqual(len(result['accepted']),1)
        self.assertTrue(result['gaps'])
        self.assertIn('![Fee Tiers](fees.png)',self.blocks['image']['text'])
        self.assertIn('Image links',rf.PROMPT_RULES)

    def simple_workspace(self):
        ws=self.manager.create_project(name='Northstar',entity_type='chain')
        (ws.sources_directory/'core.md').write_text('# Northstar\nNorthstar uses validators in 2025.\n',encoding='utf-8')
        prepare_scope(ws)
        return ws

    def test_budget_stops_dispatch_publishes_partial_and_does_not_refill(self):
        ws=self.simple_workspace()
        (ws.sources_directory/'next.md').write_text('# Northstar\nNorthstar uses checkpoints.\n',encoding='utf-8')
        prepare_scope(ws)
        raw=FactFixture()
        path=ws.project_root/'budget-test.json'
        document,_=rf.collect_facts(ws,provider=BudgetProvider(raw,path,calls=2))
        self.assertEqual(len(raw.calls),2)
        self.assertEqual(len(document['facts']),1)
        self.assertEqual(document['preparation']['status'],'partial')
        again,_=rf.collect_facts(ws,provider=BudgetProvider(raw,path,calls=2))
        self.assertEqual(len(raw.calls),2)
        self.assertEqual(len(again['facts']),1)
        self.assertEqual(rf.retry_summary(ws)['unfinished_batches'],1)

    def test_character_time_and_cancellation_limits_dispatch_nothing(self):
        raw=FactFixture()
        provider=BudgetProvider(raw,self.ws.project_root/'char-budget.json',characters=3)
        with self.assertRaises(BudgetExceeded): provider.generate('too long')
        provider=BudgetProvider(raw,self.ws.project_root/'time-budget.json',seconds=1)
        with patch('definalyzer.operation_budget.time.monotonic',return_value=provider.started+2):
            with self.assertRaises(BudgetExceeded): provider.generate('x')
        event=threading.Event();event.set()
        with self.assertRaises(OperationCancelled),cancellation_scope(event): provider.generate('x')
        self.assertFalse(raw.calls)

    def test_selected_preparation_is_real_pipeline_and_does_not_touch_other_sources(self):
        ws=self.simple_workspace()
        other=ws.sources_directory/'sdk.md';other.write_text('# SDK\nUnrelated setup.\n',encoding='utf-8')
        class Prepared(FactFixture):
            def generate(inner,prompt,**kwargs):
                if prompt.startswith('Classify saved'):
                    inner.calls.append(prompt)
                    return ProviderResponse('{"decisions":[]}',inner.name,())
                return super().generate(prompt,**kwargs)
        provider=Prepared()
        result=prepare_research(ws,provider=provider,selected_paths=['core.md'])
        self.assertEqual(result['status'],'complete')
        self.assertEqual(len(provider.calls),3)
        self.assertFalse(any('Unrelated setup' in p for p in provider.calls))
        self.assertEqual(other.read_text(encoding='utf-8'),'# SDK\nUnrelated setup.\n')
        with self.assertRaises(ValueError): prepare_research(ws,provider=provider,selected_paths=['../core.md'])
        self.assertEqual(len(preparation_sources(ws)['sources']),2)

    def test_concise_report_and_question_use_two_calls_each_then_zero_on_reopen(self):
        ws=self.simple_workspace();rf.collect_facts(ws,provider=FactFixture())
        for mode in ('question','full_review'):
            record=create(ws,title=mode,mode=mode,question='How does consensus work?' if mode=='question' else None,depth='brief')
            provider=NarrativeProvider()
            result=generate(ws,record['report_id'],provider=provider)
            self.assertEqual(result['status'],'ready_to_review')
            self.assertEqual(len(provider.calls),2)
            saved=load_revision(ws,record['report_id'])
            self.assertTrue(saved['review.json']['passed'])
            generate(ws,record['report_id'],provider=provider)
            self.assertEqual(len(provider.calls),2)
            draft=copy.deepcopy(saved['draft.json'])
            text=' '.join([draft['assertions'][0]['text']]*100)
            draft['assertions'][0]['text']=text;draft['sections'][0]['blocks'][0]['text']=text
            with self.assertRaises(ValueError): validate_draft(draft,record,saved['evidence.json'])

    def test_current_price_has_no_provider_or_extraction_call(self):
        ws=self.simple_workspace();rf.collect_facts(ws,provider=FactFixture())
        record=create(ws,title='Price',mode='question',question='What is the price right now?',depth='brief')
        provider=NarrativeProvider()
        with patch('definalyzer.research_facts.collect_facts',side_effect=AssertionError('Reports must not extract')):
            result=generate(ws,record['report_id'],provider=provider)
        self.assertEqual(result['readiness'],'insufficient')
        self.assertFalse(provider.calls)

    def test_preparation_has_one_operation_lease(self):
        from definalyzer.app import _project_workflow_lock
        ws=self.simple_workspace()
        with _project_workflow_lock(ws), self.assertRaises(RuntimeError):
            prepare_research(ws,provider=FactFixture(),selected_paths=['core.md'])

    def test_dashboard_preparation_is_read_only_and_cannot_dispatch(self):
        import time
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        from definalyzer.dashboard import create_dashboard_server
        ws=self.simple_workspace()
        class Prepared(FactFixture):
            def generate(inner,prompt,**kwargs):
                if prompt.startswith('Classify saved'):
                    inner.calls.append(prompt)
                    return ProviderResponse('{"decisions":[]}',inner.name,())
                return super().generate(prompt,**kwargs)
        provider=Prepared()
        server=create_dashboard_server(self.manager,port=0)
        server.application._provider_factory=lambda _:provider
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base=f'http://127.0.0.1:{server.server_port}'
        def request(path,data=None,token=True):
            headers={'Content-Type':'application/json'}
            if token:headers['X-DEFINALYZER-Token']=server.token
            req=Request(base+path,data=None if data is None else json.dumps(data).encode(),headers=headers)
            with urlopen(req) as response:return json.load(response)
        plan=request('/api/projects/northstar/preparation')
        self.assertEqual(plan['sources'][0]['path'],'core.md')
        self.assertFalse(provider.calls)
        data={'action':'prepare-research','source_paths':['core.md']}
        with self.assertRaises(HTTPError) as rejected:
            request('/api/projects/northstar/jobs',data,token=False)
        self.assertEqual(rejected.exception.code,403)
        with self.assertRaises(HTTPError) as rejected:
            request('/api/projects/northstar/jobs',data)
        self.assertEqual(rejected.exception.code,400)
        self.assertFalse(provider.calls)
        self.assertEqual(server.jobs.list(), [])


if __name__ == '__main__': unittest.main()
