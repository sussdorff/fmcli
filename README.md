# fmcli

Multi-account Fastmail CLI for email, calendar, contacts, and files.

## Features

- **Email**: list, search, read, send, reply
- **Mailbox**: list, move, mark-read/spam
- **Masked Email**: list, create, delete
- **Calendar**: list events, create, delete
- **Contacts**: list, search, create, delete
- **Files/Drive**: list, download, upload, delete
- **Multi-account**: configure multiple Fastmail accounts, switch with `--account`

## Installation

```bash
git clone https://github.com/sussdorff/fmcli
cd fmcli
uv sync
```

## Configuration

Create `~/.config/fmcli/config.toml`:

```toml
[[accounts]]
name = "personal"
email = "user@fastmail.com"
token = "your-api-token"

[[accounts]]
name = "work"
email = "user@company.com"
token = "your-api-token"
app_password = "your-app-password"  # required for CalDAV/CardDAV/WebDAV
```

Get your API token from [Fastmail Settings → Privacy & Security → API Tokens](https://app.fastmail.com/settings/security/tokens).

The `app_password` is only needed for calendar, contacts, and files commands. Create one at [Fastmail Settings → Privacy & Security → App Passwords](https://app.fastmail.com/settings/security/apppasswords).

**Select account:**
- `--account <name>` flag on any command
- `FMC_ACCOUNT=work fmcli email list`
- Default: first account in config file

## Usage

```bash
# Account management
fmcli account list
fmcli account show personal

# Email
fmcli email list
fmcli email list --account work --limit 50
fmcli email search "invoice"
fmcli email read <email-id>
fmcli email send --to recipient@example.com --subject "Hello" --body "Hi there"
fmcli email reply <email-id> --body "Thanks!"

# Mailbox
fmcli mailbox list
fmcli mailbox move <email-id> <mailbox-id>
fmcli mailbox mark-read <email-id>
fmcli mailbox mark-read <email-id> --unread
fmcli mailbox mark-spam <email-id>

# Masked Email
fmcli masked-email list
fmcli masked-email create --for-domain shop.example.com --description "Online shopping"
fmcli masked-email delete <masked-email-id>

# Calendar
fmcli calendar list
fmcli calendar list --days 7
fmcli calendar create --title "Team meeting" --start 2024-02-01T10:00:00 --end 2024-02-01T11:00:00
fmcli calendar delete <event-uid>

# Contacts
fmcli contacts list
fmcli contacts search "Alice"
fmcli contacts create --name "Alice Smith" --email alice@example.com --phone "+1234567890"
fmcli contacts delete <contact-uid>

# Files/Drive
fmcli files list
fmcli files list --path /Documents
fmcli files download /report.pdf ./report.pdf
fmcli files upload ./local.txt /remote.txt
fmcli files delete /old-file.txt
```

## Shell Completions

```bash
fmcli --install-completion
```

## Development

```bash
uv sync
uv run pytest
uv run pytest --cov=fmcli --cov-report=term-missing
```

## Stack

- Python 3.11+, [UV](https://github.com/astral-sh/uv)
- [jmapc](https://github.com/smkent/jmapc) — JMAP email
- [caldav](https://github.com/python-caldav/caldav) — CalDAV calendar
- [webdavclient3](https://github.com/ezhov-evgeny/webdavclient3) — CardDAV contacts + WebDAV files
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [pytest](https://pytest.org/) + pytest-cov + pytest-mock
