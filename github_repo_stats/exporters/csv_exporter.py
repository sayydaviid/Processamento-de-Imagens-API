"""Exportador CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Optional

from github_repo_stats.exceptions import ExportError


class CsvExporter:
    """Salva listas de dicionários em arquivos CSV UTF-8."""

    def save(
        self,
        path: Path,
        rows: Iterable[dict[str, Any]],
        fieldnames: Optional[list[str]] = None,
        overwrite: bool = False,
    ) -> None:
        """Grava um CSV e cria diretórios quando necessário."""

        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise ExportError(f"O arquivo CSV já existe e não será sobrescrito: {path}")

        materialized_rows = list(rows)
        if fieldnames is None and materialized_rows:
            keys: set[str] = set()
            for row in materialized_rows:
                keys.update(row.keys())
            fieldnames = sorted(keys)

        try:
            with path.open("w", newline="", encoding="utf-8") as file:
                if fieldnames is None:
                    file.write("")
                    return
                writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(materialized_rows)
        except OSError as exc:
            raise ExportError(f"Não foi possível gravar o arquivo CSV {path}: {exc}") from exc
