# fmcli Development Roadmap

## Project Overview

**fmcli** is a unified Python CLI for Fastmail that replaces MCP servers with:
- **Email**: JMAP (list, search, read, send, reply, mailbox management, masked emails)
- **Calendar**: CalDAV (list, create, update, delete events)
- **Contacts**: CardDAV (list, search, create, update, delete)
- **Files**: WebDAV (list, download, upload, delete)

**Multi-account support**: Configure multiple Fastmail accounts in `~/.config/fmcli/config.toml`, use `--account <name>` flag or `FMC_ACCOUNT` env var.

**Stack**: Python + UV, TDD, Typer CLI framework

---

## Beads Structure

### Phase 0: Epic
- **fmcli-vw7** - [EPIC] Multi-account Fastmail CLI

### Phase 1: Foundation (Priority 1)
Start here. These are blocking all other work.

1. **fmcli-66u** - [SETUP] Python+UV project scaffold with pyproject.toml
   - Initialize `uv` project with `pyproject.toml`
   - Add dependencies: `jmapc`, `caldav`, `webdavclient3`, `typer`, `pytest`, `pytest-cov`
   - Set up `tox.ini` for local testing

2. **fmcli-c24** - [SETUP] Multi-account config file handling
   - Implement `~/.config/fmcli/config.toml` parser
   - Account profiles: `name`, `email`, `token`, `app_password` (for CardDAV)
   - Support `--account` flag and `FMC_ACCOUNT` env var
   - DI for config (testable)

3. **fmcli-6lu** - [FEATURE] Account class with JMAP/CalDAV/CardDAV client factories
   - `Account(name, email, token, app_password)` class
   - Methods: `get_jmap_client()`, `get_caldav_client()`, `get_carddav_client()`, `get_webdav_client()`
   - Write tests first (TDD)
   - Use dependency injection for all clients

### Phase 2: Core Features (Priority 2)

**JMAP Email (4-5 ish):**
4. **fmcli-bch** - [FEATURE] Email commands: list, search, read, send, reply
   - `fmcli email list --account=x [--limit]`
   - `fmcli email search --query=...`
   - `fmcli email read <id>`
   - `fmcli email send --to=... --subject=...`
   - `fmcli email reply <id> --body=...`
   - Test with jmapc mocks

5. **fmcli-330** - [FEATURE] Mailbox management: list, move, mark-read/spam
   - `fmcli mailbox list`
   - `fmcli email move <id> --folder=...`
   - `fmcli email mark-read <id>`
   - `fmcli email mark-spam <id>`
   - Masked email CRUD: `fmcli masked-email list/create/delete`

**CalDAV & CardDAV (6-7 ish):**
6. **fmcli-qwi** - [FEATURE] Calendar: list, create, update, delete
   - `fmcli calendar list --account=x [--days=30]`
   - `fmcli calendar create --title=... --start=... --end=...`
   - `fmcli calendar update <id> --title=...`
   - `fmcli calendar delete <id>`
   - Test with caldav mocks

7. **fmcli-6p6** - [FEATURE] Contacts: list, search, create, update, delete
   - `fmcli contacts list --account=x`
   - `fmcli contacts search <name>`
   - `fmcli contacts create --name=... --email=...`
   - `fmcli contacts update <id> --name=...`
   - `fmcli contacts delete <id>`

### Phase 3: Polish & Docs (Priority 3)

8. **fmcli-duf** - [FEATURE] Files: list, download, upload, delete
   - `fmcli files list --account=x [--path=/]`
   - `fmcli files download <path> --output=...`
   - `fmcli files upload --local=... --remote=/path`
   - `fmcli files delete <path>`
   - Test with webdavclient3 mocks

9. **fmcli-cl0** - [TASK] Typer CLI framework setup, completions
   - Wire up typer for main CLI
   - Add `--version`, `--help`
   - Shell completions (bash/zsh/fish)
   - Account management: `fmcli account add/list/remove/default`
   - Status/health check

10. **fmcli-axr** - [TASK] README, CLI usage examples, API reference
    - README with multi-account setup instructions
    - All commands with examples
    - Configuration examples
    - Update as development progresses

---

## Development Standards

### Python + UV
- Use `uv run python` / `uv run pytest` instead of direct python/pytest
- All dependencies in `pyproject.toml`
- Virtual environment managed by UV

### TDD
- Write tests **before** implementation
- Use `pytest` with `pytest-cov` for coverage
- Mock all external services (JMAP, CalDAV, CardDAV, WebDAV)
- All public APIs must have `>= 80%` coverage

### Dependency Injection
- All classes that make external calls accept injectable dependencies
- Defaults to production instances
- Tests pass mocks via constructor
- See `/Users/malte/.claude/standards/python/dependency-injection.md`

### Code Style
- Follow Python standards (see `/Users/malte/.claude/standards/python/`)
- Type hints on all public functions
- Docstrings for all public classes/methods

---

## To Get Started

```bash
cd /Users/malte/code/fmcli

# See ready work (no blockers)
bd ready

# Pick a task and start
bd update fmcli-66u --status=in_progress

# Work on it...

# When done
bd close fmcli-66u --reason="<summary of what was accomplished>"
```

---

## Key Files to Know

- `~/.config/fmcli/config.toml` - User configuration
- `src/fmcli/account.py` - Account abstraction with client factories
- `src/fmcli/commands/` - Command implementations
- `tests/` - Test suite
- `pyproject.toml` - Dependencies and project config

