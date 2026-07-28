# Protocol Registry Extraction Prompt

## Objective

Extract every documented address, identifier, deployment detail, relationship, and data source required by the verification system.

This is a structured inventory task.

Do not analyze protocol behavior.

---

## Rules

- Use only the supplied documentation.
- Do not use prior knowledge.
- Do not guess or infer missing values.
- Preserve addresses exactly as documented.
- Preserve contract and component names exactly as documented.
- Record the source URL or document for every extracted item.
- Record the chain for every address.
- Record the deployment block when documented.
- Record historical, replaced, deprecated, and upgraded contracts.
- Do not omit duplicate addresses used for different roles.
- Use **Not documented** for missing values.
- Use **Unable to determine** when documentation is conflicting or unclear.
- Output only the registry.
- Do not include explanations, purpose statements, examples, or commentary.

---

# Protocol Registry

## Protocol

| Field | Value |
|---|---|
| Protocol Name | |
| Protocol Version | |
| Protocol Category | |
| Supported Chains | |
| Native Token | |
| Documentation URL | |
| Source Repository | |
| Deployment Repository | |
| Contract Address Repository | |

---

## Chain Deployments

| Chain | Chain ID | Network | Deployment Start Block | Deployment Date | Explorer URL | Status | Source |
|---|---:|---|---:|---|---|---|---|

---

## Core Contracts

| Name | Role | Address | Chain | Deployment Block | Deployment Transaction | Status | Source |
|---|---|---|---|---:|---|---|---|

Include all core protocol contracts, including:

- main protocol contract
- exchange
- clearinghouse
- settlement contract
- accounting contract
- lending contract
- borrowing contract
- collateral manager
- liquidation contract
- vault manager
- market manager
- pool manager
- router
- factory
- registry
- controller
- coordinator

---

## Proxy and Upgrade Information

| Proxy Name | Proxy Address | Implementation Address | Admin Address | Proxy Type | Chain | Deployment Block | Status | Source |
|---|---|---|---|---|---|---:|---|---|

Record:

- proxy contracts
- implementation contracts
- proxy administrators
- beacon contracts
- upgrade managers
- previous implementations
- current implementations

---

## Tokens

| Name | Symbol | Address | Chain | Decimals | Token Type | Role | Deployment Block | Status | Source |
|---|---|---|---|---:|---|---|---:|---|---|

Include:

- native protocol token
- governance token
- reward token
- staking token
- receipt token
- vault share token
- liquidity token
- debt token
- collateral token
- wrapped token
- bridged token
- supported settlement assets

---

## Token Supply and Burn Configuration

| Token | Address | Chain | Mint Authority | Burn Function | Burn Event | Zero-Address Burns | Additional Burn Addresses | Supply Source | Deployment Block | Source |
|---|---|---|---|---|---|---|---|---|---:|---|

Record:

- documented burn addresses
- zero address usage
- dead addresses
- burn contracts
- supply controller addresses
- minter addresses
- token migration contracts
- old token contracts
- replacement token contracts

---

## Vaults

| Name | Address | Chain | Asset | Share Token | Strategy | Controller | Deployment Block | Status | Source |
|---|---|---|---|---|---|---|---:|---|---|

---

## Pools

| Name | Address | Chain | Pool Type | Assets | LP Token | Factory | Deployment Block | Status | Source |
|---|---|---|---|---|---|---|---:|---|---|

---

## Markets

| Name | Address | Chain | Market Type | Base Asset | Quote Asset | Collateral Asset | Settlement Asset | Deployment Block | Status | Source |
|---|---|---|---|---|---|---|---|---:|---|---|

---

## Routers and Factories

| Name | Role | Address | Chain | Creates or Routes To | Deployment Block | Status | Source |
|---|---|---|---|---|---:|---|---|

---

## Oracles and Price Feeds

| Name | Provider | Address | Chain | Asset or Market | Feed Identifier | Quote Currency | Update Method | Fallback Oracle | Deployment Block | Status | Source |
|---|---|---|---|---|---|---|---|---|---:|---|---|

