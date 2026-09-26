from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fmcli.account import Account
from fmcli.config import AccountConfig
from fmcli.commands.files import (
    list_files,
    download_file,
    upload_file,
    delete_file,
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


class TestListFiles:
    def test_list_files_returns_dicts(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["/", "file.txt", "subdir/"]

        result = list_files(account, client=mock_client)

        assert len(result) == 2
        assert result[0]["name"] == "file.txt"
        assert result[0]["path"] == "file.txt"
        assert result[0]["is_dir"] is False
        assert result[1]["name"] == "subdir"
        assert result[1]["path"] == "subdir/"
        assert result[1]["is_dir"] is True

    def test_list_files_empty_dir(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["/"]

        result = list_files(account, client=mock_client)

        assert result == []

    def test_list_files_custom_path(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["/docs/"]

        list_files(account, path="/docs/", client=mock_client)

        mock_client.list.assert_called_once_with("/docs/")

    def test_list_files_nested_path_extracts_name(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["/docs/", "/docs/report.pdf"]

        result = list_files(account, path="/docs/", client=mock_client)

        assert len(result) == 1
        assert result[0]["name"] == "report.pdf"
        assert result[0]["path"] == "/docs/report.pdf"


class TestDownloadFile:
    def test_download_file(self, account: Account, mock_client: MagicMock) -> None:
        download_file(account, remote_path="/file.txt", local_path="/tmp/file.txt", client=mock_client)

        mock_client.download_sync.assert_called_once_with(
            remote_path="/file.txt",
            local_path="/tmp/file.txt",
        )

class TestUploadFile:
    def test_upload_file(self, account: Account, mock_client: MagicMock) -> None:
        upload_file(account, local_path="/tmp/file.txt", remote_path="/file.txt", client=mock_client)

        mock_client.upload_sync.assert_called_once_with(
            remote_path="/file.txt",
            local_path="/tmp/file.txt",
        )

class TestDeleteFile:
    def test_delete_file(self, account: Account, mock_client: MagicMock) -> None:
        delete_file(account, path="/file.txt", client=mock_client)

        mock_client.clean.assert_called_once_with("/file.txt")
