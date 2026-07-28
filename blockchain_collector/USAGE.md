# Blockchain Collector Usage

The collector gathers raw EVM evidence. It does not determine whether a claim
is true, classify a contract, or update research notes.

## Configure RPC endpoints

Copy `.env.example` to `.env` and add the endpoints you use:

```text
ETHEREUM_RPC_URL=https://your-ethereum-endpoint
ARBITRUM_RPC_URL=https://your-arbitrum-endpoint
BASE_RPC_URL=https://your-base-endpoint
```

Only chains referenced by a job require an endpoint.

## Run a job

From the project root:

```powershell
python -m blockchain_collector path\to\job.json path\to\evidence.json
```

The evidence path must not already exist. The collector never overwrites an
earlier evidence file.

## Guided human use

Run the interactive menu from the project root:

```powershell
python -m blockchain_collector.menu
```

The menu currently guides contract snapshots, ERC-20 token snapshots,
ERC-1967 proxy-slot checks, chunked ERC-20 transfer history, and readable
standard contract calls. It can also collect a raw transaction and receipt
from one transaction hash. The second menu workflow imports structured
verification requests from a Markdown or JSON file, runs the supported rows,
and saves ambiguous or unsupported rows in an import report for manual review.
It saves generated jobs under `jobs/` and results under `evidence/`. Generated
job, evidence, report, and summary files are not overwritten if the same job
name is used again.

For guided runs, the evidence folder contains both the authoritative raw JSON
and a shorter Markdown summary intended for human reading. The summary reports
collected values and completeness only; it does not verify the research claim.

## Machine-readable capabilities

Agents and external interfaces can inspect the current scanner contract with:

```powershell
python -m blockchain_collector.capabilities
```

The JSON output lists supported chains, operations, required and optional
parameters, standard functions, schema versions, result statuses, and launch
commands.

## Job structure

```json
{
  "schema_version": 1,
  "name": "unique-job-name",
  "metadata": {
    "research_page": "optional source context"
  },
  "requests": [
    {
      "name": "unique-request-name",
      "chain": "ethereum",
      "operation": "contract_snapshot",
      "parameters": {},
      "target": {
        "target_name": "Documented component name",
        "role": "Documented role",
        "address": "0x0000000000000000000000000000000000000000",
        "chain": "Ethereum",
        "chain_id": 1,
        "source": "URL or registry document"
      }
    }
  ]
}
```

Supported chain keys are `ethereum`, `arbitrum`, and `base`.

## Operations

### `contract_snapshot`

Collects runtime code, native balance, ERC-1967 slots, and optionally the
common `owner()` call.

```json
"parameters": {
  "block": "latest",
  "include_owner_call": true
}
```

### `erc20_snapshot`

Collects `name`, `symbol`, `decimals`, `totalSupply`, and optional balances.

```json
"parameters": {
  "block": "latest",
  "balance_addresses": ["0x..."]
}
```

### `erc20_transfers`

Collects and mechanically decodes ERC-20 `Transfer` logs in bounded chunks.
Sender and recipient filters are optional.

```json
"parameters": {
  "from_block": 19000000,
  "to_block": "latest",
  "chunk_size": 2000,
  "from_address": "0x...",
  "to_address": "0x..."
}
```

### `eip1967_slots`

Collects implementation, admin, and beacon storage slots.

```json
"parameters": {
  "block": "latest"
}
```

### `standard_call`

Supported functions are `totalSupply`, `balanceOf`, `allowance`, `owner`,
`name`, `symbol`, and `decimals`.

```json
"parameters": {
  "function": "balanceOf",
  "arguments": ["0x..."],
  "block": "latest"
}
```

### Raw operations

- `get_code`: optional `block`
- `get_balance`: optional `block`
- `get_storage_at`: required `slot`, optional `block`
- `raw_call`: required `data`, optional `value` and `block`
- `get_transaction`: required `transaction_hash`
- `get_transaction_receipt`: required `transaction_hash`
- `get_block`: required `block`, optional `full_transactions`
- `get_logs`: required `from_block` and `to_block`; optional `address` and
  `topics`
- `get_logs_chunked`: required `from_block` and `to_block`; optional
  `chunk_size` and `topics`

Block numbers may be decimal integers or `0x` quantities. Read operations
using `latest` are pinned to one recorded block per chain for consistency.

## Evidence boundaries

Evidence contains raw RPC requests and responses, timestamps, chain and block
context, registry provenance, mechanical decoding, and collection errors.

Mechanical decoding is not verification. A nonzero admin slot, a transfer to
an address, or a returned supply value requires later analysis in the context
of the specific documented claim.

See `MVP_STATUS.md` for the verified first-version boundary and deferred scope.
See `VERIFICATION_IMPORT.md` for the strict request format that connects
research output to collector jobs.
