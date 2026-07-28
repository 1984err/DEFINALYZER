# Verification Opportunities

The table or prose used by an analyst can remain above this block. The
collector importer reads only the explicitly tagged JSON below.

```definalyzer-verification
{
  "schema_version": 1,
  "name": "ethereum-weth-verification",
  "requests": [
    {
      "id": "weth-token-snapshot",
      "claim": "Example claim retained as context for a later evaluation agent.",
      "why_verify": "Example materiality explanation.",
      "chain": "ethereum",
      "operation": "erc20_snapshot",
      "parameters": {
        "block": "latest",
        "balance_addresses": []
      },
      "target": {
        "target_name": "Wrapped Ether",
        "role": "wrapped native token",
        "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "chain": "Ethereum",
        "chain_id": 1,
        "source": "https://etherscan.io/token/0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
      }
    }
  ]
}
```
