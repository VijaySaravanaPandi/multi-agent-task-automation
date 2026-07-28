"""
Entry point / orchestrator — Phase 3.

Adds a supervisor retry loop: after verification, any step that failed
AND is classified retryable gets re-executed, up to MAX_RETRIES times.
Terminal failures are never retried — they're reported immediately.
This is the concrete answer to "how do you avoid infinite retry loops":
a hard cap, plus a classification step that refuses to retry things
that can't succeed no matter how many times you try.
"""

import uuid
from core.logger import StructuredLogger
from core.trace_reader import render_trace
from core.state import TaskState, TaskStatus
from agents.base_agent import AgentInput
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.verifier import VerifierAgent
from core.errors import FailureType
from core.logger import StructuredLogger
import time

MAX_RETRIES = 2


def run_task(goal: str):
    task_id = str(uuid.uuid4())
    logger = StructuredLogger(task_id=task_id)
    task = TaskState(task_id=task_id, goal=goal, status=TaskStatus.IN_PROGRESS)

    logger.log_event("system", "task_start", f"Task {task.task_id} started",
                      reasoning="Beginning Phase 3 orchestration loop with retry supervision",
                      data={"goal": task.goal})

    planner = PlannerAgent(logger)
    executor = ExecutorAgent(logger)
    verifier = VerifierAgent(logger)
    agents_with_llm = [planner, executor, verifier]

    task_start_time = time.time()

    # --- Planner ---
    plan_output = planner.run(AgentInput(goal=goal, context={}))
    if not plan_output.success:
        task.status = TaskStatus.FAILED
        logger.log_event("system", "task_end", "Task failed at planning stage",
                          reasoning=plan_output.reasoning)
        print(f"\nDone. Status: {task.status.value}")
        return

    steps_to_run = plan_output.result
    final_results = {}  # step -> latest result dict
    prior_results = {}  # step -> outcome, carried across attempts for context
    attempt = 0

    while steps_to_run and attempt <= MAX_RETRIES:
        attempt += 1
        logger.log_event("system", "handoff", f"planner/retry -> executor (attempt {attempt})",
                          reasoning="Executing current retry batch of steps",
                          data={"steps": steps_to_run})

        exec_output = executor.run(AgentInput(goal=goal, context={"plan": steps_to_run, "prior_results": prior_results}))
        for r in exec_output.result:
            final_results[r["step"]] = r

        logger.log_event("system", "handoff", "executor -> verifier",
                          reasoning="Passing execution results as context to Verifier",
                          data={"execution_results": exec_output.result})

        verify_output = verifier.run(AgentInput(goal=goal, context={"execution": exec_output.result}))
        for v in verify_output.result:
            final_results[v["step"]]["passed"] = v["passed"]
            final_results[v["step"]]["verify_reasoning"] = v["reasoning"]
            final_results[v["step"]]["failure_type"] = v.get("failure_type")

        # Decide what to retry: only steps that failed AND are retryable.
        retry_batch = []
        for v in verify_output.result:
            if not v["passed"]:
                if v.get("failure_type") == FailureType.RETRYABLE.value and attempt <= MAX_RETRIES:
                    retry_batch.append(v["step"])
                else:
                    logger.log_event(
                        "system", "decision",
                        f"Not retrying step: {v['step'][:60]}",
                        reasoning=(
                            f"Failure type is {v.get('failure_type')}, "
                            f"or max retries ({MAX_RETRIES}) reached"
                        ),
                    )

        steps_to_run = retry_batch
        if steps_to_run:
            logger.log_event("system", "decision", f"Retrying {len(steps_to_run)} step(s)",
                              reasoning=f"Retry attempt {attempt} of {MAX_RETRIES}",
                              data={"retry_steps": steps_to_run})

    task.steps_completed = [s for s, r in final_results.items() if r.get("passed")]
    task.steps_remaining = [s for s, r in final_results.items() if not r.get("passed")]
    task.status = TaskStatus.COMPLETED if not task.steps_remaining else TaskStatus.FAILED

    logger.log_event("system", "task_end", f"Task {task.task_id} finished with status {task.status.value}",
                      reasoning=f"Completed after {attempt} attempt(s)",
                      data={
                          "steps_completed": task.steps_completed,
                          "steps_remaining": task.steps_remaining,
                      })

    total_wall_time = round(time.time() - task_start_time, 2)
    usage_totals = {"call_count": 0, "total_input_tokens": 0, "total_output_tokens": 0,
                     "total_tokens": 0, "total_latency_seconds": 0.0}
    for a in agents_with_llm:
        u = a.llm.get_usage_summary()
        for k in usage_totals:
            usage_totals[k] += u[k]
    usage_totals["total_latency_seconds"] = round(usage_totals["total_latency_seconds"], 2)

    logger.log_event(
        agent_name="system",
        event_type="cost_summary",
        detail=f"Task cost/latency: {usage_totals['total_tokens']} tokens, "
               f"{usage_totals['total_latency_seconds']}s LLM time, {total_wall_time}s wall time",
        reasoning="End-of-task accounting across all agents",
        data={**usage_totals, "total_wall_time_seconds": total_wall_time},
    )

    print(f"\nDone. Status: {task.status.value} (after {attempt} attempt(s))")
    print(render_trace(task_id))
    print(f"\n💰 Cost/Latency Summary:")
    print(f"   LLM calls: {usage_totals['call_count']}")
    print(f"   Total tokens: {usage_totals['total_tokens']} (in: {usage_totals['total_input_tokens']}, out: {usage_totals['total_output_tokens']})")
    print(f"   Total LLM time: {usage_totals['total_latency_seconds']}s")
    print(f"   Total wall time: {total_wall_time}s")


if __name__ == "__main__":
    goal = input("Enter a task goal: ")
    run_task(goal)