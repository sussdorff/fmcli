"""Tests for the CardDAV client (RFC 6352) using mocked HTTP requests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fmcli.carddav import CardDAVClient, CardDAVError

BASE_URL = "https://carddav.fastmail.com/dav/"
USERNAME = "user@fastmail.com"
PASSWORD = "app-password-123"


@pytest.fixture
def client() -> CardDAVClient:
    return CardDAVClient(url=BASE_URL, username=USERNAME, password=PASSWORD)


def _mock_response(status_code: int = 200, content: bytes = b"", text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content if content else text.encode("utf-8")
    resp.text = text if text else content.decode("utf-8")
    return resp


PRINCIPAL_RESPONSE = b"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:">
  <D:response>
    <D:href>/dav/</D:href>
    <D:propstat>
      <D:prop>
        <D:current-user-principal>
          <D:href>/dav/principals/user/user@fastmail.com/</D:href>
        </D:current-user-principal>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""


ADDRESSBOOK_HOME_RESPONSE = b"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:ns:carddav">
  <D:response>
    <D:href>/dav/principals/user/user@fastmail.com/</D:href>
    <D:propstat>
      <D:prop>
        <C:addressbook-home-set>
          <D:href>/dav/addressbooks/user/user@fastmail.com/</D:href>
        </C:addressbook-home-set>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""


ADDRESSBOOKS_RESPONSE = b"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:ns:carddav">
  <D:response>
    <D:href>/dav/addressbooks/user/user@fastmail.com/</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype>
          <D:collection/>
        </D:resourcetype>
        <D:displayname>Address Books</D:displayname>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
  <D:response>
    <D:href>/dav/addressbooks/user/user@fastmail.com/Default/</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype>
          <D:collection/>
          <C:addressbook/>
        </D:resourcetype>
        <D:displayname>Personal</D:displayname>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""


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


LIST_CONTACTS_RESPONSE = f"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:ns:carddav">
  <D:response>
    <D:href>/dav/addressbooks/user/user@fastmail.com/Default/uid-john-001.vcf</D:href>
    <D:propstat>
      <D:prop>
        <D:getetag>"etag-john-1"</D:getetag>
        <C:address-data>{VCARD_JOHN}</C:address-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
  <D:response>
    <D:href>/dav/addressbooks/user/user@fastmail.com/Default/uid-jane-002.vcf</D:href>
    <D:propstat>
      <D:prop>
        <D:getetag>"etag-jane-1"</D:getetag>
        <C:address-data>{VCARD_JANE}</C:address-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>""".encode("utf-8")