Include:

- oracle contracts
- price feed contracts
- sequencer uptime feeds
- fallback oracles
- TWAP sources
- off-chain feed identifiers
- external market identifiers

---

## Treasury and Fee Destinations

| Name | Role | Address | Chain | Asset | Fee Type | Deployment Block | Status | Source |
|---|---|---|---|---|---|---:|---|---|

Include:

- treasury
- fee collector
- protocol revenue wallet
- insurance fund
- reserve fund
- ecosystem fund
- reward distributor
- buyback contract
- burn destination

---

## Governance

| Name | Role | Address | Chain | Governance Token | Deployment Block | Status | Source |
|---|---|---|---|---|---:|---|---|

Include:

- governor
- timelock
- proposal executor
- voting contract
- delegation contract
- governance treasury
- guardian
- emergency council

---

## Administration and Permissions

| Name | Address | Chain | Permission or Role | Controlled Contract | Multisig Threshold | Deployment Block | Status | Source |
|---|---|---|---|---|---|---:|---|---|

Include:

- owner
- administrator
- operator
- guardian
- pauser
- upgrader
- minter
- burner
- liquidator
- keeper
- relayer
- multisig
- role manager

---

## Security and Recovery Components

| Name | Role | Address | Chain | Protected Component | Deployment Block | Status | Source |
|---|---|---|---|---|---:|---|---|

Include:

- security module
- insurance module
- emergency shutdown
- pause controller
- recovery contract
- bad-debt handler
- liquidation backstop
- reserve manager

---

## Staking and Rewards

| Name | Role | Address | Chain | Staked Asset | Reward Asset | Distributor | Deployment Block | Status | Source |
|---|---|---|---|---|---|---|---:|---|---|

---

## Bridges and Cross-Chain Components

| Name | Role | Address | Chain | Connected Chain | Remote Address | Token | Deployment Block | Status | Source |
|---|---|---|---|---|---|---|---:|---|---|

Include:

- bridge contracts
- canonical token bridges
- mint-and-burn bridges
- lock-and-mint bridges
- cross-chain messengers
- remote executors
- remote token addresses

---

## External Protocol Dependencies

| Protocol | Component | Address | Chain | Dependency Type | Purpose | Required for Operation | Source |
|---|---|---|---|---|---|---|---|

Include:

- oracle providers
- DEXs
- lending protocols
- bridges
- stablecoins
- settlement systems
- custody systems
- staking systems
- automation networks
- keeper networks

---

## Contract Relationships

| From Component | From Address | Relationship | To Component | To Address | Chain | Source |
|---|---|---|---|---|---|---|

Record documented relationships such as:

- calls
- controls
- upgrades
- creates
- routes through
- receives fees from
- sends rewards to
- reads prices from
- supplies liquidity to
- borrows from
- settles through
- bridges to

---

## Historical and Deprecated Components

| Name | Role | Address | Chain | Replaced By | Active From Block | Active Until Block | Deprecation Reason | Source |
|---|---|---|---|---|---:|---:|---|---|

---

## Event and Function References

| Component | Address | Chain | Event or Function | Purpose | Signature or Topic | Source |
|---|---|---|---|---|---|---|

Record documented events and functions relevant to verification, including:

- mint
- burn
- transfer
- deposit
- withdraw
- borrow
- repay
- liquidate
- collect fees
- distribute rewards
- update oracle
- pause
- unpause
- upgrade

---

## ABI and Source-Code References

| Component | Address | Chain | ABI URL | Verified Source URL | Repository Path | Compiler Version | Source |
|---|---|---|---|---|---|---|---|

---

## Verification Targets

| Target Name | Address | Chain | Role | Deployment Block | Verification Purpose | Required Related Addresses | Source |
|---|---|---|---|---:|---|---|---|

Include every address that may need to be passed into the scanner.

---

## Missing Information

| Component | Missing Field | Status | Source |
|---|---|---|---|

Use only:

- Not documented
- Unable to determine
- Conflicting documentation