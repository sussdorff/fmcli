from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "fmcli" / "config.toml"


@dataclass
class AccountConfig:
    name: str
    email: str
    token: str
    app_password: str | None = None
    login: str | None = None
    can_send: bool = False


@dataclass
class Config:
    accounts: list[AccountConfig] = field(default_factory=list)
    _path: Path = field(default=DEFAULT_CONFIG_PATH, repr=False)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Config":
        path = config_path or DEFAULT_CONFIG_PATH
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        accounts = [AccountConfig(**a) for a in data.get("accounts", [])]
        return cls(accounts=accounts, _path=path)

    def get_account(self, name: str | None = None) -> AccountConfig:
        target = name or os.environ.get("FMC_ACCOUNT")
        if target:
            for acc in self.accounts:
                if acc.name == target:
                    return acc
            raise ValueError(f"Account '{target}' not found in config")
        if not self.accounts:
            raise ValueError("No accounts configured")
        return self.accounts[0]
