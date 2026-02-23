from __future__ import annotations

from typing import Any

from fmcli.account import Account


def _get_client(account: Account, client: Any = None) -> Any:
    return client if client is not None else account.get_webdav_client()


def list_files(account: Account, path: str = "/", client: Any = None) -> list[dict]:
    """Return list of files and directories at the given WebDAV path.

    Each entry is a dict with keys: name, path, is_dir.
    The directory itself (returned as first entry by webdav3) is excluded.
    """
    c = _get_client(account, client)
    entries = c.list(path)
    result = []
    for entry in entries:
        # webdav3 list() includes the queried directory itself as first entry — skip it
        normalized_path = path.rstrip("/") + "/"
        if entry == path or entry == normalized_path or entry == "/" or entry == "":
            continue
        name = entry.rstrip("/").split("/")[-1]
        result.append({
            "name": name,
            "path": entry,
            "is_dir": entry.endswith("/"),
        })
    return result


def download_file(account: Account, remote_path: str, local_path: str, client: Any = None) -> None:
    """Download a file from WebDAV remote_path to local_path."""
    c = _get_client(account, client)
    c.download_sync(remote_path=remote_path, local_path=local_path)


def upload_file(account: Account, local_path: str, remote_path: str, client: Any = None) -> None:
    """Upload a local file to WebDAV remote_path."""
    c = _get_client(account, client)
    c.upload_sync(remote_path=remote_path, local_path=local_path)


def delete_file(account: Account, path: str, client: Any = None) -> None:
    """Delete a file or directory at the given WebDAV path."""
    c = _get_client(account, client)
    c.clean(path)
