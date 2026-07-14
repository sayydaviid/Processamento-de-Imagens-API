"""Serviço de pull requests."""

from __future__ import annotations

import logging
from typing import Any

from github_repo_stats.api import GitHubClient
from github_repo_stats.models import PullRequestRecord
from github_repo_stats.utils.date_utils import parse_iso_date
from github_repo_stats.utils.text_utils import clean_text


class PullRequestService:
    """Coleta e transforma pull requests criados pelo usuário."""

    def __init__(self, client: GitHubClient, logger: logging.Logger | None = None) -> None:
        self.client = client
        self.logger = logger or logging.getLogger(__name__)

    def get_pull_requests(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Busca todos os pull requests do repositório."""

        return self.client.paginate(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": "all", "sort": "updated", "direction": "desc"},
        )

    def get_user_pull_request_details(
        self,
        owner: str,
        repo: str,
        username: str,
        pulls: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Filtra PRs do usuário e busca os detalhes de cada PR."""

        user_pulls = [
            pull
            for pull in pulls
            if (pull.get("user") or {}).get("login", "").lower() == username.lower()
        ]

        detailed: list[dict[str, Any]] = []
        for pull in user_pulls:
            number = pull.get("number")
            if number is None:
                continue
            self.logger.info("Detalhando PR #%s", number)
            detail = self.client.get(f"/repos/{owner}/{repo}/pulls/{number}")
            if isinstance(detail, dict):
                detailed.append(detail)
        return detailed

    @staticmethod
    def flatten_pull_requests(pulls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Converte PRs detalhados em linhas exportáveis."""

        rows: list[dict[str, Any]] = []
        for pull in pulls:
            created = parse_iso_date(pull.get("created_at"))
            merged = parse_iso_date(pull.get("merged_at"))

            rows.append(
                PullRequestRecord(
                    number=pull.get("number"),
                    title=clean_text(pull.get("title")),
                    state=pull.get("state", ""),
                    draft=pull.get("draft"),
                    created_at=pull.get("created_at", ""),
                    closed_at=pull.get("closed_at", ""),
                    merged_at=pull.get("merged_at", ""),
                    created_date=created.date().isoformat() if created else "",
                    merged_date=merged.date().isoformat() if merged else "",
                    user=(pull.get("user") or {}).get("login", ""),
                    base_branch=(pull.get("base") or {}).get("ref", ""),
                    head_branch=(pull.get("head") or {}).get("ref", ""),
                    commits=pull.get("commits", 0),
                    additions=pull.get("additions", 0),
                    deletions=pull.get("deletions", 0),
                    changed_files=pull.get("changed_files", 0),
                    comments=pull.get("comments", 0),
                    review_comments=pull.get("review_comments", 0),
                    url=pull.get("html_url", ""),
                    body=clean_text(pull.get("body")),
                ).to_dict()
            )
        return rows
