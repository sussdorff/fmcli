from __future__ import annotations

from typing import Any

from jmapc import methods as m

from fmcli.account import Account


def _get_client(account: Account, client: Any = None) -> Any:
    return account.get_jmap_client(client=client)


def list_mailboxes(account: Account, client: Any = None) -> list[dict]:
    """Return all mailboxes for the account as a list of dicts."""
    c = _get_client(account, client)
    resp = c.request(m.MailboxGet(ids=None))
    return [
        {
            "id": mb.id,
            "name": mb.name,
            "role": mb.role,
            "total": mb.total_emails,
            "unread": mb.unread_emails,
        }
        for mb in resp.data
    ]


def move_email(account: Account, email_id: str, mailbox_id: str, client: Any = None) -> None:
    """Move an email to the specified mailbox."""
    c = _get_client(account, client)
    c.request(m.EmailSet(update={email_id: {"mailboxIds": {mailbox_id: True}}}))


def mark_read(account: Account, email_id: str, read: bool = True, client: Any = None) -> None:
    """Mark an email as read or unread."""
    c = _get_client(account, client)
    keywords: dict[str, Any] = {"$seen": True} if read else {}
    c.request(m.EmailSet(update={email_id: {"keywords": keywords}}))


def mark_spam(account: Account, email_id: str, client: Any = None) -> None:
    """Move an email to the Junk (spam) mailbox."""
    c = _get_client(account, client)
    mb_resp = c.request(m.MailboxGet(ids=None))
    junk = next((mb for mb in mb_resp.data if mb.role == "junk"), None)
    if junk is None:
        raise ValueError("No Junk mailbox found")
    c.request(m.EmailSet(update={email_id: {"mailboxIds": {junk.id: True}}}))
