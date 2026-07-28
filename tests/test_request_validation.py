import unittest

from blockchain_collector.request_validation import (
    PARAMETER_RULES,
    validate_operation_parameters,
)


class RequestValidationTests(unittest.TestCase):
    def test_every_supported_shape_accepts_its_minimum_parameters(self):
        minimums = {
            "contract_snapshot": {},
            "eip1967_slots": {},
            "erc20_snapshot": {},
            "erc20_transfers": {"from_block": 1, "to_block": 2},
            "get_balance": {},
            "get_block": {"block": 1},
            "get_code": {},
            "get_logs": {"from_block": 1, "to_block": 2},
            "get_logs_chunked": {"from_block": 1, "to_block": 2},
            "get_storage_at": {"slot": 0},
            "get_transaction": {"transaction_hash": "0x" + ("ab" * 32)},
            "get_transaction_receipt": {
                "transaction_hash": "0x" + ("ab" * 32)
            },
            "raw_call": {"data": "0x"},
            "standard_call": {"function": "totalSupply"},
        }

        self.assertEqual(set(minimums), set(PARAMETER_RULES))

        for operation, parameters in minimums.items():
            with self.subTest(operation=operation):
                validate_operation_parameters(operation, parameters)

    def test_rejects_missing_required_parameter(self):
        with self.assertRaisesRegex(ValueError, "transaction_hash"):
            validate_operation_parameters("get_transaction_receipt", {})

    def test_rejects_typo_in_parameter_name(self):
        with self.assertRaisesRegex(ValueError, "blok"):
            validate_operation_parameters("get_code", {"blok": "latest"})

    def test_rejects_parameter_not_used_by_operation(self):
        with self.assertRaisesRegex(ValueError, "topics"):
            validate_operation_parameters(
                "get_balance",
                {"topics": []},
            )

    def test_rejects_malformed_transaction_hash(self):
        with self.assertRaisesRegex(ValueError, "64 hexadecimal"):
            validate_operation_parameters(
                "get_transaction",
                {"transaction_hash": "0x1234"},
            )

    def test_rejects_invalid_block_and_raw_data_values(self):
        with self.assertRaisesRegex(ValueError, "block"):
            validate_operation_parameters("get_code", {"block": -1})

        with self.assertRaisesRegex(ValueError, "even-length"):
            validate_operation_parameters("raw_call", {"data": "0x123"})

    def test_validates_standard_function_and_arguments(self):
        validate_operation_parameters(
            "standard_call",
            {
                "function": "balanceOf",
                "arguments": [
                    "0x1234567890abcdef1234567890abcdef12345678"
                ],
            },
        )

        with self.assertRaisesRegex(ValueError, "requires 1"):
            validate_operation_parameters(
                "standard_call",
                {"function": "balanceOf", "arguments": []},
            )

    def test_rejects_bad_log_filter_shapes(self):
        with self.assertRaisesRegex(ValueError, "chunk_size"):
            validate_operation_parameters(
                "get_logs_chunked",
                {
                    "from_block": 1,
                    "to_block": 2,
                    "chunk_size": 0,
                },
            )

        with self.assertRaisesRegex(ValueError, "32-byte"):
            validate_operation_parameters(
                "get_logs",
                {
                    "from_block": 1,
                    "to_block": 2,
                    "topics": ["0x1234"],
                },
            )

    def test_rejects_invalid_snapshot_options(self):
        with self.assertRaisesRegex(ValueError, "boolean"):
            validate_operation_parameters(
                "contract_snapshot",
                {"include_owner_call": "yes"},
            )

        with self.assertRaisesRegex(ValueError, "balance_addresses"):
            validate_operation_parameters(
                "erc20_snapshot",
                {"balance_addresses": "0x1234"},
            )


if __name__ == "__main__":
    unittest.main()
