"""
Entry point / orchestrator.
Phase 2: real Planner -> Executor -> Verifier loop, with full context
handoffs logged at each transition so the trace shows not just what
each agent decided, but what it was given to decide with.
"""

import uuid
from core.logger import StructuredLogger
from core.state import TaskState, TaskStatus
from agents.base_agent import AgentInput
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.verifier import VerifierAgent


def run_task(goal: str):
    task_id = str(uuid.uuid4())
    logger = StructuredLogger(task_id=task_id)

    task = TaskState(task_id=task_id, goal=goal, status=TaskStatus.IN_PROGRESS)

    logger.log_event(
        agent_name="system",
        event_type="task_start",
        detail=f"Task {task.task_id} started",
        reasoning="Beginning Phase 2 orchestration loop",
        data={"goal": task.goal},
    )

    planner = PlannerAgent(logger)
    executor = ExecutorAgent(logger)
    verifier = VerifierAgent(logger)

    # --- Planner ---
    plan_output = planner.run(AgentInput(goal=goal, context={}))
    if not plan_output.success:
        task.status = TaskStatus.FAILED
        logger.log_event("system", "task_end", "Task failed at planning stage",
                          reasoning=plan_output.reasoning)
        return

    logger.log_event(
        agent_name="system",
        event_type="handoff",
        detail="planner -> executor",
        reasoning="Passing generated plan as context to Executor",
        data={"plan": plan_output.result},
    )

    # --- Executor ---
    exec_output = executor.run(AgentInput(goal=goal, context={"plan": plan_output.result}))
    task.steps_completed = [r["step"] for r in exec_output.result if r.get("outcome")]
    task.steps_remaining = [r["step"] for r in exec_output.result if not r.get("outcome")]

    logger.log_event(
        agent_name="system",
        event_type="handoff",
        detail="executor -> verifier",
        reasoning="Passing execution results as context to Verifier",
        data={"execution_results": exec_output.result},
    )

    # --- Verifier (still stub logic — real checks in Phase 3) ---
    verify_output = verifier.run(AgentInput(goal=goal, context={"execution": exec_output.result}))

    task.status = TaskStatus.COMPLETED if exec_output.success else TaskStatus.FAILED

    logger.log_event(
        agent_name="system",
        event_type="task_end",
        detail=f"Task {task.task_id} finished with status {task.status.value}",
        reasoning="Orchestration loop complete",
        data={
            "steps_completed": task.steps_completed,
            "steps_remaining": task.steps_remaining,
        },
    )

    print(f"\nDone. Status: {task.status.value}")
    print(f"Check logs/{task_id}.jsonl for the full structured trace.")


if __name__ == "__main__":
    goal = input("Enter a task goal (e.g. 'Research the benefits of solar energy and draft a summary report'): ")
    run_task(goal)