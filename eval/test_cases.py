"""
Fixed evaluation set: known tasks with known-good *expectations*.

We don't check exact LLM wording (that varies run to run) — we check
observable, structural facts: did the right action type get chosen,
did verification pass, did dry-run behave correctly, did the task
finish in a bounded number of attempts. This is what makes the eval
repeatable and meaningful as a regression check.
"""

TEST_CASES = [
    {
        "id": "search_only",
        "goal": "Search for the top 3 health benefits of drinking green tea",
        "expect": {
            "min_steps": 1,
            "requires_action_type": "search",
            "should_complete": True,
        },
    },
    {
        "id": "search_and_email",
        "goal": "Search for 3 benefits of remote work and email a short summary to vijaysaravanapandi1981@gmail.com",
        "expect": {
            "min_steps": 2,
            "requires_action_type": "email",
            "should_complete": True,
            "email_should_be_dry_run": True,  # since DRY_RUN_MODE=true in .env
        },
    },
    {
        "id": "email_disallowed_domain",
        "goal": "Draft a one-line summary about coffee and email it to someone@notarealdomain.xyz",
        "expect": {
            "min_steps": 1,
            "requires_action_type": "email",
            "email_should_be_blocked": True,  # domain not in ALLOWED_EMAIL_DOMAINS
        },
    },
    {
        "id": "vague_goal",
        "goal": "Help me with productivity",
        "expect": {
            "min_steps": 1,
            "should_complete": None,  # no strict expectation — just shouldn't crash
        },
    },
]