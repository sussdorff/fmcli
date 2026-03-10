from __future__ import annotations

from pathlib import Path
from typing import Any

import jmapc
from jmapc import methods as m
from jmapc.models.email import EmailQueryFilterCondition

from fmcli.account import Account


def _get_client(account: Account, client: Any = None) -> Any:
    return client if client is not None else account.get_jmap_client()


def _email_to_dict(email: Any) -> dict:
    from_email = ""
    if email.mail_from:
        from_email = str(email.mail_from[0].email)
    return {
        "id": email.id,
        "subject": email.subject or "",
        "from": from_email,
        "preview": email.preview or "",
        "date": str(email.received_at) if email.received_at else "",
    }


def _get_body(email: Any) -> str:
    if not email.text_body or not email.body_values:
        return ""
    first_part = email.text_body[0]
    part_id = first_part.part_id
    body_value = email.body_values.get(part_id)
    if body_value is None:
        return ""
    return body_value.value or ""


def _get_drafts_mailbox_id(client: Any) -> str:
    resp = client.request(m.MailboxGet(ids=None))
    for mbox in resp.data:
        if mbox.role == "drafts" or (hasattr(mbox.role, "value") and mbox.role.value == "drafts"):
            return mbox.id
    raise RuntimeError("No Drafts mailbox found")


def _get_identity(client: Any, account_email: str) -> Any:
    resp = client.request(m.IdentityGet())
    for identity in resp.data:
        if identity.email == account_email:
            return identity
    if resp.data:
        return resp.data[0]
    raise RuntimeError("No identity found for account")


def _resolve_mailbox_id(client: Any, mailbox: str) -> str:
    """Resolve a mailbox name or role to its ID."""
    resp = client.request(m.MailboxGet(ids=None))
    mailbox_lower = mailbox.lower()
    # Try matching by role first, then by name (case-insensitive)
    for mb in resp.data:
        if mb.role and mb.role.lower() == mailbox_lower:
            return mb.id
    for mb in resp.data:
        if mb.name and mb.name.lower() == mailbox_lower:
            return mb.id
    raise ValueError(f"Mailbox {mailbox!r} not found")


def list_emails(
    account: Account,
    limit: int = 20,
    mailbox: str | None = None,
    unread_only: bool = False,
    client: Any = None,
) -> list[dict]:
    c = _get_client(account, client)

    filter_condition = None
    filter_kwargs: dict[str, Any] = {}
    if mailbox:
        mailbox_id = _resolve_mailbox_id(c, mailbox)
        filter_kwargs["in_mailbox"] = mailbox_id
    if unread_only:
        filter_kwargs["not_keyword"] = "$seen"
    if filter_kwargs:
        filter_condition = EmailQueryFilterCondition(**filter_kwargs)

    query_resp = c.request(m.EmailQuery(filter=filter_condition, limit=limit))
    if not query_resp.ids:
        return []
    get_resp = c.request(
        m.EmailGet(
            ids=query_resp.ids,
            properties=["id", "subject", "from", "preview", "receivedAt"],
        )
    )
    return [_email_to_dict(e) for e in get_resp.data]


def search_emails(
    account: Account, query: str, limit: int = 20, client: Any = None
) -> list[dict]:
    c = _get_client(account, client)
    query_resp = c.request(
        m.EmailQuery(
            filter=EmailQueryFilterCondition(text=query),
            limit=limit,
        )
    )
    if not query_resp.ids:
        return []
    get_resp = c.request(
        m.EmailGet(
            ids=query_resp.ids,
            properties=["id", "subject", "from", "preview", "receivedAt"],
        )
    )
    return [_email_to_dict(e) for e in get_resp.data]


def read_email(account: Account, email_id: str, client: Any = None) -> dict:
    c = _get_client(account, client)
    get_resp = c.request(
        m.EmailGet(
            ids=[email_id],
            properties=[
                "id",
                "subject",
                "from",
                "preview",
                "receivedAt",
                "textBody",
                "bodyValues",
                "messageId",
                "inReplyTo",
                "attachments",
            ],
            fetch_text_body_values=True,
        )
    )
    if not get_resp.data:
        raise ValueError(f"Email {email_id!r} not found")
    email = get_resp.data[0]
    result = _email_to_dict(email)
    result["body"] = _get_body(email)
    result["attachments"] = _get_attachments(email)
    return result


def _get_attachments(email: Any) -> list[dict]:
    if not email.attachments:
        return []
    return [
        {
            "name": att.name or "(unnamed)",
            "type": att.type or "application/octet-stream",
            "size": att.size or 0,
            "blob_id": att.blob_id,
            "part_id": att.part_id,
        }
        for att in email.attachments
    ]


