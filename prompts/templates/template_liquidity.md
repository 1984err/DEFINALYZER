# Liquidity

## Purpose

Document how liquidity is created, maintained, incentivized, and managed within the protocol. Focus on liquidity mechanisms rather than protocol revenue or token economics.

Do not discuss historical TVL or trading volume.

---

## Key Questions

Answer the following using only the supplied sources.

- How is liquidity provided?
- Who supplies liquidity?
- What assets can be deposited?
- How are liquidity providers incentivized?
- How is liquidity priced?
- Are there liquidity protection mechanisms?
- Can liquidity be withdrawn at any time?
- Are there lockup periods?
- Are there protocol-owned liquidity mechanisms?
- How does the protocol maintain healthy liquidity?

Do not discuss:

- TVL
- Historical liquidity statistics
- Market share
- Trading volume
- Token price
- Revenue analysis

---

# Facts

## Liquidity Overview

## Liquidity Sources

## Supported Assets

## Liquidity Provider Requirements

## Incentive Mechanisms

## Liquidity Management

## Withdrawal Rules

## Protocol-Owned Liquidity

## Liquidity Controls

---

# Analyst Notes

Discuss observations supported by the documented facts.

Possible topics include:

- Liquidity sustainability
- Capital efficiency
- Incentive quality
- Dependency on external liquidity
- Liquidity concentration
- Design tradeoffs

Clearly distinguish inference from documented facts.

---

# Risks

Identify liquidity-related risks such as:

- Liquidity concentration
- Liquidity flight
- Incentive dependence
- Capital inefficiency
- External liquidity dependency
- Withdrawal limitations

Do not analyze market performance.

---

# Research Takeaways

Summarize:

- How liquidity is maintained
- Incentive structure
- Liquidity resilience
- Key design observations

---

# Sources

List every source used.

---

# Verification

## On-Chain Verification

| Claim | Verification Method | Status |
|--------|---------------------|--------|
| Supported assets | Contract inspection | |
| Pool contracts | Factory contracts | |
| Withdrawal rules | Contract logic | |
| Incentive contracts | Rewards contracts | |
| Protocol-owned liquidity | Treasury holdings | |

## Off-Chain Verification

| Claim | Verification Method | Status |
|--------|---------------------|--------|

---

# Automation Opportunities

| Check | Automatable | Python Approach |
|--------|------------|-----------------|
| Pool discovery | Yes | Factory contract |
| Supported assets | Yes | Pool inspection |
| Incentive contracts | Yes | Rewards contracts |
| Withdrawal restrictions | Yes | Contract inspection |
| Protocol-owned liquidity | Yes | Treasury analysis |