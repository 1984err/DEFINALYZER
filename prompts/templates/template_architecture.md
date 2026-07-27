# Architecture

## Purpose
> TEMPLATE INSTRUCTION ONLY — DO NOT INCLUDE THIS SECTION IN THE OUTPUT.

Extract and classify the protocol's documented architecture.

Focus on **how the protocol is built**, **how it operates**, and **how its components interact**.

Do not document tokenomics, governance, security analysis, or business operations unless required to understand the architecture.

---

## Scope
> TEMPLATE INSTRUCTION ONLY — DO NOT INCLUDE THIS SECTION IN THE OUTPUT.

Extract only documented information that answers the following questions:

- What is the protocol?
- What are the primary system components?
- How do the components interact?
- How do users interact with the protocol?
- What smart contracts or services exist?
- What external protocols or infrastructure are required?
- How do assets and information flow through the protocol?
- What trust assumptions are documented?
- How is the protocol upgraded?
- What architectural patterns are documented?

Do not include:

- Token distribution
- Token utility
- Governance processes
- Revenue model
- Security assessments
- Audit history
- Economic analysis

---

# Facts

## Protocol Purpose

Extract:

- Primary function
- Primary users
- Core protocol objective

---

## System Overview

Extract:

- High-level architecture
- Major subsystems
- Overall protocol structure

---

## Core Components

For each documented component record:

- Name
- Purpose
- Interacts With

---

## User Workflow

Extract the documented user flow.

Record each step separately.

Example format:

| Step | Action |
|------|--------|

Do not combine multiple workflows unless documented.

---

## Smart Contracts

For each documented contract record:

| Contract | Purpose | Upgradeable | Notes |
|----------|---------|-------------|-------|

State **Not documented** where applicable.

---

## External Dependencies

For each dependency record:

| Dependency | Purpose | Required | Notes |
|------------|---------|----------|-------|

Include:

- Protocols
- Bridges
- Oracles
- APIs
- Infrastructure
- Blockchains

Only include documented dependencies.

---

## Data & Asset Flow

Extract documented flows.

Separate:

### Asset Flow

### Data Flow

Only document observed flows.

---

## Upgradeability

Extract:

- Upgrade mechanism
- Proxy pattern
- Upgrade authority
- Immutable components
- Upgrade limitations

---

## Trust Assumptions

Extract documented assumptions regarding:

- Administrators
- Validators
- External dependencies
- Off-chain services
- Users

Do not infer assumptions.

---

## Design Patterns

Identify documented architectural patterns.

Examples:

- Factory
- Registry
- Router
- Vault
- Adapter
- Plugin
- Modular contracts
- Proxy

Only include documented patterns.

---

# Analyst Notes

Record concise observations derived from documented facts.

Examples include:

- Separation of responsibilities
- Modularity
- Upgrade strategy
- Dependency concentration
- Operational complexity
- Architectural tradeoffs

Do not speculate.

---

# Risks

Record only architecture-related risks supported by the documented architecture.

Examples:

- Centralized dependencies
- Single points of failure
- Upgrade complexity
- External protocol reliance
- Operational assumptions

Do not perform security analysis.

---

# Unknowns

Record important architectural information that could not be determined.

Examples:

- Missing documentation
- Undefined workflows
- Undocumented upgrade process
- Undocumented trust assumptions
- Conflicting documentation

Do not speculate.

---

# Key Takeaways

- Primary protocol purpose
- Most important architectural decision
- Largest dependency
- Largest trust assumption
- One key fact an analyst should remember

---

# Verification Opportunities

Only include high-impact claims that would materially affect protocol evaluation.

| High-Impact Claim | Why Verify? | Verification Method |
|-------------------|-------------|---------------------|

Do not include routine architectural descriptions or observable implementation details.

---

# Automation Opportunities

| Check | Why It Matters | Automatable | Suggested Data Source |
|--------|----------------|-------------|-----------------------|

Only include checks that would provide meaningful ongoing monitoring or validation.