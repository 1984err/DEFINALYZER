# Integrations & Dependencies

## Purpose

Document the protocol's external integrations, infrastructure dependencies, third-party services, and interoperability. Focus on systems the protocol relies on to function correctly.

Do not perform a security assessment or discuss implementation details beyond what is necessary to explain dependencies.

---

## Key Questions

Answer the following using only the supplied sources.

- Which external protocols are integrated?
- Which smart contracts does the protocol depend on?
- Which oracle providers are used?
- Which bridges are supported?
- Which wallets are officially supported?
- Which infrastructure providers are required?
- Which SDKs or APIs are available?
- Which token standards are supported?
- What external assumptions does the protocol make?
- Which dependencies are optional versus critical?

Do not discuss:

- Governance
- Tokenomics
- Revenue
- Security audits
- Market adoption

---

# Facts

## Integration Overview

## External Protocol Integrations

## Smart Contract Dependencies

## Oracle Dependencies

## Bridge Integrations

## Wallet Support

## Infrastructure Providers

## Developer Tooling

## Supported Standards

## Critical Dependencies

---

# Analyst Notes

Discuss observations supported by the documented facts.

Possible topics include:

- Dependency concentration
- Vendor lock-in
- Ecosystem interoperability
- Composability
- External trust assumptions
- Operational resilience

Clearly distinguish inference from documented facts.

---

# Risks

Identify dependency-related risks such as:

- Oracle dependency
- Bridge dependency
- Infrastructure concentration
- Third-party failure
- Cross-protocol contagion
- Vendor lock-in

Do not perform a security assessment.

---

# Research Takeaways

Summarize:

- Major integrations
- Critical dependencies
- External assumptions
- Important interoperability observations

---

# Sources

List every source used.

---

# Verification

## On-Chain Verification

| Claim | Verification Method | Status |
|--------|---------------------|--------|
| Oracle contracts | Contract inspection | |
| Bridge contracts | Contract inspection | |
| External protocol addresses | Contract registry | |
| Supported token standards | Contract interfaces | |

## Off-Chain Verification

| Claim | Verification Method | Status |
|--------|---------------------|--------|
| Wallet support | Official documentation | |
| SDK availability | Repository / documentation | |
| Infrastructure providers | Official documentation | |

---

# Automation Opportunities

| Check | Automatable | Python Approach |
|--------|------------|-----------------|
| Oracle discovery | Yes | Contract inspection |
| Bridge discovery | Yes | Contract inspection |
| Interface detection | Yes | ERC interface inspection |
| Registry validation | Yes | Registry contract queries |