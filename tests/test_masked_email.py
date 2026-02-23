from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
import jmapc.fastmail as fm

from fmcli.account import Account
from fmcli.config import AccountConfig
from fmcli.commands.masked_email import create_masked_email, delete_masked_email, list_masked_emails


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


def _make_masked_email(
    id: str,
    email: str,
    state: fm.MaskedEmailState = fm.MaskedEmailState.ENABLED,
    for_domain: str | None = None,
    description: str | None = None,
) -> fm.MaskedEmail:
    return fm.MaskedEmail(
        id=id,
        email=email,
        state=state,
        for_domain=for_domain,
        description=description,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


class TestListMaskedEmails:
    def test_returns_list_of_dicts(self, account: Account, mock_client: MagicMock) -> None:
        me_resp = MagicMock()
        me_resp.data = [
            _make_masked_email("me1", "abc123@fastmail.com", for_domain="example.com", description="Shopping"),
            _make_masked_email("me2", "xyz456@fastmail.com", state=fm.MaskedEmailState.DISABLED),
        ]
        mock_client.request.return_value = me_resp

        result = list_masked_emails(account, client=mock_client)

        assert len(result) == 2
        assert result[0]["id"] == "me1"
        assert result[0]["email"] == "abc123@fastmail.com"
        assert result[0]["state"] == "enabled"
        assert result[0]["for_domain"] == "example.com"
        assert result[0]["description"] == "Shopping"
        assert result[1]["id"] == "me2"
        assert result[1]["state"] == "disabled"

    def test_empty_list(self, account: Account, mock_client: MagicMock) -> None:
        me_resp = MagicMock()
        me_resp.data = []
        mock_client.request.return_value = me_resp

        result = list_masked_emails(account, client=mock_client)
        assert result == []

    def test_calls_masked_email_get(self, account: Account, mock_client: MagicMock) -> None:
        me_resp = MagicMock()
        me_resp.data = []
        mock_client.request.return_value = me_resp

        list_masked_emails(account, client=mock_client)

        mock_client.request.assert_called_once()
        call_arg = mock_client.request.call_args[0][0]
        assert isinstance(call_arg, fm.MaskedEmailGet)


class TestCreateMaskedEmail:
    def test_creates_with_domain_and_description(self, account: Account, mock_client: MagicMock) -> None:
        create_resp = MagicMock()
        create_resp.created = {
            "new": fm.MaskedEmail(id="me-new", email="newaddr@fastmail.com", state=fm.MaskedEmailState.PENDING)
        }
        mock_client.request.return_value = create_resp

        result = create_masked_email(
            account,
            for_domain="shop.example.com",
            description="Online shop",
            client=mock_client,
        )

        mock_client.request.assert_called_once()
        call_arg = mock_client.request.call_args[0][0]
        assert isinstance(call_arg, fm.MaskedEmailSet)
        assert call_arg.create is not None
        # Payload key can be camelCase (forDomain) or snake_case (for_domain) depending on serialization
        create_payload = list(call_arg.create.values())[0]
        domain_value = create_payload.get("forDomain") or create_payload.get("for_domain")
        assert domain_value == "shop.example.com"

        assert result["id"] == "me-new"
        assert result["email"] == "newaddr@fastmail.com"

    def test_creates_without_optional_fields(self, account: Account, mock_client: MagicMock) -> None:
        create_resp = MagicMock()
        create_resp.created = {
            "new": fm.MaskedEmail(id="me-bare", email="bare@fastmail.com", state=fm.MaskedEmailState.ENABLED)
        }
        mock_client.request.return_value = create_resp

        result = create_masked_email(account, client=mock_client)

        assert result["id"] == "me-bare"

    def test_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        create_resp = MagicMock()
        create_resp.created = {}
        mock_client.request.return_value = create_resp

        result = create_masked_email(account, client=mock_client)
        assert result is None


class TestDeleteMaskedEmail:
    def test_disables_masked_email(self, account: Account, mock_client: MagicMock) -> None:
        delete_masked_email(account, masked_email_id="me1", client=mock_client)

        mock_client.request.assert_called_once()
        call_arg = mock_client.request.call_args[0][0]
        assert isinstance(call_arg, fm.MaskedEmailSet)

    def test_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        result = delete_masked_email(account, masked_email_id="me1", client=mock_client)
        assert result is None
