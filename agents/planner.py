"""
Planner agent — Phase 1 stub.
Real planning logic (breaking a goal into steps) arrives in Phase 2.
"""

from agents.base_agent import BaseAgent, AgentInput, AgentOutput


class PlannerAgent(BaseAgent):
    name = "planner"

    def run(self, agent_input: AgentInput) -> AgentOutput:
        self.log_decision(
            detail="Planner stub invoked",
            reasoning="Phase 1 placeholder — no planning logic yet",
            data={"goal": agent_input.goal},
        )
        return AgentOutput(
            success=True,
            result="plan_placeholder",
            reasoning="Stub response, Phase 2 will implement real planning",
            next_agent="executor",
        )