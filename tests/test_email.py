from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest

from fmcli.account import Account
from fmcli.commands.email import (
    list_emails,
    read_email,
    reply_email,
    search_emails,
    send_email,
)


@pytest.fixture
def account() -> Account:
    return Account(name="personal", email="user@fastmail.com", token="tok123")


def _make_email(
    id: str,
    subject: str,
    from_email: str,
    preview: str,
    received_at: datetime | None = None,
    text_body: str | None = None,
    in_reply_to: list[str] | None = None,
    message_id: list[str] | None = None,
) -> MagicMock:
    email = MagicMock()
    email.id = id
    email.subject = subject
    from_addr = MagicMock()
    from_addr.email = from_email
    email.mail_from = [from_addr]
    email.preview = preview
    email.received_at = received_at or datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    email.in_reply_to = in_reply_to
    email.message_id = message_id or [f"<{id}@example.com>"]

    if text_body is not None:
        body_part = MagicMock()
        body_part.part_id = "1"
        email.text_body = [body_part]
        body_value = MagicMock()
        body_value.value = text_body
        email.body_values = {"1": body_value}
    else:
        email.text_body = []
        email.body_values = {}

    return email


# --- list_emails ---


def test_list_emails(account: Account) -> None:
    client = MagicMock()

    query_resp = MagicMock()
    query_resp.ids = ["id1", "id2"]

    email1 = _make_email("id1", "Hello World", "alice@example.com", "Preview one")
    email2 = _make_email("id2", "Second Email", "bob@example.com", "Preview two")

    get_resp = MagicMock()
    get_resp.data = [email1, email2]

    client.request.side_effect = [query_resp, get_resp]

    result = list_emails(account, client=client)

    assert len(result) == 2
    assert result[0] == {
        "id": "id1",
        "subject": "Hello World",
        "from": "alice@example.com",
        "preview": "Preview one",
        "date": str(email1.received_at),
    }
    assert result[1]["id"] == "id2"
    assert result[1]["subject"] == "Second Email"


def test_list_emails_limit(account: Account) -> None:
    client = MagicMock()

    query_resp = MagicMock()
    query_resp.ids = []

    client.request.return_value = query_resp

    result = list_emails(account, limit=5, client=client)

    assert result == []
    first_call_arg = client.request.call_args_list[0][0][0]
    assert first_call_arg.limit == 5


def test_list_emails_empty(account: Account) -> None:
    client = MagicMock()
    query_resp = MagicMock()
    query_resp.ids = []
    client.request.return_value = query_resp

    result = list_emails(account, client=client)

    assert result == []
    assert client.request.call_count == 1


# --- search_emails ---


def test_search_emails(account: Account) -> None:
    client = MagicMock()

    query_resp = MagicMock()
    query_resp.ids = ["id3"]

    email3 = _make_email("id3", "Invoice", "shop@example.com", "Your invoice is ready")
    get_resp = MagicMock()
    get_resp.data = [email3]

    client.request.side_effect = [query_resp, get_resp]

    result = search_emails(account, query="invoice", client=client)

    assert len(result) == 1
    assert result[0]["subject"] == "Invoice"

    first_call_arg = client.request.call_args_list[0][0][0]
    assert first_call_arg.filter.text == "invoice"


def test_search_emails_limit(account: Account) -> None:
    client = MagicMock()
    query_resp = MagicMock()
    query_resp.ids = []
    client.request.return_value = query_resp

    result = search_emails(account, query="test", limit=10, client=client)

    assert result == []
    first_call_arg = client.request.call_args_list[0][0][0]
    assert first_call_arg.limit == 10


# --- read_email ---


def test_read_email(account: Account) -> None:
    client = MagicMock()

    email = _make_email(
        "id1",
        "Full Email",
        "sender@example.com",
        "Short preview",
        text_body="Full body text here",
    )
    get_resp = MagicMock()
    get_resp.data = [email]

    client.request.return_value = get_resp

    result = read_email(account, email_id="id1", client=client)

    assert result["id"] == "id1"
    assert result["subject"] == "Full Email"
    assert result["from"] == "sender@example.com"
    assert result["body"] == "Full body text here"
    assert "date" in result


