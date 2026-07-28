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
            "get_transaction": {"transaction_hash": "0x"},
            "get_transaction_receipt": {"transaction_hash": "0x"},
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


if __name__ == "__main__":
    unittest.main()
