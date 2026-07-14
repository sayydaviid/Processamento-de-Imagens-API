"""Geração dos gráficos Matplotlib."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


class ChartGenerator:
    """Gera gráficos PNG a partir dos dados consolidados."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def generate(
        self,
        out_dir: Path,
        languages: dict[str, int],
        commit_rows: list[dict[str, Any]],
        file_rows: list[dict[str, Any]],
    ) -> None:
        """Gera todos os gráficos preservados do script original."""

        charts_dir = out_dir / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)

        self._safe_chart(lambda: self._commits_by_day(charts_dir, commit_rows), "commits por dia")
        self._safe_chart(lambda: self._changes_by_day(charts_dir, commit_rows), "adições e remoções por dia")
        self._safe_chart(lambda: self._top_files(charts_dir, file_rows), "arquivos mais alterados")
        self._safe_chart(lambda: self._languages(charts_dir, languages), "linguagens do repositório")

    def _safe_chart(self, callback: Callable[[], None], chart_name: str) -> None:
        try:
            callback()
        except Exception as exc:  # pragma: no cover - proteção para não interromper toda a coleta.
            self.logger.warning("Não foi possível gerar o gráfico %s: %s", chart_name, exc)
        finally:
            plt.close("all")

    def _commits_by_day(self, charts_dir: Path, commit_rows: list[dict[str, Any]]) -> None:
        if not commit_rows:
            self.logger.info("Sem commits para gerar gráfico de commits por dia.")
            return

        data_frame = pd.DataFrame(commit_rows)
        if "date" not in data_frame:
            return

        commits_by_day = data_frame.groupby("date").size().reset_index(name="commits").sort_values("date")
        plt.figure(figsize=(12, 5))
        plt.plot(commits_by_day["date"], commits_by_day["commits"], marker="o")
        plt.title("Commits do usuário por dia")
        plt.xlabel("Data")
        plt.ylabel("Quantidade de commits")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(charts_dir / "commits_por_dia.png", dpi=200)

    def _changes_by_day(self, charts_dir: Path, commit_rows: list[dict[str, Any]]) -> None:
        if not commit_rows:
            self.logger.info("Sem commits para gerar gráfico de adições e remoções.")
            return

        data_frame = pd.DataFrame(commit_rows)
        required = {"date", "additions", "deletions"}
        if not required.issubset(data_frame.columns):
            return

        changes_by_day = data_frame.groupby("date")[["additions", "deletions"]].sum().reset_index().sort_values("date")
        plt.figure(figsize=(12, 5))
        plt.plot(changes_by_day["date"], changes_by_day["additions"], marker="o", label="Adições")
        plt.plot(changes_by_day["date"], changes_by_day["deletions"], marker="o", label="Remoções")
        plt.title("Adições e remoções por dia")
        plt.xlabel("Data")
        plt.ylabel("Linhas")
        plt.xticks(rotation=45, ha="right")
        plt.legend()
        plt.tight_layout()
        plt.savefig(charts_dir / "adicoes_remocoes_por_dia.png", dpi=200)

    def _top_files(self, charts_dir: Path, file_rows: list[dict[str, Any]]) -> None:
        if not file_rows:
            self.logger.info("Sem arquivos alterados para gerar gráfico.")
            return

        data_frame = pd.DataFrame(file_rows)
        required = {"filename", "changes"}
        if not required.issubset(data_frame.columns):
            return

        top_files = (
            data_frame.groupby("filename")["changes"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
            .reset_index()
        )
        plt.figure(figsize=(12, 6))
        plt.barh(top_files["filename"], top_files["changes"])
        plt.title("Arquivos mais alterados pelo usuário")
        plt.xlabel("Quantidade de alterações")
        plt.ylabel("Arquivo")
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig(charts_dir / "arquivos_mais_alterados.png", dpi=200)

    def _languages(self, charts_dir: Path, languages: dict[str, int]) -> None:
        if not languages:
            self.logger.info("Sem linguagens para gerar gráfico.")
            return

        labels = list(languages.keys())
        values = list(languages.values())
        plt.figure(figsize=(8, 8))
        plt.pie(values, labels=labels, autopct="%1.1f%%")
        plt.title("Linguagens do repositório")
        plt.tight_layout()
        plt.savefig(charts_dir / "linguagens_repositorio.png", dpi=200)
