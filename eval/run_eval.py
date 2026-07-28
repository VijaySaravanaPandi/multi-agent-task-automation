"""
Evaluation runner.

Runs every case in TEST_CASES through the real orchestration pipeline,
scores each one against its expectations, and appends a summary to
results_history.jsonl so score-over-time (regression detection) is
possible: did a later prompt change make things worse?
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import StructuredLogger
from core.state import TaskState, TaskStatus
from agents.base_agent import AgentInput
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.verifier import VerifierAgent
from core.errors import FailureType
from eval.test_cases import TEST_CASES

MAX_RETRIES = 2
RESULTS_PATH = os.path.join("eval", "results_history.jsonl")


def run_single_case(case: dict) -> dict:
    goal = case["goal"]
    expect = case["expect"]
    task_id = f"eval-{case['id']}-{uuid.uuid4().hex[:8]}"
    logger = StructuredLogger(task_id=task_id)

    planner = PlannerAgent(logger)
    executor = ExecutorAgent(logger)
    verifier = VerifierAgent(logger)

    plan_output = planner.run(AgentInput(goal=goal, context={}))
    checks = {}
    passed_all = True

    if not plan_output.success:
        return _fail_result(case, task_id, "Planner failed", checks)

    steps = plan_output.result
    checks["min_steps"] = len(steps) >= expect.get("min_steps", 1)

    steps_to_run = steps
    final_results = {}
    attempt = 0
    while steps_to_run and attempt <= MAX_RETRIES:
        attempt += 1
        exec_output = executor.run(AgentInput(goal=goal, context={"plan": steps_to_run}))
        for r in exec_output.result:
            final_results[r["step"]] = r

        verify_output = verifier.run(AgentInput(goal=goal, context={"execution": exec_output.result}))
        retry_batch = []
        for v in verify_output.result:
            final_results[v["step"]]["passed"] = v["passed"]
            if not v["passed"] and v.get("failure_type") == FailureType.RETRYABLE.value and attempt <= MAX_RETRIES:
                retry_batch.append(v["step"])
        steps_to_run = retry_batch

    all_passed = all(r.get("passed") for r in final_results.values())

    # Structural checks against expectations
    action_types = [r.get("action_type") for r in final_results.values()]
    if "requires_action_type" in expect:
        checks["requires_action_type"] = expect["requires_action_type"] in action_types

    if expect.get("should_complete") is True:
        checks["should_complete"] = all_passed
    elif expect.get("should_complete") is False:
        checks["should_complete"] = not all_passed

    if expect.get("email_should_be_dry_run"):
        email_results = [r["outcome"] for r in final_results.values() if r.get("action_type") == "email"]
        checks["email_should_be_dry_run"] = any(
            isinstance(o, dict) and o.get("dry_run") is True for o in email_results
        )

    if expect.get("email_should_be_blocked"):
        email_results = [r["outcome"] for r in final_results.values() if r.get("action_type") == "email"]
        checks["email_should_be_blocked"] = any(
            isinstance(o, dict) and o.get("sent") is False and "not in ALLOWED_EMAIL_DOMAINS" in str(o.get("reason", ""))
            for o in email_results
        )

    passed_all = all(v for v in checks.values() if v is not None)

    return {
        "case_id": case["id"],
        "task_id": task_id,
        "goal": goal,
        "checks": checks,
        "passed": passed_all,
        "attempts": attempt,
    }


def _fail_result(case, task_id, reason, checks):
    return {"case_id": case["id"], "task_id": task_id, "goal": case["goal"],
            "checks": checks, "passed": False, "reason": reason}


def run_eval():
    results = []
    for case in TEST_CASES:
        print(f"Running eval case: {case['id']} ...")
        result = run_single_case(case)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  -> {status}  checks={result['checks']}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    score_pct = round((passed / total) * 100, 1) if total else 0.0

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": total,
        "passed": passed,
        "score_pct": score_pct,
        "results": results,
    }

    with open(RESULTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")

    print(f"\n{'='*50}")
    print(f"EVAL SCORE: {passed}/{total} ({score_pct}%)")
    print(f"Logged to {RESULTS_PATH}")
    print(f"{'='*50}")

    _print_regression_check(score_pct)
    return summary


def _print_regression_check(current_score: float):
    if not os.path.exists(RESULTS_PATH):
        return
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]
    if len(lines) < 2:
        return
    previous_score = lines[-2]["score_pct"]
    diff = current_score - previous_score
    if diff < 0:
        print(f"⚠️  REGRESSION: score dropped {abs(diff)}% vs previous run ({previous_score}% -> {current_score}%)")
    elif diff > 0:
        print(f"✅ Improvement: score rose {diff}% vs previous run ({previous_score}% -> {current_score}%)")
    else:
        print(f"➖ No change vs previous run ({previous_score}%)")


if __name__ == "__main__":
    run_eval()