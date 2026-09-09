import copy
import json
from pathlib import Path
from unittest.mock import patch

from tests.test_research_facts import ResearchFactTests, FactFixture
from definalyzer import research_facts as rf
from definalyzer.source_quotes import original_quote
from definalyzer.research_scope import prepare_scope
from definalyzer.registry_workflow import TokenRecord, TOKEN_FIELDS, upsert_manual_token


class RealDocumentRegressionTests(ResearchFactTests):
    # Reuse workspace helpers, without duplicating the parent suite below.
    def test_readable_markdown_quote_resolves_original_text_and_preserves_negation(self):
        text='Northstar does **not** pay [token holders](https://docs.test/holders) (opens in a new tab)\n unless activated.'
        quote=original_quote(text,'Northstar does not pay token holders unless activated.')
        self.assertEqual(quote,text)
        for invented in ('Northstar does pay token holders unless activated.', 'Northstar pays token holders.'):
            with self.assertRaises(ValueError):original_quote(text,invented)
        with self.assertRaises(ValueError):original_quote('**No** fees. **No** fees.','No fees.')

    def test_quote_projection_is_saved_as_exact_original_evidence(self):
        fact,blocks,subjects=self.proposal()
        block=next(iter(blocks.values()))
        # Use a fresh snapshot containing actual Markdown, not synthetic locators.
        self.source('# Northstar\nNorthstar charges a [2% fee](https://docs.test/fees) only on withdrawals.\n')
        scope=prepare_scope(self.workspace)
        block=scope['blocks'][0]
        fact['evidence']=[{'block_id':block['block_id'],'quote':'Northstar charges a 2% fee only on withdrawals.'}]
        checked=rf.validate_proposal(self.workspace,fact,blocks={block['block_id']:block},subjects=rf._subjects(scope))
        self.assertIn('[2% fee]',checked['evidence'][0]['quote'])
        self.assertIn('only on withdrawals',rf.resolve_reference(self.workspace,checked['evidence'][0])['context'])

    def test_scope_uses_the_same_exact_original_quote_resolution(self):
        from definalyzer.research_scope import _validate
        text='Northstar requires [validators](https://docs.test/validators) only after activation.'
        decision={'relationship':'core','role':'conceptual','subjects':['Northstar'],'evidence':['Northstar requires validators only after activation.'],'applicability':{},'reason':'Explicit subject and condition'}
        result=_validate(decision,{'text':text})
        self.assertEqual(result['evidence'],[text])
        decision['evidence']=['Northstar requires validators.']
        with self.assertRaises(ValueError):_validate(decision,{'text':text})

    def test_bold_list_labels_do_not_consume_emphasis_or_conditions(self):
        text='  * **Up to 50% of total debt** only when both balances exceed the threshold.\n  * **Up to 100%** otherwise.\nOn _Ethereum mainnet_ only.'
        self.assertEqual(original_quote(text,'Up to 50% of total debt only when both balances exceed the threshold.'),'Up to 50% of total debt** only when both balances exceed the threshold.')
        self.assertIn('_Ethereum mainnet_',original_quote(text,'On Ethereum mainnet only.'))
        with self.assertRaises(ValueError):original_quote('field_name_value','fieldnamevalue')

    def test_explicit_retry_reuses_successes_retains_history_and_rejects_stale_request(self):
        self.source('# Northstar\nNorthstar uses validator consensus.\n','good.md')
        self.source('# Northstar\nNorthstar uses checkpoints.\n','unfinished.md')
        class Selective(FactFixture):
            def generate(inner,prompt,**kwargs):
                inner.reject='unfinished.md' in prompt
                return super().generate(prompt,**kwargs)
        doc,_=self.collect(Selective())
        self.assertEqual(len(doc['facts']),1)
        summary=rf.retry_summary(self.workspace)
        self.assertEqual(summary['unfinished_batches'],1)
        with patch.object(rf,'PROMPT_RULES',rf.PROMPT_RULES+'\nUpdated rules'):
            self.assertIsNone(rf.retry_summary(self.workspace))
            with self.assertRaisesRegex(ValueError,'reload'):
                rf.collect_facts(self.workspace,provider=FactFixture(),retry_failed=True,expected_revision=summary['revision'])
        before={p:p.read_bytes() for p in (self.workspace.project_root/'facts/batches').rglob('*') if p.is_file()}
        provider=FactFixture()
        recovered,usage=rf.collect_facts(self.workspace,provider=provider,retry_failed=True,expected_revision=summary['revision'])
        self.assertEqual(len(recovered['facts']),2)
        self.assertEqual(usage['provider_calls'],3)  # one extraction, support, and cross-document conflict check
        self.assertEqual(sum(p.startswith('# Original-source') for p in provider.calls),1)
        self.assertEqual(rf.retry_summary(self.workspace)['unfinished_batches'],0)
        for path,content in before.items():self.assertEqual(path.read_bytes(),content)
        with self.assertRaisesRegex(ValueError,'reload'):
            rf.collect_facts(self.workspace,provider=provider,retry_failed=True,expected_revision=summary['revision'])
        again,reuse=rf.collect_facts(self.workspace,provider=provider)
        self.assertEqual(reuse['provider_calls'],0)
        self.assertEqual(again['revision'],recovered['revision'])

    def test_saved_token_symbol_resolves_to_asset_without_importing_protocol_as_alias(self):
        workspace=self.manager.create_project(name='Luma Governance Token',entity_type='token')
        (workspace.sources_directory/'voting.md').write_text('# LUMA\nLUMA holders may vote. Luma Protocol earns fees.\n',encoding='utf-8')
        row={key:'Not documented' for key in TOKEN_FIELDS}
        row.update(name='Luma Governance Token',symbol='LUMA',source='https://docs.test/voting',token_type='Governance token',utility='Vote')
        upsert_manual_token(workspace=workspace,token=TokenRecord(**row))
        workspace=self.manager.load_project(workspace.slug)
        scope=prepare_scope(workspace)
        subjects=rf._subjects(scope)
        primary=subjects[scope['subject']['subject_id']]
        self.assertIn('LUMA',primary['documented_aliases'])
        self.assertNotIn('Luma Protocol',primary['documented_aliases'])
        self.assertIn(scope['subject']['subject_id'],rf._batch_subjects(subjects,scope['blocks']))


# Inherit the fixture helpers only; the original test class is collected once in
# its own module. This module adds independent regression scenarios.
for _name in dir(ResearchFactTests):
    if _name.startswith('test_'):
        setattr(RealDocumentRegressionTests,_name,None)
del ResearchFactTests
