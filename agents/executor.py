"""
Executor agent — Phase 1 stub.
Real execution (search/email calls) arrives in Phase 4.
"""

from agents.base_agent import BaseAgent, AgentInput, AgentOutput


class ExecutorAgent(BaseAgent):
    name = "executor"

    def run(self, agent_input: AgentInput) -> AgentOutput:
        self.log_decision(
            detail="Executor stub invoked",
            reasoning="Phase 1 placeholder — no execution logic yet",
            data={"context": agent_input.context},
        )
        return AgentOutput(
            success=True,
            result="execution_placeholder",
            reasoning="Stub response, Phase 4 will implement real execution",
            next_agent="verifier",
        )