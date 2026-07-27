# Integrations & Dependencies

## Purpose
> TEMPLATE INSTRUCTION ONLY — DO NOT INCLUDE THIS SECTION IN THE OUTPUT.

Extract and classify documented information describing the protocol's integrations, dependencies, and external relationships.

Focus on what external systems the protocol relies on, communicates with, or integrates with to function.

Do not analyze tokenomics, governance, security, or protocol architecture except where necessary to explain an integration.

---

## Scope
> TEMPLATE INSTRUCTION ONLY — DO NOT INCLUDE THIS SECTION IN THE OUTPUT.

Extract only documented information that answers the following questions:

- What protocols does this protocol integrate with?
- What infrastructure does it depend on?
- What external services are required?
- Which dependencies are optional versus required?
- How do external systems interact with the protocol?
- What assumptions are made about those dependencies?
- What risks are introduced by external dependencies?

Do not include:

- Internal protocol components
- Governance relationships
- Token partnerships
- Marketing partnerships
- Community collaborations
- Speculative future integrations

---

# Facts

## Integration Overview

Extract:

- Overall integration strategy
- Primary external relationships
- Purpose of integrations

---

## Protocol Integrations

For each documented protocol integration:

| Protocol | Purpose | Required | Notes |
|----------|---------|----------|-------|

Only include documented integrations.

---

## Infrastructure Dependencies

For each documented infrastructure dependency:

| Dependency | Purpose | Required | Notes |
|------------|---------|----------|-------|

Examples include:

- RPC providers
- Indexers
- Sequencers
- Relayers
- Validators
- Blockchains
- Messaging layers

Only include documented dependencies.

---

## Oracle Dependencies

For each documented oracle:

| Oracle | Purpose | Required | Notes |
|--------|---------|----------|-------|

State **Not documented** if none exist.

---

## Bridge Dependencies

For each documented bridge:

| Bridge | Purpose | Required | Notes |
|--------|---------|----------|-------|

Only include documented bridges.

---

## Third-Party Services

For each documented service:

| Service | Purpose | Required | Notes |
|---------|---------|----------|-------|

Examples include:

- APIs
- Data providers
- Keeper networks
- Automation services
- Identity providers
- Storage providers

---

## Supported Networks

For each documented blockchain:

| Network | Purpose | Required |
|---------|---------|----------|

Only include documented networks.

---

## External Asset Dependencies

For each documented external asset:

| Asset | Purpose | Dependency |
|-------|---------|------------|

Examples include:

- Stablecoins
- Liquid staking tokens
- Wrapped assets
- LP tokens
- Synthetic assets

---

## Dependency Requirements

Extract documented operational requirements created by external dependencies.

Examples:

- Required availability
- Required synchronization
- Required configuration
- Required trust assumptions

---

# Analyst Notes

Record concise observations derived from documented facts.

Examples include:

- Dependency concentration
- Infrastructure complexity
- External reliance
- Ecosystem interoperability
- Critical operational dependencies
- Vendor concentration

Do not speculate.

---

# Risks

Record only dependency-related risks supported by the documented integrations.

Examples:

- Single external dependency
- Oracle reliance
- Bridge reliance
- Infrastructure concentration
- Cross-chain dependence
- Third-party service dependency

Do not speculate.

Do not perform security analysis.

---

# Unknowns

Record important dependency information that could not be determined.

Examples:

- Missing infrastructure documentation
- Undefined oracle providers
- Undocumented bridge usage
- Unknown external services
- Missing dependency requirements

---

# Key Takeaways

- Primary external dependency
- Most critical integration
- Largest infrastructure dependency
- Largest operational dependency
- One dependency fact an analyst should remember

---

# Verification Opportunities

Only include dependency claims that would materially affect protocol operation or trust.

Examples:

- Oracle provider
- Bridge implementation
- Required infrastructure
- Cross-chain messaging protocol
- External protocol reliance
- Critical third-party services

Do not include routine integration descriptions.

| High-Impact Claim | Why Verify? | Verification Method |
|-------------------|-------------|---------------------|

---

# Automation Opportunities

| Check | Why It Matters | Automatable | Suggested Data Source |
|--------|----------------|-------------|-----------------------|

Only include dependency changes or external integrations that would provide meaningful ongoing monitoring.