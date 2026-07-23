"""
Entry point.
Phase 1: just proves the skeleton wires together — creates a task,
runs stub agents in sequence, and confirms logging + state work end to end.
Phase 2 replaces this with a real orchestration loop.
"""

import uuid
from core.logger import StructuredLogger
from core.state import TaskState, TaskStatus
from agents.base_agent import AgentInput
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.verifier import VerifierAgent


def main():
    task_id = str(uuid.uuid4())
    logger = StructuredLogger(task_id=task_id)

    task = TaskState(
        task_id=task_id,
        goal="Research a topic, draft a report, and send it via email",
        status=TaskStatus.IN_PROGRESS,
    )

    logger.log_event(
        agent_name="system",
        event_type="task_start",
        detail=f"Task {task.task_id} started",
        reasoning="Initializing Phase 1 skeleton run",
        data={"goal": task.goal},
    )

    planner = PlannerAgent(logger)
    executor = ExecutorAgent(logger)
    verifier = VerifierAgent(logger)

    agent_input = AgentInput(goal=task.goal, context={})

    plan_output = planner.run(agent_input)
    exec_output = executor.run(AgentInput(goal=task.goal, context={"plan": plan_output.result}))
    verify_output = verifier.run(AgentInput(goal=task.goal, context={"execution": exec_output.result}))

    task.status = TaskStatus.COMPLETED
    logger.log_event(
        agent_name="system",
        event_type="task_end",
        detail=f"Task {task.task_id} completed (stub run)",
        reasoning="All Phase 1 stub agents ran successfully",
        data={"final_result": verify_output.result},
    )

    print(f"\nDone. Check logs/{task_id}.jsonl for the structured trace.")


if __name__ == "__main__":
    main()