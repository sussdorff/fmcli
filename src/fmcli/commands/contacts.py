from __future__ import annotations

import uuid
from typing import Any

import vobject

from fmcli.account import Account
from fmcli.carddav import CardDAVClient


def _get_client(account: Account, client: Any = None) -> CardDAVClient:
    return client if client is not None else account.get_carddav_client()


def _parse_vcard(vcard_text: str) -> dict[str, str]:
    """Parse a vCard string into a dict with id, name, email, phone using vobject."""
    result: dict[str, str] = {"id": "", "name": "", "email": "", "phone": ""}
    try:
        card = vobject.readOne(vcard_text)
    except Exception:
        # Fallback to simple line-based parsing if vobject fails
        return _parse_vcard_simple(vcard_text)

    if hasattr(card, "uid"):
        result["id"] = card.uid.value
    if hasattr(card, "fn"):
        result["name"] = card.fn.value
    if hasattr(card, "email"):
        result["email"] = card.email.value
    if hasattr(card, "tel"):
        result["phone"] = card.tel.value

    return result


def _parse_vcard_simple(content: str) -> dict[str, str]:
    """Fallback simple line-based vCard parser."""
    result: dict[str, str] = {"id": "", "name": "", "email": "", "phone": ""}
    for line in content.splitlines():
        if line.startswith("UID:"):
            result["id"] = line[4:].strip()
        elif line.startswith("FN:"):
            result["name"] = line[3:].strip()
        elif line.startswith("EMAIL"):
            result["email"] = line.split(":", 1)[-1].strip()
        elif line.startswith("TEL"):
            result["phone"] = line.split(":", 1)[-1].strip()
    return result


def _make_vcard(uid: str, name: str, email: str, phone: str = "") -> str:
    """Build a vCard 3.0 string using vobject."""
    card = vobject.vCard()
    card.add("uid").value = uid
    card.add("fn").value = name
    card.add("n").value = vobject.vcard.Name(family="", given=name)
    if email:
        card.add("email").value = email
    if phone:
        card.add("tel").value = phone
    return card.serialize()


def _update_vcard(
    vcard_text: str,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> str:
    """Parse an existing vCard, update specified fields, return serialized vCard."""
    card = vobject.readOne(vcard_text)

    if name is not None:
        if hasattr(card, "fn"):
            card.fn.value = name
        else:
            card.add("fn").value = name
        if hasattr(card, "n"):
            card.n.value = vobject.vcard.Name(family="", given=name)

    if email is not None:
        if hasattr(card, "email"):
            card.email.value = email
        else:
            card.add("email").value = email

    if phone is not None:
        if hasattr(card, "tel"):
            card.tel.value = phone
        elif phone:
            card.add("tel").value = phone

    return card.serialize()


def list_contacts(account: Account, client: Any = None) -> list[dict]:
    """Return all contacts as a list of dicts with id, name, email, phone."""
    c = _get_client(account, client)
    raw_contacts = c.list_contacts()
    contacts = []
    for entry in raw_contacts:
        parsed = _parse_vcard(entry["vcard"])
        parsed["href"] = entry.get("href", "")
        parsed["etag"] = entry.get("etag", "")
        contacts.append(parsed)
    return contacts


def search_contacts(account: Account, query: str, client: Any = None) -> list[dict]:
    """Return contacts whose name or email match the query (case-insensitive)."""
    all_contacts = list_contacts(account, client=client)
    q = query.lower()
    return [
        c for c in all_contacts
        if q in c["name"].lower() or q in c["email"].lower()
    ]


def create_contact(
    account: Account,
    name: str,
    email: str,
    phone: str = "",
    client: Any = None,
) -> str:
    """Create a new contact and return the generated UID."""
    c = _get_client(account, client)
    uid = str(uuid.uuid4())
    vcard_text = _make_vcard(uid=uid, name=name, email=email, phone=phone)
    c.create_contact(vcard_text=vcard_text, uid=uid)
    return uid


def update_contact(
    account: Account,
    uid: str,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    client: Any = None,
) -> None:
    """Update an existing contact identified by uid. Only provided fields are changed."""
    c = _get_client(account, client)

    # Find the contact by UID
    raw_contacts = c.list_contacts()
    target = None
    for entry in raw_contacts:
        parsed = _parse_vcard(entry["vcard"])
        if parsed["id"] == uid:
            target = entry
            break

    if target is None:
        raise ValueError(f"Contact not found: {uid}")

    updated_vcard = _update_vcard(
        target["vcard"], name=name, email=email, phone=phone
    )
    c.update_contact(href=target["href"], vcard_text=updated_vcard)


def delete_contact(account: Account, uid: str, client: Any = None) -> None:
    """Delete the contact identified by uid. Raises ValueError if not found."""
    c = _get_client(account, client)

    # Find the contact by UID
    raw_contacts = c.list_contacts()
    target = None
    for entry in raw_contacts:
        parsed = _parse_vcard(entry["vcard"])
        if parsed["id"] == uid:
            target = entry
            break

    if target is None:
        raise ValueError(f"Contact not found: {uid}")

    c.delete_contact(href=target["href"])