def download_attachment(
    account: Account,
    email_id: str,
    filename: str | None = None,
    index: int | None = None,
    output_dir: str = ".",
    client: Any = None,
) -> Path:
    """Download an attachment by filename or index (0-based). Returns the saved path."""
    c = _get_client(account, client)
    get_resp = c.request(
        m.EmailGet(
            ids=[email_id],
            properties=["attachments"],
        )
    )
    if not get_resp.data:
        raise ValueError(f"Email {email_id!r} not found")
    email = get_resp.data[0]
    if not email.attachments:
        raise ValueError("Email has no attachments")

    if filename:
        attachment = next((a for a in email.attachments if a.name == filename), None)
        if attachment is None:
            names = [a.name or "(unnamed)" for a in email.attachments]
            raise ValueError(f"Attachment {filename!r} not found. Available: {names}. Use --index to select by position.")
    elif index is not None:
        n = len(email.attachments)
        if index < 0 or index >= n:
            raise ValueError(f"Index {index} out of range (0-{n - 1})")
        attachment = email.attachments[index]
    else:
        attachment = email.attachments[0]

    out_name = attachment.name or f"attachment_{attachment.blob_id}"
    dest = Path(output_dir) / out_name
    c.download_attachment(attachment, dest)
    return dest


def create_draft(
    account: Account,
    to: str,
    subject: str,
    body: str,
    client: Any = None,
    in_reply_to: list[str] | None = None,
) -> str:
    """Create an email draft without sending. Returns the email ID."""
    c = _get_client(account, client)
    drafts_id = _get_drafts_mailbox_id(c)
    draft = jmapc.Email(
        mail_from=[jmapc.EmailAddress(email=account.email, name=None)],
        to=[jmapc.EmailAddress(email=to, name=None)],
        subject=subject,
        mailbox_ids={drafts_id: True},
        keywords={"$draft": True},
        in_reply_to=in_reply_to,
        body_values={"body": jmapc.EmailBodyValue(value=body, is_encoding_problem=False, is_truncated=False)},
        text_body=[jmapc.EmailBodyPart(part_id="body", type="text/plain")],
    )
    resp = c.request(m.EmailSet(create={"draft1": draft}))
    if not resp.created:
        raise RuntimeError(f"Failed to create email draft: {resp.not_created}")
    return resp.created["draft1"].id


def send_email(
    account: Account,
    to: str,
    subject: str,
    body: str,
    client: Any = None,
) -> str:
    if not account.can_send:
        return create_draft(account, to=to, subject=subject, body=body, client=client)

    c = _get_client(account, client)
    identity = _get_identity(c, account.email)
    drafts_id = _get_drafts_mailbox_id(c)

    draft = jmapc.Email(
        mail_from=[jmapc.EmailAddress(email=account.email, name=None)],
        to=[jmapc.EmailAddress(email=to, name=None)],
        subject=subject,
        mailbox_ids={drafts_id: True},
        keywords={"$draft": True},
        body_values={"body": jmapc.EmailBodyValue(value=body, is_encoding_problem=False, is_truncated=False)},
        text_body=[jmapc.EmailBodyPart(part_id="body", type="text/plain")],
    )

    responses = c.request(
        [
            m.EmailSet(create={"draft1": draft}),
            m.EmailSubmissionSet(
                create={
                    "sub1": jmapc.EmailSubmission(
                        email_id="#draft1",
                        identity_id=identity.id,
                    )
                }
            ),
        ]
    )

    email_set_resp = responses[0].response
    if not email_set_resp.created:
        raise RuntimeError(f"Failed to create email draft: {email_set_resp.not_created}")
    created_email = email_set_resp.created["draft1"]
    return created_email.id


def reply_email(account: Account, email_id: str, body: str, client: Any = None) -> str:
    c = _get_client(account, client)

    get_resp = c.request(
        m.EmailGet(
            ids=[email_id],
            properties=["id", "subject", "from", "to", "messageId", "inReplyTo", "receivedAt"],
        )
    )
    if not get_resp.data:
        raise ValueError(f"Email {email_id!r} not found")
    original = get_resp.data[0]

    reply_to_email = original.mail_from[0].email if original.mail_from else ""
    reply_subject = original.subject or ""
    if not reply_subject.lower().startswith("re:"):
        reply_subject = f"Re: {reply_subject}"

    in_reply_to = original.message_id or []

    if not account.can_send:
        return create_draft(
            account,
            to=reply_to_email,
            subject=reply_subject,
            body=body,
            client=c,
            in_reply_to=in_reply_to,
        )

    identity = _get_identity(c, account.email)
    drafts_id = _get_drafts_mailbox_id(c)

    draft = jmapc.Email(
        mail_from=[jmapc.EmailAddress(email=account.email, name=None)],
        to=[jmapc.EmailAddress(email=reply_to_email, name=None)],
        subject=reply_subject,
        in_reply_to=in_reply_to,
        mailbox_ids={drafts_id: True},
        keywords={"$draft": True},
        body_values={"body": jmapc.EmailBodyValue(value=body, is_encoding_problem=False, is_truncated=False)},
        text_body=[jmapc.EmailBodyPart(part_id="body", type="text/plain")],
    )

    responses = c.request(
        [
            m.EmailSet(create={"draft1": draft}),
            m.EmailSubmissionSet(
                create={
                    "sub1": jmapc.EmailSubmission(
                        email_id="#draft1",
                        identity_id=identity.id,
                    )
                }
            ),
        ]
    )

    email_set_resp = responses[0].response
    if not email_set_resp.created:
        raise RuntimeError(f"Failed to create reply draft: {email_set_resp.not_created}")
    created_email = email_set_resp.created["draft1"]
    return created_email.id
