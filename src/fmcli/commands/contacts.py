from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from fmcli.account import Account

CONTACTS_PATH = "/"


def _get_client(account: Account, client: Any = None) -> Any:
    return client if client is not None else account.get_carddav_client()


def _parse_vcard(content: str) -> dict:
    """Parse a simple vCard string into a dict with id, name, email, phone."""
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
    """Build a minimal vCard 3.0 string."""
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"UID:{uid}",
        f"FN:{name}",
    ]
    if email:
        lines.append(f"EMAIL:{email}")
    if phone:
        lines.append(f"TEL:{phone}")
    lines.append("END:VCARD")
    return "\r\n".join(lines)


def _download_vcard(client: Any, path: str) -> str:
    """Download a vCard from a remote path and return its content as a string."""
    with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False) as f:
        tmp = f.name
    client.download_sync(remote_path=path, local_path=tmp)
    content = Path(tmp).read_text()
    Path(tmp).unlink(missing_ok=True)
    return content


def _find_path_for_uid(client: Any, uid: str) -> str | None:
    """Return the remote path for a given UID, or None if not found."""
    paths = client.list(CONTACTS_PATH)
    for path in paths:
        if path.endswith(".vcf") and uid in path:
            return path
    return None


def list_contacts(account: Account, client: Any = None) -> list[dict]:
    """Return all contacts as a list of dicts with id, name, email, phone."""
    c = _get_client(account, client)
    paths = [p for p in c.list(CONTACTS_PATH) if p.endswith(".vcf")]
    contacts = []
    for path in paths:
        content = _download_vcard(c, path)
        contacts.append(_parse_vcard(content))
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
    content = _make_vcard(uid=uid, name=name, email=email, phone=phone)

    with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False, mode="w") as f:
        f.write(content)
        tmp = f.name

    remote_path = f"{uid}.vcf"
    c.upload_sync(remote_path=remote_path, local_path=tmp)
    Path(tmp).unlink(missing_ok=True)
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
    remote_path = _find_path_for_uid(c, uid)
    if remote_path is None:
        raise ValueError(f"Contact not found: {uid}")

    content = _download_vcard(c, remote_path)
    existing = _parse_vcard(content)

    new_name = name if name is not None else existing["name"]
    new_email = email if email is not None else existing["email"]
    new_phone = phone if phone is not None else existing["phone"]

    new_content = _make_vcard(uid=uid, name=new_name, email=new_email, phone=new_phone)

    with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False, mode="w") as f:
        f.write(new_content)
        tmp = f.name

    c.upload_sync(remote_path=remote_path, local_path=tmp)
    Path(tmp).unlink(missing_ok=True)


def delete_contact(account: Account, uid: str, client: Any = None) -> None:
    """Delete the contact identified by uid. Raises ValueError if not found."""
    c = _get_client(account, client)
    remote_path = _find_path_for_uid(c, uid)
    if remote_path is None:
        raise ValueError(f"Contact not found: {uid}")
    c.clean(remote_path)
