# Blockchain Collector Examples

`ethereum_weth_smoke_job.json` is a real-network smoke test for the raw
collector. It requests WETH9 runtime bytecode, native balance, and the raw
return value from the `totalSupply()` function selector.

The example does not decode results or verify a claim. Its address and source
are illustrative inputs; production jobs should use targets and provenance
exported from the protocol registry.

Set an Ethereum JSON-RPC endpoint in the project `.env` file:

```text
ETHEREUM_RPC_URL=https://your-ethereum-rpc-endpoint
```

Run the example from the project root:

```powershell
python -m blockchain_collector `
  examples/ethereum_weth_smoke_job.json `
  examples/ethereum_weth_smoke_evidence.json
```

The output path must not already exist. The collector will not replace prior
evidence.

`verification_requests_example.md` demonstrates the strict fenced JSON block
used to translate research verification requests into collection jobs. See
`blockchain_collector/VERIFICATION_IMPORT.md` for the importer contract and
commands.
