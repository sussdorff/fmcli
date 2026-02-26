"""RFC 6352 CardDAV client using requests + vobject + lxml."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlparse

import requests
from defusedxml import ElementTree as DefusedET
from lxml import etree

# CardDAV/WebDAV XML namespaces
DAV_NS = "DAV:"
CARDDAV_NS = "urn:ietf:params:ns:carddav"
NSMAP = {"D": DAV_NS, "C": CARDDAV_NS}


def _dav_tag(local: str) -> str:
    return f"{{{DAV_NS}}}{local}"


def _carddav_tag(local: str) -> str:
    return f"{{{CARDDAV_NS}}}{local}"


class CardDAVError(Exception):
    """Raised when a CardDAV operation fails."""


class CardDAVClient:
    """RFC 6352 CardDAV client using requests + vobject + lxml."""

    def __init__(self, url: str, username: str, password: str) -> None:
        self.base_url = url.rstrip("/") + "/"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            "User-Agent": "fmcli-carddav/1.0",
        })
        self._default_addressbook: str | None = None

    def _request(
        self,
        method: str,
        url: str,
        data: str | bytes | None = None,
        headers: dict[str, str] | None = None,
        expected_status: tuple[int, ...] = (200, 207),
    ) -> requests.Response:
        """Send a request and validate the status code."""
        resp = self.session.request(
            method=method,
            url=url,
            data=data,
            headers=headers,
        )
        if resp.status_code not in expected_status:
            raise CardDAVError(
                f"{method} {url} returned {resp.status_code}: {resp.text[:500]}"
            )
        return resp

    def _propfind(
        self,
        url: str,
        body: str,
        depth: str = "0",
    ) -> etree._Element:
        """Send a PROPFIND request and parse the multistatus response."""
        headers = {
            "Content-Type": "application/xml; charset=utf-8",
            "Depth": depth,
        }
        resp = self._request("PROPFIND", url, data=body, headers=headers)
        return DefusedET.fromstring(resp.content)

    def _report(self, url: str, body: str) -> etree._Element:
        """Send a REPORT request and parse the multistatus response."""
        headers = {
            "Content-Type": "application/xml; charset=utf-8",
            "Depth": "1",
        }
        resp = self._request("REPORT", url, data=body, headers=headers)
        return DefusedET.fromstring(resp.content)

    def _resolve_url(self, href: str) -> str:
        """Resolve a potentially relative href against the base URL."""
        if href.startswith("http://") or href.startswith("https://"):
            return href
        parsed = urlparse(self.base_url)
        return f"{parsed.scheme}://{parsed.netloc}{href}"

    def discover_principal(self) -> str:
        """Discover the current-user-principal URL."""
        body = """<?xml version="1.0" encoding="utf-8"?>
        <D:propfind xmlns:D="DAV:">
          <D:prop>
            <D:current-user-principal/>
          </D:prop>
        </D:propfind>"""

        root = self._propfind(self.base_url, body)

        for resp_elem in root.iter(_dav_tag("response")):
            for propstat in resp_elem.iter(_dav_tag("propstat")):
                principal = propstat.find(
                    f".//{_dav_tag('current-user-principal')}/{_dav_tag('href')}"
                )
                if principal is not None and principal.text:
                    return self._resolve_url(principal.text.strip())

        raise CardDAVError("Could not discover current-user-principal")

    def discover_addressbook_home(self, principal_url: str | None = None) -> str:
        """Discover the addressbook-home-set URL."""
        if principal_url is None:
            principal_url = self.discover_principal()

        body = """<?xml version="1.0" encoding="utf-8"?>
        <D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:ns:carddav">
          <D:prop>
            <C:addressbook-home-set/>
          </D:prop>
        </D:propfind>"""

        root = self._propfind(principal_url, body)

        for resp_elem in root.iter(_dav_tag("response")):
            for propstat in resp_elem.iter(_dav_tag("propstat")):
                home = propstat.find(
                    f".//{_carddav_tag('addressbook-home-set')}/{_dav_tag('href')}"
                )
                if home is not None and home.text:
                    return self._resolve_url(home.text.strip())

        raise CardDAVError("Could not discover addressbook-home-set")

    def discover_addressbooks(self, home_url: str | None = None) -> list[dict[str, str]]:
        """Discover all addressbooks under the addressbook-home-set.

        Returns a list of dicts with 'url', 'name', and 'description' keys.
        """
        if home_url is None:
            home_url = self.discover_addressbook_home()

        body = """<?xml version="1.0" encoding="utf-8"?>
        <D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:ns:carddav">
          <D:prop>
            <D:resourcetype/>
            <D:displayname/>
          </D:prop>
        </D:propfind>"""

        root = self._propfind(home_url, body, depth="1")

        addressbooks: list[dict[str, str]] = []
        for resp_elem in root.iter(_dav_tag("response")):
            href_elem = resp_elem.find(_dav_tag("href"))
            if href_elem is None or not href_elem.text:
                continue
            href = href_elem.text.strip()

            # Check if this is an addressbook
            for propstat in resp_elem.iter(_dav_tag("propstat")):
                resourcetype = propstat.find(
                    f".//{_dav_tag('resourcetype')}"
                )
                if resourcetype is None:
                    continue
                if resourcetype.find(_carddav_tag("addressbook")) is not None:
                    displayname_elem = propstat.find(
                        f".//{_dav_tag('displayname')}"
                    )
                    name = (
                        displayname_elem.text.strip()
                        if displayname_elem is not None and displayname_elem.text
                        else ""
                    )
                    addressbooks.append({
                        "url": self._resolve_url(href),
                        "name": name,
                    })

        return addressbooks

    def get_default_addressbook(self) -> str:
        """Return the URL of the default (first) addressbook.

        Caches the result after first discovery.
        """
        if self._default_addressbook is not None:
            return self._default_addressbook
        books = self.discover_addressbooks()
        if not books:
            raise CardDAVError("No addressbooks found")
        self._default_addressbook = books[0]["url"]
        return self._default_addressbook

    def list_contacts(self, addressbook_url: str | None = None) -> list[dict[str, Any]]:
        """List all contacts in an addressbook.

        Uses an addressbook-query REPORT to fetch all vCards with their data.
        Returns a list of dicts with 'href', 'etag', and 'vcard' (raw string) keys.
        """
        if addressbook_url is None:
            addressbook_url = self.get_default_addressbook()

        body = """<?xml version="1.0" encoding="utf-8"?>
        <C:addressbook-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:ns:carddav">
          <D:prop>
            <D:getetag/>
            <C:address-data/>
          </D:prop>
        </C:addressbook-query>"""

        root = self._report(addressbook_url, body)

        contacts: list[dict[str, Any]] = []
        for resp_elem in root.iter(_dav_tag("response")):
            href_elem = resp_elem.find(_dav_tag("href"))
            if href_elem is None or not href_elem.text:
                continue
            href = href_elem.text.strip()

            # Skip non-vcf entries (like the addressbook itself)
            if not href.endswith(".vcf"):
                continue

            etag = ""
            vcard_data = ""
            for propstat in resp_elem.iter(_dav_tag("propstat")):
                etag_elem = propstat.find(f".//{_dav_tag('getetag')}")
                if etag_elem is not None and etag_elem.text:
                    etag = etag_elem.text.strip().strip('"')

                address_data_elem = propstat.find(
                    f".//{_carddav_tag('address-data')}"
                )
                if address_data_elem is not None and address_data_elem.text:
                    vcard_data = address_data_elem.text.strip()

            if vcard_data:
                contacts.append({
                    "href": href,
                    "etag": etag,
                    "vcard": vcard_data,
                })

        return contacts

    def get_contact(self, href: str) -> str:
        """GET a single vCard by its href. Returns raw vCard string."""
        url = self._resolve_url(href)
        resp = self._request("GET", url, expected_status=(200,))
        return resp.text

    def create_contact(
        self,
        vcard_text: str,
        addressbook_url: str | None = None,
        uid: str | None = None,
    ) -> str:
        """PUT a new vCard into the addressbook.

        Args:
            vcard_text: The vCard content string.
            addressbook_url: Target addressbook URL. Uses default if None.
            uid: The UID for the contact filename. Extracted from vcard if None.

        Returns:
            The href of the created contact.
        """
        if addressbook_url is None:
            addressbook_url = self.get_default_addressbook()

        if uid is None:
            uid = str(uuid.uuid4())

        href = f"{addressbook_url.rstrip('/')}/{uid}.vcf"

        headers = {
            "Content-Type": "text/vcard; charset=utf-8",
            "If-None-Match": "*",  # Only create, don't overwrite
        }
        self._request("PUT", href, data=vcard_text, headers=headers, expected_status=(201, 204))
        # Return the relative path portion
        parsed = urlparse(href)
        return parsed.path

    def update_contact(self, href: str, vcard_text: str, etag: str | None = None) -> None:
        """PUT an updated vCard to the given href.

        Args:
            href: The contact's href (absolute or relative path).
            vcard_text: The updated vCard content.
            etag: Optional ETag for conditional update.
        """
        url = self._resolve_url(href)
        headers: dict[str, str] = {
            "Content-Type": "text/vcard; charset=utf-8",
        }
        if etag:
            headers["If-Match"] = f'"{etag}"'
        self._request("PUT", url, data=vcard_text, headers=headers, expected_status=(200, 204))

    def delete_contact(self, href: str, etag: str | None = None) -> None:
        """DELETE a contact by its href.

        Args:
            href: The contact's href (absolute or relative path).
            etag: Optional ETag for conditional delete.
        """
        url = self._resolve_url(href)
        headers: dict[str, str] = {}
        if etag:
            headers["If-Match"] = f'"{etag}"'
        self._request("DELETE", url, headers=headers or None, expected_status=(200, 204))