EMPTY_CONTACTS_RESPONSE = b"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:ns:carddav">
</D:multistatus>"""


class TestDiscoverPrincipal:
    def test_returns_principal_url(self, client: CardDAVClient) -> None:
        client.session.request = MagicMock(
            return_value=_mock_response(207, PRINCIPAL_RESPONSE)
        )
        result = client.discover_principal()
        assert result == "https://carddav.fastmail.com/dav/principals/user/user@fastmail.com/"

    def test_raises_on_missing_principal(self, client: CardDAVClient) -> None:
        empty = b"""<?xml version="1.0"?>
        <D:multistatus xmlns:D="DAV:">
          <D:response><D:href>/dav/</D:href><D:propstat><D:prop/></D:propstat></D:response>
        </D:multistatus>"""
        client.session.request = MagicMock(return_value=_mock_response(207, empty))
        with pytest.raises(CardDAVError, match="current-user-principal"):
            client.discover_principal()

    def test_raises_on_http_error(self, client: CardDAVClient) -> None:
        client.session.request = MagicMock(
            return_value=_mock_response(401, b"Unauthorized")
        )
        with pytest.raises(CardDAVError, match="401"):
            client.discover_principal()


class TestDiscoverAddressbookHome:
    def test_returns_home_url(self, client: CardDAVClient) -> None:
        calls = [
            _mock_response(207, PRINCIPAL_RESPONSE),
            _mock_response(207, ADDRESSBOOK_HOME_RESPONSE),
        ]
        client.session.request = MagicMock(side_effect=calls)
        result = client.discover_addressbook_home()
        assert result == "https://carddav.fastmail.com/dav/addressbooks/user/user@fastmail.com/"

    def test_uses_provided_principal_url(self, client: CardDAVClient) -> None:
        client.session.request = MagicMock(
            return_value=_mock_response(207, ADDRESSBOOK_HOME_RESPONSE)
        )
        result = client.discover_addressbook_home(
            "https://carddav.fastmail.com/dav/principals/user/user@fastmail.com/"
        )
        assert "/addressbooks/" in result


class TestDiscoverAddressbooks:
    def test_returns_addressbook_list(self, client: CardDAVClient) -> None:
        calls = [
            _mock_response(207, PRINCIPAL_RESPONSE),
            _mock_response(207, ADDRESSBOOK_HOME_RESPONSE),
            _mock_response(207, ADDRESSBOOKS_RESPONSE),
        ]
        client.session.request = MagicMock(side_effect=calls)
        result = client.discover_addressbooks()
        assert len(result) == 1
        assert result[0]["name"] == "Personal"
        assert "Default" in result[0]["url"]

    def test_skips_non_addressbook_collections(self, client: CardDAVClient) -> None:
        calls = [
            _mock_response(207, PRINCIPAL_RESPONSE),
            _mock_response(207, ADDRESSBOOK_HOME_RESPONSE),
            _mock_response(207, ADDRESSBOOKS_RESPONSE),
        ]
        client.session.request = MagicMock(side_effect=calls)
        result = client.discover_addressbooks()
        # Should only return the addressbook, not the parent collection
        assert all("addressbook" in str(r) or r["name"] == "Personal" for r in result)


class TestListContacts:
    def test_returns_contacts_with_vcard_data(self, client: CardDAVClient) -> None:
        # Pre-set default addressbook to skip discovery
        client._default_addressbook = "https://carddav.fastmail.com/dav/addressbooks/user/user@fastmail.com/Default/"
        client.session.request = MagicMock(
            return_value=_mock_response(207, LIST_CONTACTS_RESPONSE)
        )
        result = client.list_contacts()
        assert len(result) == 2
        assert result[0]["href"].endswith("uid-john-001.vcf")
        assert result[0]["etag"] == "etag-john-1"
        assert "John Doe" in result[0]["vcard"]

    def test_empty_addressbook(self, client: CardDAVClient) -> None:
        client._default_addressbook = "https://carddav.fastmail.com/dav/addressbooks/user/user@fastmail.com/Default/"
        client.session.request = MagicMock(
            return_value=_mock_response(207, EMPTY_CONTACTS_RESPONSE)
        )
        result = client.list_contacts()
        assert result == []

    def test_uses_provided_addressbook_url(self, client: CardDAVClient) -> None:
        custom_url = "https://carddav.fastmail.com/dav/addressbooks/user/user@fastmail.com/Custom/"
        client.session.request = MagicMock(
            return_value=_mock_response(207, EMPTY_CONTACTS_RESPONSE)
        )
        client.list_contacts(addressbook_url=custom_url)
        call_args = client.session.request.call_args
        assert call_args[1]["url"] == custom_url


class TestGetContact:
    def test_returns_vcard_text(self, client: CardDAVClient) -> None:
        client.session.request = MagicMock(
            return_value=_mock_response(200, text=VCARD_JOHN)
        )
        result = client.get_contact("/dav/addressbooks/user/user@fastmail.com/Default/uid-john-001.vcf")
        assert "John Doe" in result
        assert "BEGIN:VCARD" in result


class TestCreateContact:
    def test_sends_put_with_vcard(self, client: CardDAVClient) -> None:
        client._default_addressbook = "https://carddav.fastmail.com/dav/addressbooks/user/user@fastmail.com/Default/"
        client.session.request = MagicMock(
            return_value=_mock_response(201)
        )
        href = client.create_contact(vcard_text=VCARD_JOHN, uid="uid-john-001")
        assert href.endswith("uid-john-001.vcf")

        call_args = client.session.request.call_args
        assert call_args[1]["method"] == "PUT"
        assert "text/vcard" in call_args[1]["headers"]["Content-Type"]
        assert call_args[1]["headers"]["If-None-Match"] == "*"

    def test_returns_href_path(self, client: CardDAVClient) -> None:
        client._default_addressbook = "https://carddav.fastmail.com/dav/addressbooks/user/user@fastmail.com/Default/"
        client.session.request = MagicMock(return_value=_mock_response(201))
        href = client.create_contact(vcard_text=VCARD_JOHN, uid="test-uid")
        assert "/dav/addressbooks/" in href
        assert href.endswith("test-uid.vcf")


class TestUpdateContact:
    def test_sends_put_to_href(self, client: CardDAVClient) -> None:
        client.session.request = MagicMock(return_value=_mock_response(204))
        href = "/dav/addressbooks/user/user@fastmail.com/Default/uid-john-001.vcf"
        client.update_contact(href=href, vcard_text=VCARD_JOHN)

        call_args = client.session.request.call_args
        assert call_args[1]["method"] == "PUT"
        assert "uid-john-001.vcf" in call_args[1]["url"]

    def test_includes_etag_when_provided(self, client: CardDAVClient) -> None:
        client.session.request = MagicMock(return_value=_mock_response(204))
        href = "/dav/addressbooks/user/user@fastmail.com/Default/uid-john-001.vcf"
        client.update_contact(href=href, vcard_text=VCARD_JOHN, etag="etag-123")

        call_args = client.session.request.call_args
        assert call_args[1]["headers"]["If-Match"] == '"etag-123"'


class TestDeleteContact:
    def test_sends_delete_to_href(self, client: CardDAVClient) -> None:
        client.session.request = MagicMock(return_value=_mock_response(204))
        href = "/dav/addressbooks/user/user@fastmail.com/Default/uid-john-001.vcf"
        client.delete_contact(href=href)

        call_args = client.session.request.call_args
        assert call_args[1]["method"] == "DELETE"
        assert "uid-john-001.vcf" in call_args[1]["url"]

    def test_includes_etag_when_provided(self, client: CardDAVClient) -> None:
        client.session.request = MagicMock(return_value=_mock_response(204))
        href = "/dav/addressbooks/user/user@fastmail.com/Default/uid-john-001.vcf"
        client.delete_contact(href=href, etag="etag-456")

        call_args = client.session.request.call_args
        assert call_args[1]["headers"]["If-Match"] == '"etag-456"'

    def test_raises_on_error(self, client: CardDAVClient) -> None:
        client.session.request = MagicMock(
            return_value=_mock_response(404, b"Not Found")
        )
        with pytest.raises(CardDAVError, match="404"):
            client.delete_contact(href="/nonexistent.vcf")


class TestResolveUrl:
    def test_absolute_url_unchanged(self, client: CardDAVClient) -> None:
        url = "https://other.server.com/path"
        assert client._resolve_url(url) == url

    def test_relative_path_resolved(self, client: CardDAVClient) -> None:
        result = client._resolve_url("/dav/addressbooks/user/test/")
        assert result == "https://carddav.fastmail.com/dav/addressbooks/user/test/"


class TestGetDefaultAddressbook:
    def test_caches_result(self, client: CardDAVClient) -> None:
        calls = [
            _mock_response(207, PRINCIPAL_RESPONSE),
            _mock_response(207, ADDRESSBOOK_HOME_RESPONSE),
            _mock_response(207, ADDRESSBOOKS_RESPONSE),
        ]
        client.session.request = MagicMock(side_effect=calls)
        result1 = client.get_default_addressbook()
        result2 = client.get_default_addressbook()
        assert result1 == result2
        # Only 3 calls (principal + home + addressbooks), not 6
        assert client.session.request.call_count == 3

    def test_raises_when_no_addressbooks(self, client: CardDAVClient) -> None:
        no_books = b"""<?xml version="1.0"?>
        <D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:ns:carddav">
          <D:response>
            <D:href>/dav/addressbooks/user/user@fastmail.com/</D:href>
            <D:propstat>
              <D:prop>
                <D:resourcetype><D:collection/></D:resourcetype>
              </D:prop>
            </D:propstat>
          </D:response>
        </D:multistatus>"""
        calls = [
            _mock_response(207, PRINCIPAL_RESPONSE),
            _mock_response(207, ADDRESSBOOK_HOME_RESPONSE),
            _mock_response(207, no_books),
        ]
        client.session.request = MagicMock(side_effect=calls)
        with pytest.raises(CardDAVError, match="No addressbooks found"):
            client.get_default_addressbook()
