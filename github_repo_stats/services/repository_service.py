"""Serviço de dados gerais do repositório."""

from __future__ import annotations

from typing import Any

from github_repo_stats.api import GitHubClient
from github_repo_stats.models import ContributorRecord
from github_repo_stats.utils.text_utils import clean_text


class RepositoryService:
    """Coleta e transforma dados gerais do repositório."""

    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    def get_repository_data(self, owner: str, repo: str) -> dict[str, Any]:
        """Busca os metadados principais do repositório."""

        return self.client.get(f"/repos/{owner}/{repo}")

    def get_languages(self, owner: str, repo: str) -> dict[str, int]:
        """Busca as linguagens detectadas no repositório."""

        data = self.client.get(f"/repos/{owner}/{repo}/languages")
        return data if isinstance(data, dict) else {}

    def get_branches(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Busca todas as branches do repositório."""

        return self.client.paginate(f"/repos/{owner}/{repo}/branches")

    def get_tags(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Busca todas as tags do repositório."""

        return self.client.paginate(f"/repos/{owner}/{repo}/tags")

    def get_releases(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Busca todas as releases do repositório."""

        return self.client.paginate(f"/repos/{owner}/{repo}/releases")

    def get_contributors(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Busca contribuidores, incluindo autores anônimos quando existirem."""

        return self.client.paginate(f"/repos/{owner}/{repo}/contributors", params={"anon": "true"})

    @staticmethod
    def language_rows(languages: dict[str, int]) -> list[dict[str, Any]]:
        """Converte linguagens para linhas CSV com percentual."""

        language_total = sum(languages.values()) or 1
        return [
            {
                "language": language,
                "bytes": bytes_count,
                "percent": round((bytes_count / language_total) * 100, 2),
            }
            for language, bytes_count in sorted(languages.items(), key=lambda item: item[1], reverse=True)
        ]

    @staticmethod
    def branch_rows(branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Converte branches para linhas CSV."""

        return [
            {
                "name": branch.get("name"),
                "commit_sha": (branch.get("commit") or {}).get("sha", ""),
                "protected": branch.get("protected", ""),
            }
            for branch in branches
        ]

    @staticmethod
    def tag_rows(tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Converte tags para linhas CSV."""

        return [
            {
                "name": tag.get("name"),
                "commit_sha": (tag.get("commit") or {}).get("sha", ""),
                "zipball_url": tag.get("zipball_url", ""),
                "tarball_url": tag.get("tarball_url", ""),
            }
            for tag in tags
        ]

    @staticmethod
    def release_rows(releases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Converte releases para linhas CSV."""

        return [
            {
                "id": release.get("id"),
                "name": release.get("name"),
                "tag_name": release.get("tag_name"),
                "draft": release.get("draft"),
                "prerelease": release.get("prerelease"),
                "created_at": release.get("created_at"),
                "published_at": release.get("published_at"),
                "author": (release.get("author") or {}).get("login", ""),
                "url": release.get("html_url", ""),
                "body": clean_text(release.get("body")),
            }
            for release in releases
        ]

    @staticmethod
    def contributor_rows(contributors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Converte contribuidores para linhas CSV."""

        return [
            ContributorRecord(
                login=contributor.get("login", contributor.get("name", "")),
                type=contributor.get("type", ""),
                contributions=contributor.get("contributions", 0),
                profile_url=contributor.get("html_url", ""),
            ).to_dict()
            for contributor in contributors
        ]