def test_read_email_no_text_body(account: Account) -> None:
    client = MagicMock()

    email = _make_email("id1", "No Body", "sender@example.com", "preview")
    email.text_body = []
    email.body_values = {}
    get_resp = MagicMock()
    get_resp.data = [email]

    client.request.return_value = get_resp

    result = read_email(account, email_id="id1", client=client)

    assert result["body"] == ""


def test_read_email_not_found(account: Account) -> None:
    client = MagicMock()
    get_resp = MagicMock()
    get_resp.data = []
    client.request.return_value = get_resp

    with pytest.raises(ValueError, match="not found"):
        read_email(account, email_id="nonexistent", client=client)


# --- send_email ---


def test_send_email(account: Account) -> None:
    client = MagicMock()

    identity_resp = MagicMock()
    identity = MagicMock()
    identity.id = "identity-1"
    identity.email = "user@fastmail.com"
    identity_resp.data = [identity]

    mailbox_resp = MagicMock()
    drafts_mbox = MagicMock()
    drafts_mbox.role = "drafts"
    drafts_mbox.id = "mbox-drafts"
    mailbox_resp.data = [drafts_mbox]

    email_set_resp = MagicMock()
    email_set_resp.created = {"draft1": MagicMock(id="email-abc")}
    email_set_wrapper = MagicMock()
    email_set_wrapper.response = email_set_resp

    submission_set_wrapper = MagicMock()

    client.request.side_effect = [
        identity_resp,
        mailbox_resp,
        [email_set_wrapper, submission_set_wrapper],
    ]

    result = send_email(
        account,
        to="recipient@example.com",
        subject="Test Subject",
        body="Hello there",
        client=client,
    )

    assert result == "email-abc"
    assert client.request.call_count == 3


def test_send_email_error(account: Account) -> None:
    client = MagicMock()

    identity_resp = MagicMock()
    identity = MagicMock()
    identity.id = "identity-1"
    identity.email = "user@fastmail.com"
    identity_resp.data = [identity]

    mailbox_resp = MagicMock()
    drafts_mbox = MagicMock()
    drafts_mbox.role = "drafts"
    drafts_mbox.id = "mbox-drafts"
    mailbox_resp.data = [drafts_mbox]

    email_set_resp = MagicMock()
    email_set_resp.created = None
    email_set_resp.not_created = {"draft1": MagicMock(description="some error")}
    email_set_wrapper = MagicMock()
    email_set_wrapper.response = email_set_resp

    submission_set_wrapper = MagicMock()

    client.request.side_effect = [
        identity_resp,
        mailbox_resp,
        [email_set_wrapper, submission_set_wrapper],
    ]

    with pytest.raises(RuntimeError, match="Failed to create email"):
        send_email(
            account,
            to="recipient@example.com",
            subject="Test",
            body="Body",
            client=client,
        )


# --- reply_email ---


def test_reply_email(account: Account) -> None:
    client = MagicMock()

    original_email = _make_email(
        "orig-id",
        "Original Subject",
        "alice@example.com",
        "original preview",
        message_id=["<orig-id@example.com>"],
    )
    to_addr = MagicMock()
    to_addr.email = "alice@example.com"
    original_email.to = [to_addr]

    get_resp = MagicMock()
    get_resp.data = [original_email]

    identity_resp = MagicMock()
    identity = MagicMock()
    identity.id = "identity-1"
    identity.email = "user@fastmail.com"
    identity_resp.data = [identity]

    mailbox_resp = MagicMock()
    drafts_mbox = MagicMock()
    drafts_mbox.role = "drafts"
    drafts_mbox.id = "mbox-drafts"
    mailbox_resp.data = [drafts_mbox]

    email_set_resp = MagicMock()
    email_set_resp.created = {"draft1": MagicMock(id="reply-id")}
    email_set_wrapper = MagicMock()
    email_set_wrapper.response = email_set_resp

    submission_set_wrapper = MagicMock()

    client.request.side_effect = [
        get_resp,
        identity_resp,
        mailbox_resp,
        [email_set_wrapper, submission_set_wrapper],
    ]

    result = reply_email(account, email_id="orig-id", body="My reply", client=client)

    assert result == "reply-id"
    assert client.request.call_count == 4


def test_reply_email_not_found(account: Account) -> None:
    client = MagicMock()
    get_resp = MagicMock()
    get_resp.data = []
    client.request.return_value = get_resp

    with pytest.raises(ValueError, match="not found"):
        reply_email(account, email_id="bad-id", body="reply", client=client)
