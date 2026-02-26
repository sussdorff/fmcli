from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fmcli.account import Account
from fmcli.config import AccountConfig
from fmcli.commands.contacts import (
    list_contacts,
    search_contacts,
    create_contact,
    update_contact,
    delete_contact,
)


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
    """Mock CardDAVClient that returns contacts via list_contacts()."""
    return MagicMock()


VCARD_JOHN = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-john-001
FN:John Doe
EMAIL:john@example.com
TEL:+1234567890
END:VCARD"""

VCARD_JANE = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-jane-002
FN:Jane Smith
EMAIL:jane@example.com
TEL:+9876543210
END:VCARD"""

VCARD_NO_TEL = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-bob-003
FN:Bob No-Phone
EMAIL:bob@example.com
END:VCARD"""


def _make_contact_entries(*vcards: tuple[str, str, str]) -> list[dict]:
    """Build the list of dicts returned by CardDAVClient.list_contacts().

    Each tuple is (href, etag, vcard_text).
    """
    return [
        {"href": href, "etag": etag, "vcard": vcard}
        for href, etag, vcard in vcards
    ]


class TestListContacts:
    def test_returns_list_of_dicts(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "etag1", VCARD_JOHN),
            ("/ab/uid-jane-002.vcf", "etag2", VCARD_JANE),
        )

        result = list_contacts(account, client=mock_client)

        assert len(result) == 2
        assert result[0]["id"] == "uid-john-001"
        assert result[0]["name"] == "John Doe"
        assert result[0]["email"] == "john@example.com"
        assert result[0]["phone"] == "+1234567890"
        assert result[1]["id"] == "uid-jane-002"
        assert result[1]["name"] == "Jane Smith"
        assert result[1]["email"] == "jane@example.com"
        assert result[1]["phone"] == "+9876543210"

    def test_empty_list_when_no_contacts(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = []

        result = list_contacts(account, client=mock_client)

        assert result == []

    def test_contact_without_phone(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-bob-003.vcf", "etag3", VCARD_NO_TEL),
        )

        result = list_contacts(account, client=mock_client)

        assert len(result) == 1
        assert result[0]["id"] == "uid-bob-003"
        assert result[0]["name"] == "Bob No-Phone"
        assert result[0]["email"] == "bob@example.com"
        assert result[0]["phone"] == ""

    def test_calls_list_contacts_on_client(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = []

        list_contacts(account, client=mock_client)

        mock_client.list_contacts.assert_called_once()

    def test_includes_href_and_etag(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "etag1", VCARD_JOHN),
        )

        result = list_contacts(account, client=mock_client)

        assert result[0]["href"] == "/ab/uid-john-001.vcf"
        assert result[0]["etag"] == "etag1"


class TestSearchContacts:
    def test_filters_by_name(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "e1", VCARD_JOHN),
            ("/ab/uid-jane-002.vcf", "e2", VCARD_JANE),
        )

        result = search_contacts(account, query="John", client=mock_client)

        assert len(result) == 1
        assert result[0]["name"] == "John Doe"

    def test_filters_by_email(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "e1", VCARD_JOHN),
            ("/ab/uid-jane-002.vcf", "e2", VCARD_JANE),
        )

        result = search_contacts(account, query="jane@example", client=mock_client)

        assert len(result) == 1
        assert result[0]["email"] == "jane@example.com"

    def test_search_case_insensitive(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "e1", VCARD_JOHN),
        )

        result = search_contacts(account, query="JOHN", client=mock_client)

        assert len(result) == 1
        assert result[0]["name"] == "John Doe"

    def test_returns_empty_when_no_match(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "e1", VCARD_JOHN),
        )

        result = search_contacts(account, query="nonexistent", client=mock_client)

        assert result == []


class TestCreateContact:
    def test_returns_uid_string(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.create_contact.return_value = "/ab/some-uid.vcf"

        uid = create_contact(account, name="Alice", email="alice@example.com", client=mock_client)

        assert isinstance(uid, str)
        assert len(uid) > 0

    def test_calls_create_contact(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.create_contact.return_value = "/ab/some-uid.vcf"

        create_contact(account, name="Alice", email="alice@example.com", client=mock_client)

        mock_client.create_contact.assert_called_once()

    def test_vcard_contains_name_and_email(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.create_contact.return_value = "/ab/some-uid.vcf"

        create_contact(account, name="Alice", email="alice@example.com", phone="+111", client=mock_client)

        call_kwargs = mock_client.create_contact.call_args
        vcard_text = call_kwargs[1].get("vcard_text") or call_kwargs[0][0]
        assert "Alice" in vcard_text
        assert "alice@example.com" in vcard_text
        assert "+111" in vcard_text

    def test_uid_passed_to_client(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.create_contact.return_value = "/ab/some-uid.vcf"

        uid = create_contact(account, name="Alice", email="alice@example.com", client=mock_client)

        call_kwargs = mock_client.create_contact.call_args[1]
        assert call_kwargs["uid"] == uid

    def test_create_without_phone(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.create_contact.return_value = "/ab/some-uid.vcf"

        uid = create_contact(account, name="Phoneless", email="p@example.com", client=mock_client)

        assert isinstance(uid, str)
        mock_client.create_contact.assert_called_once()


class TestUpdateContact:
    def _setup_mock(self, mock_client: MagicMock) -> None:
        """Configure mock_client to return John for list_contacts."""
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "etag1", VCARD_JOHN),
        )

    def test_updates_name(self, account: Account, mock_client: MagicMock) -> None:
        self._setup_mock(mock_client)

        update_contact(account, uid="uid-john-001", name="John Updated", client=mock_client)

        mock_client.update_contact.assert_called_once()
        call_kwargs = mock_client.update_contact.call_args[1]
        assert call_kwargs["href"] == "/ab/uid-john-001.vcf"
        assert "John Updated" in call_kwargs["vcard_text"]

    def test_updates_email(self, account: Account, mock_client: MagicMock) -> None:
        self._setup_mock(mock_client)

        update_contact(account, uid="uid-john-001", email="newemail@example.com", client=mock_client)

        call_kwargs = mock_client.update_contact.call_args[1]
        assert "newemail@example.com" in call_kwargs["vcard_text"]

    def test_updates_phone(self, account: Account, mock_client: MagicMock) -> None:
        self._setup_mock(mock_client)

        update_contact(account, uid="uid-john-001", phone="+9999999999", client=mock_client)

        call_kwargs = mock_client.update_contact.call_args[1]
        assert "+9999999999" in call_kwargs["vcard_text"]

    def test_preserves_unmodified_fields(self, account: Account, mock_client: MagicMock) -> None:
        self._setup_mock(mock_client)

        update_contact(account, uid="uid-john-001", name="John Updated", client=mock_client)

        call_kwargs = mock_client.update_contact.call_args[1]
        vcard = call_kwargs["vcard_text"]
        assert "john@example.com" in vcard
        assert "+1234567890" in vcard

    def test_raises_when_uid_not_found(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "etag1", VCARD_JOHN),
        )

        with pytest.raises(ValueError, match="uid-unknown"):
            update_contact(account, uid="uid-unknown", name="Nobody", client=mock_client)

    def test_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        self._setup_mock(mock_client)

        result = update_contact(account, uid="uid-john-001", name="X", client=mock_client)

        assert result is None


class TestDeleteContact:
    def test_calls_delete_with_correct_href(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "etag1", VCARD_JOHN),
            ("/ab/uid-jane-002.vcf", "etag2", VCARD_JANE),
        )

        delete_contact(account, uid="uid-john-001", client=mock_client)

        mock_client.delete_contact.assert_called_once_with(href="/ab/uid-john-001.vcf")

    def test_raises_when_uid_not_found(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "etag1", VCARD_JOHN),
        )

        with pytest.raises(ValueError, match="uid-nonexistent"):
            delete_contact(account, uid="uid-nonexistent", client=mock_client)

    def test_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "etag1", VCARD_JOHN),
        )

        result = delete_contact(account, uid="uid-john-001", client=mock_client)

        assert result is None

    def test_does_not_delete_other_contacts(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list_contacts.return_value = _make_contact_entries(
            ("/ab/uid-john-001.vcf", "etag1", VCARD_JOHN),
            ("/ab/uid-jane-002.vcf", "etag2", VCARD_JANE),
        )

        delete_contact(account, uid="uid-john-001", client=mock_client)

        mock_client.delete_contact.assert_called_once()
        call_kwargs = mock_client.delete_contact.call_args[1]
        assert "jane" not in call_kwargs["href"]
