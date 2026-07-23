"""
Executor agent — Phase 3 update.

Same simulated-execution approach as Phase 2, but now every exception
is classified (retryable vs terminal) so the orchestrator's retry loop
knows what to do with it, instead of treating all failures the same.
"""

from agents.base_agent import BaseAgent, AgentInput, AgentOutput
from core.llm_client import LLMClient
from core.errors import classify_exception

SYSTEM_PROMPT = """You are a task execution agent. You will be given one
step from a plan. Produce a short, realistic result for completing that
step (simulated — no real external actions are taken yet).
Respond ONLY with valid JSON in this exact shape, no other text:
{
  "result": "short description of the outcome",
  "reasoning": "why you produced this outcome"
}"""


class ExecutorAgent(BaseAgent):
    name = "executor"

    def __init__(self, logger, llm_client: LLMClient | None = None):
        super().__init__(logger)
        self.llm = llm_client or LLMClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        steps = agent_input.context.get("plan", [])
        if not steps:
            self.log_decision(
                detail="No steps to execute",
                reasoning="Executor received an empty plan from context",
            )
            return AgentOutput(success=False, result=None, reasoning="Empty plan", next_agent=None)

        step_results = []
        for i, step in enumerate(steps, start=1):
            try:
                outcome = self.llm.complete_json(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=f"Step {i}: {step}",
                )
                step_results.append({"step": step, "outcome": outcome.get("result", "")})

                self.log_decision(
                    detail=f"Executed step {i}/{len(steps)}: {step}",
                    reasoning=outcome.get("reasoning", ""),
                    data={"step": step, "outcome": outcome.get("result", "")},
                )

            except Exception as e:
                failure_type = classify_exception(e)
                step_results.append({
                    "step": step,
                    "outcome": None,
                    "error": str(e),
                    "failure_type": failure_type.value,
                })
                self.log_decision(
                    detail=f"Step {i} failed: {step}",
                    reasoning=f"Classified as {failure_type.value}: {str(e)}",
                    data={"error": str(e), "failure_type": failure_type.value},
                )

        all_succeeded = all(r.get("outcome") is not None for r in step_results)

        return AgentOutput(
            success=all_succeeded,
            result=step_results,
            reasoning=f"Executed {len(steps)} steps, {'all succeeded' if all_succeeded else 'some failed'}",
            next_agent="verifier",
        )