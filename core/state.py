"""
State management skeleton.

We deliberately separate three kinds of state, since conflating them
is one of the classic failure modes in multi-agent systems:

- TaskState:  the ground-truth plan/progress the orchestrator owns
- AgentState: what an individual agent currently believes/holds
- WorldState: the last-known state of the external world (inbox, search
              results, etc.) which can drift out of sync with TaskState
              when external actions fail silently or partially.

Phase 3 (error recovery) will actively use the gap between these to
detect drift. For now this is just the data model.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskState:
    task_id: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    steps_completed: list[str] = field(default_factory=list)
    steps_remaining: list[str] = field(default_factory=list)
    current_agent: str | None = None


@dataclass
class AgentState:
    agent_name: str
    memory: dict[str, Any] = field(default_factory=dict)
    last_action: str | None = None


@dataclass
class WorldState:
    """Last confirmed observation of external systems (email sent? search returned?)."""
    facts: dict[str, Any] = field(default_factory=dict)

    def update(self, key: str, value: Any) -> None:
        self.facts[key] = value