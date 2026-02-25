from __future__ import annotations

import pytest
import jmapc
import caldav
from webdav3.client import Client as WebDAVClient

from fmcli.config import AccountConfig
from fmcli.account import Account


@pytest.fixture
def acc_config() -> AccountConfig:
    return AccountConfig(
        name="personal",
        email="user@fastmail.com",
        token="tok123",
        app_password="apppass",
    )


@pytest.fixture
def acc_config_no_apppass() -> AccountConfig:
    return AccountConfig(
        name="personal",
        email="user@fastmail.com",
        token="tok123",
        app_password=None,
    )


def test_from_config(acc_config: AccountConfig) -> None:
    account = Account.from_config(acc_config)
    assert account.name == "personal"
    assert account.email == "user@fastmail.com"
    assert account.token == "tok123"
    assert account.app_password == "apppass"
    assert account.can_send is False


def test_from_config_can_send() -> None:
    config = AccountConfig(
        name="bot",
        email="bot@fastmail.com",
        token="bottok",
        can_send=True,
    )
    account = Account.from_config(config)
    assert account.can_send is True


def test_get_jmap_client_returns_client(acc_config: AccountConfig, mocker) -> None:
    mock_create = mocker.patch.object(jmapc.Client, "create_with_api_token")
    account = Account.from_config(acc_config)
    client = account.get_jmap_client()
    mock_create.assert_called_once_with(host="api.fastmail.com", api_token="tok123")
    assert client is mock_create.return_value


def test_get_caldav_client_returns_client(acc_config: AccountConfig, mocker) -> None:
    mock_dav = mocker.patch("fmcli.account.caldav.DAVClient")
    account = Account.from_config(acc_config)
    client = account.get_caldav_client()
    mock_dav.assert_called_once_with(
        url="https://caldav.fastmail.com/dav/",
        username="user@fastmail.com",
        password="apppass",
    )
    assert client is mock_dav.return_value


def test_get_carddav_client_returns_client(acc_config: AccountConfig, mocker) -> None:
    mock_webdav = mocker.patch("fmcli.account.WebDAVClient")
    account = Account.from_config(acc_config)
    client = account.get_carddav_client()
    mock_webdav.assert_called_once_with({
        "webdav_hostname": "https://carddav.fastmail.com/dav/",
        "webdav_login": "user@fastmail.com",
        "webdav_password": "apppass",
    })
    assert client is mock_webdav.return_value


def test_get_webdav_client_returns_client(acc_config: AccountConfig, mocker) -> None:
    mock_webdav = mocker.patch("fmcli.account.WebDAVClient")
    account = Account.from_config(acc_config)
    client = account.get_webdav_client()
    mock_webdav.assert_called_once_with({
        "webdav_hostname": "https://webdav.fastmail.com/",
        "webdav_login": "user@fastmail.com",
        "webdav_password": "apppass",
    })
    assert client is mock_webdav.return_value


def test_client_injection(acc_config: AccountConfig) -> None:
    account = Account.from_config(acc_config)
    sentinel = object()
    assert account.get_jmap_client(client=sentinel) is sentinel
    assert account.get_caldav_client(client=sentinel) is sentinel
    assert account.get_carddav_client(client=sentinel) is sentinel
    assert account.get_webdav_client(client=sentinel) is sentinel


def test_app_password_fallback(acc_config_no_apppass: AccountConfig, mocker) -> None:
    mock_dav = mocker.patch("fmcli.account.caldav.DAVClient")
    mock_webdav = mocker.patch("fmcli.account.WebDAVClient")
    account = Account.from_config(acc_config_no_apppass)

    account.get_caldav_client()
    mock_dav.assert_called_once_with(
        url="https://caldav.fastmail.com/dav/",
        username="user@fastmail.com",
        password="tok123",
    )

    account.get_carddav_client()
    mock_webdav.assert_called_once_with({
        "webdav_hostname": "https://carddav.fastmail.com/dav/",
        "webdav_login": "user@fastmail.com",
        "webdav_password": "tok123",
    })

    account.get_webdav_client()
    mock_webdav.assert_called_with({
        "webdav_hostname": "https://webdav.fastmail.com/",
        "webdav_login": "user@fastmail.com",
        "webdav_password": "tok123",
    })
