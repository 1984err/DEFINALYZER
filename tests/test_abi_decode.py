import unittest

from blockchain_collector.abi_decode import decode_outputs


class AbiDecodeTests(unittest.TestCase):
    def test_decodes_uint_as_decimal_text(self):
        raw = "0x" + (123456789).to_bytes(32, "big").hex()

        self.assertEqual(decode_outputs(raw, ["uint256"]), ["123456789"])

    def test_decodes_address(self):
        address = "abcdefabcdefabcdefabcdefabcdefabcdefabcd"
        raw = "0x" + ("00" * 12) + address

        self.assertEqual(decode_outputs(raw, ["address"]), ["0x" + address])

    def test_decodes_dynamic_string(self):
        offset = (32).to_bytes(32, "big")
        text = b"Wrapped Ether"
        length = len(text).to_bytes(32, "big")
        padding = bytes(32 - len(text))
        raw = "0x" + (offset + length + text + padding).hex()

        self.assertEqual(decode_outputs(raw, ["string"]), ["Wrapped Ether"])

    def test_rejects_truncated_result(self):
        with self.assertRaisesRegex(ValueError, "shorter"):
            decode_outputs("0x01", ["uint256"])


if __name__ == "__main__":
    unittest.main()
