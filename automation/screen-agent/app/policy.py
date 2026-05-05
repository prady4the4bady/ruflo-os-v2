"""
Policy gate — checks the workflow-engine's approvals endpoint before
allowing a screen action to proceed.

When the environment variable ACTION_POLICY is set to
``"require_approval_for_shell"``, every action that mutates the screen
(mouse, keyboard, key-combo) must obtain an explicit approval record from the
workflow-engine before executing.

If the workflow-engine is unavailable or returns a non-approved status the
gate raises PolicyDeniedError with a descriptive reason.
"""
from __future__ import annotations

import os

import httpx

WORKFLOW_ENGINE_URL = os.getenv(
    "WORKFLOW_ENGINE_URL", "http://workflow-engine:8000"
).rstrip("/")

ACTION_POLICY = os.getenv("ACTION_POLICY", "")

_HTTP_TIMEOUT = float(os.getenv("POLICY_TIMEOUT_SECS", "5"))

POLICY_REQUIRE_APPROVAL = "require_approval_for_shell"


class PolicyDeniedError(Exception):
    """Raised when the policy gate rejects an action."""


async def check_policy(action_name: str) -> None:
    """
    Verify that *action_name* is permitted under the active policy.

    * If ``ACTION_POLICY`` is not ``"require_approval_for_shell"`` this
      function returns immediately (no-op).
    * Otherwise it queries ``GET /approvals/pending?action=<action_name>``
      on the workflow-engine and raises :class:`PolicyDeniedError` if the
      action is not approved or if the engine is unreachable.

    Callers should ``await`` this before executing any mutating action.
    """
    if ACTION_POLICY != POLICY_REQUIRE_APPROVAL:
        return  # policy gate is disabled

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(
                f"{WORKFLOW_ENGINE_URL}/approvals/pending",
                params={"action": action_name},
            )
    except httpx.RequestError as exc:
        raise PolicyDeniedError(
            f"Could not reach workflow-engine at {WORKFLOW_ENGINE_URL}: {exc}"
        ) from exc

    if response.status_code != 200:
        raise PolicyDeniedError(
            f"workflow-engine returned {response.status_code} for action '{action_name}'"
        )

    data: dict = response.json()
    if not data.get("approved", False):
        reason = data.get("reason", "no reason given")
        raise PolicyDeniedError(
            f"Action '{action_name}' not approved by workflow-engine: {reason}"
        )
