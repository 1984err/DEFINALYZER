# Tokenomics

## Purpose

Document the protocol's token economics, including token utility, supply mechanics, distribution, emissions, incentives, and economic design.

Do not discuss governance mechanics except where the token is directly involved. Do not perform market analysis or discuss price performance.

---

## Key Questions

Answer the following using only the supplied sources.

- Does the protocol have a native token?
- What is the token's purpose?
- What utilities does the token provide?
- What is the maximum supply?
- What is the circulating supply model?
- How are tokens minted?
- Can additional tokens be created?
- Is there a burn mechanism?
- How were tokens initially distributed?
- Are emissions ongoing?
- Are there vesting schedules?
- What incentives are tied to the token?
- How does the token support the protocol's economics?

Do not discuss:

- Price
- Market capitalization
- FDV
- Trading performance
- Governance processes beyond token utility
- Historical price action

---

# Facts

## Token Overview

## Token Utility

## Supply Model

## Initial Distribution

## Allocation Breakdown

## Emissions

## Vesting

## Burn Mechanisms

## Inflation / Deflation Characteristics

## Incentive Structure

## Economic Role

---

# Analyst Notes

Discuss observations supported by the documented facts.

Possible topics include:

- Incentive alignment
- Sustainability
- Inflation risks
- Value capture
- Economic design tradeoffs
- Long-term token utility

Clearly distinguish inference from documented facts.

---

# Risks

Identify token-related risks such as:

- Inflation
- Centralized allocation
- Vesting unlocks
- Weak value capture
- Incentive misalignment
- Token dependency

Do not discuss market price risk.

---

# Research Takeaways

Summarize:

- Purpose of the token
- Supply mechanics
- Incentive model
- Key economic observations

---

# Sources

List every source used.

---

# Verification

## On-Chain Verification

| Claim | Verification Method | Status |
|--------|---------------------|--------|
| Max supply | ERC-20 contract | |
| Total supply | ERC-20 contract | |
| Mint permissions | Contract roles | |
| Burn mechanism | Transfer events / code | |
| Token decimals | ERC-20 metadata | |

## Off-Chain Verification

| Claim | Verification Method | Status |
|--------|---------------------|--------|

---

# Automation Opportunities

| Check | Automatable | Python Approach |
|--------|------------|-----------------|
| Max supply | Yes | ERC-20 call |
| Total supply | Yes | ERC-20 call |
| Decimals | Yes | ERC-20 metadata |
| Mint role | Yes | AccessControl inspection |
| Burn address activity | Yes | Event analysis |