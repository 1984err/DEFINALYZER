# Security

## Purpose
> TEMPLATE INSTRUCTION ONLY — DO NOT INCLUDE THIS SECTION IN THE OUTPUT.

Extract and classify documented information describing the protocol's security model, security mechanisms, trust assumptions, and defensive controls.

Focus on documented security architecture and operational protections.

Do not perform an independent security audit or speculate about vulnerabilities.

---

## Scope
> TEMPLATE INSTRUCTION ONLY — DO NOT INCLUDE THIS SECTION IN THE OUTPUT.

Extract only documented information that answers the following questions:

- What security mechanisms exist?
- What trust assumptions are documented?
- What administrative controls exist?
- What protections exist for user funds?
- What permissions affect security?
- What emergency controls exist?
- What security limitations are documented?
- What external systems influence protocol security?

Do not include:

- Personal security opinions
- Independent vulnerability analysis
- Speculative attack vectors
- Market risks
- Token price risks
- General blockchain security advice

---

# Facts

## Security Overview

Extract:

- Overall security model
- Primary security objectives
- Primary trust assumptions

---

## Security Mechanisms

For each documented mechanism:

| Mechanism | Purpose | Notes |
|-----------|---------|-------|

Examples include:

- Access control
- Timelocks
- Multisig
- Permission system
- Role-based access
- Rate limiting
- Circuit breakers
- Pausable contracts

Only include documented mechanisms.

---

## Access Control

For each documented privileged role:

| Role | Permission | Restrictions |
|------|------------|--------------|

Only include documented permissions.

---

## Administrative Controls

Extract documented administrative capabilities.

Examples:

- Contract upgrades
- Parameter changes
- Treasury controls
- Emergency actions
- Oracle management
- Whitelists
- Blacklists

Only include documented controls.

---

## Trust Assumptions

Extract documented assumptions regarding:

- Administrators
- Validators
- Oracles
- Bridges
- External protocols
- Off-chain infrastructure
- Users

Do not infer assumptions.

---

## Emergency Mechanisms

For each documented mechanism:

| Mechanism | Trigger | Effect |
|-----------|---------|--------|

Examples include:

- Pause
- Shutdown
- Guardian intervention
- Emergency upgrade
- Recovery process

State **Not documented** if unavailable.

---

## External Security Dependencies

For each documented dependency:

| Dependency | Security Impact | Notes |
|------------|-----------------|-------|

Examples:

- Oracle providers
- Bridges
- Validators
- Sequencers
- Cross-chain messaging
- Keeper networks

Only include documented dependencies.

---

## User Security Responsibilities

Extract documented responsibilities expected of users.

Examples:

- Wallet security
- Key management
- Approval management
- Collateral monitoring
- Liquidation monitoring

Only include documented responsibilities.

---

## Security Limitations

Extract documented security limitations or known constraints.

Examples:

- Trusted roles
- Administrative authority
- Upgradeability
- External dependency limitations
- Operational assumptions

Only include documented limitations.

---

# Analyst Notes

Record concise observations derived from documented facts.

Examples include:

- Concentration of privileged authority
- Degree of decentralization
- Trust distribution
- Defense-in-depth
- External security dependence
- Operational resilience

Do not speculate.

Do not perform an independent security assessment.

---

# Risks

Record only security-related risks supported by the documented design.

Examples:

- Privileged administrator access
- Upgrade authority
- Oracle dependence
- Bridge dependence
- External infrastructure reliance
- Emergency authority concentration
- Trusted third parties

Do not speculate.

Do not introduce risks not supported by the documentation.

---

# Unknowns

Record important security information that could not be determined.

Examples:

- Missing access controls
- Missing emergency procedures
- Undefined privileged roles
- Missing trust assumptions
- Missing recovery procedures
- Missing security limitations

---

# Key Takeaways

- Primary security model
- Highest-impact security mechanism
- Largest trust assumption
- Largest documented security dependency
- One security fact an analyst should remember

---

# Verification Opportunities

Only include security claims that would materially affect protocol trust or user safety.

Examples:

- Contract ownership
- Upgrade authority
- Timelock configuration
- Multisig composition
- Emergency pause authority
- Oracle configuration
- Administrative permissions
- Access control implementation

Do not include routine security descriptions.

| High-Impact Claim | Why Verify? | Verification Method |
|-------------------|-------------|---------------------|

---

# Automation Opportunities

| Check | Why It Matters | Automatable | Suggested Data Source |
|--------|----------------|-------------|-----------------------|

Only include ongoing monitoring opportunities for security-critical permissions, configuration changes, or trust assumptions.