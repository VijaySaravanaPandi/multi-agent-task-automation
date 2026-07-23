"""
Structured logging foundation.

Every agent decision gets logged as a structured JSON line, not just
raw text output. This is the seed of the Phase 5 observability layer:
later we build a trace reader on top of these log files to answer
"what did the system do and why" without re-reading raw LLM output.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from config.settings import settings


class StructuredLogger:
    def __init__(self, task_id: str | None = None):
        self.task_id = task_id or str(uuid.uuid4())
        os.makedirs(settings.LOG_DIR, exist_ok=True)
        self.log_path = os.path.join(settings.LOG_DIR, f"{self.task_id}.jsonl")

    def log_event(
        self,
        agent_name: str,
        event_type: str,
        detail: str,
        reasoning: str = "",
        data: dict | None = None,
    ) -> None:
        """
        agent_name: which agent produced this event (planner/executor/verifier/system)
        event_type: e.g. 'decision', 'action', 'error', 'state_change'
        detail:     short human-readable description of what happened
        reasoning:  WHY the agent chose this action (the important part)
        data:       any structured payload worth keeping (inputs/outputs)
        """
        entry = {
            "task_id": self.task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent_name,
            "event_type": event_type,
            "detail": detail,
            "reasoning": reasoning,
            "data": data or {},
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Also echo to console for now — Phase 5 adds a proper trace viewer.
        print(f"[{entry['timestamp']}] ({agent_name}) {event_type}: {detail}")