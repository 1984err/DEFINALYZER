# Risk Assessment

## Purpose
> TEMPLATE INSTRUCTION ONLY — DO NOT INCLUDE THIS SECTION IN THE OUTPUT.

Extract and classify documented information describing the protocol's risks, assumptions, operational limitations, and failure scenarios.

Focus on risks explicitly documented by the protocol or directly implied by its documented design.

Do not perform an independent security review or speculate about undocumented vulnerabilities.

---

## Scope
> TEMPLATE INSTRUCTION ONLY — DO NOT INCLUDE THIS SECTION IN THE OUTPUT.

Extract only documented information that answers the following questions:

- What risks are documented?
- What assumptions does the protocol rely on?
- What operational limitations exist?
- What failure scenarios are described?
- What dependencies introduce risk?
- What user responsibilities are documented?
- What mitigations are documented?

Do not include:

- Personal opinions
- Security audit findings
- Independent vulnerability analysis
- Exploit history unless documented
- Speculative attack vectors
- Market risks
- Token price risks

---

# Facts

## Risk Overview

Extract:

- Primary documented risks
- Primary operational assumptions
- Major areas of protocol exposure

---

## Operational Risks

For each documented operational risk:

| Risk | Cause | Impact | Mitigation |
|------|-------|--------|------------|

Only include documented risks.

---

## Technical Risks

For each documented technical risk:

| Risk | Description | Mitigation |
|------|-------------|------------|

Examples include:

- Upgrade process
- Oracle dependence
- Cross-chain messaging
- Infrastructure dependence
- External protocol reliance

Only include documented risks.

---

## Dependency Risks

For each documented dependency-related risk:

| Dependency | Risk | Mitigation |
|------------|------|------------|

Only include documented dependencies.

---

## User Risks

Extract documented risks affecting users.

Examples:

- Liquidation
- Loss of funds
- Incorrect configuration
- Slippage
- Transaction ordering
- Asset compatibility

Record each separately.

---

## Operational Assumptions

Extract documented assumptions required for correct protocol operation.

Examples:

- Oracle availability
- Validator honesty
- Bridge operation
- External protocol availability
- User behavior

Only include documented assumptions.

---

## Failure Scenarios

For each documented failure scenario:

| Scenario | Impact | Recovery |
|----------|--------|----------|

State **Not documented** if unavailable.

---

## Risk Mitigations

Extract documented mechanisms that reduce protocol risk.

Examples:

- Timelocks
- Circuit breakers
- Rate limits
- Collateralization
- Insurance
- Redundancy
- Monitoring
- Validation

Only include documented mitigations.

---

## User Responsibilities

Extract documented responsibilities required of users.

Examples:

- Managing collateral
- Monitoring positions
- Maintaining wallet security
- Managing approvals
- Understanding liquidation conditions

Only include documented responsibilities.

---

# Analyst Notes

Record concise observations derived from documented facts.

Examples include:

- Concentration of operational risk
- Dependence on external systems
- Reliance on user behavior
- Diversity of mitigations
- Overall operational resilience based on documented design

Do not speculate.

Do not perform security analysis.

---

# Risks

Summarize the highest-impact documented risks.

Prioritize:

- Protocol operation
- User funds
- External dependencies
- Administrative authority
- Infrastructure

Do not introduce new risks not already documented above.

---

# Unknowns

Record important risk-related information that could not be determined.

Examples:

- Missing failure scenarios
- Missing mitigation strategies
- Missing operational assumptions
- Missing user responsibilities
- Missing recovery procedures

---

# Key Takeaways

- Largest documented protocol risk
- Largest operational assumption
- Most significant mitigation
- Largest dependency-related risk
- One risk fact an analyst should remember

---

# Verification Opportunities

Only include risk claims that would materially affect protocol trust or operation.

Examples:

- Emergency controls
- Oracle configuration
- Liquidation parameters
- Collateral requirements
- Upgrade permissions
- Recovery mechanisms
- Administrative controls
- Circuit breakers

Do not include routine operational descriptions.

| High-Impact Claim | Why Verify? | Verification Method |
|-------------------|-------------|---------------------|

---

# Automation Opportunities

| Check | Why It Matters | Automatable | Suggested Data Source |
|--------|----------------|-------------|-----------------------|

Only include ongoing monitoring opportunities for operational risk, protocol assumptions, or critical configuration changes.