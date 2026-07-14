"""Modelos relacionados a issues e comentários."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class IssueRecord:
    """Linha de issue criada pelo usuário analisado."""

    number: int | None
    title: str
    state: str
    created_at: str
    closed_at: str
    user: str
    comments: int
    labels: str
    url: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        """Converte o modelo para um dicionário exportável."""

        return asdict(self)


@dataclass(frozen=True)
class IssueCommentRecord:
    """Linha de comentário feito em issue ou PR via endpoint de issues."""

    id: int | None
    created_at: str
    updated_at: str
    user: str
    url: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        """Converte o modelo para um dicionário exportável."""

        return asdict(self)
