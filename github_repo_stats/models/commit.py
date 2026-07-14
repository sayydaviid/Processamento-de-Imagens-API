"""Modelos relacionados a commits e arquivos modificados."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CommitRecord:
    """Linha consolidada de um commit do usuário analisado."""

    sha: str
    short_sha: str
    date: str
    datetime: str
    week: str
    month: str
    github_author_login: str
    git_author_name: str
    git_author_email: str
    git_committer_name: str
    git_committer_email: str
    message: str
    message_first_line: str
    additions: int
    deletions: int
    total_changes: int
    changed_files: int
    found_in_branch: str
    url: str

    def to_dict(self) -> dict[str, Any]:
        """Converte o modelo para um dicionário exportável."""

        return asdict(self)


@dataclass(frozen=True)
class CommitFileRecord:
    """Linha de arquivo alterado por um commit."""

    commit_sha: str
    short_sha: str
    date: str
    filename: str
    previous_filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    raw_url: str
    blob_url: str
    commit_url: str

    def to_dict(self) -> dict[str, Any]:
        """Converte o modelo para um dicionário exportável."""

        return asdict(self)
