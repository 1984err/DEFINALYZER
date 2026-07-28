import unittest

from blockchain_collector.executor import (
    _evidence_is_partial,
    execute_collection_job,
)
from blockchain_collector.jobs import CollectionJob
from blockchain_collector.rpc import RpcEvidence, SUPPORTED_CHAINS


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


class FakeClient:
    def __init__(self, chain):
        self.chain = SUPPORTED_CHAINS[chain]
        self.validation_count = 0
        self.calls = []

    def validate_chain_id(self):
        self.validation_count += 1
        return self._evidence("eth_chainId", [], hex(self.chain.chain_id))

    def call(self, method, params):
        self.calls.append((method, params))

        if method == "eth_getBlockByNumber":
            return self._evidence(
                method,
                params,
                {"number": "0x100", "hash": "0x" + ("12" * 32)},
            )
        if method == "eth_getStorageAt":
            raise TimeoutError("node timed out")

        return self._evidence(method, params, "0x1234")

    def _evidence(self, method, params, result):
        return RpcEvidence(
            chain=self.chain.key,
            expected_chain_id=self.chain.chain_id,
            request_id=1,
            method=method,
            params=params,
            collected_at="2026-07-28T00:00:00+00:00",
            raw_response={"jsonrpc": "2.0", "id": 1, "result": result},
            result=result,
        )


def job_document():
    target = {
        "address": ADDRESS,
        "chain": "Ethereum",
        "source": "protocol-registry.md",
    }
    return {
        "schema_version": 1,
        "name": "executor-check",
        "requests": [
            {
                "name": "code",
                "chain": "ethereum",
                "operation": "get_code",
                "target": target,
            },
            {
                "name": "slot",
                "chain": "ethereum",
                "operation": "get_storage_at",
                "parameters": {"slot": 0},
                "target": target,
            },
            {
                "name": "balance",
                "chain": "ethereum",
                "operation": "get_balance",
                "target": target,
            },
        ],
    }


class ExecutorTests(unittest.TestCase):
    def test_detects_incomplete_chunked_evidence(self):
        self.assertTrue(
            _evidence_is_partial(
                "get_logs_chunked",
                {"complete": False, "chunks": []},
            )
        )
        self.assertTrue(
            _evidence_is_partial(
                "erc20_transfers",
                {"logs": {"complete": False, "chunks": []}},
            )
        )
        self.assertFalse(
            _evidence_is_partial(
                "erc20_transfers",
                {"logs": {"complete": True, "chunks": []}},
            )
        )

    def test_executes_requests_and_continues_after_failure(self):
        clients = {}

        def factory(chain):
            clients[chain] = FakeClient(chain)
            return clients[chain]

        bundle = execute_collection_job(
            CollectionJob.from_mapping(job_document()),
            job_source="job.json",
            client_factory=factory,
        )

        self.assertEqual(
            [record.status for record in bundle.records],
            ["collected", "failed", "collected"],
        )
        self.assertEqual(
            bundle.records[1].collection_error["stage"],
            "collection",
        )
        self.assertEqual(bundle.records[1].collection_error["type"], "TimeoutError")
        self.assertEqual(clients["ethereum"].validation_count, 1)
        self.assertEqual(bundle.job_source, "job.json")
        self.assertEqual(
            bundle.chain_snapshots["ethereum"]["rpc"]["result"]["number"],
            "0x100",
        )
        self.assertIn(
            ("eth_getCode", [ADDRESS, "0x100"]),
            clients["ethereum"].calls,
        )

    def test_chain_setup_failure_is_recorded_for_each_request(self):
        def failing_factory(chain):
            raise ValueError(f"missing endpoint for {chain}")

        bundle = execute_collection_job(
            CollectionJob.from_mapping(job_document()),
            client_factory=failing_factory,
        )

        self.assertEqual(len(bundle.records), 3)
        self.assertTrue(all(record.status == "failed" for record in bundle.records))
        self.assertTrue(
            all(
                record.collection_error["stage"] == "chain_setup"
                for record in bundle.records
            )
        )

    def test_rpc_error_remains_collected_raw_evidence(self):
        class RpcErrorClient(FakeClient):
            def call(self, method, params):
                if method == "eth_getBlockByNumber":
                    return self._evidence(
                        method,
                        params,
                        {"number": "0x100", "hash": "0x" + ("12" * 32)},
                    )
                return RpcEvidence(
                    chain=self.chain.key,
                    expected_chain_id=self.chain.chain_id,
                    request_id=1,
                    method=method,
                    params=params,
                    collected_at="2026-07-28T00:00:00+00:00",
                    raw_response={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "error": {"code": -32000, "message": "node error"},
                    },
                    error={"code": -32000, "message": "node error"},
                )

        bundle = execute_collection_job(
            CollectionJob.from_mapping(job_document()),
            client_factory=lambda chain: RpcErrorClient(chain),
        )

        self.assertEqual(bundle.records[0].status, "collected")
        self.assertEqual(
            bundle.records[0].evidence["rpc"]["error"]["code"],
            -32000,
        )


if __name__ == "__main__":
    unittest.main()
