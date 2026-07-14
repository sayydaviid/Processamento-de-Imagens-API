"""Modelos para estatísticas consolidadas do usuário."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class UserStatistics:
    """Estatísticas consolidadas do usuário dentro do repositório."""

    total_commits: int
    total_additions: int
    total_deletions: int
    total_changes: int
    total_file_change_events: int
    total_unique_files_changed: int
    first_commit_date: str
    last_commit_date: str
    total_pull_requests_authored: int
    total_issues_authored: int
    total_issue_comments_authored: int
    total_pr_review_comments_authored: int
    commits_by_day: dict[str, int] = field(default_factory=dict)
    commits_by_week: dict[str, int] = field(default_factory=dict)
    file_status_counts: dict[str, int] = field(default_factory=dict)
    top_files_by_changes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Converte o modelo para um dicionário exportável."""

        return asdict(self)
