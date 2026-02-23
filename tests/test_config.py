import pytest
from pathlib import Path
from fmcli.config import AccountConfig, Config


SINGLE_ACCOUNT_TOML = """\
[[accounts]]
name = "personal"
email = "user@fastmail.com"
token = "abc123"
"""

MULTI_ACCOUNT_TOML = """\
[[accounts]]
name = "personal"
email = "user@fastmail.com"
token = "abc123"

[[accounts]]
name = "work"
email = "user@company.com"
token = "def456"
app_password = "secret"
"""


def _write_config(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(content)
    return p


def test_load_single_account(tmp_path: Path) -> None:
    path = _write_config(tmp_path, SINGLE_ACCOUNT_TOML)
    config = Config.load(config_path=path)
    assert len(config.accounts) == 1
    acc = config.accounts[0]
    assert acc.name == "personal"
    assert acc.email == "user@fastmail.com"
    assert acc.token == "abc123"
    assert acc.app_password is None


def test_load_multiple_accounts(tmp_path: Path) -> None:
    path = _write_config(tmp_path, MULTI_ACCOUNT_TOML)
    config = Config.load(config_path=path)
    assert len(config.accounts) == 2
    names = [a.name for a in config.accounts]
    assert "personal" in names
    assert "work" in names


def test_get_account_by_name(tmp_path: Path) -> None:
    path = _write_config(tmp_path, MULTI_ACCOUNT_TOML)
    config = Config.load(config_path=path)
    acc = config.get_account("work")
    assert acc.name == "work"
    assert acc.email == "user@company.com"
    assert acc.token == "def456"
    assert acc.app_password == "secret"


def test_get_account_by_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _write_config(tmp_path, MULTI_ACCOUNT_TOML)
    monkeypatch.setenv("FMC_ACCOUNT", "work")
    config = Config.load(config_path=path)
    acc = config.get_account()
    assert acc.name == "work"


def test_get_account_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _write_config(tmp_path, MULTI_ACCOUNT_TOML)
    monkeypatch.delenv("FMC_ACCOUNT", raising=False)
    config = Config.load(config_path=path)
    acc = config.get_account()
    assert acc.name == "personal"


def test_missing_account_raises(tmp_path: Path) -> None:
    path = _write_config(tmp_path, MULTI_ACCOUNT_TOML)
    config = Config.load(config_path=path)
    with pytest.raises(ValueError, match="nonexistent"):
        config.get_account("nonexistent")


def test_missing_config_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.toml"
    with pytest.raises(FileNotFoundError):
        Config.load(config_path=missing)


def test_app_password_optional(tmp_path: Path) -> None:
    path = _write_config(tmp_path, SINGLE_ACCOUNT_TOML)
    config = Config.load(config_path=path)
    acc = config.accounts[0]
    assert acc.app_password is None
