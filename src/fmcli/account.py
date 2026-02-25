from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jmapc
import caldav
from webdav3.client import Client as WebDAVClient

from fmcli.config import AccountConfig

JMAP_HOST = "api.fastmail.com"
CALDAV_URL = "https://caldav.fastmail.com/dav/"
CARDDAV_URL = "https://carddav.fastmail.com/dav/"
WEBDAV_URL = "https://webdav.fastmail.com/"


@dataclass
class Account:
    name: str
    email: str
    token: str
    app_password: str | None = None
    can_send: bool = False

    @classmethod
    def from_config(cls, acc: AccountConfig) -> "Account":
        return cls(
            name=acc.name,
            email=acc.email,
            token=acc.token,
            app_password=acc.app_password,
            can_send=acc.can_send,
        )

    def _dav_password(self) -> str:
        return self.app_password or self.token

    def get_jmap_client(self, client: Any = None) -> jmapc.Client:
        if client is not None:
            return client
        return jmapc.Client.create_with_api_token(
            host=JMAP_HOST,
            api_token=self.token,
        )

    def get_caldav_client(self, client: Any = None) -> caldav.DAVClient:
        if client is not None:
            return client
        return caldav.DAVClient(
            url=CALDAV_URL,
            username=self.email,
            password=self._dav_password(),
        )

    def get_carddav_client(self, client: Any = None) -> WebDAVClient:
        if client is not None:
            return client
        return WebDAVClient({
            "webdav_hostname": CARDDAV_URL,
            "webdav_login": self.email,
            "webdav_password": self._dav_password(),
        })

    def get_webdav_client(self, client: Any = None) -> WebDAVClient:
        if client is not None:
            return client
        return WebDAVClient({
            "webdav_hostname": WEBDAV_URL,
            "webdav_login": self.email,
            "webdav_password": self._dav_password(),
        })
