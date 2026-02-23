from __future__ import annotations

import pytest
from typer.testing import CliRunner

from fmcli.__main__ import app
from fmcli import __version__

runner = CliRunner()


# ---------------------------------------------------------------------------
# Version and help
# ---------------------------------------------------------------------------


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "fmcli" in result.output
    assert __version__ in result.output


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "email" in result.output
    assert "mailbox" in result.output
    assert "calendar" in result.output
    assert "contacts" in result.output
    assert "account" in result.output
    assert "files" in result.output


def test_email_help():
    result = runner.invoke(app, ["email", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "search" in result.output
    assert "read" in result.output
    assert "send" in result.output
    assert "reply" in result.output


def test_calendar_help():
    result = runner.invoke(app, ["calendar", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "delete" in result.output


def test_contacts_help():
    result = runner.invoke(app, ["contacts", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "search" in result.output
    assert "create" in result.output
    assert "delete" in result.output


def test_mailbox_help():
    result = runner.invoke(app, ["mailbox", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output


def test_masked_email_help():
    result = runner.invoke(app, ["masked-email", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "delete" in result.output


def test_files_help():
    result = runner.invoke(app, ["files", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "download" in result.output
    assert "upload" in result.output
    assert "delete" in result.output


# ---------------------------------------------------------------------------
# Account commands
# ---------------------------------------------------------------------------


def test_account_list(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    result = runner.invoke(app, ["account", "list"])
    assert result.exit_code == 0
    assert "personal" in result.output
    assert "user@fastmail.com" in result.output


def test_account_show(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    result = runner.invoke(app, ["account", "show", "personal"])
    assert result.exit_code == 0
    assert "personal" in result.output
    assert "user@fastmail.com" in result.output
    # Token should be partially masked, not shown in full
    assert "abc123secret" not in result.output
    assert "cret" in result.output  # last 4 chars visible


def test_account_show_unknown(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    result = runner.invoke(app, ["account", "show", "nonexistent"])
    assert result.exit_code == 1


def test_account_list_no_config(tmp_path, monkeypatch):
    monkeypatch.setenv("FMCLI_CONFIG", str(tmp_path / "nonexistent.toml"))
    result = runner.invoke(app, ["account", "list"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Email commands (mocked)
# ---------------------------------------------------------------------------


def test_email_list(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch(
        "fmcli.commands.email.list_emails",
        return_value=[
            {
                "id": "abc12345678",
                "date": "2024-01-15T10:00:00",
                "from": "alice@example.com",
                "subject": "Hello",
                "preview": "Hi there",
            }
        ],
    )
    result = runner.invoke(app, ["email", "list"])
    assert result.exit_code == 0
    assert "Hello" in result.output
    assert "alice@example.com" in result.output


def test_email_list_empty(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch("fmcli.commands.email.list_emails", return_value=[])
    result = runner.invoke(app, ["email", "list"])
    assert result.exit_code == 0
    assert "No emails found" in result.output


def test_email_read(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch(
        "fmcli.commands.email.read_email",
        return_value={
            "id": "abc12345",
            "from": "alice@example.com",
            "date": "2024-01-15T10:00:00",
            "subject": "Hello",
            "body": "This is the body.",
        },
    )
    result = runner.invoke(app, ["email", "read", "abc12345"])
    assert result.exit_code == 0
    assert "Hello" in result.output
    assert "This is the body." in result.output


def test_email_send(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch("fmcli.commands.email.send_email", return_value="sent-id-999")
    result = runner.invoke(
        app,
        ["email", "send", "--to", "bob@example.com", "--subject", "Hi", "--body", "Hello Bob"],
    )
    assert result.exit_code == 0
    assert "sent-id-999" in result.output


# ---------------------------------------------------------------------------
# Mailbox commands (mocked)
# ---------------------------------------------------------------------------


def test_mailbox_list(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch(
        "fmcli.commands.mailbox.list_mailboxes",
        return_value=[
            {"id": "mb001", "name": "Inbox", "role": "inbox", "total": 100, "unread": 5}
        ],
    )
    result = runner.invoke(app, ["mailbox", "list"])
    assert result.exit_code == 0
    assert "Inbox" in result.output


# ---------------------------------------------------------------------------
# Calendar commands (mocked)
# ---------------------------------------------------------------------------


def test_calendar_list(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch(
        "fmcli.commands.calendar.list_events",
        return_value=[
            {
                "id": "uid-001",
                "title": "Team Meeting",
                "start": "2024-01-15T10:00:00",
                "end": "2024-01-15T11:00:00",
                "location": "Conference Room",
            }
        ],
    )
    result = runner.invoke(app, ["calendar", "list"])
    assert result.exit_code == 0
    assert "Team Meeting" in result.output


def test_calendar_create(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch("fmcli.commands.calendar.create_event", return_value="new-uid-001")
    result = runner.invoke(
        app,
        [
            "calendar",
            "create",
            "--title",
            "Standup",
            "--start",
            "2024-01-15T09:00:00",
            "--end",
            "2024-01-15T09:15:00",
        ],
    )
    assert result.exit_code == 0
    assert "new-uid-001" in result.output


# ---------------------------------------------------------------------------
# Contacts commands (mocked)
# ---------------------------------------------------------------------------


def test_contacts_list(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch(
        "fmcli.commands.contacts.list_contacts",
        return_value=[
            {"id": "uid-c1", "name": "Alice Smith", "email": "alice@example.com", "phone": ""}
        ],
    )
    result = runner.invoke(app, ["contacts", "list"])
    assert result.exit_code == 0
    assert "Alice Smith" in result.output


def test_contacts_search(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch(
        "fmcli.commands.contacts.search_contacts",
        return_value=[
            {"id": "uid-c1", "name": "Alice Smith", "email": "alice@example.com", "phone": ""}
        ],
    )
    result = runner.invoke(app, ["contacts", "search", "alice"])
    assert result.exit_code == 0
    assert "Alice Smith" in result.output


# ---------------------------------------------------------------------------
# Files commands (mocked)
# ---------------------------------------------------------------------------


def test_files_list(tmp_path, monkeypatch, mocker):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[[accounts]]\n'
        'name = "personal"\n'
        'email = "user@fastmail.com"\n'
        'token = "abc123secret"\n'
    )
    monkeypatch.setenv("FMCLI_CONFIG", str(config_file))
    mocker.patch(
        "fmcli.commands.files.list_files",
        return_value=[
            {"name": "report.pdf", "path": "/report.pdf", "is_dir": False},
            {"name": "photos", "path": "/photos/", "is_dir": True},
        ],
    )
    result = runner.invoke(app, ["files", "list"])
    assert result.exit_code == 0
    assert "report.pdf" in result.output
    assert "photos" in result.output
