"""Serviço de estatísticas oficiais e consolidadas."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any

from github_repo_stats.api import GitHubClient
from github_repo_stats.exceptions import GitHubApiError
from github_repo_stats.models import UserStatistics
from github_repo_stats.utils.date_utils import unix_timestamp_to_date


class StatisticsService:
    """Coleta estatísticas do GitHub Insights e consolida métricas locais."""

    def __init__(self, client: GitHubClient | None = None, logger: logging.Logger | None = None) -> None:
        self.client = client
        self.logger = logger or logging.getLogger(__name__)

    def get_repository_statistics(self, owner: str, repo: str) -> dict[str, Any]:
        """Busca estatísticas oficiais usadas pelos gráficos do GitHub Insights.

        Esses endpoints podem retornar HTTP 202 quando o GitHub ainda está
        calculando os dados. O cliente já tenta novamente e retorna ``None`` se
        a estatística não ficar pronta no tempo configurado.
        """

        if self.client is None:
            raise GitHubApiError("Cliente GitHub não configurado para buscar estatísticas.")

        endpoints = {
            "contributors": f"/repos/{owner}/{repo}/stats/contributors",
            "commit_activity": f"/repos/{owner}/{repo}/stats/commit_activity",
            "code_frequency": f"/repos/{owner}/{repo}/stats/code_frequency",
            "participation": f"/repos/{owner}/{repo}/stats/participation",
            "punch_card": f"/repos/{owner}/{repo}/stats/punch_card",
        }

        stats: dict[str, Any] = {}
        for name, path in endpoints.items():
            self.logger.info("Buscando estatística oficial: %s", name)
            try:
                stats[name] = self.client.get(path)
            except GitHubApiError as exc:
                self.logger.warning("Não foi possível buscar %s: %s", name, exc)
                stats[name] = None
        return stats

    @staticmethod
    def flatten_repo_stats_contributors(stats_contributors: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Converte estatísticas de contribuidores em resumo e série semanal."""

        summary_rows: list[dict[str, Any]] = []
        weekly_rows: list[dict[str, Any]] = []

        if not isinstance(stats_contributors, list):
            return summary_rows, weekly_rows

        for contributor in stats_contributors:
            author = contributor.get("author") or {}
            login = author.get("login", "")
            weeks = contributor.get("weeks") or []

            total_additions = sum(week.get("a", 0) for week in weeks)
            total_deletions = sum(week.get("d", 0) for week in weeks)
            total_commits = sum(week.get("c", 0) for week in weeks)

            summary_rows.append(
                {
                    "login": login,
                    "total_commits": contributor.get("total", 0),
                    "weekly_commits_sum": total_commits,
                    "total_additions": total_additions,
                    "total_deletions": total_deletions,
                    "profile_url": author.get("html_url", ""),
                }
            )

            for week in weeks:
                weekly_rows.append(
                    {
                        "login": login,
                        "week_start": unix_timestamp_to_date(week.get("w")),
                        "additions": week.get("a", 0),
                        "deletions": week.get("d", 0),
                        "commits": week.get("c", 0),
                    }
                )

        return summary_rows, weekly_rows

    @staticmethod
    def flatten_code_frequency(code_frequency: Any) -> list[dict[str, Any]]:
        """Converte frequência de código oficial para linhas CSV."""

        rows: list[dict[str, Any]] = []
        if not isinstance(code_frequency, list):
            return rows

        for item in code_frequency:
            if not isinstance(item, list) or len(item) < 3:
                continue
            rows.append(
                {
                    "week_start": unix_timestamp_to_date(item[0]),
                    "additions": item[1],
                    "deletions": item[2],
                }
            )
        return rows

    @staticmethod
    def flatten_commit_activity(commit_activity: Any) -> list[dict[str, Any]]:
        """Converte atividade semanal de commits para linhas CSV."""

        rows: list[dict[str, Any]] = []
        if not isinstance(commit_activity, list):
            return rows

        for item in commit_activity:
            days = item.get("days", [])
            rows.append(
                {
                    "week_start": unix_timestamp_to_date(item.get("week")),
                    "total": item.get("total", 0),
                    "sunday": days[0] if len(days) > 0 else 0,
                    "monday": days[1] if len(days) > 1 else 0,
                    "tuesday": days[2] if len(days) > 2 else 0,
                    "wednesday": days[3] if len(days) > 3 else 0,
                    "thursday": days[4] if len(days) > 4 else 0,
                    "friday": days[5] if len(days) > 5 else 0,
                    "saturday": days[6] if len(days) > 6 else 0,
                }
            )
        return rows

    @staticmethod
    def flatten_participation(participation: Any) -> list[dict[str, Any]]:
        """Converte participação semanal para linhas CSV."""

        rows: list[dict[str, Any]] = []
        if not isinstance(participation, dict):
            return rows

        all_weeks = participation.get("all", []) or []
        owner_weeks = participation.get("owner", []) or []
        max_len = max(len(all_weeks), len(owner_weeks))

        for index in range(max_len):
            rows.append(
                {
                    "week_index": index + 1,
                    "all_commits": all_weeks[index] if index < len(all_weeks) else 0,
                    "owner_commits": owner_weeks[index] if index < len(owner_weeks) else 0,
                }
            )
        return rows

    @staticmethod
    def flatten_punch_card(punch_card: Any) -> list[dict[str, Any]]:
        """Converte punch card oficial para linhas CSV."""

        rows: list[dict[str, Any]] = []
        if not isinstance(punch_card, list):
            return rows

        days = {
            0: "Sunday",
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
        }

        for item in punch_card:
            if not isinstance(item, list) or len(item) < 3:
                continue
            rows.append(
                {
                    "day_number": item[0],
                    "day_name": days.get(item[0], ""),
                    "hour": item[1],
                    "commits": item[2],
                }
            )
        return rows

    @staticmethod
    def aggregate_user_stats(
        commit_rows: list[dict[str, Any]],
        file_rows: list[dict[str, Any]],
        pr_rows: list[dict[str, Any]],
        issue_rows: list[dict[str, Any]],
        issue_comment_rows: list[dict[str, Any]],
        pr_comment_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Consolida as métricas finais do usuário analisado."""

        total_commits = len(commit_rows)
        total_additions = sum(int(row.get("additions") or 0) for row in commit_rows)
        total_deletions = sum(int(row.get("deletions") or 0) for row in commit_rows)
        total_changes = sum(int(row.get("total_changes") or 0) for row in commit_rows)

        dates = [row.get("date") for row in commit_rows if row.get("date")]
        commits_by_day = Counter(row.get("date") for row in commit_rows if row.get("date"))
        commits_by_week = Counter(row.get("week") for row in commit_rows if row.get("week"))
        file_churn = StatisticsService._aggregate_file_churn(file_rows)
        status_counter = Counter(row.get("status") for row in file_rows if row.get("status"))

        unique_files = len({row.get("filename") for row in file_rows if row.get("filename")})

        return UserStatistics(
            total_commits=total_commits,
            total_additions=total_additions,
            total_deletions=total_deletions,
            total_changes=total_changes,
            total_file_change_events=len(file_rows),
            total_unique_files_changed=unique_files,
            first_commit_date=min(dates) if dates else "",
            last_commit_date=max(dates) if dates else "",
            total_pull_requests_authored=len(pr_rows),
            total_issues_authored=len(issue_rows),
            total_issue_comments_authored=len(issue_comment_rows),
            total_pr_review_comments_authored=len(pr_comment_rows),
            commits_by_day=dict(sorted(commits_by_day.items())),
            commits_by_week=dict(sorted(commits_by_week.items())),
            file_status_counts=dict(status_counter),
            top_files_by_changes=file_churn[:30],
        ).to_dict()

    @staticmethod
    def _aggregate_file_churn(file_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        file_churn: defaultdict[str, dict[str, int]] = defaultdict(
            lambda: {"commits": 0, "additions": 0, "deletions": 0, "changes": 0}
        )

        for row in file_rows:
            filename = row.get("filename", "")
            if not filename:
                continue
            file_churn[filename]["commits"] += 1
            file_churn[filename]["additions"] += int(row.get("additions") or 0)
            file_churn[filename]["deletions"] += int(row.get("deletions") or 0)
            file_churn[filename]["changes"] += int(row.get("changes") or 0)

        return sorted(
            [{"filename": filename, **stats} for filename, stats in file_churn.items()],
            key=lambda item: item["changes"],
            reverse=True,
        )
