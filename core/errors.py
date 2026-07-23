"""
Failure classification.

The core judgment call in error recovery: is this failure worth
retrying, or is retrying pointless/harmful? We classify at two levels:

1. Exceptions raised during execution (network errors, rate limits,
   malformed LLM JSON) -> classified by type/message.
2. Verifier-flagged failures (the LLM ran fine but produced a bad or
   incomplete result) -> classified by the Verifier's own judgment.

Keeping this as one shared module means both the Executor's exception
handling and the Verifier's quality checks report failures in the same
vocabulary, which is what lets the orchestrator make one consistent
retry decision instead of special-casing each agent.
"""

from enum import Enum


class FailureType(str, Enum):
    RETRYABLE = "retryable"   # transient — worth trying again
    TERMINAL = "terminal"     # won't succeed on retry — stop and report


# Substrings we treat as clearly transient (network/rate-limit/timeout-ish).
RETRYABLE_SIGNALS = [
    "timeout",
    "timed out",
    "rate limit",
    "429",
    "connection",
    "temporarily unavailable",
    "503",
    "502",
]

# Substrings we treat as clearly non-transient (bad input, auth, parsing).
TERMINAL_SIGNALS = [
    "401",
    "403",
    "invalid api key",
    "authentication",
    "invalid json",
    "expecting value",  # common json.JSONDecodeError message fragment
]


def classify_exception(error: Exception) -> FailureType:
    msg = str(error).lower()

    for signal in TERMINAL_SIGNALS:
        if signal in msg:
            return FailureType.TERMINAL

    for signal in RETRYABLE_SIGNALS:
        if signal in msg:
            return FailureType.RETRYABLE

    # Default: unknown errors are treated as retryable ONCE, not assumed
    # terminal — but the orchestrator's max-retry cap prevents infinite
    # loops on something that's actually permanently broken.
    return FailureType.RETRYABLE