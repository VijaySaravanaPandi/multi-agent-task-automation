"""
Common interface every agent (Planner, Executor, Verifier) implements.

Keeping this abstract now — even before any agent does real work — means
the handoff format between agents is decided once, deliberately, instead
of accreting ad hoc dict shapes as we add agents in later phases.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from core.logger import StructuredLogger


@dataclass
class AgentInput:
    """What one agent hands to the next. Deliberately small — full history
    stays in TaskState, not duplicated into every message, to control cost."""
    goal: str
    context: dict[str, Any]


@dataclass
class AgentOutput:
    success: bool
    result: Any
    reasoning: str
    next_agent: str | None = None


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    @abstractmethod
    def run(self, agent_input: AgentInput) -> AgentOutput:
        """Every agent must implement this. Real logic lands in Phase 2/3."""
        raise NotImplementedError

    def log_decision(self, detail: str, reasoning: str, data: dict | None = None):
        self.logger.log_event(
            agent_name=self.name,
            event_type="decision",
            detail=detail,
            reasoning=reasoning,
            data=data,
        )