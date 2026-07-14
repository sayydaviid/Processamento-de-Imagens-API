"""Coordenação principal da aplicação."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from github_repo_stats.api import GitHubClient
from github_repo_stats.charts import ChartGenerator
from github_repo_stats.config import ApplicationConfig, ConfigLoader
from github_repo_stats.exceptions import ConfigurationError, GitHubApiError
from github_repo_stats.exporters import CsvExporter, JsonExporter, MarkdownExporter
from github_repo_stats.services import (
    CommitService,
    IssueService,
    PullRequestService,
    RepositoryService,
    StatisticsService,
)
from github_repo_stats.utils.file_utils import ensure_output_dir
from github_repo_stats.utils.logging_utils import add_file_handler, configure_logging


class Application:
    """Coordena serviços, exportadores e geração de artefatos."""

    def __init__(self, config: ApplicationConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.csv_exporter = CsvExporter()
        self.json_exporter = JsonExporter()
        self.markdown_exporter = MarkdownExporter()
        self.chart_generator = ChartGenerator(self.logger)

    def run(self) -> Path:
        """Executa a coleta completa e retorna a pasta de saída."""

        if not self.config.token:
            self.logger.warning(
                "GITHUB_TOKEN não está configurado. Repositórios públicos podem funcionar, "
                "mas o limite de requisições será menor."
            )

        out_dir = ensure_output_dir(
            f"github_stats_{self.config.repository}_{self.config.username}",
            root=self.config.output_root,
        )
        if self.config.log_to_file:
            add_file_handler(out_dir / "application.log")

        with GitHubClient(
            token=self.config.token,
            api_version=self.config.github_api_version,
            timeout=self.config.request_timeout,
            max_retries=self.config.max_retries,
            sleep_between_requests=self.config.sleep_between_requests,
            logger=self.logger,
        ) as client:
            self._run_with_client(client, out_dir)

        self.logger.info("Estatísticas geradas com sucesso em: %s", out_dir.resolve())
        return out_dir

    def _run_with_client(self, client: GitHubClient, out_dir: Path) -> None:
        owner = self.config.owner
        repo = self.config.repository
        username = self.config.username

        repository_service = RepositoryService(client)
        commit_service = CommitService(client, self.logger)
        pull_request_service = PullRequestService(client, self.logger)
        issue_service = IssueService(client)
        statistics_service = StatisticsService(client, self.logger)

        self.logger.info("Buscando dados gerais do repositório.")
        repo_data = repository_service.get_repository_data(owner, repo)
        self.json_exporter.save(out_dir / "json" / "repo.json", repo_data)

        self.logger.info("Buscando linguagens.")
        languages = repository_service.get_languages(owner, repo)
        self.json_exporter.save(out_dir / "json" / "languages.json", languages)
        self.csv_exporter.save(out_dir / "csv" / "languages.csv", repository_service.language_rows(languages))

        branches = self._collect_repository_lists(repository_service, owner, repo, out_dir)
        commit_rows, file_rows = self._collect_commits(commit_service, owner, repo, username, branches, out_dir)
        pr_rows = self._collect_pull_requests(pull_request_service, owner, repo, username, out_dir)
        issue_rows, issue_comment_rows, pr_comment_rows = self._collect_issues(issue_service, owner, repo, username, out_dir)
        self._collect_official_stats(
            statistics_service,
            owner,
            repo,
            out_dir,
            repo_data.get("default_branch") or "main",
        )

        user_stats = statistics_service.aggregate_user_stats(
            commit_rows=commit_rows,
            file_rows=file_rows,
            pr_rows=pr_rows,
            issue_rows=issue_rows,
            issue_comment_rows=issue_comment_rows,
            pr_comment_rows=pr_comment_rows,
        )

        self._export_derived_user_stats(out_dir, user_stats)
        self._export_summary(out_dir, owner, repo, username, repo_data, user_stats)

        self.logger.info("Gerando gráficos.")
        self.chart_generator.generate(out_dir, languages, commit_rows, file_rows)

        self.logger.info("Gerando resumo em Markdown.")
        self.markdown_exporter.save_summary(out_dir, owner, repo, username, repo_data, user_stats)

    def _collect_repository_lists(
        self,
        service: RepositoryService,
        owner: str,
        repo: str,
        out_dir: Path,
    ) -> list[dict[str, Any]]:
        self.logger.info("Buscando branches.")
        branches = service.get_branches(owner, repo)
        self.json_exporter.save(out_dir / "json" / "branches.json", branches)
        self.csv_exporter.save(out_dir / "csv" / "branches.csv", service.branch_rows(branches))

        self.logger.info("Buscando tags.")
        tags = service.get_tags(owner, repo)
        self.json_exporter.save(out_dir / "json" / "tags.json", tags)
        self.csv_exporter.save(out_dir / "csv" / "tags.csv", service.tag_rows(tags))

        self.logger.info("Buscando releases.")
        releases = service.get_releases(owner, repo)
        self.json_exporter.save(out_dir / "json" / "releases.json", releases)
        self.csv_exporter.save(out_dir / "csv" / "releases.csv", service.release_rows(releases))

        self.logger.info("Buscando contribuidores.")
        contributors = service.get_contributors(owner, repo)
        self.json_exporter.save(out_dir / "json" / "contributors.json", contributors)
        self.csv_exporter.save(out_dir / "csv" / "contributors.csv", service.contributor_rows(contributors))
        return branches

    def _collect_commits(
        self,
        service: CommitService,
        owner: str,
        repo: str,
        username: str,
        branches: list[dict[str, Any]],
        out_dir: Path,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        self.logger.info("Buscando commits do usuário em todas as branches.")
        user_commits = service.get_all_user_commits_across_branches(owner, repo, username, branches)
        self.json_exporter.save(out_dir / "json" / "my_commits_raw.json", user_commits)
        self.logger.info("Total de commits únicos encontrados para %s: %s", username, len(user_commits))

        commit_details = service.get_commit_details(owner, repo, user_commits)
        self.json_exporter.save(out_dir / "json" / "my_commits_detailed.json", commit_details)

        commit_rows, file_rows = service.flatten_user_commits(commit_details)
        commit_rows = sorted(commit_rows, key=lambda row: row.get("datetime", ""))
        file_rows = sorted(file_rows, key=lambda row: (row.get("date", ""), row.get("filename", "")))

        self.csv_exporter.save(out_dir / "csv" / "my_commits.csv", commit_rows)
        self.csv_exporter.save(out_dir / "csv" / "my_commit_files.csv", file_rows)
        return commit_rows, file_rows

    def _collect_pull_requests(
        self,
        service: PullRequestService,
        owner: str,
        repo: str,
        username: str,
        out_dir: Path,
    ) -> list[dict[str, Any]]:
        self.logger.info("Buscando pull requests.")
        pulls = service.get_pull_requests(owner, repo)
        self.json_exporter.save(out_dir / "json" / "pull_requests_raw.json", pulls)

        details = service.get_user_pull_request_details(owner, repo, username, pulls)
        self.json_exporter.save(out_dir / "json" / "my_pull_requests_detailed.json", details)

        rows = service.flatten_pull_requests(details)
        self.csv_exporter.save(out_dir / "csv" / "my_pull_requests.csv", rows)
        return rows

    def _collect_issues(
        self,
        service: IssueService,
        owner: str,
        repo: str,
        username: str,
        out_dir: Path,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        self.logger.info("Buscando issues.")
        issues = service.get_issues(owner, repo)
        self.json_exporter.save(out_dir / "json" / "issues_raw.json", issues)
        issue_rows = service.flatten_user_issues(username, issues)
        self.csv_exporter.save(out_dir / "csv" / "my_issues.csv", issue_rows)

        self.logger.info("Buscando comentários em issues.")
        issue_comments = service.get_issue_comments(owner, repo)
        self.json_exporter.save(out_dir / "json" / "issue_comments_raw.json", issue_comments)
        issue_comment_rows = service.flatten_user_issue_comments(username, issue_comments)
        self.csv_exporter.save(out_dir / "csv" / "my_issue_comments.csv", issue_comment_rows)

        self.logger.info("Buscando comentários de revisão em PRs.")
        pr_review_comments = service.get_pr_review_comments(owner, repo)
        self.json_exporter.save(out_dir / "json" / "pr_review_comments_raw.json", pr_review_comments)
        pr_comment_rows = service.flatten_user_pr_review_comments(username, pr_review_comments)
        self.csv_exporter.save(out_dir / "csv" / "my_pr_review_comments.csv", pr_comment_rows)
        return issue_rows, issue_comment_rows, pr_comment_rows

    def _collect_official_stats(
        self,
        service: StatisticsService,
        owner: str,
        repo: str,
        out_dir: Path,
        default_branch: str | None,
    ) -> None:
        self.logger.info("Buscando estatísticas oficiais do GitHub Insights.")
        official_stats = service.get_repository_statistics(owner, repo)
        self.json_exporter.save(out_dir / "json" / "official_repository_statistics.json", official_stats)

        stats_with_fallback = dict(official_stats)
        commit_activity_rows = service.flatten_commit_activity(stats_with_fallback.get("commit_activity"))
        code_frequency_rows = service.flatten_code_frequency(stats_with_fallback.get("code_frequency"))
        needs_commit_activity_fallback = not commit_activity_rows
        needs_code_frequency_fallback = not code_frequency_rows

        if needs_commit_activity_fallback or needs_code_frequency_fallback:
            if needs_commit_activity_fallback:
                self.logger.info("commit_activity oficial indisponivel. Gerando metrica manual.")
            if needs_code_frequency_fallback:
                self.logger.info("code_frequency oficial indisponivel. Gerando metrica manual.")

            manual_stats = service.get_manual_repository_statistics(owner, repo, default_branch)
            self._export_manual_repository_stats(out_dir, manual_stats)

            if needs_commit_activity_fallback:
                stats_with_fallback["commit_activity"] = manual_stats["commit_activity_api_like"]
                commit_activity_rows = service.flatten_commit_activity(stats_with_fallback.get("commit_activity"))
            if needs_code_frequency_fallback:
                stats_with_fallback["code_frequency"] = manual_stats["code_frequency_api_like"]
                code_frequency_rows = service.flatten_code_frequency(stats_with_fallback.get("code_frequency"))

        self.json_exporter.save(
            out_dir / "json" / "official_repository_statistics_with_manual_fallback.json",
            stats_with_fallback,
        )

        contributors_summary, contributors_weekly = service.flatten_repo_stats_contributors(
            stats_with_fallback.get("contributors")
        )
        self.csv_exporter.save(out_dir / "csv" / "repo_stats_contributors_summary.csv", contributors_summary)
        self.csv_exporter.save(out_dir / "csv" / "repo_stats_contributors_weekly.csv", contributors_weekly)
        self.csv_exporter.save(
            out_dir / "csv" / "repo_stats_code_frequency.csv",
            code_frequency_rows,
        )
        self.csv_exporter.save(
            out_dir / "csv" / "repo_stats_commit_activity.csv",
            commit_activity_rows,
        )
        self.csv_exporter.save(
            out_dir / "csv" / "repo_stats_participation.csv",
            service.flatten_participation(stats_with_fallback.get("participation")),
        )
        self.csv_exporter.save(
            out_dir / "csv" / "repo_stats_punch_card.csv",
            service.flatten_punch_card(stats_with_fallback.get("punch_card")),
        )

    def _export_manual_repository_stats(self, out_dir: Path, manual_stats: dict[str, Any]) -> None:
        commit_activity_fields = [
            "week_start",
            "week_timestamp",
            "total",
            "sunday",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
        ]
        code_frequency_fields = [
            "week_start",
            "week_timestamp",
            "additions",
            "deletions",
            "total_changes",
        ]

        self.csv_exporter.save(
            out_dir / "csv" / "repo_stats_commit_activity_manual.csv",
            manual_stats["commit_activity_rows"],
            fieldnames=commit_activity_fields,
        )
        self.csv_exporter.save(
            out_dir / "csv" / "repo_stats_code_frequency_manual.csv",
            manual_stats["code_frequency_rows"],
            fieldnames=code_frequency_fields,
        )
        self.json_exporter.save(
            out_dir / "json" / "repo_stats_commit_activity_manual.json",
            manual_stats["commit_activity_rows"],
        )
        self.json_exporter.save(
            out_dir / "json" / "repo_stats_code_frequency_manual_api_like.json",
            manual_stats["code_frequency_api_like"],
        )

    def _export_derived_user_stats(self, out_dir: Path, user_stats: dict[str, Any]) -> None:
        commits_by_day_rows = [
            {"date": date, "commits": count}
            for date, count in user_stats["commits_by_day"].items()
        ]
        self.csv_exporter.save(out_dir / "csv" / "my_commits_by_day.csv", commits_by_day_rows)

        commits_by_week_rows = [
            {"week": week, "commits": count}
            for week, count in user_stats["commits_by_week"].items()
        ]
        self.csv_exporter.save(out_dir / "csv" / "my_commits_by_week.csv", commits_by_week_rows)
        self.csv_exporter.save(out_dir / "csv" / "my_file_churn.csv", user_stats["top_files_by_changes"])

    def _export_summary(
        self,
        out_dir: Path,
        owner: str,
        repo: str,
        username: str,
        repo_data: dict[str, Any],
        user_stats: dict[str, Any],
    ) -> None:
        summary = {
            "repository": {
                "owner": owner,
                "repo": repo,
                "full_name": repo_data.get("full_name"),
                "url": repo_data.get("html_url"),
                "description": repo_data.get("description"),
                "default_branch": repo_data.get("default_branch"),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "pushed_at": repo_data.get("pushed_at"),
                "stars": repo_data.get("stargazers_count"),
                "forks": repo_data.get("forks_count"),
                "watchers": repo_data.get("watchers_count"),
                "open_issues": repo_data.get("open_issues_count"),
                "size_kb": repo_data.get("size"),
            },
            "user": {"username": username, **user_stats},
            "links_for_report_screenshots": {
                "repo": f"https://github.com/{owner}/{repo}",
                "contributors": f"https://github.com/{owner}/{repo}/graphs/contributors",
                "pulse": f"https://github.com/{owner}/{repo}/pulse",
                "code_frequency": f"https://github.com/{owner}/{repo}/graphs/code-frequency",
                "commits": f"https://github.com/{owner}/{repo}/commits",
                "profile": f"https://github.com/{username}",
            },
        }
        self.json_exporter.save(out_dir / "summary.json", summary)


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser da linha de comando."""

    parser = argparse.ArgumentParser(
        description="Gera estatísticas completas de um usuário em um repositório GitHub."
    )
    parser.add_argument("--owner", help="Dono do repositório. Ex: usuario ou organizacao")
    parser.add_argument("--repo", help="Nome do repositório. Ex: Processamento-de-Imagens-2026v2")
    parser.add_argument("--user", help="Usuário GitHub analisado. Ex: sayydaviid")
    parser.add_argument("--config", help="Caminho para o arquivo JSON de configuração.")
    return parser


def run_from_cli() -> None:
    """Executa a aplicação a partir da linha de comando."""

    logger = configure_logging()
    parser = build_parser()
    args = parser.parse_args()

    try:
        config = ConfigLoader().load(args)
        output_dir = Application(config, logger).run()
        print("\n[OK] Estatísticas geradas com sucesso.")
        print(f"Pasta de saída: {output_dir.resolve()}")
        print("\nArquivos principais:")
        print(f"- {output_dir / 'summary.md'}")
        print(f"- {output_dir / 'summary.json'}")
        print(f"- {output_dir / 'csv' / 'my_commits.csv'}")
        print(f"- {output_dir / 'csv' / 'my_commit_files.csv'}")
        print(f"- {output_dir / 'charts'}")
    except KeyboardInterrupt:
        logger.error("Execução interrompida pelo usuário.")
        sys.exit(130)
    except (ConfigurationError, GitHubApiError) as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Erro inesperado: %s", exc)
        sys.exit(1)
