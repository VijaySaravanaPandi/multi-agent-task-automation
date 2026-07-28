"""
Human approval gate.

Deliberately a separate, simple module (console prompt for now) so it
can be swapped later for a real UI/Slack-approval/web-dashboard flow
without touching agent or orchestrator logic — anything calling
request_human_approval() doesn't need to know how the approval is
actually collected.
"""


def request_human_approval(action_description: str, details: dict) -> bool:
    print("\n" + "=" * 60)
    print("⏸️  HUMAN APPROVAL REQUIRED (high-stakes action)")
    print("=" * 60)
    print(f"Action: {action_description}")
    for k, v in details.items():
        print(f"  {k}: {v}")
    print("=" * 60)

    answer = input("Approve this action? (yes/no): ").strip().lower()
    return answer in ("yes", "y")