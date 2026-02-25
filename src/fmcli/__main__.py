from __future__ import annotations

from typing import Optional

import typer

from fmcli import __version__
from fmcli.cli_utils import resolve_account, resolve_all_accounts, load_config

app = typer.Typer(name="fmcli", help="Multi-account Fastmail CLI", no_args_is_help=True)

email_app = typer.Typer(help="Email commands", no_args_is_help=True)
mailbox_app = typer.Typer(help="Mailbox management", no_args_is_help=True)
masked_email_app = typer.Typer(help="Masked email management", no_args_is_help=True)
calendar_app = typer.Typer(help="Calendar commands", no_args_is_help=True)
contacts_app = typer.Typer(help="Contacts commands", no_args_is_help=True)
account_app = typer.Typer(help="Account management", no_args_is_help=True)
files_app = typer.Typer(help="Files/Drive commands", no_args_is_help=True)

app.add_typer(email_app, name="email")
app.add_typer(mailbox_app, name="mailbox")
app.add_typer(masked_email_app, name="masked-email")
app.add_typer(calendar_app, name="calendar")
app.add_typer(contacts_app, name="contacts")
app.add_typer(account_app, name="account")
app.add_typer(files_app, name="files")

ACCOUNT_OPTION = typer.Option(None, "--account", "-a", help="Account name (or FMC_ACCOUNT env var)")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"fmcli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Multi-account Fastmail CLI."""


# ---------------------------------------------------------------------------
# Account commands
# ---------------------------------------------------------------------------


@account_app.command("list")
def account_list() -> None:
    """List all configured accounts."""
    config = load_config()
    if not config.accounts:
        typer.echo("No accounts configured.")
        return
    for acc in config.accounts:
        typer.echo(f"  {acc.name} <{acc.email}>")


@account_app.command("show")
def account_show(name: str = typer.Argument(..., help="Account name to show")) -> None:
    """Show account details (token is partially masked)."""
    config = load_config()
    try:
        acc = config.get_account(name)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    masked = ("*" * 8) + (acc.token[-4:] if len(acc.token) > 4 else "****")
    typer.echo(f"Name:  {acc.name}")
    typer.echo(f"Email: {acc.email}")
    typer.echo(f"Token: {masked}")


# ---------------------------------------------------------------------------
# Email commands
# ---------------------------------------------------------------------------


@email_app.command("list")
def email_list(
    account: Optional[str] = ACCOUNT_OPTION,
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of emails to list"),
    mailbox: Optional[str] = typer.Option(None, "--mailbox", "-m", help="Filter by mailbox name or role (e.g. inbox, sent, drafts)"),
    unread: bool = typer.Option(False, "--unread", help="Show only unread emails"),
    all_accounts: bool = typer.Option(False, "--all-accounts", help="Query all configured accounts"),
) -> None:
    """List recent emails."""
    from fmcli.commands.email import list_emails

    if all_accounts and account:
        typer.echo("Error: --account and --all-accounts are mutually exclusive.", err=True)
        raise typer.Exit(1)

    accounts = resolve_all_accounts() if all_accounts else [resolve_account(account)]
    for acc in accounts:
        if all_accounts:
            typer.echo(f"--- {acc.name} ({acc.email}) ---")
        emails = list_emails(acc, limit=limit, mailbox=mailbox, unread_only=unread)
        if not emails:
            typer.echo("No emails found.")
            continue
        for e in emails:
            date = e.get("date", "")[:10]
            sender = e.get("from", "")[:30]
            subject = e.get("subject", "")
            email_id = e.get("id", "")
            typer.echo(f"{email_id}  {date}  {sender:<30}  {subject}")


@email_app.command("search")
def email_search(
    query: str = typer.Argument(..., help="Search query"),
    account: Optional[str] = ACCOUNT_OPTION,
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results"),
) -> None:
    """Search emails."""
    from fmcli.commands.email import search_emails

    acc = resolve_account(account)
    emails = search_emails(acc, query=query, limit=limit)
    if not emails:
        typer.echo("No emails found.")
        return
    for e in emails:
        date = e.get("date", "")[:10]
        sender = e.get("from", "")[:30]
        subject = e.get("subject", "")
        email_id = e.get("id", "")
        typer.echo(f"{email_id}  {date}  {sender:<30}  {subject}")


