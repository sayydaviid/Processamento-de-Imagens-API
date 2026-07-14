"""Modelos relacionados a pull requests."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PullRequestRecord:
    """Linha consolidada de um pull request criado pelo usuário."""

    number: int | None
    title: str
    state: str
    draft: bool | None
    created_at: str
    closed_at: str
    merged_at: str
    created_date: str
    merged_date: str
    user: str
    base_branch: str
    head_branch: str
    commits: int
    additions: int
    deletions: int
    changed_files: int
    comments: int
    review_comments: int
    url: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        """Converte o modelo para um dicionário exportável."""

        return asdict(self)


@dataclass(frozen=True)
class PullRequestReviewCommentRecord:
    """Linha de comentário de revisão em pull request."""

    id: int | None
    pull_request_review_id: int | None
    path: str
    position: int | None
    line: int | None
    created_at: str
    updated_at: str
    user: str
    url: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        """Converte o modelo para um dicionário exportável."""

        return asdict(self)
