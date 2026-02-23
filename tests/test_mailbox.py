from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import jmapc

from fmcli.account import Account
from fmcli.config import AccountConfig
from fmcli.commands.mailbox import list_mailboxes, mark_read, mark_spam, move_email


@pytest.fixture
def account() -> Account:
    return Account.from_config(
        AccountConfig(
            name="personal",
            email="user@fastmail.com",
            token="tok123",
        )
    )


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


def _make_mailbox(id: str, name: str, role: str | None = None, total: int = 0, unread: int = 0) -> jmapc.Mailbox:
    return jmapc.Mailbox(
        id=id,
        name=name,
        role=role,
        total_emails=total,
        unread_emails=unread,
    )


class TestListMailboxes:
    def test_returns_list_of_dicts(self, account: Account, mock_client: MagicMock) -> None:
        mb_resp = MagicMock()
        mb_resp.data = [
            _make_mailbox("mb1", "Inbox", "inbox", total=10, unread=2),
            _make_mailbox("mb2", "Sent", "sent", total=50, unread=0),
            _make_mailbox("mb3", "Spam", "junk", total=3, unread=1),
        ]
        mock_client.request.return_value = mb_resp

        result = list_mailboxes(account, client=mock_client)

        assert len(result) == 3
        assert result[0] == {"id": "mb1", "name": "Inbox", "role": "inbox", "total": 10, "unread": 2}
        assert result[1] == {"id": "mb2", "name": "Sent", "role": "sent", "total": 50, "unread": 0}
        assert result[2] == {"id": "mb3", "name": "Spam", "role": "junk", "total": 3, "unread": 1}

    def test_empty_mailbox_list(self, account: Account, mock_client: MagicMock) -> None:
        mb_resp = MagicMock()
        mb_resp.data = []
        mock_client.request.return_value = mb_resp

        result = list_mailboxes(account, client=mock_client)

        assert result == []

    def test_calls_mailbox_get(self, account: Account, mock_client: MagicMock) -> None:
        mb_resp = MagicMock()
        mb_resp.data = []
        mock_client.request.return_value = mb_resp

        list_mailboxes(account, client=mock_client)

        mock_client.request.assert_called_once()
        call_arg = mock_client.request.call_args[0][0]
        assert isinstance(call_arg, jmapc.methods.MailboxGet)


class TestMoveEmail:
    def test_calls_email_set_with_mailbox_ids(self, account: Account, mock_client: MagicMock) -> None:
        move_email(account, email_id="email-42", mailbox_id="mb-inbox", client=mock_client)

        mock_client.request.assert_called_once()
        call_arg = mock_client.request.call_args[0][0]
        assert isinstance(call_arg, jmapc.methods.EmailSet)
        assert call_arg.update == {"email-42": {"mailboxIds": {"mb-inbox": True}}}

    def test_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        result = move_email(account, email_id="e1", mailbox_id="mb1", client=mock_client)
        assert result is None


class TestMarkRead:
    def test_mark_read_sets_seen_true(self, account: Account, mock_client: MagicMock) -> None:
        mark_read(account, email_id="email-42", read=True, client=mock_client)

        mock_client.request.assert_called_once()
        call_arg = mock_client.request.call_args[0][0]
        assert isinstance(call_arg, jmapc.methods.EmailSet)
        assert call_arg.update == {"email-42": {"keywords": {"$seen": True}}}

    def test_mark_unread_clears_keywords(self, account: Account, mock_client: MagicMock) -> None:
        mark_read(account, email_id="email-42", read=False, client=mock_client)

        mock_client.request.assert_called_once()
        call_arg = mock_client.request.call_args[0][0]
        assert isinstance(call_arg, jmapc.methods.EmailSet)
        assert call_arg.update == {"email-42": {"keywords": {}}}

    def test_default_read_is_true(self, account: Account, mock_client: MagicMock) -> None:
        mark_read(account, email_id="email-1", client=mock_client)

        call_arg = mock_client.request.call_args[0][0]
        assert call_arg.update["email-1"]["keywords"]["$seen"] is True

    def test_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        result = mark_read(account, email_id="e1", client=mock_client)
        assert result is None


class TestMarkSpam:
    def test_moves_email_to_junk_mailbox(self, account: Account, mock_client: MagicMock) -> None:
        mb_resp = MagicMock()
        mb_resp.data = [
            _make_mailbox("mb-inbox", "Inbox", "inbox"),
            _make_mailbox("mb-junk", "Spam", "junk"),
        ]
        email_set_resp = MagicMock()
        mock_client.request.side_effect = [mb_resp, email_set_resp]

        mark_spam(account, email_id="email-99", client=mock_client)

        assert mock_client.request.call_count == 2
        # First call: MailboxGet
        first_arg = mock_client.request.call_args_list[0][0][0]
        assert isinstance(first_arg, jmapc.methods.MailboxGet)
        # Second call: EmailSet with junk mailbox
        second_arg = mock_client.request.call_args_list[1][0][0]
        assert isinstance(second_arg, jmapc.methods.EmailSet)
        assert second_arg.update == {"email-99": {"mailboxIds": {"mb-junk": True}}}

    def test_raises_if_no_junk_mailbox(self, account: Account, mock_client: MagicMock) -> None:
        mb_resp = MagicMock()
        mb_resp.data = [
            _make_mailbox("mb-inbox", "Inbox", "inbox"),
        ]
        mock_client.request.return_value = mb_resp

        with pytest.raises(ValueError, match="No Junk mailbox found"):
            mark_spam(account, email_id="email-99", client=mock_client)

    def test_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        mb_resp = MagicMock()
        mb_resp.data = [_make_mailbox("mb-junk", "Spam", "junk")]
        email_set_resp = MagicMock()
        mock_client.request.side_effect = [mb_resp, email_set_resp]

        result = mark_spam(account, email_id="e1", client=mock_client)
        assert result is None
