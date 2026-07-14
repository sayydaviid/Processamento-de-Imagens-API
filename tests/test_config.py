from argparse import Namespace
import json

import pytest

from github_repo_stats.config import ConfigLoader
from github_repo_stats.exceptions import ConfigurationError


def test_config_uses_cli_values_before_file_values(tmp_path, monkeypatch) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({"owner": "arquivo", "repository": "repo-arquivo", "username": "usuario-arquivo"}),
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=token_teste\nGITHUB_API_VERSION=2022-11-28\n", encoding="utf-8")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_API_VERSION", raising=False)

    args = Namespace(owner="cli", repo="repo-cli", user="usuario-cli", config=str(config_file))

    config = ConfigLoader(env_file=env_file).load(args)

    assert config.owner == "cli"
    assert config.repository == "repo-cli"
    assert config.username == "usuario-cli"
    assert config.token == "token_teste"


def test_config_accepts_missing_token_for_public_repositories(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_API_VERSION", raising=False)
    args = Namespace(owner="dono", repo="repo", user="usuario", config=None)

    config = ConfigLoader(env_file=tmp_path / ".env", default_config_file=tmp_path / "config.json").load(args)

    assert config.token is None


def test_config_raises_when_required_fields_are_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    args = Namespace(owner=None, repo=None, user=None, config=None)

    with pytest.raises(ConfigurationError):
        ConfigLoader(env_file=tmp_path / ".env", default_config_file=tmp_path / "config.json").load(args)
