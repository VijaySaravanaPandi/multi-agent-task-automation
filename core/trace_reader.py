"""
Trace reader — turns a raw structured log (.jsonl) into a readable,
chronological narrative of what the system did and why.

This is the concrete answer to "can you prove it worked": instead of
re-reading raw LLM output or scrolling a wall of JSON, this produces
a clean report per task that an interviewer (or you, three months from
now) can actually read and understand at a glance.
"""

import json
import os
import sys
from config.settings import settings


EVENT_ICONS = {
    "task_start": "🚀",
    "task_end": "🏁",
    "handoff": "🔁",
    "decision": "🧠",
    "external_action": "🌐",
    "error": "⚠️",
}


def load_trace(task_id: str) -> list[dict]:
    path = os.path.join(settings.LOG_DIR, f"{task_id}.jsonl")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No log file found for task_id: {task_id}")

    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def render_trace(task_id: str) -> str:
    events = load_trace(task_id)
    if not events:
        return f"No events found for task {task_id}"

    lines = [f"{'='*70}", f"TASK TRACE: {task_id}", f"{'='*70}\n"]

    for e in events:
        icon = EVENT_ICONS.get(e.get("event_type"), "•")
        ts = e.get("timestamp", "")
        agent = e.get("agent", "unknown").upper()
        detail = e.get("detail", "")
        reasoning = e.get("reasoning", "")

        lines.append(f"{icon} [{ts}] {agent}")
        lines.append(f"   What: {detail}")
        if reasoning:
            lines.append(f"   Why:  {reasoning}")

        data = e.get("data", {})
        if data:
            summary = _summarize_data(data)
            if summary:
                lines.append(f"   Data: {summary}")
        lines.append("")

    lines.append(f"{'='*70}")
    lines.append(f"Total events: {len(events)}")
    return "\n".join(lines)


def _summarize_data(data: dict, max_len: int = 150) -> str:
    """Keep the console output readable — full data is still in the raw
    .jsonl for anyone who needs it, this is just the human-facing view."""
    text = json.dumps(data, ensure_ascii=False)
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def list_available_tasks() -> list[str]:
    if not os.path.exists(settings.LOG_DIR):
        return []
    return [
        f.removesuffix(".jsonl")
        for f in os.listdir(settings.LOG_DIR)
        if f.endswith(".jsonl")
    ]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        available = list_available_tasks()
        if not available:
            print("No task logs found in logs/. Run main.py first.")
            sys.exit(0)
        print("Usage: python core/trace_reader.py <task_id>\n")
        print("Available task IDs:")
        for t in available:
            print(f"  - {t}")
        sys.exit(0)

    task_id = sys.argv[1]
    print(render_trace(task_id))