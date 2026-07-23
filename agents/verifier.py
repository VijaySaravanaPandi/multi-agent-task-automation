"""
Verifier agent — Phase 1 stub.
Real verification + error classification arrives in Phase 3.
"""

from agents.base_agent import BaseAgent, AgentInput, AgentOutput


class VerifierAgent(BaseAgent):
    name = "verifier"

    def run(self, agent_input: AgentInput) -> AgentOutput:
        self.log_decision(
            detail="Verifier stub invoked",
            reasoning="Phase 1 placeholder — no verification logic yet",
            data={"context": agent_input.context},
        )
        return AgentOutput(
            success=True,
            result="verification_placeholder",
            reasoning="Stub response, Phase 3 will implement real verification",
            next_agent=None,
        )