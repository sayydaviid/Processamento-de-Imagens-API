"""Carregamento e validação das configurações da aplicação."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from github_repo_stats.exceptions import ConfigurationError

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - mantem uma mensagem clara se a dependência faltar.
    load_dotenv = None  # type: ignore[assignment]


DEFAULT_API_VERSION = "2022-11-28"
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_SLEEP_BETWEEN_REQUESTS = 0.15


@dataclass(frozen=True)
class ApplicationConfig:
    """Configuração validada necessária para executar a análise."""

    owner: str
    repository: str
    username: str
    token: Optional[str]
    github_api_version: str = DEFAULT_API_VERSION
    output_root: Path = Path(".")
    request_timeout: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    sleep_between_requests: float = DEFAULT_SLEEP_BETWEEN_REQUESTS
    log_to_file: bool = True


class ConfigLoader:
    """Carrega argumentos, arquivo JSON e variáveis do ``.env``.

    A ordem de prioridade é:

    1. argumentos do terminal;
    2. arquivo de configuração;
    3. erro de configuração se faltar algum campo obrigatório.

    O token é lido exclusivamente das variáveis carregadas pelo ``.env``.
    """

    def __init__(
        self,
        env_file: Path | str = ".env",
        default_config_file: Path | str = DEFAULT_CONFIG_FILE,
    ) -> None:
        self.env_file = Path(env_file)
        self.default_config_file = Path(default_config_file)

    def load(self, args: Any) -> ApplicationConfig:
        """Retorna a configuração final da aplicação."""

        self._load_environment()
        config_path = self._resolve_config_path(getattr(args, "config", None))
        config_data = self._read_config_file(config_path)

        owner = self._pick_value("owner", getattr(args, "owner", None), config_data)
        repository = self._pick_value(
            "repository",
            getattr(args, "repo", None),
            config_data,
            aliases=("repo",),
        )
        username = self._pick_value(
            "username",
            getattr(args, "user", None),
            config_data,
            aliases=("user",),
        )

        missing = [
            name
            for name, value in {
                "owner": owner,
                "repository": repository,
                "username": username,
            }.items()
            if not value
        ]
        if missing:
            campos = ", ".join(missing)
            raise ConfigurationError(
                "Dados obrigatórios ausentes: "
                f"{campos}. Informe --owner, --repo e --user no terminal "
                "ou configure esses campos em config.json."
            )

        return ApplicationConfig(
            owner=str(owner),
            repository=str(repository),
            username=str(username),
            token=os.getenv("GITHUB_TOKEN") or None,
            github_api_version=os.getenv("GITHUB_API_VERSION", DEFAULT_API_VERSION),
        )

    def _load_environment(self) -> None:
        if load_dotenv is not None:
            load_dotenv(dotenv_path=self.env_file, override=False)
            return

        if not self.env_file.exists():
            return

        for line in self.env_file.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

    def _resolve_config_path(self, cli_config: Optional[str]) -> Optional[Path]:
        if cli_config:
            return Path(cli_config)
        if self.default_config_file.exists():
            return self.default_config_file
        return None

    def _read_config_file(self, config_path: Optional[Path]) -> dict[str, Any]:
        if config_path is None:
            return {}

        if not config_path.exists():
            raise ConfigurationError(
                f"Arquivo de configuração não encontrado: {config_path}. "
                "Crie o arquivo ou informe os parâmetros pelo terminal."
            )

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"Arquivo de configuração inválido: {config_path}. "
                "Verifique se o JSON está bem formado."
            ) from exc

        if not isinstance(data, dict):
            raise ConfigurationError(
                f"Arquivo de configuração inválido: {config_path}. "
                "O conteúdo raiz deve ser um objeto JSON."
            )
        return data

    @staticmethod
    def _pick_value(
        key: str,
        cli_value: Optional[str],
        config_data: Mapping[str, Any],
        aliases: tuple[str, ...] = (),
    ) -> Optional[str]:
        if cli_value:
            return cli_value
        for candidate in (key, *aliases):
            value = config_data.get(candidate)
            if value:
                return str(value)
        return None
