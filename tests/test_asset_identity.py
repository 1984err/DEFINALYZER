import json
import tempfile
import unittest
import threading
from datetime import datetime, timezone
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from definalyzer import asset_identity as identity
from definalyzer.registry_workflow import (TokenRecord, TOKEN_FIELDS, project_tokens,
    upsert_manual_token, run_registry_workflow, registry_needs_token_discovery)
from definalyzer.workspace import WorkspaceManager
from definalyzer.providers import ProviderResponse
from definalyzer.market_data import market_snapshot_path
from definalyzer.report_contract import initialize_report_package, ReportRequest
from definalyzer.report_evidence import prepare_report_evidence, report_evidence_is_current


def token(name="Example Token", symbol="EX", address="0x" + "a" * 40, **extra):
    row = {field: "Not documented" for field in TOKEN_FIELDS}
    row.update(name=name, symbol=symbol, network="Ethereum", address=address,
               source="https://docs.example.test/token", token_type="Governance token",
               protocol_relationship="Governance of example", utility="Vote on parameters")
    row.update(extra)
    return TokenRecord(**row)


class Provider:
    name = "fixture"

    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def generate(self, prompt, *, working_directory):
        self.calls += 1
        return ProviderResponse(json.dumps({"tokens": [asdict(row) for row in self.rows]}), self.name, ())


class AssetIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manager = WorkspaceManager(Path(self.temp.name) / "output")
        self.workspace = self.manager.create_project(name="Example")

    def add(self, row=None, workspace=None):
        return upsert_manual_token(workspace=workspace or self.workspace, token=row or token())

    def test_supply_refresh_targets_one_asset_even_with_duplicate_tickers(self):
        from definalyzer.application import DefinalyzerApplication
        from definalyzer.market_data import refresh_market_data
        one = self.add(token(name="First", symbol="EX")).tokens[0]
        self.add(token(name="Second", symbol="EX", address="0x" + "b" * 40))
        sibling = next(row for row in project_tokens(self.workspace) if row.asset_id != one.asset_id)
        sibling_page = identity.asset_page(self.workspace, asdict(sibling), context=True)
        before = sibling_page.read_bytes()
        calls = []
        def fetch(url):
            calls.append(url)
            return {"id": "first", "name": "First", "symbol": "ex", "market_data": {"total_supply": 123}}
        with patch("definalyzer.market_data._fetch_json_with_backoff", side_effect=lambda url, **kwargs: fetch(url)):
            result = DefinalyzerApplication(self.manager).refresh_market_data(
                workspace=self.workspace, asset_id=one.asset_id, force=True)
        self.assertEqual(len(calls), 1)
        self.assertIn("0x" + "a" * 40, calls[0])
        self.assertEqual(len(result.token_pages), 1)
        self.assertEqual(sibling_page.read_bytes(), before)
        self.assertFalse(market_snapshot_path(self.workspace, sibling.symbol, asset_id=sibling.asset_id).exists())
        with self.assertRaisesRegex(ValueError, "not registered"):
            refresh_market_data(workspace=self.workspace, asset_id="f" * 32, fetch_json=fetch)
        self.assertEqual(len(calls), 1)

    def test_ticker_collisions_within_and_across_projects_are_distinct(self):
        one = self.add().tokens[0]
        self.add(token("Unrelated asset", address="0x" + "b" * 40))
        rows = project_tokens(self.workspace)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({r.asset_id for r in rows}), 2)
        other = self.manager.create_project(name="Other")
        three = self.add(token("Another asset", address="0x" + "c" * 40), other).tokens[0]
        self.assertNotEqual(one.asset_id, three.asset_id)
        self.assertNotEqual(market_snapshot_path(self.workspace, "EX", asset_id=rows[0].asset_id),
                            market_snapshot_path(self.workspace, "EX", asset_id=rows[1].asset_id))

    def test_shared_asset_has_independent_contexts_and_no_parent_status(self):
        one = self.add().tokens[0]
        other = self.manager.create_project(name="Other", verification_status="supported")
        two = self.add(token(utility="Different project description"), other).tokens[0]
        self.assertEqual(one.asset_id, two.asset_id)
        first = identity.asset_page(self.workspace, asdict(one), context=True)
        second = identity.asset_page(other, asdict(two), context=True)
        self.assertNotEqual(first, second)
        self.assertIn("Vote on parameters", first.read_text())
        self.assertIn("Different project description", second.read_text())
        self.assertNotIn('verification_status: "supported"', second.read_text())
        self.assertEqual(len(identity.inventory(self.manager.root)), 1)
        self.manager.delete_project(other)
        self.assertTrue(first.exists())
        self.assertTrue(identity.asset_page(self.workspace, asdict(one)).exists())
        self.assertEqual(identity.inventory(self.manager.root)[0]["projects"], ["example"])

    def test_manual_rename_retains_id_path_and_alias(self):
        row = self.add().tokens[0]
        before = identity.asset_page(self.workspace, asdict(row))
        updated = self.add(replace(row, name="Renamed asset")).tokens[0]
        self.assertEqual(row.asset_id, updated.asset_id)
        self.assertEqual(before, identity.asset_page(self.workspace, asdict(updated)))
        entry = identity.inventory(self.manager.root)[0]
        self.assertEqual(entry["title"], "Renamed asset (EX)")
        self.assertIn("Example Token", entry["aliases"])

    def test_coin_classification_is_independent_of_parent_project(self):
        chain = self.manager.create_project(name="Chain", entity_type="chain")
        native = token("Native", "NAT", "Not applicable", token_type="Native coin", network="Chain")
        self.add(native, chain)
        self.add(token("Application", "APP"), chain)
        by_name = {row["name"]: row for row in identity.inventory(self.manager.root)}
        self.assertEqual(by_name["Native"]["kind"], "coin")
        self.assertEqual(by_name["Application"]["kind"], "token")

    def test_case_sensitive_addresses_and_cross_chain_deployments_do_not_merge(self):
        a = {"network": "Solana", "address": "Abc"}
        b = {"network": "Solana", "address": "abc"}
        self.assertNotEqual(identity.deployment_key(a), identity.deployment_key(b))
        one = self.add().tokens[0]
        other = self.manager.create_project(name="Other")
        two = self.add(token(network="Base"), other).tokens[0]
        self.assertNotEqual(one.asset_id, two.asset_id)
        explicit = replace(one, network="Base", address="0x" + "b" * 40)
        self.add(explicit)
        catalog = identity.load_catalog(self.manager.root)
        self.assertEqual(len(catalog["entities"][one.asset_id]["deployments"]), 2)

    def test_user_edits_are_preserved_with_proposed_regeneration(self):
        result = self.add()
        page = result.token_pages[0]
        page.write_text(page.read_text() + "\nMy handwritten research.\n")
        saved = page.read_bytes()
        self.add(replace(result.tokens[0], utility="Updated source mechanics"))
        self.assertEqual(page.read_bytes(), saved)
        self.assertTrue(list(page.parent.glob("*.proposed.md")))

    def test_new_source_rediscovers_and_preserves_manual_values(self):
        manual = self.add().tokens[0]
        page = self.workspace.vault_entity_directory / "Tokenomics.md"
        page.write_text("# Tokenomics\n\nEX governs this protocol.\n")
        provider = Provider([token(utility="AI must not replace manual text"), token("New asset", "NEW", "0x" + "c" * 40)])
        result = run_registry_workflow(workspace=self.workspace, provider=provider)
        self.assertEqual(len(result.tokens), 2)
        self.assertEqual(next(r for r in result.tokens if r.asset_id == manual.asset_id).utility, manual.utility)
        self.assertFalse(registry_needs_token_discovery(self.workspace))
        run_registry_workflow(workspace=self.workspace, provider=provider)
        self.assertEqual(provider.calls, 1)
        source = self.workspace.sources_directory / "new.md"
        source.write_text("# New token information\n")
        self.assertTrue(registry_needs_token_discovery(self.workspace))
        provider.rows = []
        result = run_registry_workflow(workspace=self.workspace, provider=provider)
        self.assertEqual(len(result.tokens), 2)  # Omission is not deletion.
        self.assertEqual(provider.calls, 2)

    def make_legacy(self):
        registry = self.workspace.registry_directory / "registry.json"
        registry.write_text(json.dumps({"tokens": [asdict(token())], "addresses": []}))
        page = self.workspace.vault_root / "Tokens" / "EX" / "Index.md"
        page.parent.mkdir(parents=True)
        page.write_text('---\nparent_protocol: "Example"\nentity_type: "token"\n---\n\n# EX\n\nFees accrue to suppliers.\n')
        return registry, page

    def test_migration_is_additive_idempotent_and_preserves_legacy_report_scope(self):
        registry, page = self.make_legacy()
        self.workspace.vault_entity_directory.joinpath("Revenue.md").write_text("# Revenue\n\nFees accrue to suppliers.\n")
        initialize_report_package(workspace=self.workspace,
            request=ReportRequest(title="Revenue", mode="question", question="Who receives fees?"))
        prepare_report_evidence(workspace=self.workspace, report_id="revenue")
        original = {p: p.read_bytes() for p in self.manager.root.rglob("*") if p.is_file()}
        plan = identity.migrate_assets(self.manager)
        self.assertEqual(plan["assets"], 1)
        self.assertFalse((self.manager.root / "entities").exists())
        identity.migrate_assets(self.manager, preview=False)
        before = identity.load_catalog(self.manager.root)
        identity.migrate_assets(self.manager, preview=False)
        self.assertEqual(before, identity.load_catalog(self.manager.root))
        for path, data in original.items():
            self.assertEqual(path.read_bytes(), data, path)
        self.assertTrue(report_evidence_is_current(workspace=self.workspace, report_id="revenue"))
        self.assertTrue(list((self.manager.root / "entities/history").glob("*/transaction.json")))

    def test_interrupted_migration_recovers_same_ids(self):
        self.make_legacy()
        atomic = identity._atomic
        def fail_catalog(path, text):
            if path.name == "catalog.json":
                raise OSError("simulated process stop")
            return atomic(path, text)
        with patch.object(identity, "_atomic", side_effect=fail_catalog):
            with self.assertRaises(OSError):
                identity.migrate_assets(self.manager, preview=False)
        pending = json.loads((self.manager.root / "entities/pending.json").read_text())
        planned = json.loads(pending["writes"][-1]["text"])
        identity.migrate_assets(self.manager, preview=False)
        self.assertEqual(set(planned["entities"]), set(identity.load_catalog(self.manager.root)["entities"]))
        self.assertFalse((self.manager.root / "entities/pending.json").exists())

    def test_editing_a_migrated_asset_does_not_duplicate_the_legacy_registry_row(self):
        self.make_legacy()
        identity.migrate_assets(self.manager, preview=False)
        original = project_tokens(self.workspace)[0]
        self.assertTrue(original.asset_id)
        edited = replace(original, name="Renamed migrated asset", address="0x" + "b" * 40)
        result = self.add(edited)
        self.assertEqual(len(result.tokens), 1)
        self.assertEqual(result.tokens[0].asset_id, original.asset_id)
        self.assertEqual(identity.inventory(self.manager.root)[0]["name"], edited.name)

    def test_uncertain_legacy_owner_is_not_copied_into_another_project(self):
        registry, page = self.make_legacy()
        page.write_text('---\nparent_protocol: "Someone Else"\n---\n# EX\nSecret other project research\n')
        result = identity.migrate_assets(self.manager, preview=False)
        context = identity.project_asset_pages(self.workspace)[0].read_text()
        self.assertNotIn("Secret other project", context)
        self.assertIn("ownership could not be established", context)
        self.assertTrue(result["notes"])

    def test_research_this_asset_is_idempotent_and_does_not_start_analysis(self):
        row = self.add().tokens[0]
        workspace = identity.start_asset_research(self.manager, row.asset_id)
        again = identity.start_asset_research(self.manager, row.asset_id)
        self.assertEqual(workspace.slug, again.slug)
        self.assertEqual(workspace.document["subject_id"], row.asset_id)
        self.assertEqual(workspace.document["entity_type"], "token")
        self.assertEqual(workspace.document["stages"]["crawl"]["status"], "not_started")
        self.assertFalse([p for p in workspace.sources_directory.glob("*.md") if not p.name.startswith("_")])
        self.assertEqual(len(identity.inventory(self.manager.root)), 1)
        self.assertEqual(identity.inventory(self.manager.root)[0]["subject_projects"], [workspace.slug])

    def test_unrelated_id_and_path_traversal_are_rejected(self):
        row = self.add().tokens[0]
        other = self.manager.create_project(name="Other")
        with self.assertRaises(ValueError):
            self.add(row, other)
        with self.assertRaises(ValueError):
            identity.safe_path(self.manager.root, "../escape")

    def test_changed_deployment_cannot_display_old_cached_supply(self):
        from definalyzer.market_data import _unavailable_snapshot, _snapshot_matches_contract, load_market_snapshot
        row = self.add().tokens[0]
        snapshot = _unavailable_snapshot(symbol=row.symbol, network="Ethereum", address=row.address,
            platform_id="ethereum", collected_at=datetime.now(timezone.utc), detail="fixture")
        path = market_snapshot_path(self.workspace, row.symbol, asset_id=row.asset_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(snapshot)))
        self.assertIsNotNone(load_market_snapshot(self.workspace, row.symbol))
        self.add(replace(row, address="0x" + "b" * 40))
        self.assertIsNone(load_market_snapshot(self.workspace, row.symbol, asset_id=row.asset_id))
        self.assertFalse(_snapshot_matches_contract(replace(snapshot, network="Solana", contract_address="AbC"), "Solana", "abc"))

    def test_concurrent_project_registry_writer_is_rejected_without_mutation(self):
        entered, release = threading.Event(), threading.Event()
        failures = []
        @identity.registry_writer
        def holding(*, workspace):
            entered.set()
            release.wait(5)
        def run():
            try:
                holding(workspace=self.workspace)
            except Exception as exc:
                failures.append(exc)
        worker = threading.Thread(target=run)
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            with self.assertRaisesRegex(RuntimeError, "Another registry operation"):
                self.add()
            self.assertFalse((self.workspace.registry_directory / "registry.json").exists())
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(failures)
        self.assertEqual(len(self.add().tokens), 1)


if __name__ == "__main__":
    unittest.main()
