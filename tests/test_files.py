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

    def test_list_files_default_path(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["/"]

        list_files(account, client=mock_client)

        mock_client.list.assert_called_once_with("/")

    def test_list_files_detects_directories(self, account: Account, mock_client: MagicMock) -> None:
        mock_client.list.return_value = ["/", "photos/", "notes.txt"]

        result = list_files(account, client=mock_client)

        assert result[0]["is_dir"] is True
        assert result[0]["name"] == "photos"
        assert result[1]["is_dir"] is False
        assert result[1]["name"] == "notes.txt"

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

    def test_download_file_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        result = download_file(account, remote_path="/file.txt", local_path="/tmp/file.txt", client=mock_client)

        assert result is None

    def test_download_file_passes_paths_correctly(self, account: Account, mock_client: MagicMock) -> None:
        download_file(account, remote_path="/docs/report.pdf", local_path="/home/user/report.pdf", client=mock_client)

        call_kwargs = mock_client.download_sync.call_args[1]
        assert call_kwargs["remote_path"] == "/docs/report.pdf"
        assert call_kwargs["local_path"] == "/home/user/report.pdf"


class TestUploadFile:
    def test_upload_file(self, account: Account, mock_client: MagicMock) -> None:
        upload_file(account, local_path="/tmp/file.txt", remote_path="/file.txt", client=mock_client)

        mock_client.upload_sync.assert_called_once_with(
            remote_path="/file.txt",
            local_path="/tmp/file.txt",
        )

    def test_upload_file_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        result = upload_file(account, local_path="/tmp/file.txt", remote_path="/file.txt", client=mock_client)

        assert result is None

    def test_upload_file_passes_paths_correctly(self, account: Account, mock_client: MagicMock) -> None:
        upload_file(account, local_path="/home/user/photo.jpg", remote_path="/photos/photo.jpg", client=mock_client)

        call_kwargs = mock_client.upload_sync.call_args[1]
        assert call_kwargs["remote_path"] == "/photos/photo.jpg"
        assert call_kwargs["local_path"] == "/home/user/photo.jpg"


class TestDeleteFile:
    def test_delete_file(self, account: Account, mock_client: MagicMock) -> None:
        delete_file(account, path="/file.txt", client=mock_client)

        mock_client.clean.assert_called_once_with("/file.txt")

    def test_delete_file_returns_none(self, account: Account, mock_client: MagicMock) -> None:
        result = delete_file(account, path="/file.txt", client=mock_client)

        assert result is None

    def test_delete_file_correct_path(self, account: Account, mock_client: MagicMock) -> None:
        delete_file(account, path="/docs/old-report.pdf", client=mock_client)

        mock_client.clean.assert_called_once_with("/docs/old-report.pdf")

    def test_delete_file_does_not_call_other_methods(self, account: Account, mock_client: MagicMock) -> None:
        delete_file(account, path="/file.txt", client=mock_client)

        mock_client.download_sync.assert_not_called()
        mock_client.upload_sync.assert_not_called()
        mock_client.list.assert_not_called()
