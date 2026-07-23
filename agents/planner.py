"""
Planner agent — Phase 2 real implementation.

Takes a high-level goal and breaks it into a concrete, ordered list of
steps the Executor can act on. This is the first real "agent decision"
in the system — we log not just the plan, but why the model produced it.
"""

from agents.base_agent import BaseAgent, AgentInput, AgentOutput
from core.llm_client import LLMClient

SYSTEM_PROMPT = """You are a task planning agent. Given a goal, break it into
a short, ordered list of concrete steps an execution agent can carry out.
Respond ONLY with valid JSON in this exact shape, no other text:
{
  "steps": ["step 1 description", "step 2 description", ...],
  "reasoning": "one or two sentences on why you chose this breakdown"
}
Keep it to 3-6 steps. Be concrete and actionable, not vague."""


class PlannerAgent(BaseAgent):
    name = "planner"

    def __init__(self, logger, llm_client: LLMClient | None = None):
        super().__init__(logger)
        self.llm = llm_client or LLMClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        try:
            plan = self.llm.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"Goal: {agent_input.goal}",
            )
            steps = plan.get("steps", [])
            reasoning = plan.get("reasoning", "")

            self.log_decision(
                detail=f"Generated plan with {len(steps)} steps",
                reasoning=reasoning,
                data={"steps": steps},
            )

            return AgentOutput(
                success=True,
                result=steps,
                reasoning=reasoning,
                next_agent="executor",
            )

        except Exception as e:
            self.log_decision(
                detail="Planning failed",
                reasoning=f"LLM call or JSON parsing raised: {str(e)}",
                data={"error": str(e)},
            )
            return AgentOutput(
                success=False,
                result=None,
                reasoning=f"Planner failed: {str(e)}",
                next_agent=None,
            )