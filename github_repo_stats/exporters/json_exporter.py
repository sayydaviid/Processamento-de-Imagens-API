"""Exportador JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from github_repo_stats.exceptions import ExportError


class JsonExporter:
    """Salva dados em JSON UTF-8."""

    def save(self, path: Path, data: Any, overwrite: bool = False) -> None:
        """Grava dados em JSON e cria diretórios quando necessário."""

        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise ExportError(f"O arquivo JSON já existe e não será sobrescrito: {path}")

        try:
            with path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2, default=self._default)
        except OSError as exc:
            raise ExportError(f"Não foi possível gravar o arquivo JSON {path}: {exc}") from exc

    @staticmethod
    def _default(value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        raise TypeError(f"Tipo não serializável em JSON: {type(value)!r}")
