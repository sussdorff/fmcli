from __future__ import annotations

from typing import Any

from jmapc.fastmail import MaskedEmailGet, MaskedEmailSet

from fmcli.account import Account


def _get_client(account: Account, client: Any = None) -> Any:
    return account.get_jmap_client(client=client)


def list_masked_emails(account: Account, client: Any = None) -> list[dict]:
    """Return all masked emails for the account as a list of dicts."""
    c = _get_client(account, client)
    resp = c.request(MaskedEmailGet(ids=None))
    return [
        {
            "id": me.id,
            "email": me.email,
            "state": me.state.value if me.state is not None else None,
            "for_domain": me.for_domain,
            "description": me.description,
        }
        for me in resp.data
    ]


def create_masked_email(
    account: Account,
    for_domain: str | None = None,
    description: str | None = None,
    client: Any = None,
) -> dict | None:
    """Create a new masked email address and return it as a dict, or None if creation failed."""
    c = _get_client(account, client)
    payload: dict[str, Any] = {"state": "enabled"}
    if for_domain is not None:
        payload["forDomain"] = for_domain
    if description is not None:
        payload["description"] = description
    resp = c.request(MaskedEmailSet(create={"new": payload}))
    created = resp.created or {}
    me = created.get("new")
    if me is None:
        return None
    return {
        "id": me.id,
        "email": me.email,
        "state": me.state.value if me.state is not None else None,
        "for_domain": me.for_domain,
        "description": me.description,
    }


def delete_masked_email(account: Account, masked_email_id: str, client: Any = None) -> None:
    """Delete (disable) a masked email by its ID."""
    c = _get_client(account, client)
    c.request(MaskedEmailSet(update={masked_email_id: {"state": "deleted"}}))
