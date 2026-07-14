"""Serviço de estatísticas oficiais e consolidadas."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from github_repo_stats.api import GitHubClient
from github_repo_stats.exceptions import GitHubApiError
from github_repo_stats.models import UserStatistics
from github_repo_stats.utils.date_utils import parse_iso_date, unix_timestamp_to_date


DAY_NAMES = ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday")


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

    def get_manual_repository_statistics(
        self,
        owner: str,
        repo: str,
        default_branch: str | None,
    ) -> dict[str, Any]:
        """Calcula localmente estatisticas de atividade e frequencia de codigo."""

        commit_details = self.get_default_branch_commit_details(owner, repo, default_branch)
        manual_stats = self.build_manual_repository_statistics_from_commit_details(commit_details)

        skipped_merges = manual_stats.get("skipped_merge_commits", 0)
        if skipped_merges:
            self.logger.info("Ignorando %s merge commits nas metricas manuais.", skipped_merges)

        return manual_stats

    def get_default_branch_commit_details(
        self,
        owner: str,
        repo: str,
        default_branch: str | None,
    ) -> list[dict[str, Any]]:
        """Busca e detalha todos os commits da branch padrao."""

        if self.client is None:
            raise GitHubApiError("Cliente GitHub nao configurado para buscar commits da branch padrao.")

        branch_name = default_branch or "main"
        self.logger.info("Buscando commits da branch padrao para fallback manual: %s", branch_name)
        commits = self.client.paginate(f"/repos/{owner}/{repo}/commits", params={"sha": branch_name})
        self.logger.info("Total de commits encontrados na branch padrao %s: %s", branch_name, len(commits))

        detailed: list[dict[str, Any]] = []
        total = len(commits)
        for index, commit in enumerate(commits, start=1):
            sha = commit.get("sha")
            if not sha:
                continue

            self.logger.info("Detalhando commit da branch padrao %s/%s: %s", index, total, sha[:7])
            detail = self.client.get(f"/repos/{owner}/{repo}/commits/{sha}")
            if isinstance(detail, dict):
                detail["_found_in_branch"] = branch_name
                detailed.append(detail)

        return detailed

    @classmethod
    def build_manual_repository_statistics_from_commit_details(
        cls,
        commit_details: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Gera os formatos manual e compativel com a API para duas metricas."""

        # Os endpoints oficiais do GitHub podem retornar 202 por tempo indefinido;
        # estas metricas manuais sao calculadas localmente a partir dos commits da branch padrao.
        filtered_details = [detail for detail in commit_details if not cls._is_merge_commit(detail)]
        skipped_merge_commits = len(commit_details) - len(filtered_details)

        commit_activity_rows, commit_activity_api_like = cls._build_manual_commit_activity(filtered_details)
        code_frequency_rows, code_frequency_api_like = cls._build_manual_code_frequency(filtered_details)

        return {
            "commit_activity_rows": commit_activity_rows,
            "commit_activity_api_like": commit_activity_api_like,
            "code_frequency_rows": code_frequency_rows,
            "code_frequency_api_like": code_frequency_api_like,
            "skipped_merge_commits": skipped_merge_commits,
        }

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

    @classmethod
    def _build_manual_commit_activity(
        cls,
        commit_details: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        activity_by_week: dict[int, dict[str, Any]] = {}

        for commit_detail in commit_details:
            commit_datetime = cls._commit_datetime(commit_detail)
            if commit_datetime is None:
                continue

            week_start = cls._week_start_sunday(commit_datetime)
            week_timestamp = cls._week_timestamp(week_start)
            day_index = cls._github_day_index(commit_datetime)

            if week_timestamp not in activity_by_week:
                activity_by_week[week_timestamp] = {
                    "week_start": week_start.isoformat(),
                    "week_timestamp": week_timestamp,
                    "total": 0,
                    "days": [0, 0, 0, 0, 0, 0, 0],
                }

            week = activity_by_week[week_timestamp]
            week["total"] += 1
            week["days"][day_index] += 1

        rows: list[dict[str, Any]] = []
        api_like: list[dict[str, Any]] = []

        for week_timestamp in sorted(activity_by_week):
            week = activity_by_week[week_timestamp]
            days = week["days"]
            row = {
                "week_start": week["week_start"],
                "week_timestamp": week["week_timestamp"],
                "total": week["total"],
            }
            row.update({day_name: days[index] for index, day_name in enumerate(DAY_NAMES)})
            rows.append(row)

            api_like.append(
                {
                    "week": week["week_timestamp"],
                    "total": week["total"],
                    "days": days,
                }
            )

        return rows, api_like

    @classmethod
    def _build_manual_code_frequency(
        cls,
        commit_details: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[list[int]]]:
        frequency_by_week: dict[int, dict[str, Any]] = {}

        for commit_detail in commit_details:
            commit_datetime = cls._commit_datetime(commit_detail)
            if commit_datetime is None:
                continue

            week_start = cls._week_start_sunday(commit_datetime)
            week_timestamp = cls._week_timestamp(week_start)
            stats = commit_detail.get("stats", {}) or {}
            additions = cls._safe_int(stats.get("additions"))
            deletions = cls._safe_int(stats.get("deletions"))
            total_changes = cls._safe_int(stats.get("total"))
            if not total_changes:
                total_changes = additions + deletions

            if week_timestamp not in frequency_by_week:
                frequency_by_week[week_timestamp] = {
                    "week_start": week_start.isoformat(),
                    "week_timestamp": week_timestamp,
                    "additions": 0,
                    "deletions": 0,
                    "total_changes": 0,
                }

            week = frequency_by_week[week_timestamp]
            week["additions"] += additions
            week["deletions"] += deletions
            week["total_changes"] += total_changes

        rows = [frequency_by_week[week_timestamp] for week_timestamp in sorted(frequency_by_week)]
        api_like = [
            [row["week_timestamp"], row["additions"], -row["deletions"]]
            for row in rows
        ]

        return rows, api_like

    @staticmethod
    def _is_merge_commit(commit_detail: dict[str, Any]) -> bool:
        parents = commit_detail.get("parents") or []
        return isinstance(parents, list) and len(parents) > 1

    @staticmethod
    def _commit_datetime(commit_detail: dict[str, Any]) -> datetime | None:
        commit_obj = commit_detail.get("commit", {}) or {}
        author_obj = commit_obj.get("author", {}) or {}
        committer_obj = commit_obj.get("committer", {}) or {}
        raw_date = author_obj.get("date") or committer_obj.get("date")
        parsed = parse_iso_date(raw_date)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _week_start_sunday(value: datetime) -> date:
        days_since_sunday = (value.weekday() + 1) % 7
        return value.date() - timedelta(days=days_since_sunday)

    @staticmethod
    def _week_timestamp(week_start: date) -> int:
        return int(datetime.combine(week_start, time.min, tzinfo=timezone.utc).timestamp())

    @staticmethod
    def _github_day_index(value: datetime) -> int:
        return (value.weekday() + 1) % 7

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

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