@email_app.command("read")
def email_read(
    email_id: str = typer.Argument(..., help="Email ID"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Read an email by ID."""
    from fmcli.commands.email import read_email

    acc = resolve_account(account)
    try:
        e = read_email(acc, email_id=email_id)
    except ValueError as err:
        typer.echo(f"Error: {err}", err=True)
        raise typer.Exit(1)
    typer.echo(f"From:    {e.get('from', '')}")
    typer.echo(f"Date:    {e.get('date', '')}")
    typer.echo(f"Subject: {e.get('subject', '')}")
    typer.echo("")
    typer.echo(e.get("body", ""))


@email_app.command("send")
def email_send(
    to: str = typer.Option(..., "--to", help="Recipient email address"),
    subject: str = typer.Option(..., "--subject", "-s", help="Email subject"),
    body: str = typer.Option(..., "--body", "-b", help="Email body text"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Send an email."""
    from fmcli.commands.email import send_email

    acc = resolve_account(account)
    email_id = send_email(acc, to=to, subject=subject, body=body)
    typer.echo(f"Email sent. ID: {email_id}")


@email_app.command("reply")
def email_reply(
    email_id: str = typer.Argument(..., help="ID of the email to reply to"),
    body: str = typer.Option(..., "--body", "-b", help="Reply body text"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Reply to an email."""
    from fmcli.commands.email import reply_email

    acc = resolve_account(account)
    try:
        reply_id = reply_email(acc, email_id=email_id, body=body)
    except ValueError as err:
        typer.echo(f"Error: {err}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Reply sent. ID: {reply_id}")


# ---------------------------------------------------------------------------
# Mailbox commands
# ---------------------------------------------------------------------------


@mailbox_app.command("list")
def mailbox_list(
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """List all mailboxes."""
    from fmcli.commands.mailbox import list_mailboxes

    acc = resolve_account(account)
    mailboxes = list_mailboxes(acc)
    if not mailboxes:
        typer.echo("No mailboxes found.")
        return
    for mb in mailboxes:
        role = f" [{mb.get('role')}]" if mb.get("role") else ""
        typer.echo(
            f"{mb.get('id', '')[:8]}  {mb.get('name', ''):<25}"
            f"  total={mb.get('total', 0)}  unread={mb.get('unread', 0)}{role}"
        )


@mailbox_app.command("move")
def mailbox_move_email(
    email_id: str = typer.Argument(..., help="Email ID to move"),
    mailbox_id: str = typer.Argument(..., help="Destination mailbox ID"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Move an email to a mailbox."""
    from fmcli.commands.mailbox import move_email

    acc = resolve_account(account)
    move_email(acc, email_id=email_id, mailbox_id=mailbox_id)
    typer.echo(f"Moved email {email_id} to mailbox {mailbox_id}.")


@mailbox_app.command("mark-read")
def mailbox_mark_read(
    email_id: str = typer.Argument(..., help="Email ID"),
    unread: bool = typer.Option(False, "--unread", help="Mark as unread instead"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Mark an email as read (or unread)."""
    from fmcli.commands.mailbox import mark_read

    acc = resolve_account(account)
    mark_read(acc, email_id=email_id, read=not unread)
    state = "unread" if unread else "read"
    typer.echo(f"Marked email {email_id} as {state}.")


@mailbox_app.command("mark-spam")
def mailbox_mark_spam(
    email_id: str = typer.Argument(..., help="Email ID"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Move an email to the Junk/Spam folder."""
    from fmcli.commands.mailbox import mark_spam

    acc = resolve_account(account)
    try:
        mark_spam(acc, email_id=email_id)
    except ValueError as err:
        typer.echo(f"Error: {err}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Moved email {email_id} to Junk.")


# ---------------------------------------------------------------------------
# Masked email commands
# ---------------------------------------------------------------------------


@masked_email_app.command("list")
def masked_email_list(
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """List all masked email addresses."""
    from fmcli.commands.masked_email import list_masked_emails

    acc = resolve_account(account)
    entries = list_masked_emails(acc)
    if not entries:
        typer.echo("No masked emails found.")
        return
    for me in entries:
        domain = me.get("for_domain") or ""
        desc = me.get("description") or ""
        typer.echo(
            f"{me.get('id', '')[:8]}  {me.get('email', ''):<40}"
            f"  {me.get('state', ''):<10}  {domain}  {desc}"
        )


@masked_email_app.command("create")
def masked_email_create(
    for_domain: Optional[str] = typer.Option(None, "--for-domain", "-d", help="Domain this address is for"),
    description: Optional[str] = typer.Option(None, "--description", help="Optional description"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Create a new masked email address."""
    from fmcli.commands.masked_email import create_masked_email

    acc = resolve_account(account)
    result = create_masked_email(acc, for_domain=for_domain, description=description)
    if result is None:
        typer.echo("Error: Failed to create masked email.", err=True)
        raise typer.Exit(1)
    typer.echo(f"Created: {result.get('email', '')}  (ID: {result.get('id', '')})")


@masked_email_app.command("delete")
def masked_email_delete(
    masked_email_id: str = typer.Argument(..., help="Masked email ID to delete"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Delete (disable) a masked email address."""
    from fmcli.commands.masked_email import delete_masked_email

    acc = resolve_account(account)
    delete_masked_email(acc, masked_email_id=masked_email_id)
    typer.echo(f"Deleted masked email {masked_email_id}.")


# ---------------------------------------------------------------------------
# Calendar commands
# ---------------------------------------------------------------------------


@calendar_app.command("list")
def calendar_list(
    days: int = typer.Option(30, "--days", help="Number of days ahead to look"),
    today: bool = typer.Option(False, "--today", help="Show only today's remaining events"),
    account: Optional[str] = ACCOUNT_OPTION,
    all_accounts: bool = typer.Option(False, "--all-accounts", help="Query all configured accounts"),
) -> None:
    """List upcoming calendar events."""
    from fmcli.commands.calendar import list_events

    if all_accounts and account:
        typer.echo("Error: --account and --all-accounts are mutually exclusive.", err=True)
        raise typer.Exit(1)

    accounts = resolve_all_accounts() if all_accounts else [resolve_account(account)]
    for acc in accounts:
        if all_accounts:
            typer.echo(f"--- {acc.name} ({acc.email}) ---")
        events = list_events(acc, days=days, today=today)
        if not events:
            typer.echo("No events found.")
            continue
        for ev in events:
            location = f"  @ {ev.get('location')}" if ev.get("location") else ""
            typer.echo(
                f"{ev.get('start', '')[:16]}  {ev.get('title', ''):<40}{location}"
            )


@calendar_app.command("search")
def calendar_search(
    query: str = typer.Argument(..., help="Search query (matches event title)"),
    days_back: int = typer.Option(365, "--days-back", help="How many days back to search"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Search past calendar events by title."""
    from fmcli.commands.calendar import search_events

    acc = resolve_account(account)
    events = search_events(acc, query=query, days_back=days_back)
    if not events:
        typer.echo("No events found.")
        return
    for ev in events:
        location = f"  @ {ev.get('location')}" if ev.get("location") else ""
        typer.echo(
            f"{ev.get('start', '')[:16]}  {ev.get('title', ''):<40}{location}"
        )


@calendar_app.command("create")
def calendar_create(
    title: str = typer.Option(..., "--title", "-t", help="Event title"),
    start: str = typer.Option(..., "--start", help="Start datetime (ISO 8601, e.g. 2024-01-15T10:00:00)"),
    end: str = typer.Option(..., "--end", help="End datetime (ISO 8601, e.g. 2024-01-15T11:00:00)"),
    location: str = typer.Option("", "--location", "-l", help="Optional location"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Create a calendar event."""
    from fmcli.commands.calendar import create_event

    acc = resolve_account(account)
    uid = create_event(acc, title=title, start=start, end=end, location=location)
    typer.echo(f"Event created. UID: {uid}")


@calendar_app.command("delete")
def calendar_delete(
    uid: str = typer.Argument(..., help="Event UID to delete"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Delete a calendar event by UID."""
    from fmcli.commands.calendar import delete_event

    acc = resolve_account(account)
    try:
        delete_event(acc, uid=uid)
    except ValueError as err:
        typer.echo(f"Error: {err}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted event {uid}.")


# ---------------------------------------------------------------------------
# Contacts commands
# ---------------------------------------------------------------------------


@contacts_app.command("list")
def contacts_list(
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """List all contacts."""
    from fmcli.commands.contacts import list_contacts

    acc = resolve_account(account)
    contacts = list_contacts(acc)
    if not contacts:
        typer.echo("No contacts found.")
        return
    for c in contacts:
        phone = f"  {c.get('phone')}" if c.get("phone") else ""
        typer.echo(f"{c.get('name', ''):<30}  {c.get('email', ''):<40}{phone}")


@contacts_app.command("search")
def contacts_search(
    query: str = typer.Argument(..., help="Search query (name or email)"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Search contacts by name or email."""
    from fmcli.commands.contacts import search_contacts

    acc = resolve_account(account)
    contacts = search_contacts(acc, query=query)
    if not contacts:
        typer.echo("No contacts found.")
        return
    for c in contacts:
        phone = f"  {c.get('phone')}" if c.get("phone") else ""
        typer.echo(f"{c.get('name', ''):<30}  {c.get('email', ''):<40}{phone}")


@contacts_app.command("create")
def contacts_create(
    name: str = typer.Option(..., "--name", "-n", help="Full name"),
    email: str = typer.Option(..., "--email", "-e", help="Email address"),
    phone: str = typer.Option("", "--phone", "-p", help="Phone number"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Create a new contact."""
    from fmcli.commands.contacts import create_contact

    acc = resolve_account(account)
    uid = create_contact(acc, name=name, email=email, phone=phone)
    typer.echo(f"Contact created. UID: {uid}")


@contacts_app.command("delete")
def contacts_delete(
    uid: str = typer.Argument(..., help="Contact UID to delete"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Delete a contact by UID."""
    from fmcli.commands.contacts import delete_contact

    acc = resolve_account(account)
    try:
        delete_contact(acc, uid=uid)
    except ValueError as err:
        typer.echo(f"Error: {err}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted contact {uid}.")


# ---------------------------------------------------------------------------
# Files commands
# ---------------------------------------------------------------------------


@files_app.command("list")
def files_list(
    path: str = typer.Option("/", "--path", "-p", help="Remote path to list"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """List files and directories."""
    from fmcli.commands.files import list_files

    acc = resolve_account(account)
    entries = list_files(acc, path=path)
    if not entries:
        typer.echo("No files found.")
        return
    for entry in entries:
        kind = "DIR " if entry.get("is_dir") else "FILE"
        typer.echo(f"{kind}  {entry.get('path', '')}")


@files_app.command("download")
def files_download(
    remote_path: str = typer.Argument(..., help="Remote file path"),
    local_path: str = typer.Argument(..., help="Local destination path"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Download a file from Fastmail Drive."""
    from fmcli.commands.files import download_file

    acc = resolve_account(account)
    download_file(acc, remote_path=remote_path, local_path=local_path)
    typer.echo(f"Downloaded {remote_path} -> {local_path}")


@files_app.command("upload")
def files_upload(
    local_path: str = typer.Argument(..., help="Local file path"),
    remote_path: str = typer.Argument(..., help="Remote destination path"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Upload a file to Fastmail Drive."""
    from fmcli.commands.files import upload_file

    acc = resolve_account(account)
    upload_file(acc, local_path=local_path, remote_path=remote_path)
    typer.echo(f"Uploaded {local_path} -> {remote_path}")


@files_app.command("delete")
def files_delete(
    path: str = typer.Argument(..., help="Remote path to delete"),
    account: Optional[str] = ACCOUNT_OPTION,
) -> None:
    """Delete a file or directory on Fastmail Drive."""
    from fmcli.commands.files import delete_file

    acc = resolve_account(account)
    delete_file(acc, path=path)
    typer.echo(f"Deleted {path}.")


if __name__ == "__main__":
    app()
