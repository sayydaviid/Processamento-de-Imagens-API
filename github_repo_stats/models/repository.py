"""Modelos relacionados ao repositório."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RepositoryInfo:
    """Resumo dos campos principais do repositório GitHub."""

    owner: str
    repo: str
    full_name: str
    url: str
    description: str
    default_branch: str
    created_at: str
    updated_at: str
    pushed_at: str
    stars: int
    forks: int
    watchers: int
    open_issues: int
    size_kb: int

    def to_dict(self) -> dict[str, Any]:
        """Converte o modelo para um dicionário exportável."""

        return asdict(self)


@dataclass(frozen=True)
class ContributorRecord:
    """Linha de contribuidor retornado pela API do GitHub."""

    login: str
    type: str
    contributions: int
    profile_url: str

    def to_dict(self) -> dict[str, Any]:
        """Converte o modelo para um dicionário exportável."""

        return asdict(self)
