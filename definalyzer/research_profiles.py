"""Versioned research questions; documentation and measurements stay separate."""
VERSION = 1

COMMON = {
    "protocol-overview": ("What does the subject do and for whom?", "What are its documented boundaries and related systems?"),
    "architecture": ("How do assets, accounts or execution move through the system?", "What conditions and failure boundaries apply?"),
    "tokenomics": ("What rights and utility does the asset have?", "How are issuance, distribution and dilution controlled?"),
    "governance": ("Who can change or pause the system?", "What voting, upgrade and execution restrictions apply?"),
    "security": ("What custody and trust assumptions apply?", "What security reviews and their limitations are documented?"),
    "risk-assessment": ("What failure mechanisms are documented?", "What mitigations and remaining limitations are documented?"),
    "revenue-model": ("Who pays fees and who receives them?", "How do fees, revenue and incentives differ?"),
    "liquidity": ("How can users enter, redeem or exit positions?", "What liquidity and withdrawal restrictions apply?"),
    "integrations-dependencies": ("Which external systems are required?", "What exposure to each dependency is documented?"),
    "competitive-positioning": ("What design tradeoffs are documented?", "What comparable evidence supports claimed advantages?"),
}
OVERRIDES = {
    "chain": {
        "architecture": ("How do execution, consensus and finality work?", "What validator requirements and failure boundaries apply?"),
        "tokenomics": ("How does the native asset support fees and validator incentives?", "How are native issuance, distribution and dilution controlled?"),
    },
    "token": {
        "protocol-overview": ("What is the asset and how does it relate to its issuer or chain?", "What rights and enforceable value accrual does holding it provide?"),
        "architecture": ("Where is the asset deployed or represented?", "What minting, custody and transfer controls apply?"),
        "revenue-model": ("What mechanism directs value to holders?", "Who can change or disable that mechanism?"),
    },
}
OBSERVATIONS = {
    "chain": {"architecture": "Dated validator concentration, activity and finality observations.",
              "security": "Dated outages and economic-security observations.",
              "tokenomics": "Dated native supply, distribution and issuance observations.",
              "revenue-model": "Dated fees and validator revenue observations.",
              "liquidity": "Dated liquidity and withdrawal observations."},
    "protocol": {"protocol-overview": "Dated demand and utilization observations.",
                 "architecture": "Current deployment and control-state observations.",
                 "security": "Dated incidents and realized losses.",
                 "tokenomics": "Dated supply, holdings and unlock observations.",
                 "revenue-model": "Dated fees, revenue and incentive observations.",
                 "liquidity": "Dated liquidity and redemption observations."},
    "token": {"tokenomics": "Dated supply, holdings and unlock amounts.",
              "revenue-model": "Dated value-accrual and valuation inputs.",
              "liquidity": "Dated trading liquidity and market observations."},
}


def profile_questions(kind):
    profile = "token" if kind in {"token", "coin"} else kind if kind in {"chain", "protocol"} else "protocol"
    definitions = {**COMMON, **OVERRIDES.get(profile, {})}
    return {f"{topic}.{index}": {"topic": topic, "question": question,
            "profile": profile, "profile_version": VERSION, "accepts": ["documented_claim"]}
            for topic, questions in definitions.items() for index, question in enumerate(questions, 1)}


def observation_requirements(kind):
    return OBSERVATIONS["token" if kind in {"token", "coin"} else kind if kind in OBSERVATIONS else "protocol"]
