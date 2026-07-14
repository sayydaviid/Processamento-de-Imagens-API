"""Serviço de commits do usuário analisado."""

from __future__ import annotations

import logging
from typing import Any

from github_repo_stats.api import GitHubClient
from github_repo_stats.models import CommitFileRecord, CommitRecord
from github_repo_stats.utils.date_utils import parse_iso_date
from github_repo_stats.utils.text_utils import clean_text


class CommitService:
    """Coleta commits em múltiplas branches e detalha arquivos alterados."""

    def __init__(self, client: GitHubClient, logger: logging.Logger | None = None) -> None:
        self.client = client
        self.logger = logger or logging.getLogger(__name__)

    def get_all_user_commits_across_branches(
        self,
        owner: str,
        repo: str,
        username: str,
        branches: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Busca commits do usuário em todas as branches e remove duplicados por SHA.

        A busca em múltiplas branches evita perder commits que ainda não foram
        mesclados na branch principal. A deduplicação por SHA mantém apenas um
        registro de cada commit encontrado em mais de uma branch.
        """

        commits_by_sha: dict[str, dict[str, Any]] = {}

        for branch in branches:
            branch_name = branch.get("name")
            if not branch_name:
                continue

            self.logger.info("Buscando commits de %s na branch: %s", username, branch_name)
            branch_commits = self.client.paginate(
                f"/repos/{owner}/{repo}/commits",
                params={"author": username, "sha": branch_name},
            )

            for commit in branch_commits:
                sha = commit.get("sha")
                if sha:
                    commit["_found_in_branch"] = branch_name
                    commits_by_sha[sha] = commit

        return list(commits_by_sha.values())

    def get_commit_details(
        self,
        owner: str,
        repo: str,
        commits: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Busca detalhes de cada commit para obter estatísticas e arquivos."""

        detailed: list[dict[str, Any]] = []
        total = len(commits)

        for index, commit in enumerate(commits, start=1):
            sha = commit.get("sha")
            if not sha:
                continue
            self.logger.info("Detalhando commit %s/%s: %s", index, total, sha[:7])
            detail = self.client.get(f"/repos/{owner}/{repo}/commits/{sha}")
            if isinstance(detail, dict):
                detail["_found_in_branch"] = commit.get("_found_in_branch", "")
                detailed.append(detail)

        return detailed

    @staticmethod
    def flatten_user_commits(commit_details: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Transforma commits detalhados em linhas de commits e arquivos."""

        commit_rows: list[dict[str, Any]] = []
        file_rows: list[dict[str, Any]] = []

        for commit_detail in commit_details:
            commit_row = CommitService._build_commit_row(commit_detail)
            commit_rows.append(commit_row.to_dict())
            file_rows.extend(
                file_record.to_dict()
                for file_record in CommitService._build_file_rows(commit_detail)
            )

        return commit_rows, file_rows

    @staticmethod
    def _build_commit_row(commit_detail: dict[str, Any]) -> CommitRecord:
        sha = commit_detail.get("sha", "")
        short_sha = sha[:7]
        html_url = commit_detail.get("html_url", "")

        commit_obj = commit_detail.get("commit", {}) or {}
        author_obj = commit_obj.get("author", {}) or {}
        committer_obj = commit_obj.get("committer", {}) or {}
        github_author = commit_detail.get("author") or {}
        stats = commit_detail.get("stats", {}) or {}

        message = commit_obj.get("message", "")
        first_line = message.splitlines()[0] if message else ""
        author_date = author_obj.get("date")
        parsed_date = parse_iso_date(author_date)

        return CommitRecord(
            sha=sha,
            short_sha=short_sha,
            date=parsed_date.date().isoformat() if parsed_date else "",
            datetime=author_date or "",
            week=parsed_date.strftime("%Y-W%U") if parsed_date else "",
            month=parsed_date.strftime("%Y-%m") if parsed_date else "",
            github_author_login=github_author.get("login", ""),
            git_author_name=author_obj.get("name", ""),
            git_author_email=author_obj.get("email", ""),
            git_committer_name=committer_obj.get("name", ""),
            git_committer_email=committer_obj.get("email", ""),
            message=clean_text(message),
            message_first_line=clean_text(first_line),
            additions=stats.get("additions", 0),
            deletions=stats.get("deletions", 0),
            total_changes=stats.get("total", 0),
            changed_files=len(commit_detail.get("files", []) or []),
            found_in_branch=commit_detail.get("_found_in_branch", ""),
            url=html_url,
        )

    @staticmethod
    def _build_file_rows(commit_detail: dict[str, Any]) -> list[CommitFileRecord]:
        sha = commit_detail.get("sha", "")
        short_sha = sha[:7]
        html_url = commit_detail.get("html_url", "")
        commit_obj = commit_detail.get("commit", {}) or {}
        author_obj = commit_obj.get("author", {}) or {}
        parsed_date = parse_iso_date(author_obj.get("date"))

        rows: list[CommitFileRecord] = []
        for file_data in commit_detail.get("files", []) or []:
            rows.append(
                CommitFileRecord(
                    commit_sha=sha,
                    short_sha=short_sha,
                    date=parsed_date.date().isoformat() if parsed_date else "",
                    filename=file_data.get("filename", ""),
                    previous_filename=file_data.get("previous_filename", ""),
                    status=file_data.get("status", ""),
                    additions=file_data.get("additions", 0),
                    deletions=file_data.get("deletions", 0),
                    changes=file_data.get("changes", 0),
                    raw_url=file_data.get("raw_url", ""),
                    blob_url=file_data.get("blob_url", ""),
                    commit_url=html_url,
                )
            )
        return rows
