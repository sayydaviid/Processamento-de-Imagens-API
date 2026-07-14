"""Serviço de issues e comentários."""

from __future__ import annotations

from typing import Any

from github_repo_stats.api import GitHubClient
from github_repo_stats.models import IssueCommentRecord, IssueRecord, PullRequestReviewCommentRecord
from github_repo_stats.utils.text_utils import clean_text


class IssueService:
    """Coleta issues, comentários de issues e comentários de revisão em PRs."""

    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    def get_issues(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Busca issues e PRs no endpoint de issues."""

        return self.client.paginate(
            f"/repos/{owner}/{repo}/issues",
            params={"state": "all", "sort": "updated", "direction": "desc"},
        )

    def get_issue_comments(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Busca comentários feitos em issues e conversas de PR."""

        return self.client.paginate(
            f"/repos/{owner}/{repo}/issues/comments",
            params={"sort": "updated", "direction": "desc"},
        )

    def get_pr_review_comments(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Busca comentários de revisão de código em pull requests."""

        return self.client.paginate(
            f"/repos/{owner}/{repo}/pulls/comments",
            params={"sort": "updated", "direction": "desc"},
        )

    @staticmethod
    def flatten_user_issues(username: str, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filtra issues do usuário.

        Pull requests também aparecem no endpoint de issues da API do GitHub.
        Registros com a chave ``pull_request`` são ignorados para evitar dupla contagem.
        """

        rows: list[dict[str, Any]] = []
        for issue in issues:
            if "pull_request" in issue:
                continue
            if (issue.get("user") or {}).get("login", "").lower() != username.lower():
                continue

            labels = ", ".join(label.get("name", "") for label in issue.get("labels", []))
            rows.append(
                IssueRecord(
                    number=issue.get("number"),
                    title=clean_text(issue.get("title")),
                    state=issue.get("state", ""),
                    created_at=issue.get("created_at", ""),
                    closed_at=issue.get("closed_at", ""),
                    user=(issue.get("user") or {}).get("login", ""),
                    comments=issue.get("comments", 0),
                    labels=labels,
                    url=issue.get("html_url", ""),
                    body=clean_text(issue.get("body")),
                ).to_dict()
            )
        return rows

    @staticmethod
    def flatten_user_issue_comments(username: str, comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filtra comentários em issues pelo usuário analisado."""

        rows: list[dict[str, Any]] = []
        for comment in comments:
            if (comment.get("user") or {}).get("login", "").lower() != username.lower():
                continue
            rows.append(
                IssueCommentRecord(
                    id=comment.get("id"),
                    created_at=comment.get("created_at", ""),
                    updated_at=comment.get("updated_at", ""),
                    user=(comment.get("user") or {}).get("login", ""),
                    url=comment.get("html_url", ""),
                    body=clean_text(comment.get("body")),
                ).to_dict()
            )
        return rows

    @staticmethod
    def flatten_user_pr_review_comments(username: str, comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filtra comentários de revisão em pull requests pelo usuário analisado."""

        rows: list[dict[str, Any]] = []
        for comment in comments:
            if (comment.get("user") or {}).get("login", "").lower() != username.lower():
                continue
            rows.append(
                PullRequestReviewCommentRecord(
                    id=comment.get("id"),
                    pull_request_review_id=comment.get("pull_request_review_id"),
                    path=comment.get("path", ""),
                    position=comment.get("position"),
                    line=comment.get("line"),
                    created_at=comment.get("created_at", ""),
                    updated_at=comment.get("updated_at", ""),
                    user=(comment.get("user") or {}).get("login", ""),
                    url=comment.get("html_url", ""),
                    body=clean_text(comment.get("body")),
                ).to_dict()
            )
        return rows
