from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer

from fmcli.config import Config
from fmcli.account import Account


def resolve_account(account_name: Optional[str] = None) -> Account:
    """Load config and resolve account. Exits with error on failure."""
    config_path = None
    env_path = os.environ.get("FMCLI_CONFIG")
    if env_path:
        config_path = Path(env_path)
    try:
        config = Config.load(config_path)
        acc_config = config.get_account(account_name)
        return Account.from_config(acc_config)
    except FileNotFoundError:
        typer.echo(
            "Error: Config file not found. Create ~/.config/fmcli/config.toml",
            err=True,
        )
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def load_config() -> Config:
    """Load config, respecting FMCLI_CONFIG env var. Exits with error on failure."""
    config_path = None
    env_path = os.environ.get("FMCLI_CONFIG")
    if env_path:
        config_path = Path(env_path)
    try:
        return Config.load(config_path)
    except FileNotFoundError:
        typer.echo(
            "Error: Config file not found. Create ~/.config/fmcli/config.toml",
            err=True,
        )
        raise typer.Exit(1)
