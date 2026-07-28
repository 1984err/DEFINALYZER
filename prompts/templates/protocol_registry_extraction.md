# Protocol Registry Extraction

## Objective

Create a normalized, source-proven inventory of addresses, deployments,
identifiers, relationships, and technical references required for later
verification.

This registry is comprehensive infrastructure data, not an analysis page.
Do not infer behavior or repeat the same address-role record across sections.

## Rules

- Use only the supplied documentation.
- Preserve addresses and identifiers exactly as documented.
- Record chain and source provenance for every address.
- Preserve separate rows when one address has multiple documented roles.
- Preserve historical, replaced, and deprecated deployments.
- Do not guess missing chain IDs, blocks, transactions, or relationships.
- Use **Not documented** and **Unable to determine** only in required fields.
- Output only the registry.

# Protocol Registry

## Protocol

| Field | Value |
|---|---|
| Protocol | |
| Version or deployment generation | |
| Category | |
| Documentation root | |
| Source repository | |
| Deployment/address repository | |

## Chains

| Chain | Chain ID | Network | Deployment Start Block | Explorer | Status | Source |
|---|---:|---|---:|---|---|---|

## Address Inventory

| Type | Name | Role | Address | Chain | Deployment Block | Deployment Transaction | Status | Source |
|---|---|---|---|---|---:|---|---|---|

Use a controlled `Type` where possible:

- Core contract
- Proxy
- Implementation
- Proxy admin
- Beacon
- Token
- Vault
- Pool
- Market
- Router
- Factory
- Oracle
- Treasury or fee destination
- Governance
- Administrative role
- Security or recovery
- Staking or rewards
- Bridge or cross-chain
- External dependency
- Historical or deprecated

Do not add a second row merely because the address appears in another
documentation section. Add a second row only for a distinct documented role,
chain deployment, or historical state.

## Upgrade Topology

| Proxy or Upgradeable Component | Proxy Address | Implementation or Beacon | Admin or Upgrade Authority | Pattern | Chain | Effective Block | Status | Source |
|---|---|---|---|---|---|---:|---|---|

## Token Configuration

| Token | Address | Chain | Supply or Mint Authority | Burn Mechanism or Destination | Vesting or Lock Contract | Deployment Block | Source |
|---|---|---|---|---|---|---:|---|

Record only addresses and configuration references needed to collect evidence.
Token economics belong in the Tokenomics page.

## Critical Configuration Components

| Component | Address | Chain | Configuration Role | Controlled or Read By | Deployment Block | Source |
|---|---|---|---|---|---:|---|

Include material oracle, collateral, liquidation, fee, governance, pause,
bridge, and role-management configuration components.

## Cross-Chain Mapping

| Local Component | Local Address | Local Chain | Remote Component | Remote Address or Identifier | Remote Chain | Relationship | Source |
|---|---|---|---|---|---|---|---|

## Contract Relationships

| From Component | From Address | Relationship | To Component | To Address or Identifier | Chain | Source |
|---|---|---|---|---|---|---|

Record only relationships useful for understanding control, calls, upgrades,
creation, routing, custody, fee flow, rewards, oracle reads, settlement, or
bridging.

## Relevant Events and Functions

| Component | Address | Chain | Event or Function | Signature or Topic | Verification Use | Source |
|---|---|---|---|---|---|---|

Include only references likely to support a material verification request.

## ABI and Source References

| Component | Address | Chain | ABI | Verified Source | Repository Path | Compiler | Source |
|---|---|---|---|---|---|---|---|

## External Identifiers

| Provider or System | Component or Market | Identifier | Chain | Purpose | Source |
|---|---|---|---|---|---|

Include non-address oracle feed IDs, market IDs, pool IDs, deployment IDs, and
other identifiers needed for evidence collection.

## Material Missing Registry Data

| Component | Missing or Conflicting Field | Status | Source |
|---|---|---|---|

Only record missing data that blocks or weakens a material verification
request.
