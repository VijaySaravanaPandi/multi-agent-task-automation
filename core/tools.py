"""
Real external actions: web search and email sending.

Every function here is a genuine side effect on the outside world (or,
in email's case, a carefully gated one). Two safety principles are
enforced structurally, not just by convention:

1. DRY_RUN_MODE gates the only truly irreversible action (sending email).
   Default is True. It must be explicitly and deliberately turned off.
2. ALLOWED_EMAIL_DOMAINS is checked AFTER the agent has already decided
   to send, and BEFORE anything touches the network. An agent "deciding"
   to send and the system "actually sending" are two different function
   calls with a hard gate between them — see send_email() below.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from config.settings import settings


class ToolError(Exception):
    """Raised for tool-level failures — caught and classified by callers."""
    pass


# ---------------------------------------------------------------------
# SEARCH — low stakes, always runs for real (no dry-run gate needed;
# reading the web has no side effects on anyone else).
# ---------------------------------------------------------------------

_search_cache: dict[str, list[dict]] = {}


def search_web(query: str, max_results: int = 3) -> list[dict]:
    """
    Deliberate cost optimization: identical queries within the same
    process return the cached result instead of hitting Tavily again.
    This directly avoids paying for (and waiting on) redundant search
    calls when the Planner produces overlapping steps.
    """
    cache_key = f"{query.strip().lower()}::{max_results}"
    if cache_key in _search_cache:
        return _search_cache[cache_key]

    if not settings.SEARCH_API_KEY:
        raise ToolError("SEARCH_API_KEY is not set — cannot perform real search")

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.SEARCH_API_KEY,
                "query": query,
                "max_results": max_results,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        results = [
            {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
            for r in data.get("results", [])
        ]
        _search_cache[cache_key] = results
        return results
    except requests.exceptions.RequestException as e:
        raise ToolError(f"Search request failed: {str(e)}")


# ---------------------------------------------------------------------
# EMAIL — high stakes. Two-step by design:
#   agent_requests_email()  -> just records intent, no side effect
#   send_email()             -> the ONLY function that can actually send,
#                                and it re-checks dry-run + allow-list
#                                itself rather than trusting the caller.
# ---------------------------------------------------------------------

def agent_requests_email(to: str, subject: str, body: str) -> dict:
    """Called when an agent DECIDES an email should be sent. This does
    NOT send anything — it just returns a structured request. The
    orchestrator logs this as the agent's decision, separately from
    whatever send_email() later does with it."""
    return {"to": to, "subject": subject, "body": body}


def is_domain_allowed(email_address: str) -> bool:
    if not settings.ALLOWED_EMAIL_DOMAINS:
        return False  # fail closed: no allow-list configured = nothing is allowed
    domain = email_address.strip().lower().split("@")[-1]
    return domain in [d.lower() for d in settings.ALLOWED_EMAIL_DOMAINS]


def send_email(to: str, subject: str, body: str) -> dict:
    """
    The only function permitted to actually transmit an email.
    Returns a result dict describing what actually happened —
    caller must not assume success just because no exception was raised.
    """
    if not is_domain_allowed(to):
        return {
            "sent": False,
            "dry_run": settings.DRY_RUN_MODE,
            "reason": f"Recipient domain not in ALLOWED_EMAIL_DOMAINS: {to}",
        }

    if settings.DRY_RUN_MODE:
        # This is the default path. Nothing touches the network.
        return {
            "sent": False,
            "dry_run": True,
            "reason": "DRY_RUN_MODE is enabled — email was NOT actually sent",
            "would_have_sent": {"to": to, "subject": subject, "body": body},
        }

    if not settings.EMAIL_ADDRESS or not settings.EMAIL_PASSWORD:
        raise ToolError("EMAIL_ADDRESS or EMAIL_PASSWORD not set — cannot send real email")

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_ADDRESS
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        context = ssl.create_default_context()
        with smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_ADDRESS, to, msg.as_string())

        return {"sent": True, "dry_run": False, "reason": "Email sent successfully"}

    except smtplib.SMTPException as e:
        raise ToolError(f"SMTP send failed: {str(e)}")