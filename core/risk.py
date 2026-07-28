"""
Risk tiering for actions.

The core design decision here: not all actions deserve the same trust.
Searching the web is reversible and low-consequence — no approval needed.
Sending an email to a real person is irreversible once sent — it always
requires a human "yes" before the system is allowed to actually send,
regardless of what DRY_RUN_MODE is set to. Dry-run and human approval
are two independent safety layers, not substitutes for each other.
"""

from enum import Enum


class RiskTier(str, Enum):
    LOW = "low"       # auto-proceed, no approval needed
    HIGH = "high"     # must pause for human approval before acting


ACTION_RISK_TIERS = {
    "search": RiskTier.LOW,
    "other": RiskTier.LOW,
    "email": RiskTier.HIGH,
}


def get_risk_tier(action_type: str) -> RiskTier:
    return ACTION_RISK_TIERS.get(action_type, RiskTier.HIGH)  # unknown actions default to HIGH — fail safe