"""
Executor agent — Phase 8 fix.

Now carries forward accumulated results from earlier steps in the same
run, so steps like "extract from the search results" can actually see
prior outputs instead of guessing a brand-new search. This closes the
gap where the LLM misclassified analysis steps as search steps simply
because no prior context was available to work from.
"""

from agents.base_agent import BaseAgent, AgentInput, AgentOutput
from core.llm_client import LLMClient
from core.errors import classify_exception
from core.tools import search_web, agent_requests_email, send_email, ToolError
from core.risk import get_risk_tier, RiskTier
from core.approval import request_human_approval

SYSTEM_PROMPT = """You are a task execution agent. You will be given one
step from a plan, plus any results already produced by earlier steps in
this same task (if any).

Decide what kind of action this step needs:
- "search": ONLY if this step requires finding NEW information online
  that isn't already available in the prior results shown to you.
- "email": if it requires sending an email (only if the step explicitly
  mentions sending/emailing something to someone).
- "other": if this step analyzes, extracts, filters, ranks, or summarizes
  information that was ALREADY gathered in a prior step. If prior results
  are provided below and this step references "the results", "the search",
  or similar, you MUST use those prior results and classify as "other" —
  do NOT perform a new search.

Respond ONLY with valid JSON in this exact shape, no other text:
{
  "action_type": "search" | "email" | "other",
  "search_query": "query string if action_type is search, else empty string",
  "email_to": "recipient address if action_type is email, else empty string",
  "email_subject": "subject if action_type is email, else empty string",
  "email_body": "body if action_type is email, else empty string",
  "result": "if action_type is other, produce the ACTUAL extracted/summarized content using prior results provided, not a placeholder description",
  "reasoning": "why you classified and handled it this way"
}"""


class ExecutorAgent(BaseAgent):
    name = "executor"

    def __init__(self, logger, llm_client: LLMClient | None = None):
        super().__init__(logger)
        self.llm = llm_client or LLMClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        steps = agent_input.context.get("plan", [])
        prior_results = agent_input.context.get("prior_results", {})

        if not steps:
            self.log_decision(detail="No steps to execute", reasoning="Empty plan received")
            return AgentOutput(success=False, result=None, reasoning="Empty plan", next_agent=None)

        step_results = []
        for i, step in enumerate(steps, start=1):
            try:
                prior_context = self._format_prior_results(prior_results)
                user_prompt = f"Step {i}: {step}"
                if prior_context:
                    user_prompt += f"\n\nResults already available from earlier steps:\n{prior_context}"

                decision = self.llm.complete_json(SYSTEM_PROMPT, user_prompt)
                action_type = decision.get("action_type", "other")
                reasoning = decision.get("reasoning", "")

                if action_type == "search":
                    outcome = self._handle_search(step, decision, i, reasoning)
                elif action_type == "email":
                    outcome = self._handle_email(step, decision, i, reasoning)
                else:
                    outcome = decision.get("result", "")
                    self.log_decision(
                        detail=f"Executed step {i}/{len(steps)} (other): {step}",
                        reasoning=reasoning,
                        data={"outcome": outcome},
                    )

                step_results.append({"step": step, "action_type": action_type, "outcome": outcome})
                # Feed this step's outcome forward so later steps in the
                # SAME batch can reference it too.
                prior_results[step] = outcome

            except Exception as e:
                failure_type = classify_exception(e)
                step_results.append({
                    "step": step, "outcome": None,
                    "error": str(e), "failure_type": failure_type.value,
                })
                self.log_decision(
                    detail=f"Step {i} failed: {step}",
                    reasoning=f"Classified as {failure_type.value}: {str(e)}",
                    data={"error": str(e)},
                )

        all_succeeded = all(r.get("outcome") is not None for r in step_results)
        return AgentOutput(
            success=all_succeeded,
            result=step_results,
            reasoning=f"Executed {len(steps)} steps, {'all succeeded' if all_succeeded else 'some failed'}",
            next_agent="verifier",
        )

    def _format_prior_results(self, prior_results: dict) -> str:
        if not prior_results:
            return ""
        parts = []
        for step, outcome in prior_results.items():
            if isinstance(outcome, list):  # search results
                snippet = "; ".join(
                    f"{r.get('title', '')}: {r.get('content', '')[:150]}"
                    for r in outcome if isinstance(r, dict)
                )
                parts.append(f"- From step \"{step}\": {snippet}")
            elif isinstance(outcome, str) and outcome:
                parts.append(f"- From step \"{step}\": {outcome}")
        return "\n".join(parts)

    def _handle_search(self, step, decision, i, reasoning):
        query = decision.get("search_query", "") or step
        try:
            results = search_web(query, max_results=3)
            self.log_decision(
                detail=f"Executed step {i} (real search): {query}",
                reasoning=reasoning,
                data={"query": query, "num_results": len(results)},
            )
            return results
        except ToolError as e:
            self.log_decision(
                detail=f"Search tool failed on step {i}",
                reasoning=str(e),
                data={"query": query},
            )
            raise

    def _handle_email(self, step, decision, i, reasoning):
        to = decision.get("email_to", "")
        subject = decision.get("email_subject", "")
        body = decision.get("email_body", "")

        intent = agent_requests_email(to, subject, body)
        self.log_decision(
            detail=f"Agent DECIDED to send email for step {i}",
            reasoning=reasoning,
            data={"intent": intent},
        )

        risk_tier = get_risk_tier("email")
        self.logger.log_event(
            agent_name="system",
            event_type="decision",
            detail=f"Risk tier for step {i} email action: {risk_tier.value}",
            reasoning="Email is classified high-stakes; requires human approval before sending",
        )

        if risk_tier == RiskTier.HIGH:
            approved = request_human_approval(
                action_description=f"Send email (step {i}: {step})",
                details={"to": to, "subject": subject, "body": body[:200]},
            )
            self.logger.log_event(
                agent_name="system",
                event_type="decision",
                detail=f"Human approval for step {i} email: {'APPROVED' if approved else 'DENIED'}",
                reasoning="Human-in-the-loop gate result",
                data={"approved": approved},
            )
            if not approved:
                return {
                    "sent": False,
                    "dry_run": None,
                    "reason": "Blocked: human did not approve this high-stakes action",
                }

        result = send_email(to=to, subject=subject, body=body)
        self.logger.log_event(
            agent_name="system",
            event_type="external_action",
            detail=f"Email send attempt for step {i}: sent={result['sent']}",
            reasoning=result.get("reason", ""),
            data=result,
        )
        return result