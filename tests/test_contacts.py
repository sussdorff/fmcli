from __future__ import annotations

from pathlib import Path
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


def _make_download_side_effect(path_to_content: dict[str, str]):
    """Return a side_effect function that writes vCard content to local_path."""
    def _download(remote_path: str, local_path: str) -> None:
        content = path_to_content[remote_path]
        Path(local_path).write_text(content)
    return _download


class TestListContacts:
    def test_returns_list_of_dicts(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["/", "uid-john-001.vcf", "uid-jane-002.vcf"]
        mock_client.download_sync.side_effect = _make_download_side_effect({
            "uid-john-001.vcf": VCARD_JOHN,
            "uid-jane-002.vcf": VCARD_JANE,
        })

        result = list_contacts(account, client=mock_client)

        assert len(result) == 2
        assert result[0] == {"id": "uid-john-001", "name": "John Doe", "email": "john@example.com", "phone": "+1234567890"}
        assert result[1] == {"id": "uid-jane-002", "name": "Jane Smith", "email": "jane@example.com", "phone": "+9876543210"}

    def test_empty_list_when_no_vcf_files(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["/"]

        result = list_contacts(account, client=mock_client)

        assert result == []
        mock_client.download_sync.assert_not_called()

    def test_contact_without_phone(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-bob-003.vcf"]
        mock_client.download_sync.side_effect = _make_download_side_effect({
            "uid-bob-003.vcf": VCARD_NO_TEL,
        })

        result = list_contacts(account, client=mock_client)

        assert len(result) == 1
        assert result[0] == {"id": "uid-bob-003", "name": "Bob No-Phone", "email": "bob@example.com", "phone": ""}

    def test_calls_list_on_client(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["/"]

        list_contacts(account, client=mock_client)

        mock_client.list.assert_called_once_with("/")


class TestSearchContacts:
    def test_filters_by_name(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf", "uid-jane-002.vcf"]
        mock_client.download_sync.side_effect = _make_download_side_effect({
            "uid-john-001.vcf": VCARD_JOHN,
            "uid-jane-002.vcf": VCARD_JANE,
        })

        result = search_contacts(account, query="John", client=mock_client)

        assert len(result) == 1
        assert result[0]["name"] == "John Doe"

    def test_filters_by_email(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf", "uid-jane-002.vcf"]
        mock_client.download_sync.side_effect = _make_download_side_effect({
            "uid-john-001.vcf": VCARD_JOHN,
            "uid-jane-002.vcf": VCARD_JANE,
        })

        result = search_contacts(account, query="jane@example", client=mock_client)

        assert len(result) == 1
        assert result[0]["email"] == "jane@example.com"

    def test_search_case_insensitive(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf"]
        mock_client.download_sync.side_effect = _make_download_side_effect({
            "uid-john-001.vcf": VCARD_JOHN,
        })

        result = search_contacts(account, query="JOHN", client=mock_client)

        assert len(result) == 1
        assert result[0]["name"] == "John Doe"

    def test_returns_empty_when_no_match(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf"]
        mock_client.download_sync.side_effect = _make_download_side_effect({
            "uid-john-001.vcf": VCARD_JOHN,
        })

        result = search_contacts(account, query="nonexistent", client=mock_client)

        assert result == []


class TestCreateContact:
    def test_returns_uid_string(self, account: Account, mock_client: MagicMock) -> None:
        uid = create_contact(account, name="Alice", email="alice@example.com", client=mock_client)

        assert isinstance(uid, str)
        assert len(uid) > 0

    def test_calls_upload_sync(self, account: Account, mock_client: MagicMock) -> None:
        create_contact(account, name="Alice", email="alice@example.com", client=mock_client)

        mock_client.upload_sync.assert_called_once()

    def test_upload_path_ends_with_vcf(self, account: Account, mock_client: MagicMock) -> None:
        create_contact(account, name="Alice", email="alice@example.com", client=mock_client)

        call_kwargs = mock_client.upload_sync.call_args
        remote_path = call_kwargs[1].get("remote_path") or call_kwargs[0][0]
        assert remote_path.endswith(".vcf")

    def test_vcard_content_contains_name_and_email(self, account: Account, mock_client: MagicMock) -> None:
        captured: list[str] = []

        def _capture_upload(remote_path: str, local_path: str) -> None:
            captured.append(Path(local_path).read_text())

        mock_client.upload_sync.side_effect = _capture_upload

        create_contact(account, name="Alice", email="alice@example.com", phone="+111", client=mock_client)

        assert len(captured) == 1
        content = captured[0]
        assert "FN:Alice" in content
        assert "alice@example.com" in content
        assert "+111" in content

    def test_uid_matches_upload_path(self, account: Account, mock_client: MagicMock) -> None:
        uid = create_contact(account, name="Alice", email="alice@example.com", client=mock_client)

        call_kwargs = mock_client.upload_sync.call_args
        remote_path = call_kwargs[1].get("remote_path") or call_kwargs[0][0]
        assert uid in remote_path

    def test_create_without_phone(self, account: Account, mock_client: MagicMock) -> None:
        uid = create_contact(account, name="Phoneless", email="p@example.com", client=mock_client)

        assert isinstance(uid, str)
        mock_client.upload_sync.assert_called_once()


class TestUpdateContact:
    def _make_update_fixtures(self, mock_client: MagicMock) -> list[str]:
        """Configure mock_client and return a list that will hold captured vcard content."""
        mock_client.list.return_value = ["uid-john-001.vcf"]
        mock_client.download_sync.side_effect = _make_download_side_effect({
            "uid-john-001.vcf": VCARD_JOHN,
        })
        captured: list[str] = []

        def _capture_upload(remote_path: str, local_path: str) -> None:
            captured.append(Path(local_path).read_text())

        mock_client.upload_sync.side_effect = _capture_upload
        return captured

    def test_updates_name(self, account: Account, mock_client: MagicMock) -> None:
        captured = self._make_update_fixtures(mock_client)

        update_contact(account, uid="uid-john-001", name="John Updated", client=mock_client)

        mock_client.upload_sync.assert_called_once()
        assert "FN:John Updated" in captured[0]

    def test_updates_email(self, account: Account, mock_client: MagicMock) -> None:
        captured = self._make_update_fixtures(mock_client)

        update_contact(account, uid="uid-john-001", email="newemail@example.com", client=mock_client)

        assert "newemail@example.com" in captured[0]

    def test_updates_phone(self, account: Account, mock_client: MagicMock) -> None:
        captured = self._make_update_fixtures(mock_client)

        update_contact(account, uid="uid-john-001", phone="+9999999999", client=mock_client)

        assert "+9999999999" in captured[0]

    def test_preserves_unmodified_fields(self, account: Account, mock_client: MagicMock) -> None:
        captured = self._make_update_fixtures(mock_client)

        update_contact(account, uid="uid-john-001", name="John Updated", client=mock_client)

        assert "john@example.com" in captured[0]
        assert "+1234567890" in captured[0]

    def test_raises_when_uid_not_found(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf"]

        with pytest.raises(ValueError, match="uid-unknown"):
            update_contact(account, uid="uid-unknown", name="Nobody", client=mock_client)

    def test_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf"]
        mock_client.download_sync.side_effect = _make_download_side_effect({
            "uid-john-001.vcf": VCARD_JOHN,
        })

        result = update_contact(account, uid="uid-john-001", name="X", client=mock_client)

        assert result is None


class TestDeleteContact:
    def test_calls_clean_with_correct_path(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf", "uid-jane-002.vcf"]

        delete_contact(account, uid="uid-john-001", client=mock_client)

        mock_client.clean.assert_called_once_with("uid-john-001.vcf")

    def test_raises_when_uid_not_found(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf"]

        with pytest.raises(ValueError, match="uid-nonexistent"):
            delete_contact(account, uid="uid-nonexistent", client=mock_client)

    def test_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf"]

        result = delete_contact(account, uid="uid-john-001", client=mock_client)

        assert result is None

    def test_does_not_delete_other_contacts(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["uid-john-001.vcf", "uid-jane-002.vcf"]

        delete_contact(account, uid="uid-john-001", client=mock_client)

        mock_client.clean.assert_called_once()
        call_arg = mock_client.clean.call_args[0][0]
        assert "jane" not in call_arg
