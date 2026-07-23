"""
Verifier agent — Phase 3 real implementation.

Checks each executed step's outcome against the original step
description and judges whether it actually satisfies that step, not
just whether the LLM call succeeded without throwing. This is the gap
between "the API call worked" and "the task is actually done" — the
Executor can succeed technically while still producing a useless result,
and that's exactly what the Verifier exists to catch.
"""

from agents.base_agent import BaseAgent, AgentInput, AgentOutput
from core.llm_client import LLMClient
from core.errors import FailureType

SYSTEM_PROMPT = """You are a verification agent. You will be given a step
description and the outcome that was produced for it. Judge whether the
outcome genuinely satisfies the step (not just whether something was
produced, but whether it's relevant, complete, and non-generic).
Respond ONLY with valid JSON in this exact shape, no other text:
{
  "passed": true or false,
  "reasoning": "why you judged it this way"
}"""


class VerifierAgent(BaseAgent):
    name = "verifier"

    def __init__(self, logger, llm_client: LLMClient | None = None):
        super().__init__(logger)
        self.llm = llm_client or LLMClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        step_results = agent_input.context.get("execution", [])
        if not step_results:
            self.log_decision(
                detail="Nothing to verify",
                reasoning="Verifier received empty execution results",
            )
            return AgentOutput(success=False, result=[], reasoning="No execution results", next_agent=None)

        verdicts = []
        for r in step_results:
            step = r.get("step", "")
            outcome = r.get("outcome")

            # A step that already errored out during execution never
            # reaches the LLM judgment call — it's flagged directly,
            # classified by whatever exception message the Executor logged.
            if outcome is None:
                verdicts.append({
                    "step": step,
                    "passed": False,
                    "reasoning": f"Execution error: {r.get('error', 'unknown error')}",
                    "failure_type": FailureType.RETRYABLE.value,
                })
                continue

            try:
                verdict = self.llm.complete_json(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=f"Step: {step}\nOutcome produced: {outcome}",
                )
                passed = verdict.get("passed", False)
                reasoning = verdict.get("reasoning", "")

                verdicts.append({
                    "step": step,
                    "passed": passed,
                    "reasoning": reasoning,
                    # A quality miss (LLM ran fine, result just wasn't good
                    # enough) is retryable — a different generation might pass.
                    "failure_type": None if passed else FailureType.RETRYABLE.value,
                })

                self.log_decision(
                    detail=f"Verified step: {step[:60]}",
                    reasoning=reasoning,
                    data={"passed": passed},
                )

            except Exception as e:
                verdicts.append({
                    "step": step,
                    "passed": False,
                    "reasoning": f"Verifier itself failed: {str(e)}",
                    "failure_type": FailureType.TERMINAL.value,
                })
                self.log_decision(
                    detail=f"Verifier error on step: {step[:60]}",
                    reasoning=str(e),
                    data={"error": str(e)},
                )

        all_passed = all(v["passed"] for v in verdicts)

        return AgentOutput(
            success=all_passed,
            result=verdicts,
            reasoning=f"{sum(v['passed'] for v in verdicts)}/{len(verdicts)} steps passed verification",
            next_agent=None,
        )